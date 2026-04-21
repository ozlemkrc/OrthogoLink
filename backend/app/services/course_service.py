"""
Course service: CRUD operations, search, and embedding generation for stored courses.
"""
import numpy as np
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.models.course import Course, CourseSection
from app.models.schemas import CourseCreate, CourseUpdate
from app.services.embedding_service import embedding_service
from app.services.pdf_service import split_into_sections

logger = logging.getLogger(__name__)


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

    metadata_list = []
    for i, section in enumerate(sections):
        sec = CourseSection(
            course_id=course.id,
            heading=section["heading"],
            content=section["content"],
            embedding=embeddings[i].tobytes(),
        )
        db.add(sec)
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

    embedding_service.add_to_index(embeddings, metadata_list)
    embedding_service.save_index()

    await db.flush()
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

        for i, section in enumerate(sections):
            sec = CourseSection(
                course_id=course.id,
                heading=section["heading"],
                content=section["content"],
                embedding=embeddings[i].tobytes(),
            )
            db.add(sec)

        await db.flush()
        # Rebuild FAISS index to reflect changes
        await rebuild_faiss_index(db)

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


async def rebuild_faiss_index(db: AsyncSession):
    """Rebuild the entire FAISS index from stored course section embeddings."""
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
