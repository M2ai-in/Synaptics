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


def run_agent_once(prompt: str):
    dotenv.load_dotenv()

    use_openrouter = os.getenv("OPENROUTER_API_KEY") is not None

    client_details = {
        "api_key": os.getenv("OPENROUTER_API_KEY") if use_openrouter else os.getenv("OPENAI_API_KEY"),
        "api_base": "https://openrouter.ai/api/v1" if use_openrouter else "https://api.openai.com/v1/",
        "MODEL": os.getenv("MODEL_NAME"),
        "api_type": "openrouter" if use_openrouter else "openai"
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

    tools = common_tools.copy()

    if os.environ.get("TRAVERSAAL_ARES_API_KEY"):
        note_manager_tool = NoteManager(
            vector_db=vector_db,
            embedding_model=embedding_model,
            youtube_tool=youtube_tool_instance,
            ares_tool=common_tools[0]
        )
        tools.append(note_manager_tool)

    sub_agent = AgentPro(tools=common_tools, client_details=client_details if use_openrouter else None)
    planner_tool = PlannerTool(sub_agent=sub_agent)
    tools.append(planner_tool)

    agent = AgentPro(tools=tools, client_details=client_details if use_openrouter else None)
    
    return agent(prompt)