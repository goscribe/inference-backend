import ast
import json
import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
import base64
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory, extract_text_pdf, prepare_pdf, encode_image


def read_pdf(messages, pdf_paths):
    """Read PDF text and append instructions to messages"""
    for pdf_fp in pdf_paths:
        pdf_text = extract_text_pdf(pdf_fp)
        messages.append({"role": "user", "content": f"Read the following content from a pdf file: \"{pdf_text}\" Remember the content. You will have to use it later. \
        At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."})
        resp = LLM_inference(messages=messages)
        update_memory(messages, resp)
    return messages

def read_pdf_images(messages, pdf_paths, img_saving_path):
    """Generate PDF page images and append all pages per document into one message"""
    for pdf_fp in pdf_paths:
        # Prepare the PDF (convert to page images)
        prepare_pdf(pdf_fp, img_saving_path)

        doc_name = os.path.splitext(os.path.basename(pdf_fp))[0]
        doc_dir = os.path.join(img_saving_path, doc_name)

        if not os.path.exists(doc_dir):
            print(f"Warning: directory {doc_dir} not found, skipping {pdf_fp}")
            continue

        files = sorted(os.listdir(doc_dir))
        abs_paths = [os.path.abspath(os.path.join(doc_dir, f)) for f in files]

        # Build one message containing all images for this document
        content = [{
            "type": "text",
            "text": (
                f"The following images are all pages from the PDF '{doc_name}'. "
                "Carefully examine each page and internally note any figures, tables, or information "
                "that might be useful for later tasks. Do not produce any response yet; "
                "this step is only for you to remember the visual content for future reference."
            )
        }]

        for path in abs_paths:
            base64_image = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        # Append this one merged message
        messages.append({
            "role": "user",
            "content": content
        })

        resp = LLM_inference(messages=messages)

        update_memory(messages, resp)

    return messages



def read_images(messages, image_paths):
    for img_fp in image_paths:
        # Encode the image as base64
        base64_image = encode_image(img_fp)
        # Append user instruction with inline image
        image_message = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
        messages.append({
            "role": "user",
            "content": [
                {"type": "text",
                 "text": f"Look at the image at \"{img_fp}\". Remember its content. "
                         "You will later use this information to generate something. "
                         "At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."},
                image_message
            ]
        })
        
        resp = LLM_inference(messages=messages)
        
        # Update messages with the model's response (like your update_memory)
        update_memory(messages, resp)
        
    return messages