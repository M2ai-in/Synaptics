from .agent import AgentPro
from typing import Any
from agentpro.tools import AresInternetTool, CodeEngine, YouTubeSearchTool, SlideGenerationTool, NoteManager, PlannerTool # add more tools when available
# # ares_tool = AresInternetTool()
# code_tool = CodeEngine()
# youtube_tool = YouTubeSearchTool()
# slide_tool = SlideGenerationTool()
__all__ = ['AgentPro', 'ares_tool', 'code_tool', 'youtube_tool', 'slide_tool', 'note_manager_tool','planner_tool'] # add more tools when available