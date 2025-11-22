"""
Podcast Generation Service with Multi-Speaker Support
Generates podcast scripts with multiple voices (host/guest dialogue)
"""
import json
from app.models.LLM_inference import LLM_inference
from app.utils.utils import update_memory
from app.utils.workspace_context import get_workspace_context_as_message


def generate_podcast_structure(messages, title, description, user_prompt="", speakers=None, workspace_id=None, user_id=None):
    """
    Generate the structure of a multi-speaker podcast episode.
    
    Args:
        messages: Conversation history
        title: Podcast episode title
        description: Episode description
        user_prompt: Optional user requirements
        speakers: List of dicts with 'id' (ElevenLabs voice ID) and 'role' ('host' or 'guest')
        workspace_id: Optional workspace ID for fetching context
        user_id: Optional user ID for fetching context
    
    Returns:
        (messages, structured_content) - Updated messages and parsed structure
    """
    
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
    
    # Default to single speaker if none provided
    if not speakers or len(speakers) == 0:
        speakers = [{"id": "default", "role": "host"}]
    
    # Build speaker context
    speaker_context = "\n".join([
        f"- {speaker.get('name', speaker['role'].capitalize())} ({speaker['role']}) (Voice ID: {speaker['id']})"
        for speaker in speakers
    ])
    
    # Determine podcast style based on number of speakers
    if len(speakers) == 1:
        style_instruction = "Create a single-narrator podcast with clear, engaging monologue."
    else:
        # Build speaker label instructions using names
        speaker_labels = [speaker.get('name', speaker['role'].upper()) for speaker in speakers]
        label_examples = " / ".join(speaker_labels)
        
        style_instruction = f"""Create a dynamic conversation between {len(speakers)} speakers:
{speaker_context}

The dialogue should feel natural, with:
- Back-and-forth discussion between all speakers
- Questions and answers
- Different perspectives from each person
- Natural transitions between speakers
- Each speaker has a distinct personality matching their role

IMPORTANT: When writing dialogue, use these EXACT speaker names as labels:
{label_examples}

Example format:
{speaker_labels[0].upper()}: [their dialogue]
{speaker_labels[1].upper()}: [their dialogue]
{speaker_labels[2].upper() if len(speaker_labels) > 2 else speaker_labels[0].upper()}: [their dialogue]"""

    prompt = f"""You are a podcast content structuring assistant. Create a complete podcast episode structure.

Title: {title}
Description: {description}
{f"User Requirements: {user_prompt}" if user_prompt else ""}

Speakers:
{speaker_context}

{style_instruction}

Based on all the study materials and context in our conversation history, create a podcast episode that:
- Is educational, informative, and engaging
- Uses natural, conversational language
- Flows logically from one segment to the next
- Segments are 2-5 minutes each when spoken
- Each segment focuses on a specific topic or concept

For multi-speaker segments, format the content as a script using the speaker names (not roles) as labels.

Format your response as JSON:
{{
  "episodeTitle": "Enhanced episode title",
  "totalEstimatedDuration": "estimated total duration in minutes",
  "segments": [
    {{
      "title": "Segment title",
      "content": "Script content (with speaker labels if multi-speaker)",
      "speaker": "host" or "guest" or "dialogue" (for multi-speaker),
      "voiceId": "elevenlabs voice ID to use",
      "keyPoints": ["key point 1", "key point 2"],
      "estimatedDuration": "duration in minutes",
      "order": 1
    }}
  ]
}}

IMPORTANT: For the "content" field:
- If single speaker: Just the script text
- If multiple speakers: Use format "SPEAKER_NAME: text\\nSPEAKER_NAME: text" (use actual names like RACHEL, JOSH, not roles)

Analyze the study materials and create an engaging, informative podcast structure."""

    messages.append({"role": "user", "content": prompt})
    
    # Use structured JSON output for reliability
    resp = LLM_inference(
        messages=messages,
        json_output=True,
                         response_format={
                             "type": "json_schema",
                             "json_schema": {
                                 "name": "podcast_structure",
                                 "schema": {
                                     "type": "object",
                                     "properties": {
                                         "episodeTitle": {"type": "string"},
                                         "totalEstimatedDuration": {"type": "string"},
                                         "segments": {
                                             "type": "array",
                                             "items": {
                                                 "type": "object",
                                                 "properties": {
                                                     "title": {"type": "string"},
                                                     "content": {"type": "string"},
                                    "speaker": {"type": "string"},
                                    "voiceId": {"type": "string"},
                                                     "keyPoints": {
                                                         "type": "array",
                                                         "items": {"type": "string"}
                                                     },
                                                     "estimatedDuration": {"type": "string"},
                                                     "order": {"type": "integer"}
                                                 },
                                                "required": ["title", "content", "speaker", "voiceId", "keyPoints", "estimatedDuration", "order"],
                                                 "additionalProperties": False
                                             }
                                         }
                                     },
                                     "required": ["episodeTitle", "totalEstimatedDuration", "segments"],
                                     "additionalProperties": False
                                 },
                                 "strict": True
                             }
        }
    )
    
    update_memory(messages, resp)
    last_content = messages[-1].get("content", "")
    
    # Parse the JSON response
    try:
        structured_content = json.loads(last_content)
        
        # Assign voice IDs to segments based on speaker role
        for segment in structured_content.get("segments", []):
            if "speaker" not in segment or "voiceId" not in segment:
                # Default assignment
                segment_speaker = segment.get("speaker", "host")
                matching_speaker = next(
                    (s for s in speakers if s["role"] == segment_speaker),
                    speakers[0]  # Fallback to first speaker
                )
                segment["voiceId"] = matching_speaker["id"]
                segment["speaker"] = matching_speaker["role"]
        
            return messages, structured_content
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse podcast structure JSON: {e}")
        print(f"Raw content: {last_content}")
        raise ValueError(f"Invalid JSON response from LLM: {e}")


def split_dialogue_segment(segment_content, speakers):
    """
    Split a multi-speaker dialogue segment into individual speaker parts.
    Supports any number of speakers with flexible naming.
    
    Args:
        segment_content: String with format "SPEAKER: text\\nSPEAKER: text"
        speakers: List of speaker configs with 'role', 'id', and optional 'name'
    
    Returns:
        List of dicts with 'speaker', 'voiceId', 'text'
    """
    parts = []
    lines = segment_content.split('\n')
    
    # Build mapping of speaker labels (uppercase) to speaker configs
    speaker_map = {}
    for speaker in speakers:
        # Support matching by role (HOST, GUEST)
        role_upper = speaker['role'].upper()
        speaker_map[role_upper] = speaker
        
        # Support matching by name if provided (SPEAKER1, SPEAKER2, etc)
        if 'name' in speaker:
            name_upper = speaker['name'].upper()
            speaker_map[name_upper] = speaker
    
    # Also build a list of valid labels for detection
    valid_labels = list(speaker_map.keys())
    
    current_speaker = None
    current_speaker_config = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line starts with a speaker label
        if ':' in line:
            potential_speaker = line.split(':', 1)[0].strip().upper()
            
            # Check if this matches any known speaker
            if potential_speaker in speaker_map:
                # Save previous speaker's text
                if current_speaker and current_text:
                    parts.append({
                        'speaker': current_speaker_config.get('role', 'unknown'),
                        'voiceId': current_speaker_config['id'],
                        'text': ' '.join(current_text).strip()
                    })
                    current_text = []
                
                # Start new speaker
                current_speaker = potential_speaker
                current_speaker_config = speaker_map[potential_speaker]
                text_content = line.split(':', 1)[1].strip()
                if text_content:
                    current_text.append(text_content)
            else:
                # Not a recognized speaker label, add to current text
                if current_speaker:
                    current_text.append(line)
        else:
            # No colon, add to current text
            if current_speaker:
                current_text.append(line)
    
    # Don't forget the last speaker
    if current_speaker and current_text:
        parts.append({
            'speaker': current_speaker_config.get('role', 'unknown'),
            'voiceId': current_speaker_config['id'],
            'text': ' '.join(current_text).strip()
        })
    
    return parts

def generate_podcast_summary(messages, episode_title, segments):
    """
    Generate a comprehensive summary of the podcast episode.
    
    Args:
        messages: Conversation history
        episode_title: Title of the episode
        segments: List of segment dicts
    
    Returns:
        (messages, episode_summary) - Updated messages and parsed summary
    """
    
    segments_summary = "\n".join([
        f"- {seg.get('title', 'Untitled')}: {', '.join(seg.get('keyPoints', []))}"
        for seg in segments
    ])
    
    prompt = f"""Create a comprehensive summary for this podcast episode.

Episode Title: {episode_title}

Segments:
{segments_summary}

Generate a JSON summary with:
{{
  "executiveSummary": "Brief 2-3 sentence overview",
  "learningObjectives": ["objective1", "objective2", ...],
  "keyConcepts": ["concept1", "concept2", ...],
  "targetAudience": "Description of ideal listener",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

    messages.append({"role": "user", "content": prompt})
    
    # Use structured JSON output for reliability
    resp = LLM_inference(
        messages=messages,
        json_output=True,
                         response_format={
                             "type": "json_schema",
                             "json_schema": {
                                 "name": "podcast_summary",
                                 "schema": {
                                     "type": "object",
                                     "properties": {
                                         "executiveSummary": {"type": "string"},
                                         "learningObjectives": {
                                             "type": "array",
                                             "items": {"type": "string"}
                                         },
                                         "keyConcepts": {
                                             "type": "array",
                                             "items": {"type": "string"}
                                         },
                                         "targetAudience": {"type": "string"},
                                         "tags": {
                                             "type": "array",
                                             "items": {"type": "string"}
                                         }
                                     },
                    "required": ["executiveSummary", "learningObjectives", "keyConcepts", "targetAudience", "tags"],
                                     "additionalProperties": False
                                 },
                                 "strict": True
                             }
        }
    )
    
    update_memory(messages, resp)
    last_content = messages[-1].get("content", "")
    
    try:
        episode_summary = json.loads(last_content)
        return messages, episode_summary
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse summary JSON: {e}")
        # Return default summary
        return messages, {
            "executiveSummary": f"AI-generated podcast episode: {episode_title}",
            "learningObjectives": [],
            "keyConcepts": [],
            "targetAudience": "General audience",
            "tags": []
        }


def estimate_segment_duration(text, words_per_minute=150):
    """
    Estimate the duration of a text segment when spoken.
    
    Args:
        text: The text content
        words_per_minute: Average speaking rate (default 150 WPM)
    
    Returns:
        Estimated duration in seconds
    """
    word_count = len(text.split())
    duration_seconds = (word_count / words_per_minute) * 60
    return int(duration_seconds)


def create_full_transcript(segments):
    """
    Create a full markdown transcript from segments.
    
    Args:
        segments: List of segment dicts
    
    Returns:
        Full transcript as markdown string
    """
    transcript = f"# Podcast Transcript\n\n"
    
    for i, segment in enumerate(segments, 1):
        transcript += f"## Segment {i}: {segment.get('title', 'Untitled')}\n\n"
        transcript += f"**Duration:** {segment.get('duration', 0)} seconds\n\n"
        
        if segment.get('keyPoints'):
            transcript += "**Key Points:**\n"
            for point in segment['keyPoints']:
                transcript += f"- {point}\n"
            transcript += "\n"
        
        transcript += f"{segment.get('content', '')}\n\n"
        transcript += "---\n\n"
    
    return transcript


# Legacy support - simple single-voice podcast
def generate_podcast_script(messages, prompt=""):
    """
    Legacy function: Generate a simple single-voice podcast script.
    
    Args:
        messages: Conversation history
        prompt: Optional user prompt
    
    Returns:
        Updated messages with generated script
    """
    
    user_content = f"""Generate a podcast script discussing all the study materials in our conversation history.

The podcast should be divided into at least 3 distinct sections, each roughly 2-3 minutes when spoken.

{f"Additional requirements: {prompt}" if prompt else ""}

Format your response as JSON:
{{
  "scripts": [
    "Script for segment 1...",
    "Script for segment 2...",
    "Script for segment 3..."
  ]
}}

Make it engaging, educational, and conversational."""

    messages.append({"role": "user", "content": user_content})
    
    resp = LLM_inference(
        messages=messages,
        json_output=True,
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

    update_memory(messages, resp)
    return messages
