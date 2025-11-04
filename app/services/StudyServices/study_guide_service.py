import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory

def generate_summary(messages):
    """Generate descriptive summary in study-guide style"""
    messages.append({"role": "user", "content": "Now, upon all the information either provided to you, or spotted in images, please \
    generate a descriptive summary in the form of a study guide. In case of any math syntax, DO NOT use latex. Provide only what is asked - the study guide. \
    DO NOT put any words of confirmation like 'sure', 'ok...', or any comments at the end. Just provide the study guide (NOT including flashcards / worksheets). Also, write in Markdown"})
    
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


