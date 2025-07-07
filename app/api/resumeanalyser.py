from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Mapping, Any
from langchain_community.document_loaders import PyPDFLoader
import requests
import os
import json
from pathlib import Path
from app.api.auth import verify_token
import re

router = APIRouter()

# OpenRouter configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL_NAME = "mistralai/mistral-7b-instruct:free"


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

       
        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        messages = [
            {
                "role": "system",
                "content": "You are a professional resume analyzer and career advisor. Provide detailed, actionable feedback for resume-job description matching."
            },
            {"role": "user", "content": analysis_prompt}
        ]

        json_data = {
            "model": OPENROUTER_MODEL_NAME,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.3,
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=json_data,
            timeout=60,
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            analysis_result = ai_response['choices'][0]['message']['content']
            return {"analysis": analysis_result, "resume_text" : resume_text, "job_description" : job_description}
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
        You are a world-class resume builder and career optimization expert.

        Your task is to generate a clean, complete HTML resume that is **tailored to the job description** while preserving existing experience and structure from the candidate's resume.

        ---

        ### Key Instructions:

        1. Use all relevant information from the candidate's resume.
        2. You MAY add inferred skills, achievements, tools, or keywords **only if they are strongly suggested by the job description.**
        3. Highlight or enhance areas that improve alignment with the JD — especially in the summary, skills, and experience sections.
        4. Do NOT create fake job history or false employers.
        5. Include all standard sections: Contact Info, Summary, Skills, Experience, Projects, Education, Certifications.
        6. Take your time to produce a complete and professional resume — no shortcuts or missing content.
        7. Output must be a **single-line escaped HTML string**, clean, ATS-friendly, and directly usable in frontend or PDF.
        8. Return only valid JSON in this format:

        {{
        "aiGeneratedResume": "<div>...tailored HTML resume...</div>"
        }}
        Only return a valid JSON object.
        
            Do NOT wrap the response in triple backticks (```) or markdown formatting.
            Do NOT include explanations, commentary, or extra text.
            Return only clean JSON that can be directly parsed using JSON.parse().


        ---

        ### Candidate's Resume:
        \"\"\"{req.resume_text}\"\"\"

        ---

        ### Job Description:
        \"\"\"{req.job_description}\"\"\"
        """

    else:
        resume_prompt = f"""
        You are a professional resume editor and formatting expert.

        Your task is to **enhance the candidate's existing resume** for clarity, formatting, completeness, and presentation — **without adding any fake or new information**.

        ---

        ### Key Instructions:

        1. Do **not fabricate** or infer new skills, experience, or technologies that aren't clearly in the original resume.
        2. Keep all original content intact — improve only grammar, structure, formatting, and flow.
        3. Format the output as a clean, modern resume in semantic HTML.
        4. Take your time and ensure the output includes **all major resume sections** with no incomplete data.
        5. Your output should be a **single-line escaped HTML string**, ready for rendering or PDF export.
        6. Do NOT include markdown, newlines (`\n`), tabs (`\t`), or backticks (`` ` ``).
        7. Return only valid JSON in this format:

        {{
        "aiGeneratedResume": "<div>...clean, enhanced HTML resume...</div>"
        }}
        Only return a valid JSON object. Do not include explanations, markdown, or commentary.

        ---

        ### Original Resume:
        \"\"\"{req.resume_text}\"\"\"
        """
    
    try:
        headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        }
        json_data = {
            "model": OPENROUTER_MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": resume_prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.3,
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=json_data,
            timeout=60,
        )

        if response.status_code == 200:
            ai_response = response.json()
            result = ai_response['choices'][0]['message']['content']
            try:
                cleaned_result = result.strip()
                # Remove triple backticks if present
                cleaned_result = re.sub(r"^```(json)?|```$", "", cleaned_result, flags=re.IGNORECASE).strip()
                parsed_result = json.loads(cleaned_result)
                return parsed_result
            except json.JSONDecodeError:
                return {"error": "Failed to parse AI response as JSON", "raw": result}
        else:
            raise HTTPException(status_code=500, detail=f"Error from resume generation service: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating resume: {str(e)}")

