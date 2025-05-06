from openai import OpenAI
from typing import List, Dict
import json
import os
import re
from .tools.base import Tool
import time

REACT_AGENT_SYSTEM_PROMPT = """
Answer the following questions as best you can. You have access to the following tools:

{tools}

"IMPORTANT: When you receive real-time information from the external tools, trust that information and include it in your final answer, even if it concerns events beyond your training cutoff."

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
"""

FINAL_ANSWER_SYSTEM_PROMPT = """
Provided the observation from the tool, answer the question. You can call further tool usage or provide the final answer

Use the following format:
Question: the input question you must answer
Thoought: think to call further tools or provide the final answer
Action: the action to take, either one of [{tool_names}] or "Final Answer"
Action Input: the input to the action if applicable
Observation: the result of the action if applicable
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
"""

class AgentPro:
    def __init__(self, llm = None, tools: List[Tool] = [], system_prompt: str = None, react_prompt: str = REACT_AGENT_SYSTEM_PROMPT, final_prompt: str = FINAL_ANSWER_SYSTEM_PROMPT, client_details: Dict = None):
        super().__init__()
        if client_details:
            self.client = OpenAI(
                api_key=client_details.get("api_key"),
                base_url=client_details.get("api_base"),
            )
            self.model = client_details.get("MODEL")
        else:
            self.client = llm if llm else OpenAI()
            self.model = 'gpt-4o-mini'
        self.tools = self.format_tools(tools)
        self.react_prompt = react_prompt.format(
            tools="\n\n".join(map(lambda tool: tool.get_tool_description(), tools)),
            tool_names=", ".join(map(lambda tool: tool.name, tools))
        )
        self.messages = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
        self.messages.append({"role": "system", "content": self.react_prompt})
        self.final_prompt = final_prompt.format(
            tools="\n\n".join(map(lambda tool: tool.get_tool_description(), tools)),
            tool_names=", ".join(map(lambda tool: tool.name, tools))
        )

    def format_tools(self, tools: List[Tool]) -> Dict:
        tool_names = list(map(lambda tool: tool.name, tools))
        return dict(zip(tool_names, tools))

    def parse_actions(self, response: str):
        lines = response.splitlines()
        actions = []
        current_action = None
        current_input = ""
        inside_input = False
        inside_observation = False

        for line in lines:
            if line.strip().startswith("Action:"):
                if current_action and current_input:
                    parsed_input = self.safe_parse_input(current_input.strip())
                    actions.append((current_action, parsed_input))
                current_action = line.replace("Action:", "").strip()
                current_input = ""
                inside_input = False
                inside_observation = False

            elif line.strip().startswith("Action Input:"):
                current_input = line.replace("Action Input:", "").strip()
                inside_input = True
                inside_observation = False
            elif line.strip().startswith("Observation:"):
                inside_observation = True
                continue

            elif inside_input and not inside_observation:
                current_input += "\n" + line

        if current_action and current_input:
            parsed_input = self.safe_parse_input(current_input.strip())
            actions.append((current_action, parsed_input))

        return actions
    
    def safe_parse_input(self, input_str):
        if not isinstance(input_str, str):
            return input_str
        input_str = input_str.strip()
        if input_str.startswith("```"):
            input_str = re.sub(r"^```(?:json)?", "", input_str)
            input_str = re.sub(r"```$", "", input_str.strip())
        decoder = json.JSONDecoder()
        try:
            obj, idx = decoder.raw_decode(input_str)
            return obj
        except json.JSONDecodeError:
            return input_str

    def tool_call(self, response):
        action, action_input = self.parse_action_string(response)
        try:
            if action.strip().lower() in self.tools:
                tool_observation = self.tools[action].run(action_input)
                return f"Observation: {tool_observation}"
            return f"Observation: Tool '{action}' not found. Available tools: {list(self.tools.keys())}"
        except Exception as e:
            return f"Observation: There was an error executing the tool\nError: {e}"

    def generate_response(self, prompt:str = None):
        retries = 5
        if prompt is None:
            pass
        else:
            self.messages.append(
                {"role": "user", "content": prompt}
            )
        for _ in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    max_tokens=8000
                ).choices[0].message.content.strip()
                return response
            except Exception as e:
                if "Rate limit" in str(e):
                    print("Rate limit error, retrying...")
                    time.sleep(10)
                else:
                    raise e
        return "Error: Rate limit exceeded multiple times."

    def __call__(self, prompt):
        response = self.generate_response(prompt)
        tools_called = False
        final_answer_seen = False

        while True:
            self.messages.append({"role": "assistant", "content": response})
            print("="*80)
            print(response)
            print("="*80)

            # Check if Final Answer is already in the response
            # if "Final Answer:" in response:
            #     final_answer_seen = True

            actions = self.parse_actions(response)
            print("Actions:", actions)

            for action, action_input in actions:
                if action.lower() in self.tools:
                    print(f"🛠️ Calling tool: {action} with input: {action_input}")
                    tool_observation = self.tools[action.lower()].run(action_input)
                    self.messages.append({"role": "assistant", "content": f"Observation: {tool_observation}"})
                    tools_called = True
                elif action.lower() == "final answer":
                    continue  # Let it fall through
                else:
                    error_message = f"Observation: Tool '{action}' not found. Available tools: {list(self.tools.keys())}"
                    print(error_message)
                    self.messages.append({"role": "assistant", "content": error_message})
            
            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()

            if final_answer_seen:
                if tools_called:
                    print("✅ Final answer found and tools already used. Ending loop.")
                    return response.split("Final Answer:")[-1].strip()
                else:
                    # No tools used, just return the answer directly
                    return response.split("Final Answer:")[-1].strip()

            # If not final yet, generate next response
            response = self.generate_response(self.final_prompt)