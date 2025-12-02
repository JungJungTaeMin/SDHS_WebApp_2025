"""
Unified AI Client for all AI operations
"""
import json
from typing import Optional, Dict, Any
from openai import OpenAI

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings


class AIClient:
    """Centralized AI client for Perplexity API calls"""
    
    def __init__(self):
        if not settings.pplx_api_key:
            raise ValueError("PPLX_API_KEY is not configured")
        
        self.client = OpenAI(
            api_key=settings.pplx_api_key,
            base_url="https://api.perplexity.ai"
        )
        self.model = "sonar-pro"
    
    def chat(
        self, 
        system_prompt: str, 
        user_prompt: str,
        response_format: Optional[Dict] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Send a chat completion request
        
        Args:
            system_prompt: System message content
            user_prompt: User message content
            response_format: Optional JSON schema for structured output
            temperature: Creativity level (0.0-1.0)
        
        Returns:
            Response content as string
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        completion = self.client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content
    
    def chat_json(
        self, 
        system_prompt: str, 
        user_prompt: str,
        schema: Dict[str, Any],
        schema_name: str = "response"
    ) -> Dict:
        """
        Send a chat request expecting JSON response
        
        Args:
            system_prompt: System message content
            user_prompt: User message content
            schema: JSON schema for the response
            schema_name: Name for the schema
        
        Returns:
            Parsed JSON response as dict
        """
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "schema": schema
            }
        }
        
        content = self.chat(system_prompt, user_prompt, response_format)
        return json.loads(content)
    
    def extract_json(self, content: str) -> Dict:
        """Extract JSON from response that may contain markdown"""
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find('{')
        end = content.rfind('}') + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        return json.loads(content[start:end])


# Singleton instance
_ai_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get or create AI client singleton"""
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client
