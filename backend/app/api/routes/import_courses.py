"""
University course import API routes.
Allows importing courses from Turkish university catalogs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.core.database import get_db
from app.services.university_scraper import gtu_scraper
from app.services.course_service import create_course
from app.models.schemas import CourseCreate, CourseOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/import", tags=["Import"])


class ImportRequest(BaseModel):
    """Request schema for importing courses."""
    university: str  # "gtu", "itu", "metu", etc.
    department_codes: Optional[List[str]] = None
    limit_per_department: Optional[int] = None


class ImportResponse(BaseModel):
    """Response schema for import operations."""
    message: str
    total_imported: int
    total_failed: int
    imported_courses: List[str]  # List of course codes


class UniversityInfo(BaseModel):
    """Information about supported universities."""
    code: str
    name: str
    available: bool


@router.get("/universities", response_model=List[UniversityInfo])
async def list_universities():
    """List all supported universities for import."""
    return [
        {
            "code": "gtu",
            "name": "Gebze Teknik Üniversitesi",
            "available": True,
        },
        {
            "code": "itu",
            "name": "İstanbul Teknik Üniversitesi",
            "available": False,
        },
        {
            "code": "metu",
            "name": "Orta Doğu Teknik Üniversitesi",
            "available": False,
        },
        {
            "code": "iyte",
            "name": "İzmir Yüksek Teknoloji Enstitüsü",
            "available": False,
        },
        {
            "code": "hacettepe",
            "name": "Hacettepe Üniversitesi",
            "available": False,
        },
    ]


@router.get("/gtu/departments")
async def get_gtu_departments():
    """Get list of GTU departments."""
    try:
        departments = await gtu_scraper.get_departments()
        return {"departments": departments}
    except Exception as e:
        logger.error(f"Error fetching GTU departments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gtu/preview")
async def preview_gtu_courses(
    department_codes: Optional[List[str]] = None,
    limit: int = 5
):
    """
    Preview courses that would be imported from GTU without actually importing them.
    Useful for checking data quality before bulk import.
    """
    try:
        logger.info(f"Previewing GTU courses for departments: {department_codes}")
        courses = await gtu_scraper.bulk_import(
            department_codes=department_codes,
            limit_per_dept=limit
        )
        return {
            "total_courses": len(courses),
            "courses": courses[:10]  # Return first 10 for preview
        }
    except Exception as e:
        logger.error(f"Error previewing GTU courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gtu/import", response_model=ImportResponse)
async def import_gtu_courses(
    db: AsyncSession = Depends(get_db),
    department_codes: Optional[List[str]] = None,
    limit_per_department: Optional[int] = None,
):
    """
    Import courses from GTU course catalog into the database.
    This will scrape the GTU website and add courses to your system.
    """
    logger.info(f"Starting GTU course import... Departments: {department_codes}")
    
    try:
        # Scrape courses from GTU
        courses_data = await gtu_scraper.bulk_import(
            department_codes=department_codes,
            limit_per_dept=limit_per_department
        )
        
        if not courses_data:
            raise HTTPException(
                status_code=404,
                detail="No courses found for the specified departments"
            )
        
        # Import courses into database
        imported = []
        failed = []
        
        for course_data in courses_data:
            try:
                course_create = CourseCreate(**course_data)
                # Check if course already exists
                from sqlalchemy import select
                from app.models.course import Course
                
                result = await db.execute(
                    select(Course).where(Course.code == course_create.code)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Course {course_create.code} already exists, skipping")
                    failed.append(course_create.code)
                    continue
                
                # Create course with embeddings
                await create_course(db, course_create)
                imported.append(course_create.code)
                logger.info(f"Successfully imported course: {course_create.code}")
                
            except Exception as e:
                logger.error(f"Failed to import course {course_data.get('code')}: {str(e)}")
                failed.append(course_data.get('code', 'unknown'))
                continue
        
        # Commit all changes
        await db.commit()
        
        return ImportResponse(
            message=f"Import complete: {len(imported)} courses imported, {len(failed)} failed",
            total_imported=len(imported),
            total_failed=len(failed),
            imported_courses=imported
        )
        
    except Exception as e:
        logger.error(f"Error during GTU import: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generic", response_model=ImportResponse)
async def import_from_university(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generic endpoint for importing courses from any supported university.
    Currently only supports GTU.
    """
    if request.university.lower() == "gtu":
        return await import_gtu_courses(
            db=db,
            department_codes=request.department_codes,
            limit_per_department=request.limit_per_department
        )
    else:
        raise HTTPException(
            status_code=501,
            detail=f"University '{request.university}' is not yet supported. Currently available: GTU"
        )
