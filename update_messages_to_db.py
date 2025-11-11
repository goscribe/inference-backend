#!/usr/bin/env python3
"""
Script to update main.py to use Supabase database instead of messages.json files
Run this once to update all message handling
"""
import re

def update_main_py():
    with open('app/main.py', 'r') as f:
        content = f.read()
    
    # Replace all messages.json reads
    content = re.sub(
        r'with open\(f?"{ROOT_DIR}/{user}/{session}/messages\.json", "r"(?:, encoding="utf-8")?\) as f:\s*messages = json\.load\(f\)',
        'messages = get_messages(session)',
        content
    )
    
    # Replace all messages.json writes
    content = re.sub(
        r'with open\(f?"{ROOT_DIR}/{user}/{session}/messages\.json", "w"(?:, encoding="utf-8")?\) as f:\s*json\.dump\(messages, f(?:, indent=2)?(?:, ensure_ascii=False)?\)',
        'save_messages(user, session, messages)',
        content
    )
    
    with open('app/main.py', 'w') as f:
        f.write(content)
    
    print("✅ Updated main.py to use Supabase database for messages")
    print("   - Replaced all messages.json reads with get_messages()")
    print("   - Replaced all messages.json writes with save_messages()")

if __name__ == "__main__":
    update_main_py()

