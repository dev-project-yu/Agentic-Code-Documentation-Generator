from __future__ import annotations

from typing import Any, Dict

import google.generativeai as genai

from app.config import settings


class GeminiService:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL
        self.enabled = bool(self.api_key)
        self.client = None
        if self.enabled:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model_name)

    def generate(self, prompt: str, system_instruction: str | None = None) -> str:
        if not self.enabled or self.client is None:
            raise RuntimeError("Gemini API Key 未配置，无法调用 LLM。")
        final_prompt = prompt
        if system_instruction:
            final_prompt = f"{system_instruction}\n\n{prompt}"
        response = self.client.generate_content(final_prompt, generation_config={"temperature": 0.2, "top_p": 0.9, "max_output_tokens": 2000})
        return getattr(response, "text", "") or ""
