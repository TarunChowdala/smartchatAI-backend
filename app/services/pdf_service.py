"""PDF generation service for resume builder."""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from fastapi import HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
import asyncio
from playwright.async_api import async_playwright


class PDFService:
    """Service for generating PDFs from resume templates."""
    
    def __init__(self):
        # Get templates directory
        self.templates_dir = Path(__file__).parent.parent / "templates" / "resume"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Valid template IDs
        self.valid_templates = ["modern", "minimal", "tech", "classic"]
        
        # Track if browsers are installed
        self._browsers_installed = False
    
    def _validate_template_id(self, template_id: str):
        """Validate template ID."""
        if template_id not in self.valid_templates:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid template_id. Must be one of: {', '.join(self.valid_templates)}"
            )
    
    def _render_html(self, template_id: str, resume_data: Dict[str, Any]) -> str:
        """
        Render HTML from template and resume data.
        
        Args:
            template_id: Template identifier (modern, minimal, tech)
            resume_data: Resume data dictionary
            
        Returns:
            Rendered HTML string
        """
        self._validate_template_id(template_id)
        
        try:
            template_path = self.templates_dir / f"{template_id}.html"
            if not template_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"Template file not found: {template_path}"
                )
            
            template = self.jinja_env.get_template(f"{template_id}.html")
            # Ensure we're passing the data correctly - unpack the resume_data dict
            html = template.render(**resume_data)
            return html
        except HTTPException:
            raise
        except TypeError as e:
            # Handle case where data structure doesn't match template expectations
            error_msg = str(e) if str(e) else repr(e)
            if "'builtin_function_or_method' object is not iterable" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid resume data structure. Ensure all list fields (highlights, experience, projects, skills.categories) are arrays."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Template rendering failed (TypeError): {error_msg}"
            )
        except KeyError as e:
            error_msg = str(e) if str(e) else repr(e)
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field in resume data: {error_msg}"
            )
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            error_type = type(e).__name__
            raise HTTPException(
                status_code=500,
                detail=f"Template rendering failed ({error_type}): {error_msg}"
            )
    
    def _ensure_browsers_installed(self):
        """Ensure Playwright browsers are installed."""
        if self._browsers_installed:
            return
        
        try:
            # Try to import playwright and check if browsers are installed
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    self._browsers_installed = True
                    return
                except Exception:
                    pass
        except Exception:
            pass
        
        # Try to install browsers
        try:
            result = subprocess.run(
                ["playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if result.returncode == 0:
                self._browsers_installed = True
                return
        except Exception:
            pass
        
        # If we get here, browsers aren't installed and we couldn't install them
        raise HTTPException(
            status_code=500,
            detail="Playwright browser not installed. Add 'playwright install chromium' to your build process."
        )
    
    async def _html_to_pdf(self, html: str) -> bytes:
        """
        Convert HTML to PDF using Playwright.
        
        Args:
            html: HTML content string
            
        Returns:
            PDF bytes
            
        Raises:
            HTTPException: If PDF generation fails
        """
        # Ensure browsers are installed before attempting PDF generation
        self._ensure_browsers_installed()
        
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set content
                await page.set_content(html, wait_until="networkidle")
                
                # Generate PDF with A4 settings
                pdf_bytes = await page.pdf(
                    format="A4",
                    margin={
                        "top": "0mm",
                        "right": "0mm",
                        "bottom": "0mm",
                        "left": "0mm"
                    },
                    print_background=True,
                    prefer_css_page_size=True
                )
                
                await browser.close()
                
                return pdf_bytes
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            if "Executable doesn't exist" in error_msg or "browser" in error_msg.lower():
                raise HTTPException(
                    status_code=500,
                    detail="Playwright browser not installed. Add 'playwright install chromium' to your Render build command."
                )
            # Re-raise with better error message
            raise HTTPException(
                status_code=500,
                detail=f"PDF generation failed: {error_msg}"
            )
    
    async def generate_pdf(self, template_id: str, resume_data: Dict[str, Any]) -> bytes:
        """
        Generate PDF from template and resume data.
        
        Args:
            template_id: Template identifier (modern, minimal, tech)
            resume_data: Resume data dictionary
            
        Returns:
            PDF bytes
            
        Raises:
            HTTPException: If template or data is invalid
        """
        try:
            # Render HTML
            html = self._render_html(template_id, resume_data)
            
            # Convert to PDF
            pdf_bytes = await self._html_to_pdf(html)
            
            return pdf_bytes
            
        except HTTPException:
            # Re-raise HTTPExceptions as-is (they already have proper error messages)
            raise
        except Exception as e:
            # Extract error message properly
            error_msg = str(e) if str(e) else repr(e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate PDF: {error_msg}"
            )
    
    def create_pdf_response(self, pdf_bytes: bytes, filename: str = "resume.pdf") -> Response:
        """
        Create FastAPI Response with PDF content.
        
        Args:
            pdf_bytes: PDF file bytes
            filename: Download filename
            
        Returns:
            FastAPI Response object
        """
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )


# Singleton instance
pdf_service = PDFService()

