from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
# from fileConverter import *
from LLM_openAI_api import read_pdf, update_memory, read_pdf_images, read_images, generate_summary, generate_flashcards_q, generate_flashcards_a, generate_worksheet_q, generate_worksheet_a, generate_mindmap_mermaid, prompt_input, generate_podcast_script
import requests
from markdownConvertor import *
converter = MarkdownToEditorJS()
import shutil
from LLM_inference import LLM_inference
from dotenv import load_dotenv
from eleven_labs import *
from supabase import create_client

app = Flask(__name__)
CORS(app)  # allow all origins for frontend JS

# Global state
server_status = {"busy": False}

# Define commands and corresponding functions
command_list = ["init_session", "append_image", "append_pdflike", "remove_img", "remove_pdf", "analyse_pdf", "analyse_img", "generate_study_guide", "generate_flashcard_questions", "generate_worksheet_questions", "mark_worksheet_questions", "inference_from_prompt", "generate_podcast"]

model = "gemma3:27b-it-qat"  
load_dotenv()
ROOT_DIR = "Data"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)



def init_session(request):

    # Get parameters
    CURRENT_SESSION_ID = request.form.get("session")
    CURRENT_USER_ID = request.form.get("user")

    # Validate input
    if not CURRENT_SESSION_ID:
        print("No session ID provided")
        return {"error": "No session ID provided"}, 400
    if not CURRENT_USER_ID:
        print("Not Logged in.")
        return {"error": "No permission."}, 400

    # Build directory hierarchy: <UserID>/<SessionID>/{pdfs, imgs}
    user_dir = os.path.join(ROOT_DIR, CURRENT_USER_ID)
    session_dir = os.path.join(user_dir, CURRENT_SESSION_ID)
    pdf_dir = os.path.join(session_dir, "pdfs")
    img_dir = os.path.join(session_dir, "imgs")

    # Create necessary folders
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    # Save user info in the user's root folder
    # user_info_path = os.path.join(user_dir, "userInfo.json")
    # with open(user_info_path, "w") as f:
    #     json.dump({"user": CURRENT_USER}, f, indent=2)
    

    # Initialize default LLM messages
    messages = [
        {
            "role": "system",
            "content": "Your task is to serve as a study tool - given the info that will be provided next, in form "
                       "of either text or image, you will try your best to understand them. You will be asked to generate a summary in case we have to "
                       "check your understanding. You will generate a study guide covering the given information. The guide shall contain 1) a "
                       "descriptive summary of all given materials in the form of a lecture note, 2) a set of flashcard questions, short in form, along with "
                       "corresponding answers, 3) an organized worksheet served as an exercise, supplied along with an answer sheet. "
                       "Your responses will be listened by a front end, so answer only what is being asked, and follow the form. Good Luck!"
        },
        {
            "role": "user",
            "content": "You will be writing a note and prepare some questions on following materials. Materials will be given"
        },
    ]  # Default instruction messages

    # Send initial message to Ollama to get assistant's first response
    resp = LLM_inference(messages=messages)
    # Append only the assistant's message content
    messages.append({"role": "assistant", "content": resp.choices[0].message.content})

    # Save messages.json inside session folder
    messages_path = os.path.join(session_dir, "messages.json")
    with open(messages_path, "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Session '{CURRENT_SESSION_ID}' initialized under user '{CURRENT_USER_ID}'.")
    return {"message": f"Session '{CURRENT_SESSION_ID}' initialized successfully for user '{CURRENT_USER_ID}'"}, 200


def append_image(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    if 'file' not in request.files:
        return {"error": "No Image Included!"}, 400

    file = request.files['file']
    filename = file.filename
    if not filename:
        return {"error": "Empty filename"}, 400

    # Path: <ROOT_DIR>/<user>/<session>/imgs
    upload_folder = os.path.join(ROOT_DIR, user, session, "imgs")
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)

    with open(file_path, "wb") as f:
        f.write(file.read())

    return {"message": f"File saved at: {file_path}: Success"}, 200


def append_pdflike(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    if 'file' not in request.files:
        return {"error": "No File Included!"}, 400

    file = request.files['file']
    filename = file.filename
    if not filename:
        return {"error": "Empty filename"}, 400

    upload_folder = os.path.join(ROOT_DIR, user, session, "pdfs")
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)

    with open(file_path, "wb") as f:
        f.write(file.read())

    return {"message": f"File saved at: {file_path}: Success"}, 200


def remove_img(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    filename = request.form.get("filename")
    if not filename:
        return {"error": "No filename provided."}, 400

    imgs_dir = os.path.join(ROOT_DIR, user, session, "imgs")
    os.makedirs(imgs_dir, exist_ok=True)
    file_path = os.path.normpath(os.path.join(imgs_dir, os.path.basename(filename)))
    if not file_path.startswith(os.path.normpath(imgs_dir) + os.sep):
        return {"error": "Invalid filename."}, 400

    if not os.path.isfile(file_path):
        return {"error": f"File not found: {filename}"}, 404

    try:
        os.remove(file_path)
        return {"message": f"Image '{filename}' removed successfully."}, 200
    except OSError as e:
        return {"error": f"Failed to remove file: {str(e)}"}, 500


def remove_pdf(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    filename = request.form.get("filename")
    if not filename:
        return {"error": "No filename provided."}, 400

    pdfs_dir = os.path.join(ROOT_DIR, user, session, "pdfs")
    os.makedirs(pdfs_dir, exist_ok=True)
    file_path = os.path.normpath(os.path.join(pdfs_dir, os.path.basename(filename)))

    if not file_path.startswith(os.path.normpath(pdfs_dir) + os.sep):
        return {"error": "Invalid filename."}, 400

    if not os.path.isfile(file_path):
        return {"error": f"File not found: {filename}"}, 404

    # Remove main PDF file
    try:
        os.remove(file_path)
    except OSError as e:
        return {"error": f"Failed to remove PDF file: {str(e)}"}, 500

    # Remove associated dissected folder if exists
    base_no_ext = os.path.splitext(filename)[0]
    associated_folder = os.path.normpath(os.path.join(pdfs_dir, f"{base_no_ext}_assets"))
    assets_removed = False
    if os.path.isdir(associated_folder):
        try:
            shutil.rmtree(associated_folder)
            assets_removed = True
        except OSError as e:
            return {
                "message": f"PDF '{filename}' removed, but failed to remove associated dissected folder.",
                "error": str(e)
            }, 500

    msg = f"PDF '{filename}' removed successfully."
    if assets_removed:
        msg += " Associated dissected folder removed."
    return {"message": msg}, 200



def analyse_pdf(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400
   

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)
    pdf_dir_path = f"{ROOT_DIR}/{user}/{session}/pdfs"
    entries = os.listdir(pdf_dir_path)
    if len(entries) == 0:
        print(f"No PDFs uploaded.")
        return {"INFO": "No PDFs uploaded."}, 200
        
    pdf_paths = [os.path.abspath(os.path.join(pdf_dir_path, entry)) for entry in entries]
    print(pdf_paths)
    messages = read_pdf(messages, pdf_paths)
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing PDF texts Successful")

    img_saving_path = f"{ROOT_DIR}/{user}/{session}/pdf_images"
    os.makedirs(f"{img_saving_path}", exist_ok=True)
    messages = read_pdf_images(messages, pdf_paths, img_saving_path)

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing PDF Image Content Successful")

    last_content = messages[-1].get("content", "")
    return {"message": "Analyse PDFs Successful"}, 200
    
# Global variable to store the full history of current session
FULL_HISTORY = {"content": None}


def analyse_img(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)
    img_dir_path = f"{ROOT_DIR}/{user}/{session}/imgs"
    entries = os.listdir(img_dir_path)
    if len(entries) == 0:
        print(f"No imagess uploaded.")
        return {"INFO": "No images uploaded."}, 200
        
    img_paths = [os.path.abspath(os.path.join(img_dir_path, entry)) for entry in entries]
    messages = read_images(messages, img_paths)
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing Images Successful")
    return {"message": "Analysing Images Successful"}, 200


def generate_study_guide(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)

    messages = generate_summary(messages)
    markdown_text = messages[-1].get("content", "")
    print("Generating Study Guide Markdown Successfully")
    messages = generate_mindmap_mermaid(messages)
    mindmap_mermaid = messages[-1].get("content", "")
    print("Generating Study Guide Mindmap Successfully")

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
    
    # editorjs_json = converter.convert(markdown_text)
    # json_str = json.dumps(editorjs_json, indent=2, ensure_ascii=False)
    
    return {"markdown": markdown_text, "mermaid": mindmap_mermaid}, 200


def generate_flashcard_questions(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    num_questions = request.form.get("num_questions")
    difficulty = request.form.get("difficulty")

    if not num_questions:
        print("Number of Questions not Specified.")
        return {"error": "Number of Questions not Specified."}, 400
    if not difficulty:
        print("Difficulty not Specified.")
        return {"error": "Difficulty not Specified."}, 400

    # --- Load message history ---
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)

    # --- Generate flashcard Q/A using pre-existing helper functions ---
    messages = generate_flashcards_q(messages, num_questions, difficulty)
    print("Generating Flashcard Questions Successful.")
    messages = generate_flashcards_a(messages)
    print("Generating Flashcard Answers Successful.")

    # --- Append JSON conversion instruction ---
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

    response = LLM_inference(messages=messages, json_output=True, 
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

    # --- Extract model output ---
    model_output = response.choices[0].message.content
    messages.append({"role": "assistant", "content": model_output})

    # --- Save updated conversation ---
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    # --- Parse model output safely ---
    try:
        parsed = json.loads(model_output)
        flashcards = parsed.get("flashcards", [])
        with open(f"{ROOT_DIR}/{user}/{session}/flashcards.json", "w", encoding="utf-8") as f:
            json.dump(flashcards, f, indent=2, ensure_ascii=False)
        print("Generating Flashcard JSON Successful.")
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse JSON. Raw output:")
        print(model_output)
        print("Error:", e)
        return {"error": "Invalid JSON returned by model."}, 500

    # --- Return API response ---
    last_content = model_output
    return {"flashcards": last_content}, 200

     
def generate_worksheet_questions(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    num_questions = request.form.get("num_questions")
    difficulty = request.form.get("difficulty")

    if not num_questions:
        print("Number of Questions not Specified.")
        return {"error": "Number of Questions not Specified."}, 400
    if not difficulty:
        print("Difficulty not Specified.")
        return {"error": "Difficulty not Specified."}, 400

    num_questions = int(num_questions)

    # --- Load conversation history ---
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)

    # --- Generate questions and answers ---
    messages = generate_worksheet_q(messages, num_questions, difficulty)
    print("Generating Worksheet Questions Successful.")
    messages = generate_worksheet_a(messages)
    print("Generating Worksheet Answers Successful.")

    # --- Append prompt for JSON conversion ---
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
Now, you may begin. You must produce exactly {num_questions} problems in total."""
    })

    response = LLM_inference(messages=messages, json_output=True, 
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

    # --- Extract model output ---
    worksheet_str = response.choices[0].message.content
    messages.append({"role": "assistant", "content": worksheet_str})

    # --- Save updated conversation ---
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    # --- Parse JSON safely ---
    try:
        worksheet_obj = json.loads(worksheet_str)
        with open(f"{ROOT_DIR}/{user}/{session}/worksheet.json", "w", encoding="utf-8") as f:
            json.dump(worksheet_obj, f, indent=2, ensure_ascii=False)

        print("Generating Worksheet JSON Successful.")
        return {"worksheet": worksheet_str}, 200

    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse JSON. Raw response:")
        print(worksheet_str)
        print("Error:", e)
        return {"error": "Failed to parse model output."}, 500



def mark_worksheet_question(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    question = request.form.get("question")
    answer = request.form.get("answer")
    mark_scheme = request.form.get("mark_scheme")
    points = request.form.get("points")

    if not question:
        print("Questions not Specified.")
        return {"error": "Questions not Specified."}, 400
    if not mark_scheme:
        mark_scheme = ""
    if not answer:
        print("Answer not Specified.")
        return {"error": "Answer not Specified."}, 400
    if not points:
        print("Points not Specified. Defaulting to 1.")
        points = 1

    points = float(points)

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

    response = LLM_inference(messages=messages, json_output=True, 
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

    model_output = response.choices[0].message.content
    return {"marking": model_output}, 200


    

def inference_from_prompt(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    prompt = request.form.get("prompt")
    if not prompt:
        print("No prompt input.")
        return {"error": "No prompt input."}, 400

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)
        
    messages = prompt_input(messages, prompt)
    
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    print("Last message:", messages[-1])
    print("Prompting Successful")
    return {"last_response": last_content}, 200


def generate_podcast(request):
    user = request.form.get("user")
    session = request.form.get("session")
    podcast_id = request.form.get("podcast_id")
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    prompt = request.form.get("prompt")
    if not prompt:
        prompt = ""

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)
        
    messages = generate_podcast_script(messages, prompt)
    
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")

    audio_dir = f"{ROOT_DIR}/{user}/{session}/podcasts"
    if os.path.exists(audio_dir):
        shutil.rmtree(audio_dir)  # remove the entire directory and contents
    os.makedirs(audio_dir)  # recreate the directory


    last_content = messages[-1].get("content", "")
    
    try:
        parsed = json.loads(last_content)
        scripts = parsed.get("scripts", []) 
        with open(f"{ROOT_DIR}/{user}/{session}/scripts.json", "w", encoding="utf-8") as f:
            json.dump(scripts, f, indent=2, ensure_ascii=False)
        print("Generating Scripts JSON Successful.")
    except json.JSONDecodeError as e:
        print("⚠️ Failed to parse JSON. Raw output:")
        print(model_output)
        print("Error:", e)
        return {"error": "Invalid JSON returned by model."}, 500
    
    for i in range(len(scripts)):
        audio_path = f"{audio_dir}/{i}.mp3"
        text_to_speech(scripts[i], audio_path)
        print(f"Finished generating audio for section {i}")
        with open(audio_path, "rb") as f:
            supabase.storage.from_("media").upload(
                f"{user}/{session}/podcasts/{podcast_id}/{i}",
                f,
                file_options={"content-type": "audio/mpeg"}
            )
    
    return {"script": last_content}, 200



function_list = [init_session, append_image, append_pdflike, remove_img, remove_pdf, analyse_pdf, analyse_img, generate_study_guide, generate_flashcard_questions, generate_worksheet_questions, mark_worksheet_question, inference_from_prompt, generate_podcast]

@app.route("/upload", methods=["POST"])
def upload_content():
    # Each request runs in its own thread under Flask’s threaded mode

    # Extract command from request
    command = request.form.get("command")
    if not command:
        return jsonify({"error": "No command provided"}), 400

    # Look up command index
    try:
        cmd_index = command_list.index(command)
    except ValueError:
        return jsonify({"error": f"Unknown command '{command}'"}), 400

    try:
        # Execute the function (safe to run concurrently)
        func_response = function_list[cmd_index](request)

        if isinstance(func_response, tuple) and len(func_response) == 2:
            data, status_code = func_response
            return jsonify(data), status_code
        else:
            return jsonify(func_response), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Function execution failed: {str(e)}"}), 500


@app.route("/session_files", methods=["GET"])
def get_all_files():
    def list_dir(d, kind):
        if not os.path.isdir(d):
            return []
        out = []
        for name in sorted(os.listdir(d)):
            path = os.path.join(d, name)
            if os.path.isfile(path):
                try:
                    out.append({
                        "name": name,
                        "path": path,
                        "type": kind,
                        "size_bytes": os.path.getsize(path),
                        "modified_ts": os.path.getmtime(path),
                        "modified_iso": time.strftime(
                            "%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path))
                        ),
                    })
                except OSError:
                    continue
        return out

    users = {}
    for user_entry in sorted(os.listdir(ROOT_DIR)):
        user_path = os.path.join(ROOT_DIR, user_entry)
        if not os.path.isdir(user_path) or user_entry.startswith(".") or user_entry == "__pycache__":
            continue

        user_sessions = {}
        for session_entry in sorted(os.listdir(user_path)):
            session_path = os.path.join(user_path, session_entry)
            if not os.path.isdir(session_path):
                continue

            pdf_dir = os.path.join(session_path, "pdfs")
            img_dir = os.path.join(session_path, "imgs")
            if not (os.path.isdir(pdf_dir) or os.path.isdir(img_dir)):
                continue


            pdfs = list_dir(pdf_dir, "pdf")
            imgs = list_dir(img_dir, "img")
            
            counts = {"pdfs": len(pdfs), "imgs": len(imgs), "all": len(pdfs) + len(imgs)}
            
            user_sessions[session_entry] = {
                "counts": counts,
                "imgs": imgs,
                "pdfs": pdfs,
                "user": user_entry
            }


        if user_sessions:
            users[user_entry] = user_sessions

    resp = {"users": users, "user_count": len(users)}
    return jsonify(resp), 200




    
@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    Returns HTTP 200 with a JSON indicating the server is alive.
    """
    return jsonify({"status": "healthy", "server_status": "busy" if server_status["busy"] else "idle"}), 200  


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "busy" if server_status["busy"] else "idle"}), 200

if __name__ == "__main__":
    app.run(threaded=True, host="0.0.0.0", port=61016)
