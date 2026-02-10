"""Resume analysis and generation service."""
import os
import json
import re
from pathlib import Path
from fastapi import HTTPException
from langchain_community.document_loaders import PyPDFLoader
import requests
from typing import Optional
from app.config import settings
from app.services.usage_limit_service import usage_limit_service
from app.services.auth_service import auth_service


class ResumeService:
    """Service for resume analysis and generation."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.api_url = settings.gemini_api_url
        self.temp_dir = settings.temp_resumes_dir
    
    def extract_resume_text(self, file_path: str) -> str:
        """
        Extract text from PDF resume.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted resume text
            
        Raises:
            HTTPException: If PDF cannot be loaded or is empty
        """
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error loading PDF: {str(e)}"
            )
        
        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No content could be extracted from the resume"
            )
        
        resume_text = ""
        for doc in documents:
            resume_text += doc.page_content + "\n"
        
        return resume_text
    
    def call_gemini_api(self, prompt: str, timeout: int = 60, api_key: Optional[str] = None) -> str:
        """
        Call Gemini API with prompt.
        
        Args:
            prompt: Input prompt
            timeout: Request timeout in seconds
            api_key: Optional Gemini API key (user's key or settings)
            
        Returns:
            API response text
            
        Raises:
            HTTPException: If API call fails
        """
        key = api_key or self.api_key
        headers = {
            "x-goog-api-key": key,
            "Content-Type": "application/json"
        }
        json_body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        
        response = requests.post(
            f"{self.api_url}/{self.model}:generateContent",
            headers=headers,
            json=json_body,
            timeout=timeout
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Error from AI service: {response.text}"
            )
        
        ai_response = response.json()
        try:
            return ai_response["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            raise HTTPException(
                status_code=500,
                detail="Unexpected Gemini API response format"
            )
    
    def analyze_resume(self, resume_text: str, job_description: str, user_id: str) -> dict:
        """
        Analyze resume against job description.
        
        Args:
            resume_text: Extracted resume text
            job_description: Job description text
            user_id: User ID for usage limits
            
        Returns:
            Analysis result dictionary
        """
        # Check usage limit
        usage_limit_service.check_resume_limit(user_id)
        
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
            {resume_text}

            ---

            ### Job Description:
            {job_description}
            """
        
        user_api_key = auth_service.get_gemini_api_key(user_id)
        analysis_result = self.call_gemini_api(analysis_prompt, timeout=60, api_key=user_api_key)
        cleaned_result = re.sub(r"^```(json)?|```$", "", analysis_result, flags=re.IGNORECASE).strip()
        
        # Increment usage count
        usage_limit_service.increment_resume_count(user_id)
        
        return {
            "analysis": cleaned_result,
            "resume_text": resume_text,
            "job_description": job_description
        }
    
    def generate_resume(self, resume_type: str, resume_text: str, user_id: str, job_description: str = "") -> dict:
        """
        Generate/formatted resume JSON.
        
        Args:
            resume_type: Type of resume generation ("jd_resume" or other)
            resume_text: Original resume text
            user_id: User ID for usage limits
            job_description: Job description (for JD-tailored resumes)
            
        Returns:
            Generated resume JSON structure
            
        Raises:
            HTTPException: If generation fails
        """
        # Check usage limit
        usage_limit_service.check_resume_limit(user_id)
        
        if resume_type == "jd_resume":
            resume_prompt = f"""
        You are a world-class resume builder and ATS optimization engine used by platforms like Rezi, Kickresume, and Novoresume.

        Your task is to extract, normalize, and restructure the candidate’s resume into a **clean, professional, design-agnostic JSON format**, optimized for the given job description.

        You must preserve factual accuracy while improving clarity, impact, and keyword alignment.

        ---

        ## 📄 CONTENT RULES (STRICT)

        1. Extract and use ONLY the candidate’s existing information from the resume.
        2. Tailor the **summary, experience highlights, and skills** to the job description using relevant keywords.
        3. You MAY infer tools, technologies, or skills ONLY if:
        - They are strongly implied by the resume OR
        - Explicitly required by the job description and clearly aligned with the candidate’s background.
        4. DO NOT fabricate:
        - Companies
        - Job titles
        - Employment dates
        - Degrees or certifications
        5. Improve bullet points by:
        - Using strong action verbs
        - Focusing on impact and outcomes
        - Keeping them concise and ATS-friendly
        6. Normalize all dates to **YYYY-MM** format when possible.
        7. Organize skills into clear, categorized groups.
        8. If a field is missing:
        - Use empty string for strings
        - Empty array for lists
        - Empty object for objects
        9. Output must be **pure JSON only**, no markdown, no explanations.

        ---

        ## ✅ OUTPUT FORMAT (STRICT — DO NOT DEVIATE)

        Return ONLY valid JSON in the following structure:

        {{
        "basics": {{
            "full_name": "",
            "title": "",
            "location": {{
            "city": "",
            "region": "",
            "country": ""
            }},
            "contact": {{
            "email": "",
            "phone": "",
            "linkedin": "",
            "github": "",
            "portfolio": ""
            }}
        }},
        "summary": {{
            "headline": "",
            "highlights": ["..."]
        }},
        "experience": [
            {{
            "company": "",
            "role": "",
            "location": "",
            "employment_type": "",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or null",
            "is_current": false,
            "summary": "",
            "highlights": ["..."],
            "tech_stack": ["..."]
            }}
        ],
        "projects": [
            {{
            "name": "",
            "type": "",
            "link": "",
            "description": "",
            "highlights": ["..."],
            "tech_stack": ["..."]
            }}
        ],
        "education": [
            {{
            "institution": "",
            "degree": "",
            "location": "",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM",
            "gpa": "",
            "highlights": ["..."]
            }}
        ],
        "skills": {{
            "categories": [
            {{
                "name": "Frontend",
                "items": ["..."]
            }},
            {{
                "name": "Backend",
                "items": ["..."]
            }},
            {{
                "name": "Database",
                "items": ["..."]
            }},
            {{
                "name": "Cloud & DevOps",
                "items": ["..."]
            }},
            {{
                "name": "Tools & Platforms",
                "items": ["..."]
            }},
            {{
                "name": "Soft Skills",
                "items": ["..."]
            }}
            ]
        }},
        "certifications": ["..."],
        "achievements": ["..."],
        "metadata": {{
            "target_role": "",
            "experience_level": "",
            "resume_version": ""
        }}
        }}

        ---

        ### Candidate Resume:
        {resume_text}

        ---

        ### Job Description:
        {job_description}
    """

        else:
            resume_prompt = f"""
        You are an elite resume formatting and grammar expert used by resume apps like Novoresume and Zety.

        Your task is to extract and structure the candidate's resume data into a clean JSON format, improving clarity and organization — **without changing or fabricating content**.

        ---

        📄 **Content Rules**:
        1. Extract and use ONLY the candidate's existing information from the resume.
        2. DO NOT add fake experiences, infer technologies, or fabricate any information.
        3. DO NOT alter job roles, company names, or any factual information.
        4. ONLY improve grammar, tighten sentence structure, and enhance clarity in descriptions.
        5. Organize skills into appropriate categories (frontend, backend, database, tools, soft_skills).
        6. Extract all available information: name, contact details, experience, projects, education, and skills.
        7. If a field is not available in the resume, use an empty string for strings, empty array for arrays, or empty object for objects.
        8. Ensure all sections are properly structured and complete.

        ---

        ✅ **Output Format** - Return ONLY valid JSON in this exact structure:
        {{
          "name": "Full Name",
          "contact": {{
            "phone": "phone number or empty string",
            "email": "email address or empty string",
            "location": "location or empty string"
          }},
          "summary": "Professional summary (improved grammar and clarity)",
          "experience": [
            {{
              "role": "Job Title",
              "company": "Company Name",
              "location": "Location or empty string",
              "duration": "Duration or empty string",
              "details": ["Achievement 1", "Achievement 2", ...]
            }}
          ],
          "projects": [
            {{
              "title": "Project Title",
              "link": "URL or empty string (optional)",
              "details": ["Description 1", "Description 2", ...]
            }}
          ],
          "education": [
            {{
              "degree": "Degree Name",
              "university": "University Name",
              "duration": "Duration or empty string",
              "cgpa": "CGPA/GPA or empty string"
            }}
          ],
          "skills": {{
            "frontend": ["Skill1", "Skill2", ...],
            "backend": ["Skill1", "Skill2", ...],
            "database": ["Skill1", "Skill2", ...],
            "tools": ["Tool1", "Tool2", ...],
            "soft_skills": ["Skill1", "Skill2", ...]
          }}
        }}

        Do not return markdown, explanations, code blocks, or extra formatting.  
        Only return valid JSON that can be parsed directly.

        ---

        ### Original Resume:
        {resume_text}
        """
        
        user_api_key = auth_service.get_gemini_api_key(user_id)
        result = self.call_gemini_api(resume_prompt, timeout=60, api_key=user_api_key)
        cleaned_result = result.strip()
        cleaned_result = re.sub(r"^```(json)?|```$", "", cleaned_result, flags=re.IGNORECASE).strip()
        
        # Increment usage count
        usage_limit_service.increment_resume_count(user_id)
        
        try:
            return json.loads(cleaned_result)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse AI response as JSON"
            )


# Singleton instance
resume_service = ResumeService()

