from agentpro import AgentPro
from agentpro.tools import (
    AresInternetTool, CodeEngine, YouTubeSearchTool,
    SlideGenerationTool, NoteManager, FAISSVectorDB, PlannerTool
)
import os
import dotenv
from sentence_transformers import SentenceTransformer
import faiss
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

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    note_store = []
    faiss_index = faiss.IndexFlatIP(embedding_model.get_sentence_embedding_dimension())
    vector_db = FAISSVectorDB(faiss_index, note_store)

    youtube_tool_instance = YouTubeSearchTool(client_details=client_details)

    common_tools = [
        AresInternetTool(),
        CodeEngine(client_details),
        youtube_tool_instance,
        SlideGenerationTool(client_details=client_details)
    ]

    # Optional tools
    tools = common_tools.copy()

    if os.environ.get("TRAVERSAAL_ARES_API_KEY"):
        note_manager_tool = NoteManager(
            vector_db=vector_db,
            embedding_model=embedding_model,
            youtube_tool=youtube_tool_instance,
            ares_tool=common_tools[0]  # AresInternetTool
        )
        tools.append(note_manager_tool)

    # Create a sub-agent with all common tools (for planner)
    sub_agent = AgentPro(tools=common_tools, client_details=client_details if use_openrouter else None)

    # Add the PlannerTool with the sub-agent injected
    planner_tool = PlannerTool(sub_agent=sub_agent)
    tools.append(planner_tool)

    # Main agent
    agent = AgentPro(tools=tools, client_details=client_details if use_openrouter else None)

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