import aiofiles
import tempfile
from pathlib import Path
from typing import Union
from fastapi import UploadFile, HTTPException
import PyPDF2
import docx
import io
from loguru import logger

class FileProcessor:
    """Handle file upload and text extraction"""
    
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    async def extract_text(self, file: UploadFile) -> str:
        """Extract text from uploaded file"""
        logger.info(f"Processing file: {file.filename} ({file.content_type})")
        
        # Validate file
        await self._validate_file(file)
        
        # Read file content
        content = await file.read()
        
        try:
            if file.filename.lower().endswith('.pdf'):
                text = await self._extract_pdf_text(content)
            elif file.filename.lower().endswith('.docx'):
                text = await self._extract_docx_text(content)
            elif file.filename.lower().endswith('.txt'):
                text = content.decode('utf-8')
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            logger.success(f"Successfully extracted {len(text)} characters from {file.filename}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {file.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")
    
    async def _validate_file(self, file: UploadFile):
        """Validate file size and extension"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        # Check extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_ext} not allowed. Supported: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Reset file position to beginning
        await file.seek(0)
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF content"""
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            raise Exception(f"PDF parsing error: {str(e)}")
    
    async def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX content"""
        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX parsing error: {str(e)}")