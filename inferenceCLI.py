#!/usr/bin/env python3
import argparse
import ast
import json
import requests
import fitz  # PyMuPDF
import os

def update_memory(messages, resp):
    last_output = ''
    for line in resp.iter_lines():
        if line:
            y = json.loads(line.decode("utf-8"))
            last_output = last_output + y['message']['content']
    
    messages.append({"role": "assistant", "content": last_output})
    return messages

def prepare_pdf(doc_path):
    doc_name, ext = os.path.splitext(os.path.basename(doc_path))
    try:
        os.mkdir(f"pdf_images/{doc_name}")
    except:
        print("Warning: failed to create image container")
    
    doc = fitz.open(doc_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap()

        try:
            output_name = f"pdf_images/{doc_name}/page_{page_num + 1}.png"
            pix.save(output_name)
        except:
            print("Warning: failed to save image")

def extract_text_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def main():
    parser = argparse.ArgumentParser(description="Independent script for flashcard & WSQ generation")

    # Define arguments
    parser.add_argument("--instruction_text", type=str, required=True,
                        help="Instruction text (string)")
    parser.add_argument("--pdf_paths", type=str, default="[]",
                        help="List of PDF paths in form ['str1','str2',...]")
    parser.add_argument("--pdf_text", type=str, default="",
                        help="Extracted or provided PDF text")
    parser.add_argument("--image_paths", type=str, default="[]",
                        help="List of image paths in form ['str1','str2',...]")
    parser.add_argument("--num_flashcard", type=int, default=5,
                        help="Number of flashcards to generate")
    parser.add_argument("--flashcard_difficulty", type=str, choices=["easy", "medium", "hard"], default="hard",
                        help="Flashcard difficulty")
    parser.add_argument("--num_wsq", type=int, default=10,
                        help="Number of WSQ questions to generate")
    parser.add_argument("--wsq_difficulty", type=str, choices=["easy", "medium", "hard"], default="hard",
                        help="WSQ difficulty")

    # Parse arguments
    args = parser.parse_args()

    instruction_text = args.instruction_text
    pdf_paths = ast.literal_eval(args.pdf_paths)  # safely convert string list -> Python list
    pdf_text = args.pdf_text
    image_paths = ast.literal_eval(args.image_paths)
    num_flashcard = args.num_flashcard
    flashcard_difficulty = args.flashcard_difficulty
    num_wsq = args.num_wsq
    wsq_difficulty = args.wsq_difficulty

    # Model Config
    url = "http://localhost:11434/api/chat"
    model = "gemma3:27b"  # replace with your model

    """ System Prompt """
    messages = [
        {"role": "system", "content": "Your task is to serve as a study tool - given the info that will be provided next, in form \
        of either text or image, you will try your best to understant them. You will be asked to generate a summary in case we have to \
        check your understanding. You will generate a study guide covering the given information. The guide shall contain 1) a \
        descriptive summary of all given materials in the form of a lecture note, 2) a set of flashcard questions, short in form, along with \
        corresponding answers, 3) a organized worksheet served as an excercise, supplied along with an answer sheet. \
        Your responses will be listened by a front end, so answer only what is being asked, and follow the form. Good Luck!"},
        {"role": "user", "content": instruction_text},
    ]

    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )

    messages = update_memory(messages, resp)  

    """Read all Images"""
    for img_fp in image_paths:
        messages.append({"role": "user", "content": f"Look at the image at {img_fp}. Summarize its content."})
        resp = requests.post(
            url,
            json={"model": model, "messages": messages}
        )
        messages = update_memory(messages, resp)

    """Read PDF text content"""
    for pdf_fp in pdf_paths:
        pdf_text = extract_text_pdf(pdf_fp)
        messages.append({"role": "user", "content": f"Read the following content from a pdf file: \"{pdf_text}\" Remember the content. You will have to use it later. \
        At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."})
        resp = requests.post(
            url,
            json={"model": model, "messages": messages}
        )
        messages = update_memory(messages, resp)
    print("finished reading all pdfs")

    """Read PDF Images"""
    try: 
        os.mkdir("pdf_images")
    except:
        pass
    for pdf_fp in pdf_paths:
        prepare_pdf(pdf_fp)
    # Iterate through docs, then feed all page images to LLM.
    doc_list = sorted(os.listdir("pdf_images"))
    for doc_image_fp in doc_list:
        files = sorted(os.listdir(f"pdf_images/{doc_image_fp}"))
        abs_paths = [os.path.abspath(os.path.join(f"pdf_images/{doc_image_fp}", f)) for f in files]
        for path in abs_paths:
            messages.append({"role": "user", "content": f"Please look at the image \"{path}\". This is a page from the pdf you just read. This section is for you to scan through the figures in the PDFs. If there is something new and useful, remember its content. You will be later using \
            these informations to generate something. At this stage, you don't have to generate anything yet. Maybe just note something down for you to remember later."})
            resp = requests.post(
                url,
                json={"model": model, "messages": messages}
            )
            messages = update_memory(messages, resp)
    print("INFO: Finished reading all images")

    """Generate Descriptive Summary"""
    messages.append({"role": "user", "content": "Now, upon all the information either provided to you, or sppotted in images, Please \
    generate a descriptive summary in the form of a lecture note. In case of any math syntax, use latex - quoted in $$. Provide only what is asked - the lecture note. Do not put any words of \
    confirmation like 'sure', 'ok...', or any comments at the end. Just provide the lecture note."})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    """Flashcard Questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or sppotted in images, \
    please generate {num_flashcard} flashcard questions. The questions shall have difficulty level '{flashcard_difficulty}'. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    The answers shall be concise, short, as conforming the the form of flashcards. \
    Again, do not respond excess words."})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    """Worksheet Questions"""
    messages.append({"role": "user", "content": f"Now, upon all the information either provided to you, or sppotted in images, \
    please generate {num_wsq} long questions for a worksheet. They can be of any type: MCQs, FRQs, or even essays, but be organized in terms of the order so that it fits well with a worksheet. The questions shall have difficulty level '{wsq_difficulty}'. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Question1> \n 2. <Question2> \n 3. <Question3> \n ... \
    Do not include the answers - they will be asked in the next message. Again, do not respond excess words."})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    messages.append({"role": "user", "content": f"Now, generate the corresponding answers. \
    FOLLOW STRICTLY THIS FORMAT: \n\
    1. <Answer1> \n 2. <Answer2> \n 3. <Answer3> \n ... \
    Again, do not respond excess words."})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    """Mindmap"""
    messages.append({"role": "user", "content": """Now, please generate a mindmap of the given information using the provided syntax. 
    Actually, this is mermaid.js phrasing in case you know. 
    Given is an example: 
    'graph LR
        A["Square Rect"] -- "Link text" --> B(("Circle"))
        A --> C("Round Rect")
        B --> D{"Rhombus"}
        C --> D'
    Each note is labeled with a capital letter (e.g., `A`). To connect two nodes, use `-->`. The text in a node is wraped in 
    `()` or `[]` or `(())` or `{}`. `()` represents a rectangle of rounded corners, so `C("Round Rect")` will simply be a node labeled by `C`,
    of shape round rectangular, and with text 'Round Rect' in the middle. Similarly, `[]` creates nodes with square rectangular shapes. 
    `(())` creates nodes that are circular. Finally `{}` creates rombus shapped nodes. You can also add labels to the connections: 
    do it with `-- "<connection label>" -->`. Now feel free to draw the mindmap with this syntax. Start the file with `graph LR\n`. 
    Always wrap text in "". this is for safty issue. Sometimes, you would have to include () in a node, and that breaks the mermaid.js syntax. 
    Remember, only produce the mermaid.js file. Also use connection labels where you think the association need more clarification. 
    For the use of latex if math is needed. Please use $$<latex content>$$. mermaid.js only recognize double doller signs. 
    In any case, DO NOT use `&`. This breaks mermaid graph rendering. Use the word "and" instead.
    Do not include any additional text. Important: **Spit the plain text, so no `s quoted outside.**
    You MUST continue after this header:
    graph LR\n"""})
    resp = requests.post(
        url,
        json={"model": model, "messages": messages}
    )
    messages = update_memory(messages, resp)

    with open("full_inference.json", "w") as f:
        json.dump(messages, f, indent=2)

    

if __name__ == "__main__":
    main()
