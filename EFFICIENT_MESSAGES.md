# Efficient Message Handling

## Problem
Previously, every time we added a message, we were:
1. Loading ALL messages
2. Deleting ALL messages in DB
3. Rewriting ALL messages

This is **extremely inefficient** and causes:
- Unnecessary database writes
- Slower response times
- Higher database costs
- Potential race conditions

## Solution

### Use `append_message()` instead of `save_messages()`

```python
# ❌ BAD (rewrites everything)
messages = get_messages(session)
messages.append({"role": "user", "content": "Hello"})
save_messages(user, session, messages)  # Deletes and rewrites all!

# ✅ GOOD (just append)
append_message(user, session, "user", "Hello")  # One insert!
```

## When to Use Each Function

### `append_message(user_id, session_id, role, content)`
**Use for:** Adding new messages incrementally
**When:** 
- User sends a prompt
- LLM responds
- Processing PDFs/images (each step)

```python
# User asks question
append_message(user, session, "user", prompt)

# Get LLM response
response = LLM_inference(messages)
append_message(user, session, "assistant", response.choices[0].message.content)
```

### `save_messages(user_id, session_id, messages)`
**Use for:** Initial session setup or rebuilding history
**When:**
- `init_session` - creating a new session
- Migrating from old data
- Rebuilding/resetting conversation

```python
# Only use for initialization
messages = [
    {"role": "system", "content": "You are a study assistant"},
    {"role": "user", "content": "Let's begin"}
]
save_messages(user, session, messages)  # Setup only!
```

## Current Status

**Most functions still use `save_messages()`** - Need to refactor!

### Functions to Update:

1. ✅ `init_session` - Keep `save_messages()` (initialization)
2. ❌ `analyse_pdf` - Should use `append_message()`
3. ❌ `analyse_img` - Should use `append_message()`
4. ❌ `generate_study_guide` - Should use `append_message()`
5. ❌ `generate_flashcard_questions` - Should use `append_message()`
6. ❌ `generate_worksheet_questions` - Should use `append_message()`
7. ❌ `inference_from_prompt` - Should use `append_message()`
8. ❌ `generate_podcast_structure_endpoint` - Should use `append_message()`

## Performance Comparison

### Before (Inefficient)
```
10 message conversation:
- Read: 10 rows
- Delete: 10 rows
- Insert: 11 rows (adding 1 new)
Total: 31 DB operations
```

### After (Efficient)
```
10 message conversation:
- Insert: 1 row (just the new message)
Total: 1 DB operation
```

**31x fewer database operations!** 🚀

## Migration Strategy

### Pattern to Replace:

```python
# Current pattern (INEFFICIENT)
messages = get_messages(session)
messages = some_processing(messages)  # Adds messages to array
save_messages(user, session, messages)

# Better pattern
messages = get_messages(session)
result = some_processing(messages)  # Returns new messages
for msg in result['new_messages']:
    append_message(user, session, msg['role'], msg['content'])
```

### Caveat

Some LLM service functions modify the messages array in place. We'd need to:
1. Track which messages are new
2. Only append the new ones
3. Or refactor services to return only new messages

## Quick Win

For now, keep current approach but:
- Document it as "needs optimization"
- Plan refactor when time permits
- At least we're off the filesystem! ✅

## Future: Batch Append

Could add batch append for efficiency:
```python
def append_messages(user_id, session_id, new_messages):
    """Append multiple messages at once"""
    # Get current max sequence
    # Insert all with incremented sequences
    # One transaction, faster than individual appends
```

This would be ideal for functions that add multiple messages in one go.

