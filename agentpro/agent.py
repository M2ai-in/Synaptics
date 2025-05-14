from openai import OpenAI
from typing import List, Dict, Union
import json
import os
import re
import time
from .tools.base import Tool
REACT_AGENT_SYSTEM_PROMPT = """
Answer the following questions as best you can. You have access to the following tools:

{tools}

"IMPORTANT: When you receive real-time information from the external tools, trust that information and include it in your final answer, even if it concerns events beyond your training cutoff.
Only provide a Final Answer if you are certain no tools are needed. If a tool is relevant, you MUST call it using Action and wait for an Observation before concluding."

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}], or "Final Answer" if no tools are needed
Action Input: the input to the action (only if using a tool)
Observation: the result of the action (only if a tool was used)
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question only if you are not using a tool
"""

FINAL_ANSWER_SYSTEM_PROMPT = """
Provided the observation from the tool, answer the question. You can call further tool usage or provide the final answer.

Use the following format:
Question: the input question you must answer
Thought: think to call further tools or provide the final answer
Action: the action to take, either one of [{tool_names}] or "Final Answer"
Action Input: the input to the action if applicable
Observation: the result of the action if applicable
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
"""
class AgentPro:
    def __init__(
        self,
        llm=None,
        tools: List[Tool] = [],
        system_prompt: str = None,
        react_prompt: str = REACT_AGENT_SYSTEM_PROMPT,
        final_prompt: str = FINAL_ANSWER_SYSTEM_PROMPT,
        client_details: Dict = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        max_steps: int = 2,
        max_tool_calls: int = 2,
    ):
        self.client = (llm if llm else OpenAI(api_key=client_details.get("api_key"), base_url=client_details.get("api_base")))
        self.model = client_details.get("MODEL", "gpt-4o-mini") if client_details else "gpt-4o-mini"
        print(f"Using model: {self.model} for AgentPro")
        self.tools = {tool.name.lower().replace(" ", "_"): tool for tool in tools}
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        tool_descriptions = "\n\n".join(tool.get_tool_description() for tool in tools)
        tool_names = ", ".join(self.tools.keys())
        self.react_prompt = react_prompt.format(tools=tool_descriptions, tool_names=tool_names)
        self.final_prompt = final_prompt.format(tools=tool_descriptions, tool_names=tool_names)
        self.system_prompt = system_prompt
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
        self.messages.append({"role": "system", "content": self.react_prompt})
    def clear_history(self): """Resets the conversation to the initial system prompts."""
        self.messages = []
        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})
        self.messages.append({"role": "system", "content": self.react_prompt})
    def safe_parse_input(self, input_str: str) -> Union[dict, str]:
        input_str = input_str.strip()
        if input_str.startswith("```"):
            input_str = re.sub(r"^```(?:json)?", "", input_str)
            input_str = re.sub(r"```$", "", input_str.strip())
        try:
            return json.loads(input_str)
        except json.JSONDecodeError:
            return input_str
    def parse_actions(self, response: str) -> List[tuple]:
        lines = response.splitlines()
        actions = []
        current_action = None
        current_input = ""
        inside_input = False
        inside_observation = False
        print("Parsing actions from response...")
        for line in lines:
            if line.strip().startswith("Action:"):
                if current_action and current_input:
                    actions.append((current_action, self.safe_parse_input(current_input)))
                current_action = line.replace("Action:", "").strip().lower()
                current_input = ""
                inside_input = False
                inside_observation = False
            elif line.strip().startswith("Action Input:"):
                current_input = line.replace("Action Input:", "").strip()
                inside_input = True
                inside_observation = False
            elif line.strip().startswith("Observation:"):
                inside_observation = True
            elif inside_input and not inside_observation:
                current_input += "\n" + line
        if current_action and current_input:
            actions.append((current_action, self.safe_parse_input(current_input)))
        return actions
    def generate_response(self, prompt: str = None, temperature: float = None, max_tokens: int = None) -> str:
        retries = 5
        if prompt:
            self.messages.append({"role": "user", "content": prompt})
        for _ in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    max_tokens=max_tokens if max_tokens is not None else self.max_tokens
                ).choices[0].message.content.strip()
                return response
            except Exception as e:
                if "Rate limit" in str(e):
                    print("Rate limited, retrying...")
                    time.sleep(10)
                else: raise e
        return "Error: Rate limit exceeded multiple times."
    def __call__(self, prompt: str, temperature: float = None, max_tokens: int = None, clear_history:bool=False) -> str:
        if clear_history: self.clear_history()
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        response = self.generate_response(prompt, temperature, max_tokens)
        last_valid_response = response
        tool_usage_count = 0
        for step in range(self.max_steps):
            self.messages.append({"role": "assistant", "content": response})
            print("=" * 80)
            print(response)
            print("=" * 80)
            if "Final Answer:" in response and not self.parse_actions(response):
                print("Final answer found in response.")
                return response.split("Final Answer:")[-1].strip()
            actions = self.parse_actions(response)
            if not actions:
                print("No actions found and no final answer.")
                break
            for action, action_input in actions:
                tool = self.tools.get(action)
                if tool:
                    if tool_usage_count >= self.max_tool_calls:
                        print("Max tool usage reached.")
                        return last_valid_response
                    print(f"\U0001f6e0\ufe0f Calling tool: {action} with input: {action_input}")
                    try:
                        tool_result = tool.run(action_input, temperature, max_tokens)
                        print(f"Tool result: {tool_result}")
                    except Exception as e:
                        print(f"Error while calling tool: {e}")
                        tool_result = f"Error while calling tool: {e}"
                    tool_usage_count += 1
                    self.messages.append({"role": "assistant", "content": f"Observation: {tool_result}"})
                else:
                    error_message = f"Observation: Tool '{action}' not found. Available tools: {list(self.tools.keys())}"
                    print(error_message)
                    self.messages.append({"role": "assistant", "content": error_message})
            response = self.generate_response(self.final_prompt, temperature, max_tokens)
            if response:
                last_valid_response = response
        print("Max steps reached. Returning best attempt.")
        return last_valid_response
