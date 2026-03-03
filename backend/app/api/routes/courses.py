"""
Course management API routes (Admin-side).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.schemas import CourseCreate, CourseOut, CourseListOut
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(data: CourseCreate, db: AsyncSession = Depends(get_db)):
    """Create a new course, generate embeddings, and add to FAISS index."""
    try:
        course = await course_service.create_course(db, data)
        # Reload with sections
        course = await course_service.get_course_by_id(db, course.id)
        return course
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[CourseListOut])
async def list_courses(db: AsyncSession = Depends(get_db)):
    """List all stored courses."""
    courses = await course_service.get_all_courses(db)
    return courses


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single course with its sections."""
    course = await course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a course and rebuild FAISS index."""
    deleted = await course_service.delete_course(db, course_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Course not found")
    # Rebuild FAISS index after deletion
    await course_service.rebuild_faiss_index(db)


@router.post("/rebuild-index", status_code=status.HTTP_200_OK)
async def rebuild_index(db: AsyncSession = Depends(get_db)):
    """Manually rebuild the FAISS index from stored embeddings."""
    await course_service.rebuild_faiss_index(db)
    return {"message": "FAISS index rebuilt successfully"}
