from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import json
import time
import traceback
from datetime import datetime
# from fileConverter import *
from app.services.FileServices.file_service import read_pdf_images, read_pdf, read_images
from app.services.StudyServices.study_guide_service import generate_summary, generate_mindmap_mermaid
from app.services.StudyServices.flashcard_service import generate_flashcards_q, generate_flashcards_a, generate_flashcards_json
from app.services.StudyServices.worksheet_service import generate_worksheet_q, generate_worksheet_a, generate_worksheet_json, mark_question
from app.services.StudyServices.podcast_service import (
    generate_podcast_script,
    generate_podcast_structure,
    generate_podcast_summary,
    split_dialogue_segment,
    estimate_segment_duration,
    create_full_transcript
)
from app.services.StudyServices.comprehension_check_service import generate_segmentation, validate_summary_correctness
from app.services.ChatService.chat_service import prompt_input
from app.utils.utils import update_memory, safe_json_parse
import requests
from markdownConvertor import *
converter = MarkdownToEditorJS()
import shutil
from app.models.LLM_inference import LLM_inference
from dotenv import load_dotenv
from eleven_labs import *
from supabase import create_client
from openai import OpenAI
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)  # allow all origins for frontend JS

# Global state
server_status = {"busy": False}

# ==================== LOGGING MIDDLEWARE ====================
@app.before_request
def log_request():
    """Log incoming request details"""
    g.start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Get command if it exists
    command = request.form.get('command', 'N/A')
    print(f"\n[{timestamp}] → {request.method} {request.path} | command: {command}")
    
    # Log form data (exclude common fields, show important ones)
    if request.form:
        excluded_keys = {'user', 'session', 'command'}
        form_items = {k: v for k, v in request.form.items() if k not in excluded_keys}
        if form_items:
            for key, value in form_items.items():
                # Truncate long values
                if len(str(value)) > 100:
                    print(f"  {key}: {str(value)[:100]}...")
                else:
                    print(f"  {key}: {value}")
    
    # Log JSON data
    if request.is_json:
        try:
            json_data = request.get_json()
            json_str = json.dumps(json_data, indent=2)
            if len(json_str) > 300:
                print(f"  JSON: {json_str[:300]}...")
            else:
                print(f"  JSON: {json_str}")
        except:
            pass
    
    # Log files
    if request.files:
        for key, file in request.files.items():
            print(f"  file: {file.filename}")

@app.after_request
def log_response(response):
    """Log outgoing response details"""
    elapsed_time = time.time() - g.start_time if hasattr(g, 'start_time') else 0
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    status_emoji = "✓" if response.status_code < 400 else "✗"
    print(f"[{timestamp}] ← {status_emoji} {response.status_code} | {elapsed_time:.2f}s\n")
    
    return response
# ==================== END LOGGING MIDDLEWARE ====================


# Define commands and corresponding functions
command_list = [
    "init_session", 
    "append_image", 
    "append_pdflike", 
    "remove_img", 
    "remove_pdf", 
    "analyse_pdf", 
    "analyse_img", 
    "generate_study_guide", 
    "generate_flashcard_questions", 
    "generate_worksheet_questions", 
    "mark_worksheet_questions", 
    "inference_from_prompt", 
    "generate_podcast_structure",  # Generate structure with LLM
    "generate_podcast_audio_from_text",  # TTS + upload from text
    "generate_image",  # AI image generation
    "generate_podcast_image",  # Generate podcast cover image from summary
    # "regenerate_podcast_segment"  # Regenerate a specific segment
    "generate_study_guide_segmentation",
    "validate_study_guide_comperhension",
]

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

    
    messages = generate_flashcards_q(messages, num_questions, difficulty)
    print("Generating Flashcard Questions Successful.")
    messages = generate_flashcards_a(messages)
    print("Generating Flashcard Answers Successful.")
    messages = generate_flashcards_json(messages)

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    safe_json_parse(messages, f"{ROOT_DIR}/{user}/{session}/flashcards.json")
    last_content = messages[-1].get("content", "")
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

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r", encoding="utf-8") as f:
        messages = json.load(f)

    messages = generate_worksheet_q(messages, num_questions, difficulty)
    print("Generating Worksheet Questions Successful.")
    messages = generate_worksheet_a(messages)
    print("Generating Worksheet Answers Successful.")
    messages = generate_worksheet_json(messages, worksheet_id=session, num_questions=num_questions)

    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    
    safe_json_parse(messages, f"{ROOT_DIR}/{user}/{session}/worksheet.json")
    worksheet_str = messages[-1].get("content", "")    
    return {"worksheet": worksheet_str}, 200


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
    markings = mark_question(question, answer, mark_scheme, points)
    return {"marking": markings}, 200


    

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


def generate_podcast_structure_endpoint(request):
    """
    Generate podcast structure using LLM.
    Returns the structured content - frontend stores it.
    """
    user = request.form.get("user")
    session = request.form.get("session")
    
    if not user or not session:
        return {"error": "Session not initialized."}, 400

    # Get podcast parameters
    title = request.form.get("title", "Untitled Podcast")
    description = request.form.get("description", "")
    user_prompt = request.form.get("prompt", "")
    generate_intro = request.form.get("generate_intro", "true").lower() == "true"
    generate_outro = request.form.get("generate_outro", "true").lower() == "true"
    
    # Parse speakers
    speakers_json = request.form.get("speakers", "[]")

    try:
        speakers = json.loads(speakers_json)
        if not speakers:
            speakers = [{"id": "default", "role": "host"}]
    except json.JSONDecodeError:
        return {"error": "Invalid speakers JSON format"}, 400
    
    print(f"🎙️ Generating podcast structure: '{title}'")
    
    # Load conversation history
    with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "r") as f:
        messages = json.load(f)

    try:
        # Generate podcast structure
        messages, structured_content = generate_podcast_structure(
            messages,
            title,
            description,
            user_prompt,
            speakers,
        )
        
        # Save updated messages
        with open(f"{ROOT_DIR}/{user}/{session}/messages.json", "w") as f:
            json.dump(messages, f, indent=2)
        
        print(f"✅ Generated structure with {len(structured_content.get('segments', []))} segments")
        
        # Just return structure - frontend will store it
        return {
            "success": True,
            "structure": structured_content
        }, 200
    
    except Exception as e:
        print(f"❌ Error generating structure: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate structure: {str(e)}"}, 500

def generate_podcast_audio_from_text(request):
    """
    Generate audio from provided text and upload to Supabase.
    Handles both single-speaker and multi-speaker dialogue.
    
    For dialogue, text should be formatted like:
    HOST: Welcome to the show!
    GUEST: Thanks for having me!
    """
    user = request.form.get("user")
    session = request.form.get("session")
    podcast_id = request.form.get("podcast_id")
    segment_index = request.form.get("segment_index")
    text = request.form.get("text")
    
    # Parse speakers JSON (required for dialogue)
    speakers_json = request.form.get("speakers", "[]")
    try:
        speakers = json.loads(speakers_json)
    except json.JSONDecodeError:
        return {"error": "Invalid speakers JSON format"}, 400
    
    if not all([user, session, podcast_id, text]):
        return {"error": "Missing required fields: user, session, podcast_id, text"}, 400
    
    if segment_index is None:
        return {"error": "segment_index is required"}, 400
    
    try:
        segment_index = int(segment_index)
    except ValueError:
        return {"error": "segment_index must be an integer"}, 400
    
    print(f"🎵 Generating audio for segment {segment_index} (podcast: {podcast_id})")
    
    # Create audio directory
    audio_dir = f"{ROOT_DIR}/{user}/{session}/podcasts/{podcast_id}"
    os.makedirs(audio_dir, exist_ok=True)
    
    try:
        uploaded_files = []
        
        # Check if this is dialogue (contains speaker markers like "SPEAKER:")
        # Look for pattern: WORD(S): at start of lines
        is_dialogue = False
        for line in text.split('\n'):
            line_stripped = line.strip().upper()
            if ':' in line_stripped:
                potential_speaker = line_stripped.split(':', 1)[0].strip()
                # Check if this speaker exists in speakers list
                if speakers:
                    for speaker in speakers:
                        if (potential_speaker == speaker['role'].upper() or 
                            potential_speaker == speaker.get('name', '').upper()):
                            is_dialogue = True
                            break
                if is_dialogue:
                    break
        
        if is_dialogue:
            print(f"   Detected dialogue, splitting into parts...")
            
            # Split dialogue into parts
            dialogue_parts = split_dialogue_segment(text, speakers)
            
            # Generate individual audio files
            part_files = []
            total_duration = 0
            
            for part_idx, part in enumerate(dialogue_parts):
                audio_filename = f"segment_{segment_index}_part_{part_idx}.mp3"
                audio_path = f"{audio_dir}/{audio_filename}"
                
                # Generate TTS
                text_to_speech(part['text'], audio_path, voice_id=part['voiceId'])
                duration = estimate_segment_duration(part['text'])
                total_duration += duration
                
                part_files.append(audio_path)
                print(f"      ✅ Part {part_idx}: {part['speaker']} ({duration}s)")
            
            # Concatenate all parts into one audio file
            print(f"   🔗 Joining {len(part_files)} parts into one file...")
            combined_audio = AudioSegment.empty()
            for part_file in part_files:
                audio_segment = AudioSegment.from_mp3(part_file)
                combined_audio += audio_segment
            
            # Export combined file
            combined_filename = f"segment_{segment_index}.mp3"
            combined_path = f"{audio_dir}/{combined_filename}"
            combined_audio.export(combined_path, format="mp3")
            
            # Upload combined file to Supabase
            object_key = f"{user}/{session}/podcasts/{podcast_id}/{combined_filename}"
            with open(combined_path, "rb") as f:
                supabase.storage.from_("media").upload(
                    object_key,
                    f,
                    file_options={"content-type": "audio/mpeg"}
                )
            
            # Clean up individual part files
            for part_file in part_files:
                if os.path.exists(part_file):
                    os.remove(part_file)
            
            print(f"   ✅ Combined audio uploaded ({total_duration}s) -> {object_key}")
            
            return {
                "success": True,
                "segmentIndex": segment_index,
                "objectKey": object_key,
                "duration": total_duration,
                "type": "dialogue",
                "partCount": len(dialogue_parts)
            }, 200
        
        else:
            # Single speaker - need voice_id
            voice_id = request.form.get("voice_id")
            if not voice_id:
                # Try to get from first speaker
                if speakers:
                    voice_id = speakers[0]["id"]
                else:
                    return {"error": "voice_id required for single-speaker segments"}, 400
            
            audio_filename = f"segment_{segment_index}.mp3"
            audio_path = f"{audio_dir}/{audio_filename}"
            
            # Generate TTS
            text_to_speech(text, audio_path, voice_id=voice_id)
            duration = estimate_segment_duration(text)
            
            # Upload to Supabase
            object_key = f"{user}/{session}/podcasts/{podcast_id}/{audio_filename}"
        with open(audio_path, "rb") as f:
            supabase.storage.from_("media").upload(
                    object_key,
                f,
                file_options={"content-type": "audio/mpeg"}
            )
    
            print(f"   ✅ Generated and uploaded ({duration}s) -> {object_key}")
            
            return {
                "success": True,
                "segmentIndex": segment_index,
                "objectKey": object_key,
                "duration": duration,
                "type": "monologue"
            }, 200
    
    except Exception as e:
        print(f"❌ Error generating audio: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate audio: {str(e)}"}, 500


def generate_image(request):
    """
    Generate an image using DALL-E 2 (fastest model)
    
    Parameters:
    - prompt: Text description of the image to generate
    - user: User ID (optional, for file organization)
    - session: Session ID (optional, for file organization)
    - size: Image size - "256x256", "512x512", or "1024x1024" (default: "512x512")
    
    Returns:
    - image_url: URL of the generated image (from OpenAI, temporary)
    - local_path: Path where image is saved locally
    - supabase_url: Public URL from Supabase storage (if user/session provided)
    """
    prompt = request.form.get("prompt")
    if not prompt:
        return {"error": "No prompt provided"}, 400
    
    user = request.form.get("user")
    session = request.form.get("session")
    size = request.form.get("size", "512x512")  # Default to medium size for speed
    
    # Validate size
    valid_sizes = ["256x256", "512x512", "1024x1024"]
    if size not in valid_sizes:
        return {"error": f"Invalid size. Must be one of: {', '.join(valid_sizes)}"}, 400
    
    try:
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        
        print(f"Generating image with prompt: {prompt[:100]}...")
        
        # Generate image using DALL-E 2 (faster than DALL-E 3)
        response = client.images.generate(
            model="dall-e-2",  # Fastest model
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        print(f"✓ Image generated: {image_url}")
        
        # Download and save the image
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            return {"error": "Failed to download generated image"}, 500
        
        # Create directory structure if user/session provided
        if user and session:
            image_dir = os.path.join(ROOT_DIR, user, session, "generated_images")
            os.makedirs(image_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}.png"
            local_path = os.path.join(image_dir, filename)
        else:
            # Save to temp directory if no user/session
            temp_dir = os.path.join(ROOT_DIR, "temp_images")
            os.makedirs(temp_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}.png"
            local_path = os.path.join(temp_dir, filename)
        
        # Save image locally
        with open(local_path, "wb") as f:
            f.write(image_response.content)
        
        print(f"✓ Image saved to: {local_path}")
        
        result = {
            "image_url": image_url,  # OpenAI URL (temporary)
            "local_path": local_path,
            "filename": filename,
            "size": size
        }
        
        # Upload to Supabase if user/session provided
        if user and session:
            try:
                with open(local_path, "rb") as f:
                    supabase_path = f"{user}/{session}/generated_images/{filename}"
                    supabase.storage.from_("media").upload(
                        supabase_path,
                        f,
                        file_options={"content-type": "image/png"}
                    )
                
                # Get public URL
                supabase_url = supabase.storage.from_("media").get_public_url(supabase_path)
                result["supabase_url"] = supabase_url
                print(f"✓ Image uploaded to Supabase: {supabase_url}")
            except Exception as e:
                print(f"⚠️  Failed to upload to Supabase: {e}")
                # Continue anyway, local file still available
        
        return result, 200
        
    except Exception as e:
        print(f"❌ Error generating image: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate image: {str(e)}"}, 500


def generate_podcast_image(request):
    """
    Generate a podcast cover image from a summary
    
    Parameters:
    - summary: Text summary of the podcast content
    - user: User ID
    - session: Session ID
    
    Returns:
    - image_url: URL of the generated image
    - local_path: Path where image is saved locally
    - supabase_url: Public URL from Supabase storage
    """
    summary = request.form.get("summary")
    user = request.form.get("user")
    session = request.form.get("session")
    
    if not summary:
        return {"error": "No summary provided"}, 400
    if not user or not session:
        return {"error": "User and session are required"}, 400
    
    try:
        # Create an image prompt from the summary
        # Use LLM to convert summary into a good image prompt
        prompt_messages = [
            {
                "role": "system",
                "content": "You are an expert at creating image prompts for DALL-E. Given a podcast summary, create a concise, visual prompt for a podcast cover image. The prompt should be descriptive, artistic, and suitable for a podcast cover. Keep it under 400 characters. Focus on visual elements, style, and mood."
            },
            {
                "role": "user",
                "content": f"Create an image prompt for a podcast cover based on this summary:\n\n{summary}"
            }
        ]
        
        print("Generating image prompt from summary...")
        prompt_response = LLM_inference(messages=prompt_messages)
        image_prompt = prompt_response.choices[0].message.content.strip()
        print(f"Generated prompt: {image_prompt}")
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        
        print(f"Generating podcast cover image...")
        
        # Generate image using DALL-E 2 at 512x512 (good for podcast covers)
        response = client.images.generate(
            model="dall-e-2",
            prompt=image_prompt,
            size="512x512",  # Perfect size for podcast covers
            # quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        print(f"✓ Image generated: {image_url}")
        
        # Download the image
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            return {"error": "Failed to download generated image"}, 500
        
        # Create directory structure
        image_dir = os.path.join(ROOT_DIR, user, session, "podcast_images")
        os.makedirs(image_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"podcast_cover_{timestamp}.png"
        local_path = os.path.join(image_dir, filename)
        
        # Save image locally
        with open(local_path, "wb") as f:
            f.write(image_response.content)
        
        print(f"✓ Image saved to: {local_path}")
        
        # Prepare Supabase storage path
        image_key = f"{user}/{session}/podcast_images/{filename}"
        
        result = {
            "image_url": image_url,
            "local_path": local_path,
            "filename": filename,
            "size": "512x512",
            "prompt": image_prompt,
            "image_key": image_key  # Supabase storage path
        }
        
        # Upload to Supabase
        try:
            with open(local_path, "rb") as f:
                supabase.storage.from_("media").upload(
                    image_key,
                    f,
                    file_options={"content-type": "image/png"}
                )
            
            # Get public URL
            supabase_url = supabase.storage.from_("media").get_public_url(image_key)
            result["supabase_url"] = supabase_url
            print(f"✓ Image uploaded to Supabase: {supabase_url}")
            print(f"✓ Image key: {image_key}")
        except Exception as e:
            print(f"⚠️  Failed to upload to Supabase: {e}")
            # Continue anyway, local file still available
        
        return result, 200
        
    except Exception as e:
        print(f"❌ Error generating podcast image: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to generate podcast image: {str(e)}"}, 500
    
def generate_study_guide_segmentation(request):
    user = request.form.get("user")
    session = request.form.get("session")
    study_guide = request.form.get("study_guide")

    if not user or not session:
        return {"error": "Session not initialized."}, 400
    if not study_guide:
        print("Study guide not provided.")
        return {"error": "Study guide not provided."}, 400
    
    messages = generate_study_guide_segmentation(study_guide)
    safe_json_parse(messages, f"{ROOT_DIR}/{user}/{session}/study_guide_segmentation.json")
    segmentation_str = messages[-1].get("content", "")
    return {"segmentation": segmentation_str}, 200  

def validate_study_guide_comperhension(request):
    user = request.form.get("user")
    session = request.form.get("session")
    if not user or not session:
        return {"error": "Session not initialized."}, 400
    study_guide = request.form.get("study_guide")
    segment_content = request.form.get("segment_content")
    student_response = request.form.get("student_response")

    if not study_guide:
        print("Study guide not provided.")
        return {"error": "Study guide not provided."}, 400
    if not segment_content:
        print("Segment content not provided.")
        return {"error": "Segment content not provided."}, 400
    if not student_response:
        print("Student response not provided.")
        return {"error": "Student response not provided."}, 400
    
    messages = validate_summary_correctness(study_guide, segment_content, student_response)
    feedback_str = messages[-1].get("content", "")
    return {"feedback": feedback_str}, 200  



function_list = [
    init_session, 
    append_image, 
    append_pdflike, 
    remove_img, 
    remove_pdf, 
    analyse_pdf, 
    analyse_img, 
    generate_study_guide, 
    generate_flashcard_questions, 
    generate_worksheet_questions, 
    mark_worksheet_question, 
    inference_from_prompt, 
    generate_podcast_structure_endpoint,  # Generate structure
    generate_podcast_audio_from_text,  # TTS + upload
    generate_image,  # AI image generation
    generate_podcast_image,  # Generate podcast cover from summary
    # regenerate_podcast_segment_endpoint  # Regenerate one segment
    generate_study_guide_segmentation,
    validate_study_guide_comperhension
]

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
    PORT = int(os.getenv("PORT", 61016))
    app.run(threaded=True, host="0.0.0.0", port=PORT)
