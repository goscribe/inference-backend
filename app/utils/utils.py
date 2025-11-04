import ast
import json
import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
import base64


def update_memory(messages, resp):
    """Updates messages with model response from OpenAI"""
    last_output = resp.choices[0].message.content
    messages.append({"role": "assistant", "content": last_output})
    return messages

def extract_text_pdf(path):
    """Extract text from a PDF"""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def prepare_pdf(doc_path, image_saving_path):
    """Generate page images from a PDF"""
    doc_name, _ = os.path.splitext(os.path.basename(doc_path))
    os.makedirs(f"{image_saving_path}/{doc_name}", exist_ok=True)
    
    doc = fitz.open(doc_path)
    for page_num, page in enumerate(doc):
        pix = page.get_pixmap()
        output_name = f"{image_saving_path}/{doc_name}/page_{page_num + 1}.png"
        try:
            pix.save(output_name)
        except Exception as e:
            print(f"Warning: failed to save image {output_name} ({e})")

def encode_image(image_path):
    """Encode an image file to base64 for sending inline"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def safe_json_parse(messages, save_path):
    """Extract the last model response and safely parse into <save_path>.json"""
    try:
        parsed = json.loads(messages[-1].get("content", ""))
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False)
        print("Parsed JSON Successful.")
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse JSON. Raw output:")
        print(messages[-1].get("content", ""))
        print("Error:", e)

