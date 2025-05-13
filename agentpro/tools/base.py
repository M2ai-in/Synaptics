from typing import Any
from abc import ABC, abstractmethod
from pydantic import BaseModel
from openai import OpenAI
import os
class Tool(ABC, BaseModel):
    name: str
    description: str
    arg: str
    def model_post_init(self, __context: Any) -> None:
        self.name = self.name.lower().replace(' ', '_')
        self.description = self.description.strip().lower()
        self.arg = self.arg.strip().lower()
    @abstractmethod
    def run(self, prompt: str) -> str:  pass
    def get_tool_description(self):     return f"Tool: {self.name}\nDescription: {self.description}\nArg: {self.arg}\n"
class LLMTool(Tool):
    client: Any = None
    model: str = "gpt-4o-mini"
    client_details: dict = None
    temperature: float = 0.7
    max_tokens: int = 4000
    def __init__(self, client_details: dict=None, model_name:str = "gpt-4o-mini",**data) -> None:
        super().__init__(**data)
        if client_details:
            self.client = OpenAI(api_key=client_details.get("api_key"), base_url=client_details.get("api_base"))
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key: raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
        self.model = model_name
    def run(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ).choices[0].message.content.strip()
            return response
        except Exception as e:
            return f"Error running LLMTool '{self.name}': {str(e)}"
