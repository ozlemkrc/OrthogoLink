"""
Course service: CRUD operations and embedding generation for stored courses.
"""
import numpy as np
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.course import Course, CourseSection
from app.models.schemas import CourseCreate
from app.services.embedding_service import embedding_service
from app.services.pdf_service import split_into_sections

logger = logging.getLogger(__name__)


async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    """Create a course, split its description, generate embeddings, and index them."""
    # Create the course record
    course = Course(
        code=data.code,
        name=data.name,
        department=data.department,
        credits=data.credits,
        description=data.description,
    )
    db.add(course)
    await db.flush()  # Get the course.id

    # Split the description into sections
    sections = split_into_sections(data.description)
    texts = [f"{s['heading']}: {s['content']}" for s in sections]

    # Generate embeddings
    embeddings = embedding_service.encode(texts)

    # Create section records with serialized embeddings
    section_records = []
    metadata_list = []
    for i, section in enumerate(sections):
        sec = CourseSection(
            course_id=course.id,
            heading=section["heading"],
            content=section["content"],
            embedding=embeddings[i].tobytes(),
        )
        db.add(sec)
        section_records.append(sec)
        metadata_list.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_name": course.name,
            "section_heading": section["heading"],
        })

    # Add to FAISS index
    embedding_service.add_to_index(embeddings, metadata_list)
    embedding_service.save_index()

    await db.flush()
    logger.info(f"Course {course.code} created with {len(sections)} sections")
    return course


async def get_all_courses(db: AsyncSession) -> list[Course]:
    """Retrieve all courses."""
    result = await db.execute(
        select(Course).options(selectinload(Course.sections)).order_by(Course.code)
    )
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
                "section_heading": sec.heading,
            })

    if embeddings:
        emb_array = np.vstack(embeddings)
        embedding_service.build_index(emb_array, metadata)
        embedding_service.save_index()
        logger.info(f"FAISS index rebuilt with {len(embeddings)} vectors")
