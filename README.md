# Sendable Requests to Server

These requests allows you to initialize a session, upload images and PDF-like files, set instructions, start LLM sessions, analyse files, generate study guides, flashcards, worksheets, mindmaps, and retrieve history.

All communication is done via `POST` requests to the server endpoint:

```
https://txp-tckxn64wn5vtgip72-kzoemq8qw-custom.service.onethingrobot.com/upload
```

Each request uses `FormData` with a `command` key and optional additional fields.

---

## 1. Initialize Session

**Command:** `init_session`  
**FormData:**  
```js
formData.append("command", "init_session");
formData.append("id", "<SESSION_ID>");
```

**Status:**  
- Success: `{"message": "Session '<SESSION_ID>' initialized successfully"}`  
- Failure: `{"error": "No session ID provided"}`  

---

## 2. Upload Image

**Command:** `append_image`  
**FormData:**  
```js
formData.append("command", "append_image");
formData.append("file", <File Object>);
```

**Status:**  
- Success: `{"message": "File saved at: <path>: Success"}`  
- Failure: `{"error": "...error details..."}`  

---

## 3. Upload PDF-like

**Command:** `append_pdflike`  
**FormData:**  
```js
formData.append("command", "append_pdflike");
formData.append("file", <File Object>);
```

**Status:** Same as Upload Image  

---

## 4. Remove Image

**Command:** `remove_img`  
**FormData:**  
```js
formData.append("command", "remove_img");
formData.append("filename", "<IMAGE_FILENAME>");
````

**Status:**

* Success: `{"message": "File '<IMAGE_FILENAME>' removed successfully."}`
* Failure:

  * Session not initialized: `{"error": "Session not initialized."}`
  * Filename missing: `{"error": "No filename provided."}`
  * File not found: `{"error": "File not found: <IMAGE_FILENAME>"}`
  * Other errors: `{"error": "...error details..."}`

---

## 5. Remove PDF

**Command:** `remove_pdf`
**FormData:**

```js
formData.append("command", "remove_pdf");
formData.append("filename", "<PDF_FILENAME>");
```

**Status:**

* Success:

  * PDF removed only: `{"message": "PDF '<PDF_FILENAME>' removed successfully."}`
  * PDF and associated image folder removed: `{"message": "PDF '<PDF_FILENAME>' removed successfully. Associated image folder '<BASENAME>' removed."}`
* Failure:

  * Session not initialized: `{"error": "Session not initialized."}`
  * Filename missing: `{"error": "No filename provided."}`
  * PDF not found: `{"error": "File not found: <PDF_FILENAME>"}`
  * Other errors: `{"error": "...error details..."}`



---

## 6. Set Instruction Text

**Command:** `set_instruct`  
**FormData:**  
```js
formData.append("command", "set_instruct");
formData.append("instruction_text", "<INSTRUCTION_TEXT>");
```

**Status:**  
- Success: `{"message": "Instruction Text Reset Successful"}`  
- Failure: `{"error": "...error details..."}`  

---

## 7. Start LLM Session

**Command:** `start_LLM_session`  
**FormData:**  
```js
formData.append("command", "start_LLM_session");
```

**Status:**  
- Success: `{"message": "Start LLM Session Successful"}`  
- Failure: `{"error": "...error details..."}`  

---

## 8. Analyse PDF

**Command:** `analyse_pdf`  
**FormData:**  
```js
formData.append("command", "analyse_pdf");
```

**Status:**  
- Success: `{"message": "Analyse PDFs Successful"}`  
- Failure: `{"error": "...error details..."}`  

---

## 9. Analyse Image

**Command:** `analyse_img`  
**FormData:**  
```js
formData.append("command", "analyse_img");
```

**Status:**  
- Success: `{"message": "Analysing Images Successful"}`  
- Failure: `{"error": "...error details..."}`  

---

## 10. Generate Study Guide

**Command:** `generate_study_guide`  
**FormData:**  
```js
formData.append("command", "generate_study_guide");
```

**Status:**  
- Success: `{"markdown": "<generated markdown content>", "mermaid": "<mindmap mermaid source>"}`  
- Failure: `{"error": "...error details..."}`  

---

## 11. Generate Flashcard Questions

**Command:** `generate_flashcard_questions`  
**FormData:**  
```js
formData.append("command", "generate_flashcard_questions");
formData.append("num_questions", "<NUMBER>");
formData.append("difficulty", "<easy|medium|hard>");
```

**Status:**  
- Success: `{"last_response": "<JSON flashcards>"}`
- Failure: `{"error": "...error details..."}`  

---

## 12. Generate Worksheet Questions

**Command:** `generate_worksheet_questions`  
**FormData:**  
```js
formData.append("command", "generate_worksheet_questions");
formData.append("num_questions", "<NUMBER>");
formData.append("difficulty", "<easy|medium|hard>");
```

**Status:**  
- Success: `{"last_response": "<JSON worksheet>"}`
- Failure: `{"error": "...error details..."}`  

---

## 13. Generate Mindmap

**Command:** `generate_mindmap`  
**FormData:**  
```js
formData.append("command", "generate_mindmap");
```

**Status:**  
- Success: `{"message": "Generate Mindmap Successful"}`  
- Failure: `{"error": "...error details..."}`  

---

## 14. Retrieve Full History

**Command:** `retrieve_full_history`  
**FormData:**  
```js
formData.append("command", "retrieve_full_history");
```

**Status:**  
- Success: `{"message": "Full History Uploaded."}`  
- Failure: `{"error": "...error details..."}`  

> To actually fetch the history, call the separate endpoint:  
> `GET /full_history` → `{"full_history": [...messages...]}`  

---

## 15. Inference from Prompt

**Command:** `inference_from_prompt`  
**FormData:**  
```js
formData.append("command", "inference_from_prompt");
formData.append("prompt", "<PROMPT_TEXT>");
```

**Status:**  
- Success: `{"last_response": "<generated content>"}`  
- Failure: `{"error": "...error details..."}`  

---

### Notes

- Always run `init_session` first before any other command.  
- Uploads require valid `File` objects.  
- Errors always come as JSON: `{"error": "...message..."}`.  
- `generate_flashcard_answers` and `generate_worksheet_answers` are not separate commands (handled inside their respective question-generation commands).  

## Worksheet JSON Format:
```
workspaceId,
      title: `New Worksheet ${worksheets.length + 1}`,
      description: 'Generated practice problems',
      difficulty: 'MEDIUM',
      estimatedTime: '30 min',
      problems: [
        {
          question: 'Sample question 1',
          answer: 'Sample answer 1',
          type: 'TEXT',
        },
        {
          question: 'Sample question 2',
          answer: 'Sample answer 2',
          type: 'TEXT',
        },
        {
          question: 'Sample question 3',
          answer: 'Sample answer 3',
          type: 'MULTIPLE_CHOICE',
          options: ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
        },
        {
          question: 'Sample question 4',
          answer: 'Sample answer 4',
          type: 'NUMERIC',
        },
        {
          question: 'Sample question 5',
          answer: 'Sample answer 5',
          type: 'TRUE_FALSE',
        },
        {
          question: 'Sample question 6',
          answer: 'Sample answer 6',
          type: 'MATCHING',
          options: ['Option 1', 'Option 2', 'Option 3'],
        }
      ],
```


### Notes

- Make sure to **initialize a session first** (`init_session`) before sending any other commands.  
- All file uploads require a `File` object from a `<input type="file">` element.  
- All output JSON responses are displayed in `<pre>` blocks for readability in the frontend.  
- Errors will be returned as HTTP errors or caught exceptions.


## Endpoint: `/session_files`

Returns a listing of all files grouped by **session**.  
A session is represented by a directory in the server’s working directory that contains
at least a `pdfs/` or `imgs/` subfolder.

### Method
`GET /session_files`

### Response
- **200 OK** — JSON object containing session data.
- **400/500** — Error response if something went wrong.

### JSON Format Example

```json
{
  "sessions": {
    "session123": {
      "counts": {
        "pdfs": 2,
        "imgs": 1,
        "all": 3
      },
      "pdfs": [
        {
          "name": "doc1.pdf",
          "path": "session123/pdfs/doc1.pdf",
          "type": "pdf",
          "size_bytes": 15324,
          "modified_ts": 1724819200.0,
          "modified_iso": "2025-08-28T08:46:40"
        },
        {
          "name": "doc2.pdf",
          "path": "session123/pdfs/doc2.pdf",
          "type": "pdf",
          "size_bytes": 90213,
          "modified_ts": 1724819300.0,
          "modified_iso": "2025-08-28T08:48:20"
        }
      ],
      "imgs": [
        {
          "name": "image1.png",
          "path": "session123/imgs/image1.png",
          "type": "img",
          "size_bytes": 30241,
          "modified_ts": 1724819400.0,
          "modified_iso": "2025-08-28T08:50:00"
        }
      ],
      "all": [
        { "... pdf or img entries ..." }
      ]
    },
    "session456": {
      "counts": { "pdfs": 0, "imgs": 4, "all": 4 },
      "pdfs": [],
      "imgs": [ { "... entries ..." } ],
      "all": [ { "... entries ..." } ]
    }
  },
  "session_count": 2
}
````

### Notes

* `sessions` is a dictionary keyed by session name.
* Each session includes:

  * `counts`: number of PDFs, images, and total files.
  * `pdfs`, `imgs`, `all`: arrays of file metadata.
* File metadata includes:

  * `name`: filename only.
  * `path`: relative path to the file.
  * `type`: `"pdf"` or `"img"`.
  * `size_bytes`: file size.
  * `modified_ts`: last modified timestamp (epoch).
  * `modified_iso`: last modified time (ISO format).




## Some Notes on Implementation
### Why choose server-run LLM?
Most APIs (e.g. ChatGPT) does not support multiple pdf upload and analysis. We use the Gemma multimodal model, which 
accepts vision and text input. With that, we can flexiblly feed the model with any file that can be depomposed into 
text, and image components. PDF fits such decomposition, thus also any files that can be safely converted into PDFs.   

**The other advantage** is that server-run LLM can easily be fine-tuned. Currently, we don't have the data for fine-tuning 
but user-sharing is implemented, such that in the future, when enough users share their self-made of adjusted study guides, 
flashcards, and worksheets, these data can be collected and used to fine-tune the model.
