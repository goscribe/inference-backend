import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory

def generate_worksheet_q(messages, num_quests=5, difficulty="hard"):
    """Generate worksheet questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or spotted in images, \
    please generate {num_quests} long questions for a worksheet. They can be of any type: MCQs, FRQs, or even essays, but be organized in terms of the order so that it fits well with a worksheet. The questions shall have difficulty level '{difficulty}'. Please include at least 2 MCQs. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

def generate_podcast_script(messages, prompt):
    """Generate Script for Podcast"""
#     messages.append({"role": "user", "content": f"""
# Now, please generate a script for a podcast discussing everything mentioned in the entire history of this chat. 
# The podcast should be divided into **at least 3 distinct sections**, each roughly 2–3 minutes in spoken length. 
# Each section should be one string element in the "scripts" array of the JSON schema. 
# Do not output anything else besides the JSON object matching the schema.
# The student also has this additional requirement: [{prompt}]"""})
    messages.append({"role": "user", "content": f"""
You are suppose to generate a script for a podcast, but this is now a test. For all 3 segment of the podcast, have only 
the sentence: "This is a test"."""})

    resp = LLM_inference(messages=messages, json_output=True, 
                         response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "script_container",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "scripts": {
                                                "type": "array",
                                                "minItems": 3,
                                                "items": {"type": "string"}
                                            }
                                        },
                                        "required": ["scripts"],
                                        "additionalProperties": False
                                    },
                                    "strict": True
                                }
                            }
                        )

    messages = update_memory(messages, resp)
    messages.append({"role": "assistant", "content": model_output})
    return messages