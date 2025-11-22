"""
Workspace Context Utility
Fetches workspace data (FileAssets, Flashcards, etc.) and formats for LLM input
Uses direct SQL queries to Supabase
"""
import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
else:
    supabase = None


def fetch_file_assets_by_ids(file_asset_ids: List[str]) -> List[Dict]:
    """
    Fetch FileAsset records by specific IDs using direct SQL query to Supabase.
    
    Args:
        file_asset_ids: List of FileAsset IDs
    
    Returns:
        List of FileAsset dictionaries
    """
    if not file_asset_ids or not supabase:
        return []
    
    try:
        # Query Supabase directly using SQL - include aiTranscription field
        response = supabase.table("FileAsset").select("*, aiTranscription").in_("id", file_asset_ids).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Warning: Failed to fetch FileAssets by IDs from Supabase: {e}")
        return []


def fetch_file_assets(workspace_id: str) -> List[Dict]:
    """
    Fetch FileAsset records for a workspace using direct SQL query to Supabase.
    
    Args:
        workspace_id: Workspace/Session ID
    
    Returns:
        List of FileAsset dictionaries
    """
    if not supabase:
        return []
    
    try:
        # Query Supabase directly - include aiTranscription field
        response = supabase.table("FileAsset")\
            .select("*, aiTranscription")\
            .eq("workspaceId", workspace_id)\
            .order("createdAt", desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Warning: Failed to fetch FileAssets from Supabase: {e}")
        return []


def fetch_flashcards_by_ids(flashcard_ids: List[str]) -> List[Dict]:
    """
    Fetch Flashcard records by specific IDs using direct SQL query to Supabase.
    
    Args:
        flashcard_ids: List of Flashcard IDs
    
    Returns:
        List of Flashcard dictionaries
    """
    if not flashcard_ids or not supabase:
        return []
    
    try:
        # Query Supabase directly
        response = supabase.table("Flashcard").select("*").in_("id", flashcard_ids).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Warning: Failed to fetch Flashcards by IDs from Supabase: {e}")
        return []


def fetch_flashcards(workspace_id: str) -> List[Dict]:
    """
    Fetch Flashcard records for a workspace using direct SQL query to Supabase.
    
    Args:
        workspace_id: Workspace/Session ID
    
    Returns:
        List of Flashcard dictionaries with 'term' and 'definition'
    """
    if not supabase:
        # Fallback to local JSON (legacy support)
        try:
            flashcards_path = f"Data/{user_id}/{workspace_id}/flashcards.json"
            if os.path.exists(flashcards_path):
                with open(flashcards_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "flashcards" in data:
                        return data["flashcards"]
                    elif isinstance(data, list):
                        return data
        except Exception as e:
            print(f"Warning: Failed to read flashcards from file: {e}")
        return []
    
    try:
        # Query Supabase directly
        response = supabase.table("Flashcard")\
            .select("*")\
            .eq("workspaceId", workspace_id)\
            .order("createdAt", desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Warning: Failed to fetch Flashcards from Supabase: {e}")
        # Fallback to local JSON (legacy support)
        try:
            flashcards_path = f"Data/{user_id}/{workspace_id}/flashcards.json"
            if os.path.exists(flashcards_path):
                with open(flashcards_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "flashcards" in data:
                        return data["flashcards"]
                    elif isinstance(data, list):
                        return data
        except Exception:
            pass
        return []


def format_file_assets_context(file_assets: List[Dict]) -> str:
    """
    Format FileAsset data into LLM context string.
    
    Args:
        file_assets: List of FileAsset dictionaries
    
    Returns:
        Formatted context string
    """
    if not file_assets:
        return ""
    
    context_parts = ["## UPLOADED FILES AND THEIR CONTENT"]
    context_parts.append("=" * 60)
    
    for asset in file_assets:
        file_name = asset.get("fileName", "Unknown")
        file_type = asset.get("fileType", "unknown")
        
        context_parts.append(f"\n### File: {file_name}")
        context_parts.append(f"Type: {file_type}")
        
        # Get aiTranscription (or processedContent as fallback)
        transcription_raw = asset.get("aiTranscription") or asset.get("processedContent")
        
        if transcription_raw:
            # Parse JSON if it's a string
            if isinstance(transcription_raw, str):
                try:
                    transcription = json.loads(transcription_raw)
                except json.JSONDecodeError:
                    transcription = {"comprehensiveDescription": transcription_raw}
            else:
                transcription = transcription_raw
            
            # Extract all parts
            text_content = transcription.get("textContent")
            comprehensive_description = transcription.get("comprehensiveDescription")
            image_descriptions = transcription.get("imageDescriptions", [])
            
            # Add comprehensive description (main content)
            if comprehensive_description:
                context_parts.append(f"\nContent:\n{comprehensive_description}")
            
            # Add text content if available
            if text_content:
                context_parts.append(f"\nText Content:\n{text_content}")
            
            # Add image descriptions if available
            if image_descriptions:
                context_parts.append("\nVisual Content:")
                for img_desc in image_descriptions:
                    page_num = img_desc.get("page", "?")
                    description = img_desc.get("description", "")
                    context_parts.append(f"\nPage {page_num}: {description}")
        
        context_parts.append("\n" + "-" * 60)
    
    return "\n".join(context_parts)


def format_flashcards_context(flashcards: List[Dict]) -> str:
    """
    Format Flashcard data into LLM context string.
    
    Args:
        flashcards: List of Flashcard dictionaries with 'term' and 'definition'
    
    Returns:
        Formatted context string
    """
    if not flashcards:
        return ""
    
    context_parts = ["## EXISTING FLASHCARDS"]
    context_parts.append("=" * 60)
    context_parts.append("These flashcards have already been created for this workspace:")
    context_parts.append("")
    
    for i, card in enumerate(flashcards, 1):
        term = card.get("term", "")
        definition = card.get("definition", "")
        context_parts.append(f"{i}. **{term}**")
        context_parts.append(f"   → {definition}")
        context_parts.append("")
    
    return "\n".join(context_parts)


def get_workspace_context(
    workspace_id: str = None,
    file_asset_ids: List[str] = None,
    flashcard_ids: List[str] = None,
    include_file_assets: bool = True,
    include_flashcards: bool = True,
    max_file_content_length: int = 2000,  # Truncate long content
    include_worksheets: bool = False
) -> str:
    """
    Fetch and format workspace context for LLM input.
    
    This function aggregates workspace data and formats it as a context string.
    Can fetch by workspace_id OR by specific IDs (more efficient for large workspaces).
    
    Args:
        workspace_id: Workspace/Session ID (optional if using IDs)
        file_asset_ids: Optional list of specific FileAsset IDs to fetch
        flashcard_ids: Optional list of specific Flashcard IDs to fetch
        include_file_assets: Whether to include FileAsset content
        include_flashcards: Whether to include Flashcard data
        max_file_content_length: Max characters per file content (truncate if longer)
        include_worksheets: Whether to include Worksheet data (future)
    
    Returns:
        Formatted context string ready to be prefixed to LLM messages
    """
    context_parts = []
    
    # Fetch and format FileAssets
    if include_file_assets:
        if file_asset_ids:
            # Fetch specific files by ID (more efficient)
            file_assets = fetch_file_assets_by_ids(file_asset_ids)
        elif workspace_id:
            # Fetch all files in workspace
            file_assets = fetch_file_assets(workspace_id)
        else:
            file_assets = []
        
        if file_assets:
            context_parts.append(format_file_assets_context(file_assets))
    
    # Fetch and format Flashcards
    if include_flashcards:
        if flashcard_ids:
            # Fetch specific flashcards by ID
            flashcards = fetch_flashcards_by_ids(flashcard_ids)
        elif workspace_id:
            # Fetch all flashcards in workspace
            flashcards = fetch_flashcards(workspace_id)
        else:
            flashcards = []
        
        if flashcards:
            context_parts.append(format_flashcards_context(flashcards))
    
    # Future: Worksheets, Study Guides, etc.
    if include_worksheets:
        # TODO: Implement worksheet fetching
        pass
    
    # Combine all context parts
    if context_parts:
        full_context = "\n\n".join(context_parts)
        # Add header and footer
        header = "# WORKSPACE CONTEXT\n\nThis context contains all uploaded files, flashcards, and other workspace data.\n\n"
        footer = "\n\n---\n\nUse the above context when generating content. Reference specific files, flashcards, or concepts as needed.\n"
        return header + full_context + footer
    
    return ""


def get_workspace_context_as_message(
    workspace_id: str = None,
    user_id: str = None,
    file_asset_ids: List[str] = None,
    flashcard_ids: List[str] = None,
    include_file_assets: bool = True,
    include_flashcards: bool = True,
    max_file_content_length: int = 2000
) -> Dict:
    """
    Get workspace context formatted as an LLM message object.
    
    Args:
        workspace_id: Workspace/Session ID
        user_id: User ID
        include_file_assets: Whether to include FileAsset content
        include_flashcards: Whether to include Flashcard data
    
    Returns:
        Dictionary with 'role' and 'content' keys, ready to append to messages array
    """
    context = get_workspace_context(
        workspace_id=workspace_id,
        file_asset_ids=file_asset_ids,
        flashcard_ids=flashcard_ids,
        include_file_assets=include_file_assets,
        include_flashcards=include_flashcards,
        max_file_content_length=max_file_content_length
    )
    

    print(context)

    if not context:
        return None
    
    return {
        "role": "user",
        "content": context
    }

