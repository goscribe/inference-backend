# Session + Upload Frontend

This frontend allows you to initialize a session, upload images and PDF-like files, set instructions, start LLM sessions, analyse files, generate study guides and flashcards, and retrieve full history.

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
const formData = new FormData();
formData.append("command", "init_session");
formData.append("id", "<SESSION_ID>");
```

**JavaScript Snippet:**  
```js
async function initSession() {
  const formData = new FormData();
  formData.append("command", "init_session");
  formData.append("id", "my_session_id");

  const response = await fetch("https://txp-tckxn64wn5vtgip72-kzoemq8qw-custom.service.onethingrobot.com/upload", {
    method: "POST", body: formData
  });
  const result = await response.json();
  console.log(result);
}
```

**Expected Status:**  
- Success: `"Session initialized successfully!"`  
- Failure: `"Error: <HTTP_STATUS> <STATUS_TEXT>"`  

---

## 2. Upload Image

**Command:** `append_image`  
**FormData:**  
```js
formData.append("command", "append_image");
formData.append("file", <File Object>);
```

**JavaScript Snippet:**  
```js
async function uploadImage() {
  const formData = new FormData();
  formData.append("command", "append_image");
  formData.append("file", fileInput.files[0]);

  const response = await fetch(serverURL, { method: "POST", body: formData });
  const result = await response.json();
  console.log(result);
}
```

**Expected Status:**  
- Success: `"Upload success: <message>"`  
- Failure: `"Error: <HTTP_STATUS> <STATUS_TEXT>"`  

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

## 4. Set Instruction Text

**Command:** `set_instruct`  
**FormData:**  
```js
formData.append("command", "set_instruct");
formData.append("instruction_text", "<INSTRUCTION_TEXT>");
```

**Status:**  
- Success: `"Instruction Text Reset Successful"`  
- Failure: `"Error: <HTTP_STATUS> <STATUS_TEXT>"`  

---

## 5. Start LLM Session

**Command:** `start_LLM_session`  
**FormData:**  
```js
formData.append("command", "start_LLM_session");
```

**Status:**  
- Success: `"LLM session started: <message>"`  

---

## 6. Analyse PDF

**Command:** `analyse_pdf`  
**FormData:**  
```js
formData.append("command", "analyse_pdf");
```

**Status:**  
- Success: `"PDF analysis started: <message>"`  

---

## 7. Analyse Image

**Command:** `analyse_img`  
**FormData:**  
```js
formData.append("command", "analyse_img");
```

**Status:**  
- Success: `"Image analysis started: <message>"`  

---

## 8. Generate Study Guide

**Command:** `generate_study_guide`  
**FormData:**  
```js
formData.append("command", "generate_study_guide");
```

**Status:**  
- Success: JSON string with study guide contents.  

---

## 9. Generate Flashcard Questions

**Command:** `generate_flashcard_questions`  
**FormData:**  
```js
formData.append("command", "generate_flashcard_questions");
formData.append("num_questions", "<NUMBER>");
formData.append("difficulty", "<easy|medium|hard>");
```

**Status:**  
- Success: JSON string with questions  

---

## 10. Generate Flashcard Answers

**Command:** `generate_flashcard_answers`  
**FormData:**  
```js
formData.append("command", "generate_flashcard_answers");
```

**Status:**  
- Success: JSON string with answers  

---

## 11. Retrieve Full History

**Command:** `retrieve_full_history`  
**FormData:**  
```js
formData.append("command", "retrieve_full_history");
```

**Status:**  
- Success: JSON string containing full session message history  

---

### Notes

- Make sure to **initialize a session first** (`init_session`) before sending any other commands.  
- All file uploads require a `File` object from a `<input type="file">` element.  
- All output JSON responses are displayed in `<pre>` blocks for readability in the frontend.  
- Errors will be returned as HTTP errors or caught exceptions.  
