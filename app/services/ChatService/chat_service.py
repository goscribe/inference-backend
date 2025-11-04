import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory

def prompt_input(messages, prompt):
    """Generate any inference from any prompt"""
    messages.append({"role": "user", "content": prompt})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages