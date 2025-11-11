"""
Simple message storage using Supabase PostgreSQL
No foreign keys to avoid conflicts with Prisma's users table
"""
from supabase import create_client
import os
import json
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class MessageStore:
    """Handle message storage in Supabase"""
    
    @staticmethod
    def append_message(user_id: str, session_id: str, role: str, content) -> bool:
        """
        Append a single message (EFFICIENT - no rewrite)
        
        Args:
            user_id: User ID
            session_id: Session/Workspace ID
            role: Message role ('system', 'user', 'assistant')
            content: Message content (can be dict/list for complex content)
        
        Returns:
            bool: True if successful
        """
        try:
            # Get current max sequence number
            response = supabase.table("llm_messages")\
                .select("sequence")\
                .eq("session_id", session_id)\
                .order("sequence", desc=True)\
                .limit(1)\
                .execute()
            
            # Calculate next sequence
            next_sequence = 0
            if response.data:
                next_sequence = response.data[0]["sequence"] + 1
            
            # Convert complex content to JSON string if needed
            if isinstance(content, (dict, list)):
                content = json.dumps(content)
            
            # Insert new message
            supabase.table("llm_messages").insert({
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sequence": next_sequence
            }).execute()
            
            return True
            
        except Exception as e:
            print(f"Error appending message: {e}")
            return False
    
    @staticmethod
    def save_messages(user_id: str, session_id: str, messages: List[Dict]) -> bool:
        """
        Save messages for a session (ONLY use for initialization)
        Replaces all existing messages for this session
        
        Args:
            user_id: User ID (reference to Prisma user, not a FK)
            session_id: Session/Workspace ID
            messages: List of message objects [{"role": "user", "content": "..."}]
        
        Returns:
            bool: True if successful
        """
        try:
            # First, delete existing messages for this session
            supabase.table("llm_messages").delete().eq("session_id", session_id).execute()
            
            # Insert new messages with sequence numbers
            for i, msg in enumerate(messages):
                # Convert complex content (with images) to JSON string if needed
                content = msg.get("content", "")
                if isinstance(content, (dict, list)):
                    content = json.dumps(content)
                
                supabase.table("llm_messages").insert({
                    "user_id": user_id,
                    "session_id": session_id,
                    "role": msg.get("role", "user"),
                    "content": content,
                    "sequence": i
                }).execute()
            
            return True
            
        except Exception as e:
            print(f"Error saving messages: {e}")
            return False
    
    @staticmethod
    def get_messages(session_id: str) -> List[Dict]:
        """
        Get all messages for a session in order
        
        Args:
            session_id: Session/Workspace ID
        
        Returns:
            List of message objects [{"role": "user", "content": "..."}]
        """
        try:
            response = supabase.table("llm_messages")\
                .select("role, content, sequence")\
                .eq("session_id", session_id)\
                .order("sequence")\
                .execute()
            
            messages = []
            for row in response.data:
                content = row["content"]
                # Try to parse JSON content (for image messages)
                try:
                    content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string
                
                messages.append({
                    "role": row["role"],
                    "content": content
                })
            
            return messages
            
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    @staticmethod
    def session_exists(session_id: str) -> bool:
        """Check if a session has any messages"""
        try:
            response = supabase.table("llm_messages")\
                .select("id", count="exact")\
                .eq("session_id", session_id)\
                .limit(1)\
                .execute()
            
            return response.count > 0
            
        except Exception as e:
            print(f"Error checking session: {e}")
            return False
    
    @staticmethod
    def delete_session_messages(session_id: str) -> bool:
        """Delete all messages for a session"""
        try:
            supabase.table("llm_messages").delete().eq("session_id", session_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting messages: {e}")
            return False


# Convenience functions
def append_message(user_id: str, session_id: str, role: str, content) -> bool:
    """Append a single message (efficient)"""
    return MessageStore.append_message(user_id, session_id, role, content)


def save_messages(user_id: str, session_id: str, messages: List[Dict]) -> bool:
    """Save messages to Supabase (only use for initialization)"""
    return MessageStore.save_messages(user_id, session_id, messages)


def get_messages(session_id: str) -> List[Dict]:
    """Get messages from Supabase"""
    return MessageStore.get_messages(session_id)


def session_exists(session_id: str) -> bool:
    """Check if session has messages"""
    return MessageStore.session_exists(session_id)


def delete_session_messages(session_id: str) -> bool:
    """Delete all messages for a session"""
    return MessageStore.delete_session_messages(session_id)

