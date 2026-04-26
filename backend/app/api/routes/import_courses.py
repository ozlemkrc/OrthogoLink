"""
University course import API routes.
Allows importing courses from Turkish university catalogs.
Supports GTU, ITU, METU, Hacettepe, and IYTE.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.core.database import get_db
from app.core.security import require_admin
from app.services.university_scraper import UNIVERSITY_SCRAPERS
from app.services.course_service import create_course
from app.models.course import Course, User
from app.models.schemas import CourseCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/import", tags=["Import"])


class ImportRequest(BaseModel):
    university: str
    department_codes: Optional[List[str]] = None
    limit_per_department: Optional[int] = None


class ImportFailure(BaseModel):
    label: str
    reason: str


class ImportResponse(BaseModel):
    message: str
    total_fetched: int
    total_imported: int
    total_skipped: int
    total_failed: int
    imported_courses: List[str]
    skipped_courses: List[str] = []
    failed_courses: List[ImportFailure] = []


class UniversityInfo(BaseModel):
    code: str
    name: str
    available: bool


@router.get("/universities", response_model=List[UniversityInfo])
async def list_universities():
    """List all supported universities for import."""
    return [
        {"code": code, "name": scraper.name, "available": True}
        for code, scraper in UNIVERSITY_SCRAPERS.items()
    ]


@router.get("/{university_code}/departments")
async def get_departments(university_code: str):
    """Get list of departments for a specific university."""
    scraper = UNIVERSITY_SCRAPERS.get(university_code.lower())
    if not scraper:
        raise HTTPException(status_code=404, detail=f"University '{university_code}' not found")
    try:
        departments = await scraper.get_departments()
        return {"university": scraper.name, "departments": departments}
    except Exception as e:
        logger.error("Error fetching departments for %s: %s", university_code, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch departments. The university site may be unavailable.")


@router.post("/{university_code}/preview")
async def preview_courses(
    university_code: str,
    department_codes: Optional[List[str]] = None,
    limit: int = 5,
):
    """Preview courses that would be imported from a university."""
    scraper = UNIVERSITY_SCRAPERS.get(university_code.lower())
    if not scraper:
        raise HTTPException(status_code=404, detail=f"University '{university_code}' not found")
    try:
        courses = await scraper.bulk_import(
            department_codes=department_codes,
            limit_per_dept=limit,
        )
        return {
            "university": scraper.name,
            "total_courses": len(courses),
            "courses": courses[:20],
        }
    except Exception as e:
        logger.error("Error previewing courses for %s: %s", university_code, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to preview courses. The university site may be unavailable.")


@router.post("/{university_code}/import", response_model=ImportResponse)
async def import_courses(
    university_code: str,
    db: AsyncSession = Depends(get_db),
    department_codes: Optional[List[str]] = None,
    limit_per_department: Optional[int] = None,
    _admin: User = Depends(require_admin),
):
    """Import courses from a university into the database."""
    scraper = UNIVERSITY_SCRAPERS.get(university_code.lower())
    if not scraper:
        raise HTTPException(status_code=404, detail=f"University '{university_code}' not found")

    logger.info(f"Starting import from {scraper.name}... Departments: {department_codes}")

    try:
        courses_data = await scraper.bulk_import(
            department_codes=department_codes,
            limit_per_dept=limit_per_department,
        )

        if not courses_data:
            raise HTTPException(status_code=404, detail="No courses found")

        imported: List[str] = []
        skipped: List[str] = []
        failed: List[ImportFailure] = []
        seen_in_batch: set[tuple[str, str]] = set()

        for course_data in courses_data:
            # Normalize identity before uniqueness checks: trim + uppercase code,
            # trim university. Prevents duplicate inserts from whitespace drift
            # or mixed-case codes coming out of the scraper.
            raw_code = (course_data.get("code") or "").strip().upper()
            raw_uni = (course_data.get("university") or scraper.name).strip()
            course_data["code"] = raw_code
            course_data["university"] = raw_uni
            identity = (raw_uni, raw_code)
            label = f"{raw_uni}::{raw_code}"

            if not raw_code:
                failed.append(ImportFailure(label=label, reason="Missing course code"))
                continue

            if identity in seen_in_batch:
                logger.info(f"{label} duplicated within fetch batch; skipping")
                skipped.append(label)
                continue
            seen_in_batch.add(identity)

            try:
                course_create = CourseCreate(**course_data)

                result = await db.execute(
                    select(Course).where(
                        Course.code == course_create.code,
                        Course.university == course_create.university,
                    )
                )
                if result.scalar_one_or_none():
                    logger.info(f"Course {label} already exists, skipping")
                    skipped.append(label)
                    continue

                # Use a savepoint so a constraint violation on this row
                # (e.g. duplicate code from another university) only rolls
                # back this one insert, leaving the outer transaction intact.
                async with db.begin_nested():
                    await create_course(db, course_create)
                imported.append(label)
                logger.info(f"Imported: {label}")
            except Exception as e:
                logger.error(f"Failed to import {label}: {e}", exc_info=True)
                failed.append(ImportFailure(label=label, reason=str(e)[:200]))

        await db.commit()

        return ImportResponse(
            message=(
                f"Import from {scraper.name}: "
                f"{len(imported)} imported, {len(skipped)} skipped, {len(failed)} failed "
                f"(fetched {len(courses_data)})"
            ),
            total_fetched=len(courses_data),
            total_imported=len(imported),
            total_skipped=len(skipped),
            total_failed=len(failed),
            imported_courses=imported,
            skipped_courses=skipped,
            failed_courses=failed,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during import from %s: %s", university_code, e, exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Import failed. Check server logs for details.")


# Keep backward compatibility for GTU-specific endpoints
@router.get("/gtu/departments")
async def get_gtu_departments():
    return await get_departments("gtu")


@router.post("/gtu/preview")
async def preview_gtu_courses(
    department_codes: Optional[List[str]] = None,
    limit: int = 5,
):
    return await preview_courses("gtu", department_codes, limit)


@router.post("/gtu/import", response_model=ImportResponse)
async def import_gtu_courses(
    db: AsyncSession = Depends(get_db),
    department_codes: Optional[List[str]] = None,
    limit_per_department: Optional[int] = None,
    admin: User = Depends(require_admin),
):
    return await import_courses(
        "gtu",
        db=db,
        department_codes=department_codes,
        limit_per_department=limit_per_department,
        _admin=admin,
    )
