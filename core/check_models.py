"""
Gemini Model Availability Checker.

Utility script to list all available Google Gemini LLM models supporting content generation
for a configured GEMINI_API_KEY.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

def list_gemini_models():
    """Queries Google Generative AI API and prints active content generation models."""
    load_dotenv()
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)

if __name__ == "__main__":
    list_gemini_models()

