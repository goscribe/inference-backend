import ast
import json
import os
import fitz  # PyMuPDF
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory
from app.utils.workspace_context import get_workspace_context_as_message

def generate_summary(messages, workspace_id=None, user_id=None):
    """Generate descriptive summary in study-guide style"""
    # Prepend workspace context if available
    if workspace_id and user_id:
        context_message = get_workspace_context_as_message(
            workspace_id=workspace_id,
            user_id=user_id,
            include_file_assets=True,
            include_flashcards=True
        )
        if context_message:
            # Insert after system message (if exists) or at beginning
            insert_index = 0
            if messages and messages[0].get("role") == "system":
                insert_index = 1
            messages.insert(insert_index, context_message)
    messages.append({"role": "user", "content": "Now, upon all the information either provided to you, or spotted in images, please \
    generate a descriptive summary in the form of a study guide. Format this study guide as if it were written for a student - make it clear, \
    well-organized, easy to understand, and educational. Use a student-friendly tone that explains concepts clearly, breaks down complex ideas into \
    digestible sections, and highlights key points. Structure it like comprehensive study notes that a student would use to review and learn the material. \
    For any mathematical expressions, use LaTeX syntax with markdown formatting: use $...$ for inline math (e.g., $x^2 + y^2 = r^2$) and $$...$$ for block/display math equations (e.g., $$\\int_0^1 f(x)dx$$). Provide only what is asked - the study guide. \
    DO NOT put any words of confirmation like 'sure', 'ok...', or any comments at the end. Just provide the study guide (NOT including flashcards / worksheets). Also, write in Markdown\
    Make it as comprehensive as possible, include all materials that are present in the workspace context and the files provided. Additionally, if any more complex graphics are needed, please use embedded html (SVG vector graphics) to represent these.\n\n\
    IMPORTANT: When generating SVG graphics, follow these guidelines:\n\
    - Use a viewBox that provides adequate space (e.g., viewBox=\"0 0 800 600\" or larger for complex diagrams)\n\
    - Set explicit width and height attributes (e.g., width=\"800\" height=\"600\") to ensure proper sizing\n\
    - Use detailed, precise coordinates and measurements - avoid tiny or cramped graphics\n\
    - Include proper styling with CSS within the SVG (fill, stroke, stroke-width, font-size, etc.)\n\
    - For text elements, use appropriate font sizes (minimum 14px, preferably 16-20px for readability)\n\
    - Use clear, visible stroke widths (minimum 2px for lines, thicker for emphasis)\n\
    - Ensure adequate spacing between elements for clarity\n\
    - Use meaningful colors and contrast for better visibility\n\
    - For diagrams with multiple elements, scale appropriately so nothing appears too small\n\
    - Example structure: <svg viewBox=\"0 0 800 600\" width=\"800\" height=\"600\" xmlns=\"http://www.w3.org/2000/svg\"><style>text { font-size: 18px; font-family: Arial, sans-serif; }</style>...</svg>\n\
    - Make graphics comprehensive and detailed - prioritize clarity and completeness over compactness"})
    
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


