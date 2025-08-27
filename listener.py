from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from fileConverter import *
from LLM import read_pdf, update_memory, read_pdf_images, read_images, generate_summary, generate_flashcards_q, generate_flashcards_a, generate_worksheet_q, generate_worksheet_a, generate_mindmap_mermaid, prompt_input
import requests

app = Flask(__name__)
CORS(app)  # allow all origins for frontend JS

# Global state
server_status = {"busy": False}

# Define commands and corresponding functions
command_list = ["init_session", "append_image", "append_pdflike", "set_instruct", "start_LLM_session", "analyse_pdf", "retrieve_full_history", "analyse_img", "generate_study_guide", "generate_flashcard_questions", "generate_flashcard_answers", "generate_worksheet_questions", "generate_worksheet_answers", "generate_mindmap", "inference_from_prompt", "overwrite", "process", "analyze"]  # example commands

url = "http://localhost:11434/api/chat"
model = "gemma3:27b"  

# PDF_FOLDER = "pdfs"
# IMG_FOLDER = "imgs"
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CURRENT_SESSION_ID = False

def init_session(request):
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = request.form.get("id")
    if not CURRENT_SESSION_ID:
        print("No session ID provided")
        return {"error": "No session ID provided"}, 400

    # Create session folder and subfolders
    os.makedirs(CURRENT_SESSION_ID, exist_ok=True)
    os.makedirs(f"{CURRENT_SESSION_ID}/pdfs", exist_ok=True)
    os.makedirs(f"{CURRENT_SESSION_ID}/imgs", exist_ok=True)

    # Initialize default LLM messages
    messages = [
        {"role": "system", "content": "Your task is to serve as a study tool - given the info that will be provided next, in form \
        of either text or image, you will try your best to understant them. You will be asked to generate a summary in case we have to \
        check your understanding. You will generate a study guide covering the given information. The guide shall contain 1) a \
        descriptive summary of all given materials in the form of a lecture note, 2) a set of flashcard questions, short in form, along with \
        corresponding answers, 3) a organized worksheet served as an excercise, supplied along with an answer sheet. \
        Your responses will be listened by a front end, so answer only what is being asked, and follow the form. Good Luck!"},
        {"role": "user", "content": "You will be writing a note and prepare some questions on following materials. Materials will be given"},
    ]    # For init, defaulting instruct text to this vague command. This can be overwritten by set_instruct
    
    # Save messages.json in the session folder
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Session '{CURRENT_SESSION_ID}' initialized.")
    return {"message": f"Session '{CURRENT_SESSION_ID}' initialized successfully"}, 200

def append_image(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400
        
    if 'file' not in request.files:
        print("No Image Included!")
        return {"error": "No Image Included!"}, 400

    file = request.files['file']
    filename = file.filename
    if not filename:
        print("Empty filename")
        return
        
    UPLOAD_FOLDER = os.path.join(CURRENT_SESSION_ID, "imgs")
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as f:
        f.write(file.read())

    print(f"File saved at: {file_path}")
    return {"message": f"File saved at: {file_path}: Success"}, 200
 

def append_pdflike(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400
        
    if 'file' not in request.files:
        print("No Image Included!")
        return {"error": "No Image Included!"}, 400

    file = request.files['file']
    filename = file.filename
    if not filename:
        print("Empty filename")
        return
        
    UPLOAD_FOLDER = os.path.join(CURRENT_SESSION_ID, "pdfs")
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as f:
        f.write(file.read())

    print(f"File saved at: {file_path}")
    convert_all_to_pdf(UPLOAD_FOLDER)
    return {"message": f"File saved at: {file_path}: Success"}, 200


def set_instruct(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    instruct_text = request.form.get("instruction_text")
    if not CURRENT_SESSION_ID:
        print("No changes needed for instruction text.")
        return {"INFO": "No changes needed for instruction text."}, 200

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages[-1] = {"role": "user", "content": instruct_text}
    
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Instruction Text Reset Successful")
    return {"message": "Instruction Text Reset Successful"}, 200

def start_LLM_session(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)  

    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Start LLM Session Successful")
    return {"message": "Start LLM Session Successful"}, 200

# Global variable to store the latest response
LAST_RESPONSE = {"content": None}

@app.route("/last_response", methods=["POST"])
def set_last_response():
    global LAST_RESPONSE
    data = request.get_json()
    LAST_RESPONSE["content"] = data.get("last_response", "")
    print("Last response updated:", LAST_RESPONSE["content"])
    return jsonify({"message": "Last response saved."}), 200

@app.route("/last_response", methods=["GET"])
def get_last_response():
    global LAST_RESPONSE
    if LAST_RESPONSE["content"] is None:
        return jsonify({"last_response": "No last response stored yet."}), 200
    return jsonify({"last_response": LAST_RESPONSE["content"]}), 200

def analyse_pdf(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    pdf_dir_path = f"{CURRENT_SESSION_ID}/pdfs"
    entries = os.listdir(pdf_dir_path)
    if len(entries) == 0:
        print(f"No PDFs uploaded.")
        return {"INFO": "No PDFs uploaded."}, 200
        
    pdf_paths = [os.path.abspath(os.path.join(pdf_dir_path, entry)) for entry in entries]
    messages = read_pdf(messages, pdf_paths)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing PDF texts Successful")

    img_saving_path = f"{CURRENT_SESSION_ID}/pdf_images"
    os.makedirs(f"{img_saving_path}", exist_ok=True)
    messages = read_pdf_images(messages, pdf_paths, img_saving_path)

    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing PDF Image Content Successful")

    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    return {"message": "Analyse PDFs Successful"}, 200
    
# Global variable to store the full history of current session
FULL_HISTORY = {"content": None}

@app.route("/full_history", methods=["POST"])
def set_full_history():
    global FULL_HISTORY
    data = request.get_json()
    FULL_HISTORY["content"] = data.get("full_history", "")
    print("full history updated:", FULL_HISTORY["content"])
    return jsonify({"message": "Full Hiistory Updated."}), 200

@app.route("/full_history", methods=["GET"])
def get_full_history():
    global FULL_HISTORY
    if FULL_HISTORY["content"] is None:
        return jsonify({"full_history": "No full history stored yet."}), 200
    return jsonify({"full_history": FULL_HISTORY["content"]}), 200

def retrieve_full_history(response):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400
    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    global FULL_HISTORY
    FULL_HISTORY["content"] = messages
    print("full history uploaded:", FULL_HISTORY["content"])
    return jsonify({"message": "Full Hiistory Uploaded."}), 200


def analyse_img(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    img_dir_path = f"{CURRENT_SESSION_ID}/imgs"
    entries = os.listdir(img_dir_path)
    if len(entries) == 0:
        print(f"No imagess uploaded.")
        return {"INFO": "No images uploaded."}, 200
        
    img_paths = [os.path.abspath(os.path.join(img_dir_path, entry)) for entry in entries]
    messages = read_images(messages, img_paths)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Analysing Images Successful")

    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    return {"message": "Analysing Images Successful"}, 200


def generate_study_guide(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_summary(messages)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Study Guide Successful")
    return {"message": "Generating Study Guide Successful"}, 200

FLASHCARD_Q_AVAILABLE = False
def generate_flashcard_questions(request):
    global CURRENT_SESSION_ID
    global FLASHCARD_Q_AVAILABLE
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        FLASHCARD_Q_AVAILABLE = False
        return {"error": "Session not initialized."}, 400

    num_questions = request.form.get("num_questions")
    difficulty = request.form.get("difficulty")

    if not num_questions:
        print("Number of Questions not Specified.")
        return {"error": "Number of Questions not Specified."}, 400
    if not difficulty:
        print("Difficulty not Specified.")
        return {"error": "Difficulty not Specified."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_flashcards_q(messages, num_questions, difficulty)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Flashcard Questions Successful.")
    FLASHCARD_Q_AVAILABLE = True
    return {"message": "Generating Flashcard Questions Successful."}, 200

def generate_flashcard_answers(request):
    global CURRENT_SESSION_ID
    global FLASHCARD_Q_AVAILABLE
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        FLASHCARD_Q_AVAILABLE = False
        return {"error": "Session not initialized."}, 400
    if not FLASHCARD_Q_AVAILABLE:
        print("No Flashcard Questions Available.")
        return {"error": "No Flashcard Questions Available."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_flashcards_a(messages)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Flashcard Answers Successful.")
    FLASHCARD_Q_AVAILABLE = True
    return {"message": "Generating Flashcard Answers Successful."}, 200

WS_Q_AVAILABLE = False
def generate_worksheet_questions(request):
    global CURRENT_SESSION_ID
    global WS_Q_AVAILABLE
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        FLASHCARD_Q_AVAILABLE = False
        return {"error": "Session not initialized."}, 400

    num_questions = request.form.get("num_questions")
    difficulty = request.form.get("difficulty")

    if not num_questions:
        print("Number of Questions not Specified.")
        return {"error": "Number of Questions not Specified."}, 400
    if not difficulty:
        print("Difficulty not Specified.")
        return {"error": "Difficulty not Specified."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_worksheet_q(messages, num_questions, difficulty)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Worksheet Questions Successful.")
    WS_Q_AVAILABLE = True
    return {"message": "Generating Worksheet Questions Successful."}, 200

def generate_worksheet_answers(request):
    global CURRENT_SESSION_ID
    global WS_Q_AVAILABLE
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        FLASHCARD_Q_AVAILABLE = False
        return {"error": "Session not initialized."}, 400
    if not WS_Q_AVAILABLE:
        print("No Worksheet Questions Available.")
        return {"error": "No Worksheet Questions Available."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_worksheet_a(messages)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Worksheet Answers Successful.")
    FLASHCARD_Q_AVAILABLE = True
    return {"message": "Generating Worksheet Answers Successful."}, 200

def generate_mindmap(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
    messages = generate_mindmap_mermaid(messages)
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generate Mindmap Successful")
    return {"message": "Generate Mindmap Successful"}, 200

def inference_from_prompt(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    prompt = request.form.get("prompt")
    if not prompt:
        print("No prompt input.")
        return {"error": "No prompt input."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)
        
    messages = prompt_input(messages, prompt)
    
    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
        
    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print(f"Prompting Successful")
    return {"message": "Prompting Successful"}, 200
    
    

def overwrite_fn(msg):
    print("Running overwrite_fn with message:", msg)
    # Put your logic here

def process_fn(msg):
    print("Running process_fn with message:", msg)
    # Put your logic here

def analyze_fn(msg):
    print("Running analyze_fn with message:", msg)
    # Put your logic here

function_list = [init_session, append_image, append_pdflike, set_instruct, start_LLM_session, analyse_pdf, retrieve_full_history, analyse_img, generate_study_guide, generate_flashcard_questions, generate_flashcard_answers, generate_worksheet_questions, generate_worksheet_answers, generate_mindmap, inference_from_prompt, overwrite_fn, process_fn, analyze_fn]

@app.route("/upload", methods=["POST"])
def upload_content():
    global server_status

    if server_status["busy"]:
        return jsonify({"error": "Server is busy"}), 503

    # Extract command from request
    command = request.form.get("command")
    if not command:
        return jsonify({"error": "No command provided"}), 400

    # Look up command index
    try:
        cmd_index = command_list.index(command)
    except ValueError:
        return jsonify({"error": f"Unknown command '{command}'"}), 400

    # Set busy, run function synchronously, then set idle
    server_status["busy"] = True
    try:
        function_list[cmd_index](request)  # pass raw request/message
    except Exception as e:
        server_status["busy"] = False
        return jsonify({"error": f"Function execution failed: {e}"}), 500
    finally:
        server_status["busy"] = False


    return jsonify({"message": f"Command '{command}' executed successfully"}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "busy" if server_status["busy"] else "idle"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10227)
