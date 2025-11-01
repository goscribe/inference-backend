#!/usr/bin/env python3
import ast
import json
import os
import fitz  # PyMuPDF
from LLM_inference import LLM_inference
from dotenv import load_dotenv
import base64

load_dotenv()

# --------- Utility Functions ---------

def update_memory(messages, resp):
    """Updates messages with model response from OpenAI"""
    last_output = resp.choices[0].message.content
    messages.append({"role": "assistant", "content": last_output})
    return messages

def extract_text_pdf(path):
    """Extract text from a PDF"""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def prepare_pdf(doc_path, image_saving_path):
    """Generate page images from a PDF"""
    doc_name, _ = os.path.splitext(os.path.basename(doc_path))
    os.makedirs(f"{image_saving_path}/{doc_name}", exist_ok=True)
    
    doc = fitz.open(doc_path)
    for page_num, page in enumerate(doc):
        pix = page.get_pixmap()
        output_name = f"{image_saving_path}/{doc_name}/page_{page_num + 1}.png"
        try:
            pix.save(output_name)
        except Exception as e:
            print(f"Warning: failed to save image {output_name} ({e})")

def encode_image(image_path):
    """Encode an image file to base64 for sending inline"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# --------- Core Module Functions ---------

def read_pdf(messages, pdf_paths):
    """Read PDF text and append instructions to messages"""
    for pdf_fp in pdf_paths:
        pdf_text = extract_text_pdf(pdf_fp)
        messages.append({"role": "user", "content": f"Read the following content from a pdf file: \"{pdf_text}\" Remember the content. You will have to use it later. \
        At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."})
        resp = LLM_inference(messages=messages)
        update_memory(messages, resp)
    return messages

def read_pdf_images(messages, pdf_paths, img_saving_path):
    """Generate PDF page images and append all pages per document into one message"""
    for pdf_fp in pdf_paths:
        # Prepare the PDF (convert to page images)
        prepare_pdf(pdf_fp, img_saving_path)

        doc_name = os.path.splitext(os.path.basename(pdf_fp))[0]
        doc_dir = os.path.join(img_saving_path, doc_name)

        if not os.path.exists(doc_dir):
            print(f"Warning: directory {doc_dir} not found, skipping {pdf_fp}")
            continue

        files = sorted(os.listdir(doc_dir))
        abs_paths = [os.path.abspath(os.path.join(doc_dir, f)) for f in files]

        # Build one message containing all images for this document
        content = [{
            "type": "text",
            "text": (
                f"The following images are all pages from the PDF '{doc_name}'. "
                "Carefully examine each page and internally note any figures, tables, or information "
                "that might be useful for later tasks. Do not produce any response yet; "
                "this step is only for you to remember the visual content for future reference."
            )
        }]

        for path in abs_paths:
            base64_image = encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })

        # Append this one merged message
        messages.append({
            "role": "user",
            "content": content
        })

        resp = LLM_inference(messages=messages)

        update_memory(messages, resp)

    return messages



def read_images(messages, image_paths):
    for img_fp in image_paths:
        # Encode the image as base64
        base64_image = encode_image(img_fp)
        # Append user instruction with inline image
        image_message = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
        messages.append({
            "role": "user",
            "content": [
                {"type": "text",
                 "text": f"Look at the image at \"{img_fp}\". Remember its content. "
                         "You will later use this information to generate something. "
                         "At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."},
                image_message
            ]
        })
        
        resp = LLM_inference(messages=messages)
        
        # Update messages with the model's response (like your update_memory)
        update_memory(messages, resp)
        
    return messages

def generate_summary(messages):
    """Generate descriptive summary in study-guide style"""
    messages.append({"role": "user", "content": "Now, upon all the information either provided to you, or spotted in images, please \
    generate a descriptive summary in the form of a study guide. In case of any math syntax, DO NOT use latex. Provide only what is asked - the study guide. \
    DO NOT put any words of confirmation like 'sure', 'ok...', or any comments at the end. Just provide the study guide (NOT including flashcards / worksheets). Also, write in Markdown"})
    
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

def generate_flashcards_q(messages, num_flashcards=5, difficulty="hard"):
    """Generate flashcard questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or spotted in images, \
    please generate {num_flashcards} flashcard questions. The questions shall have difficulty level '{difficulty}'. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

def generate_flashcards_a(messages):
    """Generate flashcard answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

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

def generate_worksheet_a(messages):
    """Generate worksheet answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    Again, do not respond excess words."})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

def generate_mindmap_mermaid(messages):
    """Generate mermaid plot for mind map"""
    messages.append({"role": "user", "content": """Now, please generate a mindmap of the given information using the provided syntax. 
    Actually, this is mermaid.js phrasing in case you know. 
    Given is an example: 
    'graph LR;
        A["Square Rect"] -- "Link text" --> B(("Circle"));
        A --> C("Round Rect");
        B --> D{"Rhombus"};
        C --> D';
    Each note is labeled with a capital letter (e.g., `A`). To connect two nodes, use `-->`. The text in a node is wrapped in 
    `()` or `[]` or `(())` or `{}`. `()` represents a rectangle of rounded corners, so `C("Round Rect")` will simply be a node labeled by `C`,
    of shape round rectangular, and with text 'Round Rect' in the middle. Similarly, `[]` creates nodes with square rectangular shapes. 
    `(())` creates nodes that are circular. Finally `{}` creates rhombus-shaped nodes. You can also add labels to the connections: 
    do it with `-- "<connection label>" -->`. Now feel free to draw the mindmap with this syntax. Start the file with `graph LR\n`. 
    Always wrap text in "". this is for safety issue. Sometimes, you would have to include () in a node, and that breaks the mermaid.js syntax. 
    Remember, only produce the mermaid.js file. Also use connection labels where you think the association need more clarification. 
    For the use of latex if math is needed. Please use $$<latex content>$$. mermaid.js only recognizes double dollar signs. 
    In any case, DO NOT use `&`. This breaks mermaid graph rendering. Use the word "and" instead.
    Do not include any additional text. Important: **generate ONLY the plain text** This means you shouldn't put something like "```mermaid" in front.
    You MUST continue (**WITHOUT INSERTING ANYTHING IN FRONT**) after this header:
    graph LR;\n"""})
    resp = LLM_inference(messages=messages)
    update_memory(messages, resp)
    return messages

def prompt_input(messages, prompt):
    """Generate any inference from any prompt"""
    messages.append({"role": "user", "content": prompt})
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

    model_output = response.choices[0].message.content
    messages.append({"role": "assistant", "content": model_output})
    return messages
