import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class NeuroSymbolicAnalyzer:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.default_model = "llama3"
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def analyze(self, source_code, diagnostics, security_warnings, model_name=None):
        prompt = self.build_prompt(source_code, diagnostics, security_warnings)
        
        try:
            payload = {
                "model": "llama3", 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "num_ctx": 1024,
                    "num_predict": 350,
                    "temperature": 0.1
                }
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=180)
            if resp.status_code == 200:
                return f"### 🦙 Local AI (llama3)\n\n{resp.json().get('response', '')}"
            return f"### ⚠️ Local AI Error {resp.status_code}"
        except Exception as e:
            return f"### ❌ AI Unavailable\n\nOllama Error: {str(e)}"

    def build_prompt(self, source_code, diagnostics, security_warnings):
        diag_text = "\n".join(
            f"- [{d.get('type')}] Line {d.get('line','?')}: {d.get('message')}"
            for d in diagnostics
        ) if diagnostics else "None"

        return (
            "You are a Mini-C compiler expert. Fix the code below.\n\n"
            f"Code:\n```c\n{source_code.strip()}\n```\n\n"
            f"Errors:\n{diag_text}\n\n"
            "Provide: 1) Root cause  2) Fixed code  3) One-line tip. Be concise."
        )
