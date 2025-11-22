"""
File processing service - processes files and returns comprehensive descriptions
Designed to be called by primary backend over HTTPS
"""
import requests
import fitz  # PyMuPDF
from io import BytesIO
import base64
from typing import Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client for image descriptions
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def download_file_to_memory(url: str, timeout: int = 60) -> BytesIO:
    """
    Download file from URL to memory (BytesIO)
    
    Args:
        url: File URL (signed URL or public URL)
        timeout: Request timeout in seconds
    
    Returns:
        BytesIO object with file content
    
    Raises:
        requests.RequestException: If download fails
    """
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Read into memory
        file_bytes = BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            file_bytes.write(chunk)
        file_bytes.seek(0)
        
        return file_bytes
    except requests.Timeout:
        raise Exception(f"Download timeout after {timeout}s")
    except requests.RequestException as e:
        raise Exception(f"Failed to download file: {str(e)}")


def extract_text_from_pdf_bytes(pdf_bytes: BytesIO) -> str:
    """
    Extract all text from PDF in memory
    
    Args:
        pdf_bytes: BytesIO containing PDF data
    
    Returns:
        Extracted text string
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}\n")
        
        doc.close()
        return "\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {str(e)}")


def describe_image_with_vision_api(image_base64: bytes, page_num: int) -> str:
    """
    Describe a single image using OpenAI Vision API
    
    Args:
        image_base64: Base64 encoded image bytes
        page_num: Page number for context
    
    Returns:
        Description string
    """
    try:
        # Convert bytes to base64 string
        base64_string = base64.b64encode(image_base64).decode('utf-8')
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Cheaper model for descriptions
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this page/image in detail. Include any text, diagrams, charts, tables, or visual elements. Be comprehensive but concise."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_string}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500  # Limit tokens for cost control
        )
        
        return response.choices[0].message.content
    except Exception as e:
        # Return fallback description if Vision API fails
        return f"Page {page_num + 1}: [Image description unavailable - {str(e)}]"


def process_pdf_comprehensive(file_url: str, max_pages: Optional[int] = None) -> Dict:
    """
    Process PDF and generate comprehensive description
    
    Args:
        file_url: URL to PDF file
        max_pages: Optional limit on pages to process (for large files)
    
    Returns:
        Dictionary with processed content:
        {
            "textContent": str,
            "imageDescriptions": List[Dict],
            "comprehensiveDescription": str,
            "pageCount": int,
            "status": "success"
        }
    """
    try:
        # Download PDF to memory
        pdf_bytes = download_file_to_memory(file_url)
        pdf_bytes_copy = BytesIO(pdf_bytes.read())  # Create copy for text extraction
        pdf_bytes.seek(0)  # Reset for image processing
        
        # Open PDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        
        # Limit pages if specified (for very large PDFs)
        pages_to_process = min(page_count, max_pages) if max_pages else page_count
        
        # Extract text
        text_content = extract_text_from_pdf_bytes(pdf_bytes_copy)
        
        # Process pages for visual descriptions (sample pages for large PDFs)
        image_descriptions = []
        
        # For large PDFs, sample pages instead of processing all
        if page_count > 50:
            # Sample every 5th page + first and last pages
            pages_to_describe = [0] + list(range(4, pages_to_process, 5)) + [pages_to_process - 1]
            pages_to_describe = sorted(set(pages_to_describe))
        else:
            # Process all pages for smaller PDFs
            pages_to_describe = list(range(pages_to_process))
        
        for page_idx in pages_to_describe:
            try:
                page = doc[page_idx]
                # Convert to image at lower resolution (50% scale for memory efficiency)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                image_bytes = pix.tobytes("png")
                
                # Describe image
                description = describe_image_with_vision_api(image_bytes, page_idx + 1)
                
                image_descriptions.append({
                    "page": page_idx + 1,
                    "description": description,
                    "hasVisualContent": True
                })
                
                pix = None  # Free memory
            except Exception as e:
                print(f"Warning: Failed to process page {page_idx + 1}: {e}")
                image_descriptions.append({
                    "page": page_idx + 1,
                    "description": f"[Page {page_idx + 1} processing failed]",
                    "hasVisualContent": False
                })
        
        doc.close()
        
        # Generate comprehensive description
        comprehensive = generate_comprehensive_description(text_content, image_descriptions, page_count)
        
        return {
            "textContent": text_content,
            "imageDescriptions": image_descriptions,
            "comprehensiveDescription": comprehensive,
            "pageCount": page_count,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "textContent": None,
            "imageDescriptions": [],
            "comprehensiveDescription": None,
            "pageCount": 0
        }


def process_image_comprehensive(file_url: str) -> Dict:
    """
    Process image and generate comprehensive description
    
    Args:
        file_url: URL to image file
    
    Returns:
        Dictionary with processed content
    """
    try:
        # Download image
        image_bytes = download_file_to_memory(file_url)
        image_data = image_bytes.read()
        
        # Describe image using Vision API
        base64_string = base64.b64encode(image_data).decode('utf-8')
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe this image in comprehensive detail. Include all text, visual elements, diagrams, charts, and any important information visible."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_string}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        description = response.choices[0].message.content
        
        return {
            "textContent": None,  # Images don't have extractable text
            "imageDescriptions": [{
                "page": 1,
                "description": description,
                "hasVisualContent": True
            }],
            "comprehensiveDescription": description,
            "pageCount": 1,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "textContent": None,
            "imageDescriptions": [],
            "comprehensiveDescription": None,
            "pageCount": 0
        }


def generate_comprehensive_description(text_content: str, image_descriptions: list, page_count: int) -> str:
    """
    Generate a comprehensive description combining text and image descriptions
    
    Args:
        text_content: Extracted text from PDF
        image_descriptions: List of image descriptions
        page_count: Total number of pages
    
    Returns:
        Comprehensive description string
    """
    parts = []
    
    # Add header
    parts.append(f"DOCUMENT SUMMARY ({page_count} pages)\n")
    parts.append("=" * 50 + "\n\n")
    
    # Add text content summary (truncate if very long)
    if text_content:
        text_preview = text_content[:2000] if len(text_content) > 2000 else text_content
        parts.append("TEXT CONTENT:\n")
        parts.append(text_preview)
        if len(text_content) > 2000:
            parts.append(f"\n[... {len(text_content) - 2000} more characters of text ...]")
        parts.append("\n\n")
    
    # Add visual content descriptions
    if image_descriptions:
        parts.append("VISUAL CONTENT DESCRIPTIONS:\n")
        parts.append("-" * 50 + "\n")
        for img_desc in image_descriptions:
            parts.append(f"Page {img_desc['page']}: {img_desc['description']}\n")
        parts.append("\n")
    
    return "\n".join(parts)


def process_file(file_url: str, file_type: str, max_pages: Optional[int] = None) -> Dict:
    """
    Main entry point for file processing
    
    Args:
        file_url: URL to file (signed URL or public URL)
        file_type: Type of file ('pdf' or 'image')
        max_pages: Optional limit on PDF pages to process
    
    Returns:
        Dictionary with processed content (see process_pdf_comprehensive or process_image_comprehensive)
    """
    try:
        if file_type.lower() == "pdf":
            return process_pdf_comprehensive(file_url, max_pages)
        elif file_type.lower() in ["image", "img", "png", "jpg", "jpeg"]:
            return process_image_comprehensive(file_url)
        else:
            return {
                "status": "error",
                "error": f"Unsupported file type: {file_type}",
                "textContent": None,
                "imageDescriptions": [],
                "comprehensiveDescription": None,
                "pageCount": 0
            }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Processing failed: {str(e)}",
            "textContent": None,
            "imageDescriptions": [],
            "comprehensiveDescription": None,
            "pageCount": 0
        }

