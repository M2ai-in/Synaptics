from agentpro.tools.base import Tool
from pydantic import PrivateAttr

class PlannerTool(Tool):
    name: str = "planner_tool"
    description: str = (
        "Acts as a teacher assistant: recommends YouTube videos, summarizes content, "
        "and plans learning paths."
    )
    arg: str = "Instruction like 'plan deep learning', 'recommend videos on transformers', or 'summarize a topic'."

    _sub_agent = PrivateAttr()

    def __init__(self, sub_agent):
        super().__init__()
        self._sub_agent = sub_agent

    def run(self, prompt: str) -> str:
        print(f"🛠️ Calling Planner Tool with topic: {prompt}")
        intent, _, topic = prompt.partition(" ")
        intent = intent.strip().lower()
        topic = topic.strip()

        if not topic:
            return "Please provide a topic along with the instruction."

        if intent in ["plan", "learning", "learn"]:
            print("Planning learning for topic:", topic)
            return self.plan_learning(topic)
        elif intent in ["recommend", "video", "videos"]:
            print("Recommending videos for topic:", topic)
            return self.recommend_videos(topic)
        elif intent in ["summarize", "notes", "note"]:
            print("Summarizing and making notes for topic:", topic)
            return self.summarize_and_note(topic)
        else:
            return (
                "I didn't understand that. Try: 'plan deep learning', "
                "'recommend videos on transformers', or 'summarize quantum mechanics'."
            )

    def plan_learning(self, topic: str) -> str:
        prompt = f"Break down the topic '{topic}' into a step-by-step learning plan with subtopics."
        result= self._sub_agent(prompt)
        print("The result is :", result)
        return result

    def recommend_videos(self, topic: str) -> str:
        prompt = f"Find top YouTube videos to learn about {topic} effectively."
        # return self._sub_agent(prompt)
        result= self._sub_agent(prompt)
        print("The result is :", result)
        return result

    def summarize_and_note(self, topic: str) -> str:
        prompt = f"Search and summarize key points from online resources and make concise notes on {topic}."
        # return self._sub_agent(prompt)
        result= self._sub_agent(prompt)
        print("The result is :", result)
        return result