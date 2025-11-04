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
    "id": {worksheet_id},
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
            "mark_scheme": "A string that tells an instructor how to mark: what is acceptable, and what is not enough or incorrect. Include also what is required to achieve a certain amount of points",
            "points": <integer value representing total points for this question>
        }},
        {{
            "question": "<Question 2>",
            "answer": "<Answer 2>",
            "type": "TEXT",
            "options": [Keep this empty],
            "mark_scheme": "A string that tells an instructor how to mark: what is acceptable, and what is not enough or incorrect. Include also what is required to achieve a certain amount of points",
            "points": <integer value representing total points for this question>
        }},
        {{
            "question": "<Question 3>",
            "answer": "<Answer 3>",
            "type": "MULTIPLE_CHOICE",
            "options": ["<Option 1>", "<Option 2>", "<Option 3>"],
            "mark_scheme": "an answer explanation",
            "points": <integer value representing total points for this question>
        }},
        {{
            "question": "<Question 4>",
            "answer": "<Answer 4>",
            "type": "NUMERIC",
            "options": [Keep this empty],
            "mark_scheme": "an answer explanation",
            "points": <integer value representing total points for this question>
        }},
        {{
            "question": "<Question 5>",
            "answer": "<Answer 5>",
            "type": "TRUE_FALSE",
            "options": [Keep this empty],
            "mark_scheme": "an answer explanation",
            "points": <integer value representing total points for this question>
        }},
        {{
            "question": "<Question 6>",
            "answer": "<Answer 6>",
            "type": "MATCHING",
            "options": ["Option 1", "Option 2", "Option 3"],
            "mark_scheme": "an answer explanation",
            "points": <integer value representing total points for this question>
        }}
    ]
}}
Adhere strictly to this format. Return ONLY the JSON object, no code blocks or extra text. 
Be careful about punctuation and escaping. One important note: for multiple choice questions, 
do NOT put the choices in the question. Only write them in the "options" entry. 
You would have to identify whether your original questions includes these choices and avoid writing them in the "question" entry. 
Now, you may begin. You must produce exactly {num_quests} problems in total."""
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
                                                    "minItems": num_quests,
                                                    "maxItems": num_quests,
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
                                                            "mark_scheme": {"type": "string"},
                                                            "points": {"type": "integer"}
                                                        },
                                                        "required": [
                                                            "question",
                                                            "answer",
                                                            "type",
                                                            "options",
                                                            "mark_scheme",
                                                            "points"
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
            f"And here is a mark scheme for reference: {mark_scheme}.\n\n"
            f"The total point value for this question is {points}.\n\n"
            "For your response, please follow this JSON schema:\n"
            "{\n"
            "  correctness: <1 for entirely correct, 0 for incorrect, 2 for partially correct>,\n"
            "  feedback: <your feedback or grading justification>,\n"
            "  achievedPoints: <numerical score achieved based on the mark_scheme and the total point value>\n"
            "}\n"
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
                                                "correctness": {"type": "integer"},
                                                "feedback": {"type": "string"},
                                                "achievedPoints": {"type": "number"},
                                            },
                                            "required": ["correctness", "feedback", "achievedPoints"],
                                            "additionalProperties": False
                                        },
                                        "strict": True
                                    }
                                }
                            )

    markings = resp.choices[0].message.content
    return markings