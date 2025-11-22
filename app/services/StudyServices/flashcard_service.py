import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory
from app.utils.workspace_context import get_workspace_context_as_message


def generate_flashcards_q(messages, num_flashcards=5, difficulty="hard", workspace_id=None, user_id=None):
    """Generate flashcard questions"""
    # Prepend workspace context if available (exclude flashcards to avoid duplication)
    if workspace_id and user_id:
        context_message = get_workspace_context_as_message(
            workspace_id=workspace_id,
            user_id=user_id,
            include_file_assets=True,
            include_flashcards=False  # Don't include existing flashcards
        )
        if context_message:
            # Insert after system message (if exists) or at beginning
            insert_index = 0
            if messages and messages[0].get("role") == "system":
                insert_index = 1
            messages.insert(insert_index, context_message)
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or spotted in images, \
    please generate {num_flashcards} flashcard questions. The questions shall have difficulty level '{difficulty}'. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    messages = update_memory(messages, resp)
    return messages

def generate_flashcards_a(messages):
    """Generate flashcard answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    messages = update_memory(messages, resp)
    return messages


def generate_flashcards_json(messages):
    messages.append({
            "role": "user",
            "content": """Now, read off the questions and answers you wrote. Convert them into a JSON file according to this format: 
    [
        {"term": "<Question 1>",
        "definition": "<Answer 1>"}, 
        {"term": "<Question 2>",
        "definition": "<Answer 2>"}, 
        {"term": "<Question 3>",
        "definition": "<Answer 3>"}, 
    ]
    Adhere strictly to this format. When you start your generation, do not include any texts that do not belong to the JSON.
    Return ONLY the JSON file following "[..." You shall NOT have anything like "json" or `` in front, ONLY the raw text for the JSON source!!!
    Remember, ONLY THE RAW TEXT, not a code block.
    Be aware of any punctuations that might conflict with JSON syntax. This is extremely important!!! Now, you may begin."""
        })

    resp = LLM_inference(messages=messages, json_output=True, 
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "flashcard_container",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "flashcards": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "term": {"type": "string"},
                                                    "definition": {"type": "string"}
                                                },
                                                "required": ["term", "definition"],
                                                "additionalProperties": False
                                            }
                                        }
                                    },
                                    "required": ["flashcards"],
                                    "additionalProperties": False
                                },
                                "strict": True}
                            }
                        )

    messages = update_memory(messages, resp)
    return messages