import requests
import os
from pydantic import HttpUrl
from .base import Tool

class AresInternetTool(Tool):
    name: str = "Ares Internet Search Tool"
    description: str = "Tool to search real-time relevant content from the internet"
    arg: str = "A single string parameter that will be searched on the internet to find relevant content"

    # Specific Parameters
    url: HttpUrl = "https://api-ares.traversaal.ai/live/predict"
    x_api_key: str = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.x_api_key is None:
            self.x_api_key = os.environ.get("TRAVERSAAL_ARES_API_KEY")
            if not self.x_api_key:
                raise ValueError("TRAVERSAAL_ARES_API_KEY environment variable not set")

    def run(self, prompt: str, temp = 0.7, max_tokens= 4000) -> str:
        print(f"🛠️ Calling Ares Internet Search Tool with prompt: {prompt} , temperature: {temp}, and max_tokens: {max_tokens}")
        payload = {"query": [prompt]}
        response = requests.post(self.url, json=payload, headers={
            "x-api-key": self.x_api_key,
            "content-type": "application/json"
        })
        print(f"Response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        response = response.json()
        return response['data']['response_text']