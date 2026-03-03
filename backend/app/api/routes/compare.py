"""
Comparison API routes (User-side).
Handles text input and PDF upload for syllabus comparison.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import CompareTextRequest, ComparisonResponse
from app.services.comparison_service import compare_syllabus
from app.services.pdf_service import extract_text_from_pdf

router = APIRouter(prefix="/compare", tags=["Comparison"])


@router.post("/text", response_model=ComparisonResponse)
async def compare_text(request: CompareTextRequest):
    """
    Compare pasted syllabus text against stored courses.
    """
    if len(request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Input text is too short. Please provide a meaningful syllabus text."
        )
    try:
        result = compare_syllabus(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/pdf", response_model=ComparisonResponse)
async def compare_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF syllabus and compare against stored courses.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        contents = await file.read()
        text = extract_text_from_pdf(contents)

        if len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from the PDF."
            )

        result = compare_syllabus(text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
