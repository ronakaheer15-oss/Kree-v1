"""
LLM Gateway Router
Acts as the central traffic cop for Kree's intelligence.
Routes prompts either to the Cloud (Gemini) or Local GPU (Ollama/Gemma)
based on the user's active intelligence mode.
"""
import os
import json
import logging
from pathlib import Path

# Try to import Google's SDK for cloud mode
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# We use requests for local Ollama to avoid adding heavy SDK dependencies
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

class KreeIntelligenceEngine:
    def __init__(self, mode="CLOUD_GEMINI"):
        """
        Available modes:
        - CLOUD_GEMINI
        - LOCAL_NEXUS_E4B (Ollama: gemma2:2b)
        - LOCAL_CORE_26B  (Ollama: gemma2:27b)
        - LOCAL_APEX_31B  (Ollama: command-r or similar 30B+)
        """
        self.mode = mode
        self.ollama_host = "http://127.0.0.1:11434"
        
        # Load real mode from config if it exists
        config_path = Path(os.path.dirname(__file__)).parent / "config" / "settings.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.mode = cfg.get("intelligence_mode", self.mode)
            except Exception:
                pass

        # Setup Cloud Client
        self.client = None
        if "CLOUD" in self.mode and genai:
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                self.client = genai.Client(api_key=api_key)

    def _get_local_model_name(self):
        if "NEXUS" in self.mode:
            return "gemma2:2b"
        elif "CORE" in self.mode:
            return "gemma2:27b"
        elif "APEX" in self.mode:
            # Fallback to an available large model, or just use 27b if standard
            return "gemma2:27b"
        return "gemma2:2b"

    def is_local_mode(self):
        return "LOCAL" in self.mode

    def generate_content(self, prompt, system_instruction=None):
        """
        Main text generation interface used across Kree codebase.
        Returns a string response.
        """
        if self.is_local_mode():
            return self._generate_local(prompt, system_instruction)
        else:
            return self._generate_cloud(prompt, system_instruction)

    def _generate_cloud(self, prompt, system_instruction=None):
        if not self.client:
            return "Error: Gemini API key not found or genai SDK missing."
        
        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_instruction
            ) if system_instruction else types.GenerateContentConfig(temperature=0.7)
            
            # Use flash-lite for basic operations
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            logger.error(f"[Gateway] Cloud generation failed: {e}")
            return f"Error connecting to Cloud Intelligence: {str(e)}"

    def _generate_local(self, prompt, system_instruction=None):
        if not requests:
            return "Error: Python 'requests' module not installed."

        model_name = self._get_local_model_name()
        
        # Build the conversation for Ollama
        messages = []
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction
            })
        messages.append({
            "role": "user",
            "content": prompt
        })

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        }

        try:
            url = f"{self.ollama_host}/api/chat"
            res = requests.post(url, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            return f"[ERROR] Local Mode Active ({self.mode}), but Ollama is not running. Please install Ollama and run '{model_name}'."
        except Exception as e:
            logger.error(f"[Gateway] Local generation failed: {e}")
            return f"Error interacting with Local Intelligence: {str(e)}"

# Singleton for easy importing
gateway = KreeIntelligenceEngine()
