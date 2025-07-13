from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Mapping, Any
from langchain_community.document_loaders import PyPDFLoader
import requests
from dotenv import load_dotenv
load_dotenv()
import os
import json
from pathlib import Path
from app.api.auth import verify_token
import re


router = APIRouter()

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.5-flash:generateContent"


class genereate_resume_model(BaseModel):
    resume_type : str
    resume_text : str
    job_description : str

class ResumeAnalysisRequest(BaseModel):
    job_description: str


@router.post("/compare-resume-jd")
async def compare_resume_jd(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    request: Request = None
):
    # Verify token
    verify_token(request)
    
    # Parse job description if it's JSON string
    try:
        if job_description.startswith('{') or job_description.startswith('['):
            job_description = json.loads(job_description)
            if isinstance(job_description, dict):
                job_description = job_description.get('job_description', str(job_description))
            elif isinstance(job_description, list):
                job_description = ' '.join(job_description)
    except json.JSONDecodeError:
        # If not JSON, use as is
        pass


    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension != '.pdf':
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported for resume analysis"
        )

    file_location = f"temp_resumes/{file.filename}"
    os.makedirs("temp_resumes", exist_ok=True)
    
    try:
        # Save the uploaded file
        with open(file_location, "wb") as f:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file uploaded")
            f.write(content)

        # Extract text from PDF
        try:
            loader = PyPDFLoader(file_location)
            documents = loader.load()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error loading PDF: {str(e)}"
            )

        if not documents:
            raise HTTPException(status_code=400, detail="No content could be extracted from the resume")

        # Extract text from all pages
        resume_text = ""
        for doc in documents:
            resume_text += doc.page_content + "\n"
        # Prepare analysis prompt

        analysis_prompt = f"""
            You are a world-class resume analysis and career optimization expert.

            Take your time to thoroughly analyze the candidate's resume and compare it with the provided job description.

            Provide a complete and accurate analysis including scoring, strengths and weaknesses. Your response must be detailed and fully aligned with job expectations — do not skip or shorten any part of the analysis.

            ---

            ### Resume Analysis Requirements:

            1. **Resume Score** (out of 100) — evaluate structure, clarity, formatting, grammar, and overall presentation.
            2. **Job Match Score** (out of 100) — evaluate how well the resume aligns with the job description.
            3. **Top 3–5 Strengths** — list strong areas relevant to the job.
            4. **Top 3–5 Areas for Improvement** — specific, actionable areas where the resume can improve.
            5. **3–5 Actionable Recommendations** — changes to improve matching, structure, or clarity.
            6. **Missing Keywords** — keywords from the JD not found in the resume.
            7. **Recommended Keywords to Add** — job-specific keywords that should be added.
            ---

            ### Respond in this exact JSON format:
            {{
            "resumeScore": number,
            "jobMatchScore": number,
            "strengths": ["..."],
            "improvements": ["..."],
            "recommendations": ["..."],
            "missingKeywords": ["..."],
            "recommendedKeywords": ["..."],
            }}

            ---

            ### Candidate Resume:
            \"\"\"{resume_text}\"\"\"

            ---

            ### Job Description:
            \"\"\"{job_description}\"\"\"
            """

       
        # Call Gemini API
        headers = {
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json"
        }

        # Gemini expects the prompt in the 'contents' field
        json_body = {
            "contents": [
                {"parts": [{"text": analysis_prompt}]}
            ]
        }

        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers=headers,
            json=json_body,
            timeout=60,
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            try:
                analysis_result = ai_response["candidates"][0]["content"]["parts"][0]["text"]
                # Remove markdown code block formatting if present
                cleaned_result = re.sub(r"^```(json)?|```$", "", analysis_result, flags=re.IGNORECASE).strip()
                return {"analysis": cleaned_result, "resume_text": resume_text, "job_description": job_description}
            except Exception:
                return {"error": "Unexpected Gemini API response format", "raw": ai_response}
        else:
            raise HTTPException(status_code=500, detail=f"Error from AI service: {response.text}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing analysis: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(file_location):
            os.remove(file_location)


@router.post("/generate-resume")
async def generate_resume(request : Request,req : genereate_resume_model):

    # Verify token
    verify_token(request)
    # print(req, "====req")
    resume_prompt = ""
    if req.resume_type == "jd_resume":
        resume_prompt = f"""
        You are a world-class resume builder used by platforms like Rezi and Kickresume.

        Your task is to generate a **clean, ATS-optimized HTML resume** tailored to the job description, while preserving the original structure of the candidate's resume.

        ---

        📌 **Formatting Instructions**:
        - Use semantic HTML-like tags:
        - <h2> for main sections: Contact Information, Professional Summary, Work Experience, Skills, Education, Certifications.
        - <h3> for job titles, companies, degrees, institutions.
        - <ul><li> for bullet points like achievements and skills.
        - Return the final HTML in **a single escaped line inside JSON** (machine-readable and PDF-ready).

        ---

        📄 **Content Rules**:
        1. Use and keep the candidate's existing information.
        2. Tailor the resume to the job description using **relevant keywords** in the summary, skills, and experience.
        3. You may infer tools, skills, and technologies **if they are strongly suggested by the job description**.
        4. DO NOT fabricate jobs or fake experience.
        5. Maintain clean and consistent formatting without tables, columns, or images.
        6. Optimize for ATS systems and human readability.

        ---

        ✅ **Output Format**:
        {{
        "aiGeneratedResume": "<div>...escaped single-line HTML resume...</div>"
        }}

        DO NOT include markdown, explanations, or extra formatting.  
        Only return valid JSON.

        ---

        ### Candidate's Resume:
        \"\"\"{req.resume_text}\"\"\"

        ### Job Description:
        \"\"\"{req.job_description}\"\"\"
        """

    else:
       resume_prompt = f"""
        You are an elite resume formatting and grammar expert used by resume apps like Novoresume and Zety.

        Your task is to enhance the candidate’s resume by improving formatting, structure, clarity, and flow — **without changing or fabricating content**.

        ---

        📌 **Formatting Instructions**:
        - Format in HTML using:
        - <h2> for sections (Summary, Skills, Work Experience, Education, Certifications).
        - <h3> for job titles, companies, degrees, etc.
        - <ul><li> for achievements and lists.
        - Output should be a **single-line escaped HTML string inside valid JSON**.

        ---

        📄 **Content Rules**:
        1. DO NOT add fake experiences or infer technologies.
        2. DO NOT alter the job roles or company names.
        3. ONLY correct grammar, tighten sentence structure, format cleanly, and enhance clarity.
        4. Ensure no section is left incomplete.
        5. Optimize spacing, bullet alignment, and tag hierarchy.

        ---

        ✅ **Output Format**:
        {{
        "aiGeneratedResume": "<div>...clean, enhanced single-line HTML resume...</div>"
        }}

        Do not return markdown, explanations, or newlines.  
        Only valid JSON.

        ---

        ### Original Resume:
        \"\"\"{req.resume_text}\"\"\"
        """
    
    try:
        headers = {
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        }
        json_body = {
            "contents": [
                {"parts": [{"text": resume_prompt}]}
            ]
        }
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers=headers,
            json=json_body,
            timeout=60,
        )

        if response.status_code == 200:
            ai_response = response.json()
            try:
                result = ai_response["candidates"][0]["content"]["parts"][0]["text"]
                cleaned_result = result.strip()
                # Remove triple backticks if present
                cleaned_result = re.sub(r"^```(json)?|```$", "", cleaned_result, flags=re.IGNORECASE).strip()
                parsed_result = json.loads(cleaned_result)
                return parsed_result
            except json.JSONDecodeError:
                return {"error": "Failed to parse AI response as JSON", "raw": result}
            except Exception:
                return {"error": "Unexpected Gemini API response format", "raw": ai_response}
        else:
            raise HTTPException(status_code=500, detail=f"Error from resume generation service: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")

