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
    messages = update_memory(messages, resp)
    return messages

def generate_worksheet_a(messages):
    """Generate worksheet answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    messages = update_memory(messages, resp)
    return messages


def generate_worksheet_json(messages, worksheet_id, num_quests):
    messages.append({
        "role": "user",
        "content": f"""Now, read off the questions and answers you wrote. Convert them into a JSON file according to this format: 
{{
    "id": {session},
    "title": "<A Title For Your Worksheet>",
    "description": "<Make a Description for this Worksheet>",
    "difficulty": "<Choice from these: EASY, MEDIUM, HARD>",
    "estimatedTime": "<Estimate how long required to do the questions>",
    "problems": [
        {{
            "question": "<Question 1>",
            "answer": "<Answer 1>",
            "type": "TEXT",
            "options": [Keep this empty],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }},
        {{
            "question": "<Question 2>",
            "answer": "<Answer 2>",
            "type": "TEXT",
            "options": [Keep this empty],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }},
        {{
            "question": "<Question 3>",
            "answer": "<Answer 3>",
            "type": "MULTIPLE_CHOICE",
            "options": ["<Option 1>", "<Option 2>", "<Option 3>"],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }},
        {{
            "question": "<Question 4>",
            "answer": "<Answer 4>",
            "type": "NUMERIC",
            "options": [Keep this empty],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }},
        {{
            "question": "<Question 5>",
            "answer": "<Answer 5>",
            "type": "TRUE_FALSE",
            "options": [Keep this empty],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }},
        {{
            "question": "<Question 6>",
            "answer": "<Answer 6>",
            "type": "MATCHING",
            "options": ["Option 1", "Option 2", "Option 3"],
            "mark_scheme": {{
                "points": [
                    {{
                        "point": 1,
                        "requirements": "Description of what's needed for this point"
                    }}
                ],
                "totalPoints": <integer value representing total points for this question>
            }}
        }}
    ]
}}
Adhere strictly to this format. Return ONLY the JSON object, no code blocks or extra text. 
Be careful about punctuation and escaping. One important note: for multiple choice questions, 
do NOT put the choices in the question. Only write them in the "options" entry. 
You would have to identify whether your original questions includes these choices and avoid writing them in the "question" entry. 
Now, you may begin. You must produce exactly {num_questions} problems in total."""
    })

    resp = LLM_inference(messages=messages, json_output=True, 
                            response_format={
                                    "type": "json_schema",
                                    "json_schema": {
                                        "name": "worksheet_container",
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "title": {"type": "string"},
                                                "description": {"type": "string"},
                                                "difficulty": {"type": "string"},
                                                "estimatedTime": {"type": "string"},
                                                "problems": {
                                                    "type": "array",
                                                    "minItems": num_questions,
                                                    "maxItems": num_questions,
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "question": {"type": "string"},
                                                            "answer": {"type": "string"},
                                                            "type": {"type": "string"},
                                                            "options": {
                                                                "type": "array",
                                                                "items": {"type": "string"}
                                                            },
                                                            "mark_scheme": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "points": {
                                                                        "type": "array",
                                                                        "items": {
                                                                            "type": "object",
                                                                            "properties": {
                                                                                "point": {"type": "integer"},
                                                                                "requirements": {"type": "string"}
                                                                            },
                                                                            "required": ["point", "requirements"],
                                                                            "additionalProperties": False
                                                                        }
                                                                    },
                                                                    "totalPoints": {"type": "integer"}
                                                                },
                                                                "required": ["points", "totalPoints"],
                                                                "additionalProperties": False
                                                            }
                                                        },
                                                        "required": [
                                                            "question",
                                                            "answer",
                                                            "type",
                                                            "options",
                                                            "mark_scheme"
                                                        ],
                                                        "additionalProperties": False
                                                    }
                                                }
                                            },
                                            "required": ["id", "title", "description", "difficulty", "estimatedTime", "problems"],
                                            "additionalProperties": False
                                        },
                                        "strict": True
                                    }
                                }
                            )

    messages = update_memory(messages, resp)
    return messages


def mark_question(question, answer, mark_scheme, points):
    """Generate worksheet answers"""
    messages = [{
        "role": "user",
        "content": (
            f"You would have to mark a student's answer to a question and give feedback. "
            f"A marking scheme will be given.\n\n"
            f"Here is the question: {question}\n"
            f"Here is the answer you have to mark: {answer}\n"
            f"And here is the mark scheme for reference:\n{mark_scheme_text}\n"
            f"The total point value for this question is {total_points}.\n\n"
            "For your response, please follow this JSON schema:\n"
            "{\n"
            "  totalPoints: <sum of all achievedPoints from the points array>,\n"
            "  points: [\n"
            "    {\n"
            "      point: <the max point value for this criteria from mark scheme>,\n"
            "      requirements: <the requirements text from mark scheme>,\n"
            "      achievedPoints: <points earned for this criteria>,\n"
            "      feedback: <specific feedback for this criteria>\n"
            "    },\n"
            "    ... (one object for each marking criteria)\n"
            "  ]\n"
            "}\n"
            "Provide grading for EACH marking point in the mark scheme.\n"
            "Now you may begin."
        )
    }]

    resp = LLM_inference(messages=messages, json_output=True, 
                            response_format={
                                    "type": "json_schema",
                                    "json_schema": {
                                        "name": "answer_feedback",
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "totalPoints": {"type": "number"},
                                                "points": {
                                                    "type": "array",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "point": {"type": "integer"},
                                                            "requirements": {"type": "string"},
                                                            "achievedPoints": {"type": "number"},
                                                            "feedback": {"type": "string"}
                                                        },
                                                        "required": ["point", "requirements", "achievedPoints", "feedback"],
                                                        "additionalProperties": False
                                                    }
                                                }
                                            },
                                            "required": ["totalPoints", "points"],
                                            "additionalProperties": False
                                        },
                                        "strict": True
                                    }
                                }
                            )

    markings = resp.choices[0].message.content
    return markings
