# Workspace Context Usage Guide

## Overview

`get_workspace_context` fetches workspace data (FileAssets, Flashcards, etc.) from your tRPC backend and formats it for LLM input. This context can be prefixed before any service call (podcast, worksheet, flashcards, etc.) to give the LLM full awareness of workspace content.

## Quick Start

```python
from app.utils.workspace_context import get_workspace_context_as_message

# Get context as message (ready to prepend)
context_message = get_workspace_context_as_message(
    workspace_id="workspace_123",
    user_id="user_456",
    include_file_assets=True,
    include_flashcards=True
)

# Use in your service
messages = get_messages(session)
if context_message:
    messages.insert(0, context_message)  # Insert after system message

# Your service code continues...
resp = LLM_inference(messages=messages)
```

## Function Reference

### `get_workspace_context(workspace_id, user_id, ...)`

Returns a formatted string with all workspace context.

**Parameters:**
- `workspace_id` (str): Workspace/Session ID
- `user_id` (str): User ID
- `include_file_assets` (bool): Include FileAsset content (default: True)
- `include_flashcards` (bool): Include Flashcard data (default: True)
- `include_worksheets` (bool): Include Worksheet data (default: False, future)

**Returns:** Formatted context string

**Example:**
```python
context = get_workspace_context(
    workspace_id="workspace_123",
    user_id="user_456"
)
print(context)
# Output:
# # WORKSPACE CONTEXT
# 
# ## UPLOADED FILES AND THEIR CONTENT
# ### File: economics_chapter7.pdf
# Content Summary: ...
# 
# ## EXISTING FLASHCARDS
# 1. **Market Equilibrium**
#    → The point where supply equals demand
# ...
```

### `get_workspace_context_as_message(workspace_id, user_id, ...)`

Returns context formatted as an LLM message object (ready to append to messages array).

**Parameters:** Same as `get_workspace_context`

**Returns:** Dictionary with `{"role": "user", "content": "..."}` or `None` if no context

**Example:**
```python
context_message = get_workspace_context_as_message(
    workspace_id="workspace_123",
    user_id="user_456"
)

if context_message:
    messages.insert(0, context_message)
```

## Integration Examples

### Podcast Service

```python
# In podcast_service.py
from app.utils.workspace_context import get_workspace_context_as_message

def generate_podcast_structure(messages, title, description, ..., workspace_id=None, user_id=None):
    # Prepend workspace context
    if workspace_id and user_id:
        context_message = get_workspace_context_as_message(
            workspace_id=workspace_id,
            user_id=user_id,
            include_file_assets=True,
            include_flashcards=True
        )
        if context_message:
            # Insert after system message
            insert_index = 0
            if messages and messages[0].get("role") == "system":
                insert_index = 1
            messages.insert(insert_index, context_message)
    
    # Continue with podcast generation...
```

### Worksheet Service

```python
# In worksheet_service.py
from app.utils.workspace_context import get_workspace_context_as_message

def generate_worksheet_q(messages, num_quests, difficulty, workspace_id=None, user_id=None):
    # Prepend workspace context
    if workspace_id and user_id:
        context_message = get_workspace_context_as_message(
            workspace_id=workspace_id,
            user_id=user_id,
            include_file_assets=True,
            include_flashcards=True
        )
        if context_message:
            insert_index = 0
            if messages and messages[0].get("role") == "system":
                insert_index = 1
            messages.insert(insert_index, context_message)
    
    # Continue with worksheet generation...
```

### Flashcard Service

```python
# In flashcard_service.py
from app.utils.workspace_context import get_workspace_context_as_message

def generate_flashcards_q(messages, num_flashcards, difficulty, workspace_id=None, user_id=None):
    # Prepend workspace context (exclude flashcards to avoid duplication)
    if workspace_id and user_id:
        context_message = get_workspace_context_as_message(
            workspace_id=workspace_id,
            user_id=user_id,
            include_file_assets=True,
            include_flashcards=False  # Don't include existing flashcards
        )
        if context_message:
            insert_index = 0
            if messages and messages[0].get("role") == "system":
                insert_index = 1
            messages.insert(insert_index, context_message)
    
    # Continue with flashcard generation...
```

## Configuration

Set these environment variables in your `.env`:

```bash
# tRPC Backend URL (for fetching workspace data)
TRPC_BACKEND_URL=https://your-trpc-backend.com

# Optional: Direct database access (if you have Prisma Python client)
DATABASE_URL=postgresql://...
```

## API Endpoints Required

Your tRPC backend needs these endpoints:

### GET `/api/fileAssets`
**Query Params:**
- `workspaceId` (string)
- `userId` (string)

**Response:**
```json
[
  {
    "id": "file_123",
    "fileName": "economics.pdf",
    "fileType": "pdf",
    "processedContent": "DOCUMENT SUMMARY...",
    "textContent": "Full text...",
    "pageCount": 90,
    "processingStatus": "completed"
  }
]
```

### GET `/api/flashcards`
**Query Params:**
- `workspaceId` (string)
- `userId` (string)

**Response:**
```json
[
  {
    "id": "card_123",
    "term": "Market Equilibrium",
    "definition": "The point where supply equals demand",
    "difficulty": "medium"
  }
]
```

## Format Output

The context is formatted as:

```
# WORKSPACE CONTEXT

This context contains all uploaded files, flashcards, and other workspace data.

## UPLOADED FILES AND THEIR CONTENT
============================================================

### File: economics_chapter7.pdf
Type: pdf
Pages: 90

Content Summary:
DOCUMENT SUMMARY (90 pages)
...
[comprehensive description from process_file]

------------------------------------------------------------

## EXISTING FLASHCARDS
============================================================
These flashcards have already been created for this workspace:

1. **Market Equilibrium**
   → The point where supply equals demand

2. **Price Mechanism**
   → How prices adjust to balance supply and demand

---

Use the above context when generating content. Reference specific files, flashcards, or concepts as needed.
```

## Benefits

1. **Context Awareness**: LLM knows all workspace content
2. **Consistency**: References actual files and flashcards
3. **Efficiency**: No need to re-process files for each service
4. **Flexibility**: Can include/exclude different data types

## Notes

- Context is fetched fresh each time (not cached)
- If API calls fail, function returns empty context (graceful degradation)
- Context is inserted after system message but before user prompts
- Large workspaces may produce long context strings (monitor token usage)

