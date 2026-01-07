"""Resume analysis API routes."""
from fastapi import APIRouter, UploadFile, File, Form, Depends
from app.dependencies import get_current_user
from app.services.resume_service import resume_service
from app.services.pdf_service import pdf_service
from app.models.schemas import GenerateResumeRequest, GeneratePDFRequest
from app.decorators import handle_exceptions
import os
import json

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/compare-resume-jd")
@handle_exceptions
async def compare_resume_jd(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Compare resume with job description and provide analysis.
    
    Args:
        file: Resume PDF file
        job_description: Job description text
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Analysis result with scores and recommendations
    """
    # Parse job description if it's JSON string
    try:
        if job_description.startswith('{') or job_description.startswith('['):
            job_description = json.loads(job_description)
            if isinstance(job_description, dict):
                job_description = job_description.get('job_description', str(job_description))
            elif isinstance(job_description, list):
                job_description = ' '.join(job_description)
    except json.JSONDecodeError:
        pass
    
    # Validate file
    if not file.filename:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension != 'pdf':
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported for resume analysis"
        )
    
    # Save file temporarily
    os.makedirs(resume_service.temp_dir, exist_ok=True)
    file_location = f"{resume_service.temp_dir}/{file.filename}"
    
    try:
        content = await file.read()
        if not content:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        with open(file_location, "wb") as f:
            f.write(content)
        
        # Extract text and analyze
        user_id = current_user["uid"]
        resume_text = resume_service.extract_resume_text(file_location)
        result = resume_service.analyze_resume(resume_text, job_description, user_id)
        
        return result
    finally:
        # Clean up temporary file
        if os.path.exists(file_location):
            os.remove(file_location)


@router.post("/generate-resume")
@handle_exceptions
async def generate_resume(
    req: GenerateResumeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate/formatted resume JSON from text.
    
    Args:
        req: Generate resume request with resume type, text, and optional JD
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Generated resume JSON structure
    """
    return resume_service.generate_resume(
        resume_type=req.resume_type,
        resume_text=req.resume_text,
        user_id=current_user["uid"],
        job_description=req.job_description
    )


@router.post("/generate-pdf")
@handle_exceptions
async def generate_pdf(
    req: GeneratePDFRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate PDF resume from template and resume data.
    
    Args:
        req: PDF generation request with template_id and resume_data
        current_user: Current user data from token (dependency injection)
        
    Returns:
        PDF file as downloadable response
    """
    pdf_bytes = await pdf_service.generate_pdf(
        template_id=req.template_id,
        resume_data=req.resume_data
    )
    
    filename = f"resume_{req.template_id}_{current_user['uid'][:8]}.pdf"
    return pdf_service.create_pdf_response(pdf_bytes, filename)

