from agentpro import AgentPro
from agentpro.tools import (AresInternetTool, CodeEngine, YouTubeSearchTool,SlideGenerationTool, DataScienceTool)
import os
import dotenv
import numpy as np
def main():
    dotenv.load_dotenv()
    use_openrouter = os.getenv("OPENROUTER_API_KEY") is not None
    if use_openrouter:
        print('Using OpenRouter API')
        client_details = {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "api_base": "https://openrouter.ai/api/v1",
            "MODEL": os.getenv("MODEL_NAME"),
            "api_type": "openrouter"
        }
        CODE_MODEL=os.getenv("CODE_MODEL_NAME") if os.getenv("CODE_MODEL_NAME") else "gpt-4o-mini"
        YT_MODEL=os.getenv("YT_MODEL_NAME") if os.getenv("YT_MODEL_NAME") else "gpt-4o-mini"
        SLIDE_MODEL=os.getenv("SLIDE_MODEL_NAME") if os.getenv("SLIDE_MODEL_NAME") else "gpt-4o-mini"
        DATA_MODEL=os.getenv("DATA_MODEL_NAME") if os.getenv("DATA_MODEL_NAME") else "gpt-4o-mini"
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY environment variable is not set.")
            return
        client_details = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "api_base": "https://api.openai.com/v1/",
            "MODEL": os.getenv("MODEL_NAME"),
            "api_type": "openai"
        }
        CODE_MODEL="gpt-4o-mini"
        YT_MODEL="gpt-4o-mini"
        SLIDE_MODEL="gpt-4o-mini"
        DATA_MODEL="gpt-4o-mini"
    code_tool = CodeEngine(client_details=client_details, model_name=CODE_MODEL)
    youtube_tool = YouTubeSearchTool(client_details=client_details, model_name=YT_MODEL)
    slide_tool = SlideGenerationTool(client_details=client_details, model_name=SLIDE_MODEL)
    data_science_tool = DataScienceTool(client_details=client_details, model_name=DATA_MODEL)
    common_tools = [
        code_tool, youtube_tool, slide_tool, data_science_tool
    ]
    tools = common_tools.copy()
    if os.environ.get("TRAVERSAAL_ARES_API_KEY"):
        ares_tool = AresInternetTool(client_details=client_details)
        tools.append(ares_tool)

    agent = AgentPro(tools=tools, client_details=client_details if use_openrouter else None, temperature=0.1, max_tokens=4000)
    print("AgentPro is initialized and ready. Enter 'quit' to exit.")
    print("Available tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    while True:
        user_input = input("\nEnter your query: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break

        try:
            response = agent(user_input)
            print(f"\nAgent Response:\n{response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("Starting AgentPro...")
    main()