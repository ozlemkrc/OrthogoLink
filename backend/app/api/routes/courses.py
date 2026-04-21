"""
Course management API routes (Admin-side).
Includes CRUD, search, filtering, and dashboard statistics.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from typing import Optional
from app.core.database import get_db
from app.core.security import require_admin
from app.models.course import Course, CourseSection, ComparisonResult, User
from app.models.schemas import CourseCreate, CourseUpdate, CourseOut, CourseListOut
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Create a new course, generate embeddings, and add to FAISS index."""
    try:
        course = await course_service.create_course(db, data)
        course = await course_service.get_course_by_id(db, course.id)
        return course
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[CourseListOut])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by code, name, or department"),
    department: Optional[str] = Query(None, description="Filter by department"),
    university: Optional[str] = Query(None, description="Filter by university"),
):
    """List all stored courses with optional search and filtering."""
    courses = await course_service.get_all_courses(
        db,
        search=search,
        department=department,
        university=university,
    )
    return courses


@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db)):
    """Get list of all unique departments in the database."""
    result = await db.execute(
        select(distinct(Course.department)).where(Course.department.isnot(None)).order_by(Course.department)
    )
    departments = [row[0] for row in result.all() if row[0]]
    return {"departments": departments}


@router.get("/universities")
async def list_universities(db: AsyncSession = Depends(get_db)):
    """Get list of all unique universities in the database."""
    result = await db.execute(
        select(distinct(Course.university)).where(Course.university.isnot(None)).order_by(Course.university)
    )
    universities = [row[0] for row in result.all() if row[0]]
    return {"universities": universities}


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    course_count = await db.scalar(select(func.count()).select_from(Course)) or 0
    section_count = await db.scalar(select(func.count()).select_from(CourseSection)) or 0
    comparison_count = await db.scalar(select(func.count()).select_from(ComparisonResult)) or 0

    # Department distribution
    dept_result = await db.execute(
        select(Course.department, func.count(Course.id))
        .where(Course.department.isnot(None))
        .group_by(Course.department)
        .order_by(func.count(Course.id).desc())
    )
    dept_distribution = [{"department": row[0], "count": row[1]} for row in dept_result.all()]

    # Recent comparisons
    recent_result = await db.execute(
        select(ComparisonResult)
        .order_by(ComparisonResult.created_at.desc())
        .limit(5)
    )
    recent_comparisons = [
        {
            "id": c.id,
            "input_preview": c.input_text_preview[:100] if c.input_text_preview else "",
            "overall_similarity": c.overall_similarity,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in recent_result.scalars().all()
    ]

    # Average similarity across all comparisons
    avg_sim = await db.scalar(
        select(func.avg(ComparisonResult.overall_similarity))
    )

    from app.services.embedding_service import embedding_service
    index_size = embedding_service.index.ntotal if embedding_service.index else 0

    return {
        "course_count": course_count,
        "section_count": section_count,
        "comparison_count": comparison_count,
        "index_vectors": index_size,
        "average_similarity": round(avg_sim, 4) if avg_sim else 0,
        "department_distribution": dept_distribution,
        "recent_comparisons": recent_comparisons,
    }


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single course with its sections."""
    course = await course_service.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Update an existing course. Re-generates embeddings if description changes."""
    course = await course_service.update_course(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Delete a course and rebuild FAISS index."""
    deleted = await course_service.delete_course(db, course_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Course not found")
    await course_service.rebuild_faiss_index(db)


@router.post("/rebuild-index", status_code=status.HTTP_200_OK)
async def rebuild_index(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Manually rebuild the FAISS index from stored embeddings."""
    await course_service.rebuild_faiss_index(db)
    return {"message": "FAISS index rebuilt successfully"}
