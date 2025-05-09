import os
import dotenv
from agentpro import AgentPro
from agentpro.tools import (
    AresInternetTool,
    CodeEngine,
    YouTubeSearchTool,
    SlideGenerationTool,
    DataScienceTool
)
class AgentRunner:
    def __init__(self, temperature: float = 0.1, max_tokens: int = 4000):
        dotenv.load_dotenv()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client_details = self._get_client_details()
        self.tools = self._init_tools()
        self.agent = AgentPro(
            tools=self.tools,
            client_details=self.client_details if self.client_details["api_type"] == "openrouter" else None,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    def _get_client_details(self) -> dict:
        if os.getenv("OPENROUTER_API_KEY"):
            print("Using OpenRouter API")
            return {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "api_base": "https://openrouter.ai/api/v1",
                "MODEL": os.getenv("MODEL_NAME", "gpt-4o-mini"),
                "api_type": "openrouter"
            }
        elif os.getenv("OPENAI_API_KEY"):
            print("Using OpenAI API")
            return {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "api_base": "https://api.openai.com/v1/",
                "MODEL": os.getenv("MODEL_NAME", "gpt-4o-mini"),
                "api_type": "openai"
            }
        else:
            raise EnvironmentError("No API key found in environment variables.")
    def _get_model(self, env_key: str, fallback: str = "gpt-4o-mini") -> str:
        return os.getenv(env_key, fallback)
    def _init_tools(self) -> list:
        code_tool = CodeEngine(
            client_details=self.client_details,
            model_name=self._get_model("CODE_MODEL_NAME"),
            temp=self.temperature,
            max_tokens=self.max_tokens
        )
        yt_tool = YouTubeSearchTool(
            client_details=self.client_details,
            model_name=self._get_model("YT_MODEL_NAME")
        )
        slide_tool = SlideGenerationTool(
            client_details=self.client_details,
            model_name=self._get_model("SLIDE_MODEL_NAME")
        )
        data_tool = DataScienceTool(
            client_details=self.client_details,
            model_name=self._get_model("DATA_MODEL_NAME"),
            temp=self.temperature,
            max_tokens=self.max_tokens
        )
        tools = [code_tool, yt_tool, slide_tool, data_tool]
        if os.getenv("TRAVERSAAL_ARES_API_KEY"):
            tools.append(AresInternetTool(client_details=self.client_details))
        return tools
    def run(self, prompt: str, clear_history:bool=False) -> str:
        return self.agent(prompt, clear_history=clear_history)