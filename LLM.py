from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from fileConverter import *
from LLM import read_pdf, update_memory, read_pdf_images, read_images, generate_summary, generate_flashcards_q, generate_flashcards_a, generate_worksheet_q, generate_worksheet_a, generate_mindmap_mermaid, prompt_input
import requests
from markdownConvertor import *
converter = MarkdownToEditorJS()
import shutil

app = Flask(__name__)
CORS(app)  # allow all origins for frontend JS

# Global state
server_status = {"busy": False}

# Define commands and corresponding functions
command_list = ["init_session", "restore_session", "append_image", "append_pdflike", "remove_img", "remove_pdf", "set_instruct", "start_LLM_session", "analyse_pdf", "retrieve_full_history", "analyse_img", "generate_study_guide", "generate_flashcard_questions", "generate_worksheet_questions", "generate_mindmap", "inference_from_prompt"]

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

def restore_session(request):
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = request.form.get("id")
    if not CURRENT_SESSION_ID:
        print("No session ID provided")
        return {"error": "No session ID provided"}, 400

    if not os.path.isdir(CURRENT_SESSION_ID):
        print("Not an existing session.")
        return {"error": f"Session {CURRENT_SESSION_ID} does not exist"}, 404

    print(f"Session '{CURRENT_SESSION_ID}' restored.")
    return {"message": f"Session '{CURRENT_SESSION_ID}' restored successfully"}, 200

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

def remove_img(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    filename = request.form.get("filename")
    if not filename:
        print("No filename provided in form data.")
        return {"error": "No filename provided."}, 400

    safe_name = os.path.basename(filename)
    imgs_dir = os.path.join(CURRENT_SESSION_ID, "imgs")
    # Extra safety: ensure imgs_dir is normalized and file path lives inside it
    file_path = os.path.normpath(os.path.join(imgs_dir, safe_name))
    imgs_dir_norm = os.path.normpath(imgs_dir)

    if not file_path.startswith(imgs_dir_norm + os.sep) and file_path != imgs_dir_norm:
        # If this triggers, the filename attempted to escape the imgs dir
        print(f"Attempted path traversal: {filename} -> {file_path}")
        return {"error": "Invalid filename."}, 400

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return {"error": f"File not found: {safe_name}"}, 404

    if not os.path.isfile(file_path):
        print(f"Path exists but is not a file: {file_path}")
        return {"error": "Target is not a file."}, 400

    try:
        os.remove(file_path)
        print(f"Removed file: {file_path}")
        return {"message": f"File '{safe_name}' removed successfully."}, 200
    except OSError as e:
        print(f"Failed to remove file {file_path}: {e}")
        return {"error": f"Failed to remove file: {str(e)}"}, 500

def remove_pdf(request):
    global CURRENT_SESSION_ID
    if not CURRENT_SESSION_ID:
        print("Session not initialized.")
        return {"error": "Session not initialized."}, 400

    filename = request.form.get("filename")
    if not filename:
        print("No filename provided in form data.")
        return {"error": "No filename provided."}, 400

    # Normalize and secure the filename (prevent path traversal)
    safe_name = os.path.basename(filename)
    pdfs_dir = os.path.join(CURRENT_SESSION_ID, "pdfs")
    file_path = os.path.normpath(os.path.join(pdfs_dir, safe_name))
    pdfs_dir_norm = os.path.normpath(pdfs_dir)

    if not (file_path == pdfs_dir_norm or file_path.startswith(pdfs_dir_norm + os.sep)):
        print(f"Attempted path traversal: {filename} -> {file_path}")
        return {"error": "Invalid filename."}, 400

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return {"error": f"File not found: {safe_name}"}, 404

    if not os.path.isfile(file_path):
        print(f"Path exists but is not a file: {file_path}")
        return {"error": "Target is not a file."}, 400

    # Determine the associated images folder name (basename without extension)
    base_no_ext = os.path.splitext(safe_name)[0]
    pdf_images_root = os.path.join(CURRENT_SESSION_ID, "pdf_images")
    associated_img_folder = os.path.normpath(os.path.join(pdf_images_root, base_no_ext))

    # Safety check: ensure associated_img_folder sits under pdf_images_root
    pdf_images_root_norm = os.path.normpath(pdf_images_root)
    if not (associated_img_folder == pdf_images_root_norm or associated_img_folder.startswith(pdf_images_root_norm + os.sep)):
        # This should not normally happen because we used basename and a simple folder name,
        # but we check to be extra safe.
        print(f"Associated image folder path unsafe: {associated_img_folder}")
        return {"error": "Invalid associated image folder path."}, 400

    # Attempt removal of the PDF file and then the folder (if present)
    try:
        os.remove(file_path)
        print(f"Removed PDF file: {file_path}")
    except OSError as e:
        print(f"Failed to remove PDF file {file_path}: {e}")
        return {"error": f"Failed to remove PDF file: {str(e)}"}, 500

    img_folder_removed = False
    if os.path.isdir(associated_img_folder):
        try:
            shutil.rmtree(associated_img_folder)
            img_folder_removed = True
            print(f"Removed associated image folder: {associated_img_folder}")
        except OSError as e:
            # PDF removed, but failed to remove image folder — return partial success
            print(f"Failed to remove associated image folder {associated_img_folder}: {e}")
            return {
                "message": f"PDF '{safe_name}' removed, but failed to remove associated image folder '{base_no_ext}'.",
                "error": str(e)
            }, 500

    # Successful removal
    msg = f"PDF '{safe_name}' removed successfully."
    if img_folder_removed:
        msg += f" Associated image folder '{base_no_ext}' removed."
    return {"message": msg}, 200



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
    print(pdf_paths)
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
        return {"error": "Session not initialized."}, 400

    with open(f"{CURRENT_SESSION_ID}/messages.json", "r") as f:
        messages = json.load(f)

    messages = generate_summary(messages)
    markdown_text = messages[-1].get("content", "")
    print("Generating Study Guide Markdown Successfully")
    messages = generate_mindmap_mermaid(messages)
    mindmap_mermaid = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = markdown_text
    print("Generating Study Guide Mindmap Successfully")

    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)
    
    # editorjs_json = converter.convert(markdown_text)
    # json_str = json.dumps(editorjs_json, indent=2, ensure_ascii=False)
    
    return {"markdown": markdown_text, "mermaid": mindmap_mermaid}, 200


def generate_flashcard_questions(request):
    global CURRENT_SESSION_ID
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
    print("Generating Flashcard Questions Successful.")
    messages = generate_flashcards_a(messages)
    print("Generating Flashcard Answers Successful.")

    messages.append({"role": "user", "content": """Now, read off the questions and answers you wrote. Convert them into a JSON file according to this format: 
    [
        {"term": "<Question 1>",
        definition: "<Answer 1>"}, 
        {"term": "<Question 2>",
        definition: "<Answer 2>"}, 
        {"term": "<Question 3>",
        definition: "<Answer 3>"}, 
    ]
    Adhere strictly to this format. When you start your generation. Do not include any texts that does not belong to the JSON.
    Return ONLY the JSON file following "[..." You shall NOT have any thing like "json" or `` in front, ONLY the raw text for the JSON source!!!
    Remember, ONLY THE RAW TEXT, not a code block.
    Be aware of any punctuations that might conflict with JSON syntax. This is extremely important!!! Now, you may begin."""})
    
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)  

    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Flashcard JSON Successful.")
    FLASHCARD_Q_AVAILABLE = True
    return {"last_response": last_content}, 200

     
    

def generate_worksheet_questions(request):
    global CURRENT_SESSION_ID
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
    print("Generating Worksheet Questions Successful.")
    messages = generate_worksheet_a(messages)
    print("Generating Worksheet Answers Successful.")

    messages.append({"role": "user", "content": f"""Now, read off the questions and answers you wrote. Convert them into a JSON file according to this format: 
    {{
        id: {CURRENT_SESSION_ID},
        title: '<A Title For Your Worksheet>',
        description: '<Make a Description for this Worksheet>',
        difficulty: '<Choice from these: EASY, MEDIUM, HARD>',
        estimatedTime: '<Estimate how long required to do the questions>',
        problems: [
        {{
          question: '<Question 1>',
          answer: '<Answer 1>',
          type: 'TEXT <if the question is not a MCQ, put TEXT here>',
        }},
        {{
          question: '<Question 2>',
          answer: '<Answer 2>',
          type: 'TEXT',
        }},
        {{
          question: '<Question 3>',
          answer: '<Answer 3>',
          type: 'MULTIPLE_CHOICE <if the question is MCQ, put MULTIPLE_CHOICE here>',
          options: ['<Option 1>', '<Option 2>', '<Option 3>', ...],
        }},
        {{
          question: '<Question 4>',
          answer: '<Answer 4>',
          type: 'NUMERIC <if the answer is one single numerical value, put NUMERIC here>',
        }},
        {{
          question: '<Question 5>',
          answer: '<Answer 5>',
          type: 'TRUE_FALSE <if the answer is either true or false, put TRUE_FALSE here>',
        }},
        {{
          question: '<Question 5>',
          answer: '<Answer 5>',
          type: 'MATCHING <if the task is to select all matching options, put MATCHING here>',
          options: ['Option 1', 'Option 2', 'Option 3', ...],
        }}, 
        ...
        ],
    }}
    Adhere strictly to this format. When you start your generation. Do not include any texts that does not belong to the JSON.
    Return ONLY the JSON file following "[..." You shall NOT have any thing like "json" or `` in front, ONLY the raw text for the JSON source!!!
    Remember, ONLY THE RAW TEXT, not a code block.
    Be aware of any punctuations that might conflict with JSON syntax. This is extremely important!!! Now, you may begin."""})
    
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)  

    with open(f"{CURRENT_SESSION_ID}/messages.json", "w") as f:
        json.dump(messages, f, indent=2)

    last_content = messages[-1].get("content", "")
    global LAST_RESPONSE
    LAST_RESPONSE["content"] = last_content
    print("Generating Worksheet JSON Successful.")
    FLASHCARD_Q_AVAILABLE = True
    return {"last_response": last_content}, 200

    

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
    print("Last message:", messages[-1])
    print("Prompting Successful")
    return {"last_response": last_content}, 200
    
    

def overwrite_fn(msg):
    print("Running overwrite_fn with message:", msg)
    # Put your logic here

def process_fn(msg):
    print("Running process_fn with message:", msg)
    # Put your logic here

def analyze_fn(msg):
    print("Running analyze_fn with message:", msg)
    # Put your logic here

@app.route("/session_files", methods=["GET"])
def get_all_files():
    base_pwd = os.getcwd()

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

    sessions = {}
    for entry in sorted(os.listdir(base_pwd)):
        if entry.startswith(".") or entry == "__pycache__":
            continue
        session_path = os.path.join(base_pwd, entry)
        if not os.path.isdir(session_path):
            continue

        # Only treat as a session if it has at least pdfs/ or imgs/
        pdf_dir = os.path.join(session_path, "pdfs")
        img_dir = os.path.join(session_path, "imgs")
        if not (os.path.isdir(pdf_dir) or os.path.isdir(img_dir)):
            continue

        pdfs = list_dir(pdf_dir, "pdf")
        imgs = list_dir(img_dir, "img")
        all_files = sorted(pdfs + imgs, key=lambda x: (x["type"], x["name"]))

        sessions[entry] = {
            "counts": {"pdfs": len(pdfs), "imgs": len(imgs), "all": len(all_files)},
            "pdfs": pdfs,
            "imgs": imgs,
            "all": all_files,
        }

    resp = {"sessions": sessions, "session_count": len(sessions)}
    return jsonify(resp), 200


function_list = [init_session, restore_session, append_image, append_pdflike, remove_img, remove_pdf, set_instruct, start_LLM_session, analyse_pdf, retrieve_full_history, analyse_img, generate_study_guide, generate_flashcard_questions, generate_worksheet_questions, generate_mindmap, inference_from_prompt]

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
        # Capture the function's return value
        func_response = function_list[cmd_index](request)  # always (dict, status)
        if isinstance(func_response, tuple) and len(func_response) == 2:
            data, status_code = func_response
            return jsonify(data), status_code
        else:
            return jsonify(func_response), 200
    except Exception as e:
        server_status["busy"] = False
        return jsonify({"error": f"Function execution failed: {e}"}), 500
    finally:
        server_status["busy"] = False

    
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
    app.run(host="0.0.0.0", port=10227)
