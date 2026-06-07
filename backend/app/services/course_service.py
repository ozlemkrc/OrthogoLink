"""
Course service: CRUD operations, search, and embedding generation for stored courses.
"""
import numpy as np
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text
from sqlalchemy.orm import selectinload
from app.models.course import Course, CourseSection
from app.models.schemas import CourseCreate, CourseUpdate
from app.services.embedding_service import embedding_service
from app.services.vector_search import to_vector_literal
from app.services.pdf_service import split_into_sections
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _use_faiss() -> bool:
    """True when the legacy in-process FAISS backend is active (single-worker)."""
    return settings.SEARCH_BACKEND == "faiss"


async def _store_section_vectors(db: AsyncSession, pairs: list[tuple]) -> None:
    """Write embedding_vec for each (CourseSection, embedding) pair (pgvector).

    Uses a numeric-only vector literal rather than a bound vector parameter, so it
    is driver-agnostic and carries no injection risk (values come from the model).
    Sections must already be flushed so their ``id`` is populated.
    """
    for sec, emb in pairs:
        literal = to_vector_literal(emb)
        await db.execute(
            text(f"UPDATE course_sections SET embedding_vec = '{literal}'::vector WHERE id = :id"),
            {"id": sec.id},
        )


async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    """Create a course, split its description, generate embeddings, and index them."""
    course = Course(
        code=data.code,
        name=data.name,
        university=data.university,
        faculty=data.faculty,
        department=data.department,
        credits=data.credits,
        description=data.description,
        source_url=data.source_url,
        source_fetched_at=data.source_fetched_at,
        parser_name=data.parser_name,
        parser_version=data.parser_version,
    )
    db.add(course)
    await db.flush()

    sections = split_into_sections(data.description)
    texts = [f"{s['heading']}: {s['content']}" for s in sections]
    embeddings = embedding_service.encode(texts)

    section_pairs: list[tuple] = []
    metadata_list = []
    for i, section in enumerate(sections):
        sec = CourseSection(
            course_id=course.id,
            heading=section["heading"],
            content=section["content"],
            embedding=embeddings[i].tobytes(),
        )
        db.add(sec)
        section_pairs.append((sec, embeddings[i]))
        metadata_list.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "university": course.university or "",
            "faculty": course.faculty or "",
            "section_heading": section["heading"],
            "section_content": section["content"],
            "department": data.department or "",
        })

    await db.flush()  # assign section ids before writing vectors

    if _use_faiss():
        embedding_service.add_to_index(embeddings, metadata_list)
        embedding_service.save_index()
    else:
        await _store_section_vectors(db, section_pairs)

    logger.info(f"Course {course.code} created with {len(sections)} sections")
    return course


async def update_course(db: AsyncSession, course_id: int, data: CourseUpdate) -> Optional[Course]:
    """Update a course. If description changes, regenerate embeddings."""
    course = await get_course_by_id(db, course_id)
    if not course:
        return None

    description_changed = False
    if data.name is not None:
        course.name = data.name
    if data.university is not None:
        course.university = data.university
    if data.faculty is not None:
        course.faculty = data.faculty
    if data.department is not None:
        course.department = data.department
    if data.credits is not None:
        course.credits = data.credits
    if data.description is not None and data.description != course.description:
        course.description = data.description
        description_changed = True

    if description_changed:
        # Delete old sections
        for section in course.sections:
            await db.delete(section)
        await db.flush()

        # Re-create sections with new embeddings
        sections = split_into_sections(data.description)
        texts = [f"{s['heading']}: {s['content']}" for s in sections]
        embeddings = embedding_service.encode(texts)

        section_pairs: list[tuple] = []
        for i, section in enumerate(sections):
            sec = CourseSection(
                course_id=course.id,
                heading=section["heading"],
                content=section["content"],
                embedding=embeddings[i].tobytes(),
            )
            db.add(sec)
            section_pairs.append((sec, embeddings[i]))

        await db.flush()
        if _use_faiss():
            # Rebuild FAISS index to reflect changes (no in-place delete in FAISS).
            await rebuild_faiss_index(db)
        else:
            # pgvector: deleted sections are gone via cascade; just write new vectors.
            await _store_section_vectors(db, section_pairs)

    await db.flush()
    return await get_course_by_id(db, course_id)


async def get_all_courses(
    db: AsyncSession,
    search: Optional[str] = None,
    department: Optional[str] = None,
    university: Optional[str] = None,
) -> list[Course]:
    """Retrieve all courses with optional search and department filter."""
    query = select(Course).options(selectinload(Course.sections)).order_by(Course.code)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Course.code.ilike(search_term),
                Course.name.ilike(search_term),
                Course.university.ilike(search_term),
                Course.faculty.ilike(search_term),
                Course.department.ilike(search_term),
            )
        )

    if department:
        query = query.where(Course.department == department)

    if university:
        query = query.where(Course.university == university)

    result = await db.execute(query)
    return result.scalars().all()


async def get_course_by_id(db: AsyncSession, course_id: int) -> Course | None:
    """Retrieve a single course by ID."""
    result = await db.execute(
        select(Course).options(selectinload(Course.sections)).where(Course.id == course_id)
    )
    return result.scalar_one_or_none()


async def delete_course(db: AsyncSession, course_id: int) -> bool:
    """Delete a course. Note: requires FAISS index rebuild."""
    course = await get_course_by_id(db, course_id)
    if not course:
        return False
    await db.delete(course)
    await db.flush()
    return True


async def reembed_all_sections(db: AsyncSession):
    """
    Re-encode every course section from its stored text using the current model
    and update both the binary embedding and the pgvector column (or the FAISS
    index, depending on backend). Called when the embedding model has changed.
    """
    result = await db.execute(
        select(CourseSection).options(selectinload(CourseSection.course))
    )
    sections = result.scalars().all()

    if not sections:
        if _use_faiss():
            embedding_service.index = None
            embedding_service.id_map = []
            embedding_service.save_index()
        logger.info("No sections to re-embed")
        return

    texts = [
        f"{sec.heading}: {sec.content}" if sec.content else (sec.heading or "")
        for sec in sections
    ]
    logger.info(f"Re-embedding {len(texts)} sections with model '{settings.MODEL_NAME}'...")
    emb_array = embedding_service.encode(texts)

    metadata = []
    for i, sec in enumerate(sections):
        sec.embedding = emb_array[i].tobytes()
        metadata.append({
            "course_id": sec.course.id,
            "course_code": sec.course.code,
            "course_name": sec.course.name,
            "university": sec.course.university or "",
            "faculty": sec.course.faculty or "",
            "section_heading": sec.heading,
            "section_content": sec.content or "",
            "department": sec.course.department or "",
        })

    await db.flush()
    if _use_faiss():
        embedding_service.build_index(emb_array, metadata)
        embedding_service.save_index()
    else:
        await _store_section_vectors(db, [(sections[i], emb_array[i]) for i in range(len(sections))])
    logger.info(f"Re-embedding complete: {len(sections)} sections indexed")


async def ensure_pgvector_ready(db: AsyncSession):
    """Startup hook for the pgvector backend.

    Mirrors the FAISS model-marker check: if the stored vectors were built with a
    different embedding model than the one now configured, re-embed everything.
    Then record the current model name. Safe to call when no courses exist yet.
    """
    res = await db.execute(text("SELECT model_name FROM embedding_meta WHERE id = 1"))
    row = res.first()
    stored = row[0] if row else None
    if stored is not None and stored != settings.MODEL_NAME:
        logger.warning(
            "Embedding model changed ('%s' -> '%s'); re-embedding all sections for pgvector",
            stored, settings.MODEL_NAME,
        )
        await reembed_all_sections(db)
    await db.execute(
        text(
            "INSERT INTO embedding_meta (id, model_name) VALUES (1, :m) "
            "ON CONFLICT (id) DO UPDATE SET model_name = :m"
        ),
        {"m": settings.MODEL_NAME},
    )
    await db.commit()


async def index_vector_count(db: AsyncSession) -> int:
    """Number of searchable section vectors, for health/stats — backend-aware."""
    if _use_faiss():
        return embedding_service.index.ntotal if embedding_service.index else 0
    return await db.scalar(
        select(func.count()).select_from(CourseSection).where(CourseSection.embedding_vec.isnot(None))
    ) or 0


async def rebuild_faiss_index(db: AsyncSession):
    """Rebuild the entire FAISS index from stored course section embeddings.

    No-op under the pgvector backend, where search reads the shared DB directly and
    there is no in-process index to rebuild (delete/update already mutate the DB).
    """
    if not _use_faiss():
        return
    result = await db.execute(
        select(CourseSection).options(selectinload(CourseSection.course))
    )
    sections = result.scalars().all()

    if not sections:
        embedding_service.index = None
        embedding_service.id_map = []
        embedding_service.save_index()
        logger.info("FAISS index cleared (no sections)")
        return

    embeddings = []
    metadata = []
    for sec in sections:
        if sec.embedding:
            emb = np.frombuffer(sec.embedding, dtype=np.float32)
            embeddings.append(emb)
            metadata.append({
                "course_id": sec.course.id,
                "course_code": sec.course.code,
                "course_name": sec.course.name,
                "university": sec.course.university or "",
                "faculty": sec.course.faculty or "",
                "section_heading": sec.heading,
                "section_content": sec.content or "",
                "department": sec.course.department or "",
            })

    if embeddings:
        emb_array = np.vstack(embeddings)
        embedding_service.build_index(emb_array, metadata)
        embedding_service.save_index()
        logger.info(f"FAISS index rebuilt with {len(embeddings)} vectors")
