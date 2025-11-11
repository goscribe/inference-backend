import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory



def generate_segmentation(study_guide):
    """Generate study guide segmentation for comperhension check"""
    messages = [{
        "role": "user",
        "content": (
            f"You will be assisting a student in memorizing some study content. Here is the process: you will first \
             be provided with a full study guide or a document containing all the knowedges. Then, you shall segment the \
             guide into several pieces and provide them to the student. The student shall try to memorize them and \
             write the segments down given some hints. You job now is to perform the study guide segmentation and hint generation. \
             Below is the study guide: \n{study_guide}\n"
            "You shall generate a json file according to the following format:\n\
            [{\"hint\": <a string containing the hint>, \"content\": <the exact segmented content from the study guide>}, \n\
            {\"hint\": <a string containing the hint>, \"content\": <the exact segmented content from the study guide>}, ...]\n\
            Now you may begin."
            
        )
    }]

    resp = LLM_inference(messages=messages, json_output=True, 
                        response_format = {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "study_guide_segmentation",
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "segments": {
                                                "type": "array",
                                                "description": "A list of study segments with their corresponding hints for memorization.",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "hint": {
                                                            "type": "string",
                                                            "description": "A short textual hint that helps the student recall the content."
                                                        },
                                                        "content": {
                                                            "type": "string",
                                                            "description": "The exact text segment taken from the original study guide."
                                                        }
                                                    },
                                                    "required": ["hint", "content"],
                                                    "additionalProperties": False
                                                }
                                            }
                                        },
                                        "required": ["segments"],
                                        "additionalProperties": False
                                    }
                                }
                            }
                        )

    segmentations = resp.choices[0].message.content
    return segmentations

def validate_summary_correctness(study_guide, segment_content, student_response):
    """Evaluate the student's understanding of the segment for the study guide"""
    messages = [{
        "role": "user",
        "content": (
            f"You will be assisting a student in memorizing some study content. Here is the process: you will first \
             be provided with a full study guide or a document containing all the knowedges. Then, you shall segment the \
             guide into several pieces and provide them to the student. The student shall try to memorize them and \
             write the segments down given some hints. You job now is to perform the last phase: the study guide is ALREADY \
             sengmented and provided to the student. You all now evaluate whether the student gains a comperhensive understanding \
             based on his/her response. For reference: this is the full study guide: \n{study_guide}\n\
             This is the specific segment content that the student is trying to memorize: \n{segment_content}\n\
             and This is the student's response: \n{student_response}\n\
             You shall now give a rating and feedback of the student's response following this json format:\n"
            "{\"valid\": TRUE/FALSE, \"feedback\": <some feedback for how is the student's summary. if the summary is invalid, then \
             how to improve or what to ponder.>}\n\
             Now you may begin."   
        )
    }]

    resp = LLM_inference(messages=messages, json_output=True, 
                        response_format = {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "student_response_evaluation",
                                    "schema": {
                                        "type": "object",
                                        "description": "Evaluation of a student's memorization response against the study guide segment.",
                                        "properties": {
                                            "valid": {
                                                "type": "boolean",
                                                "description": (
                                                    "Indicates whether the student's response demonstrates a correct and comprehensive "
                                                    "understanding of the study guide segment."
                                                )
                                            },
                                            "feedback": {
                                                "type": "string",
                                                "description": (
                                                    "Detailed feedback explaining why the response is valid or invalid. "
                                                    "If invalid, include guidance on what specific aspects the student should improve or reflect on."
                                                )
                                            }
                                        },
                                        "required": ["valid", "feedback"],
                                        "additionalProperties": False
                                    }
                                }
                            }
                        )

    segmentations = resp.choices[0].message.content
    return segmentations