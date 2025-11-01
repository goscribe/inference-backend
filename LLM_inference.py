from openai import OpenAI
import os
from dotenv import load_dotenv


MODEL = "gpt-5-nano"

def LLM_inference(messages, json_output=False, response_format=None):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key, timeout=120000)
    if json_output:
        output = client.chat.completions.create(model=MODEL, messages=messages, response_format=response_format)
    else:
        output = client.chat.completions.create(model=MODEL, messages=messages)
    return output
    
