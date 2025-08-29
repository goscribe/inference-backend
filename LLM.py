#!/usr/bin/env python3
import ast
import json
import os
import requests
import fitz  # PyMuPDF

# --------- Utility Functions ---------

def update_memory(messages, resp):
    """Updates messages with model response from streaming API"""
    last_output = ''
    for line in resp.iter_lines():
        if line:
            y = json.loads(line.decode("utf-8"))
            last_output += y['message']['content']
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
        except:
            print(f"Warning: failed to save image {output_name}")

# --------- Core Module Functions ---------

MODEL_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma3:27b"  # replace with your model

def read_pdf(messages, pdf_paths):
    """Read PDF text and append instructions to messages"""
    for pdf_fp in pdf_paths:
        pdf_text = extract_text_pdf(pdf_fp)
        messages.append({"role": "user", "content": f"Read the following content from a pdf file: \"{pdf_text}\" Remember the content. You will have to use it later. \
        At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."})
        resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
        update_memory(messages, resp)
    return messages

def read_pdf_images(messages, pdf_paths, img_saving_path):
    """Generate PDF page images and append instructions to messages"""
    for pdf_fp in pdf_paths:
        prepare_pdf(pdf_fp, img_saving_path)
    
    doc_list = sorted(os.listdir(img_saving_path))
    for doc_name in doc_list:
        files = sorted(os.listdir(f"{img_saving_path}/{doc_name}"))
        abs_paths = [os.path.abspath(os.path.join(f"{img_saving_path}/{doc_name}", f)) for f in files]
        for path in abs_paths:
            messages.append({
                "role": "user",
                "content": f"Please look at the image \"{path}\". This is a page from the pdf you just read. This section is for you to scan through the figures in the PDFs. If there is something new and useful, remember its content. You will be later using \
                these informations to generate something. At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."
            })
            resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
            update_memory(messages, resp)
    return messages

def read_images(messages, image_paths):
    """Read arbitrary images and append instructions"""
    for img_fp in image_paths:
        messages.append({
            "role": "user",
            "content": f"Look at the image at \"{img_fp}\". Remember its content. You will be later using \
            these informations to generate something. At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."
        })
        resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
        update_memory(messages, resp)
    return messages

def generate_summary(messages):
    """Generate descriptive summary in study-guide style"""
    messages.append({"role": "user", "content": "Now, upon all the information either provided to you, or sppotted in images, Please \
    generate a descriptive summary in the form of a study guide. In case of any math syntax, DO NOT use latex. Provide only what is asked - the study guide. DO NOT put any words of \
    confirmation like 'sure', 'ok...', or any comments at the end. Just provide the study guide (NOT including fashcards / worksheets)."})
    
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages

def generate_flashcards_q(messages, num_flashcards=5, difficulty="hard"):
    """Generate flashcard questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or sppotted in images, \
    please generate {num_flashcards} flashcard questions. The questions shall have difficulty level '{difficulty}'. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages

def generate_flashcards_a(messages):
    """Generate flashcard answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Again, do not respond excess words."})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages

def generate_worksheet_q(messages, num_quests=5, difficulty="hard"):
    """Generate worksheet questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or sppotted in images, \
    please generate {num_quests} long questions for a worksheet. They can be of any type: MCQs, FRQs, or even essays, but be organized in terms of the order so that it fits well with a worksheet. The questions shall have difficulty level '{difficulty}'. Please include at least 2 MCQs\
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages

def generate_worksheet_a(messages):
    """Generate worksheet answers"""
    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    Again, do not respond excess words."})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
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
    Each note is labeled with a capital letter (e.g., `A`). To connect two nodes, use `-->`. The text in a node is wraped in 
    `()` or `[]` or `(())` or `{}`. `()` represents a rectangle of rounded corners, so `C("Round Rect")` will simply be a node labeled by `C`,
    of shape round rectangular, and with text 'Round Rect' in the middle. Similarly, `[]` creates nodes with square rectangular shapes. 
    `(())` creates nodes that are circular. Finally `{}` creates rombus shapped nodes. You can also add labels to the connections: 
    do it with `-- "<connection label>" -->`. Now feel free to draw the mindmap with this syntax. Start the file with `graph LR\n`. 
    Always wrap text in "". this is for safty issue. Sometimes, you would have to include () in a node, and that breaks the mermaid.js syntax. 
    Remember, only produce the mermaid.js file. Also use connection labels where you think the association need more clarification. 
    For the use of latex if math is needed. Please use $$<latex content>$$. mermaid.js only recognize double doller signs. 
    In any case, DO NOT use `&`. This breaks mermaid graph rendering. Use the word "and" instead.
    Do not include any additional text. Important: **generate ONLY the plain text** This means you shouldn't put something like "```mermaid" in front.
    You MUST continue (**WITHOUT INSERTING ANYTHING IN FRONT**) after this header:
    graph LR;\n"""})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages

def prompt_input(messages, prompt):
    """Generate any inference from any prompt"""
    messages.append({"role": "user", "content": prompt})
    resp = requests.post(MODEL_URL, json={"model": MODEL_NAME, "messages": messages})
    update_memory(messages, resp)
    return messages
