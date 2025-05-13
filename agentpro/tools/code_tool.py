import re
import subprocess
import sys
from .base import LLMTool
class CodeEngine(LLMTool):
    name: str = "Code Generation and Execution Tool"
    description: str = "A coding tool that can take a prompt and generate executable Python code. It parses and executes the code. Returns the code and the error if the code execution fails."
    arg: str = "A single string parameter describing the coding task. Donot include any code or comments. The tool will generate the code for you."
    def __init__(self, client_details: dict = None, model_name:str ='', temp:float = 0.7, max_tokens:int = 4000,**data):
        super().__init__(client_details=client_details, model_name=model_name,**data)
        print(f"Using model: {self.model} for code generation")
        self.temperature = temp if temp else 0.7
        self.max_tokens = max_tokens if max_tokens else 4000
    def parse_and_exec_code(self, response: str):
        print("Parsing and executing code...")
        result = re.search(r'```python\s*([\s\S]*?)\s*```', response)
        if not result: return "No Python code block found", "Failed to extract code"
        code_string = result.group(1)
        if "pip install" in code_string.split("\n")[0]:
            print("Requires PIP package installations")
            packages = code_string.split("\n")[0].split("pip install")[-1].strip()
            if "," in packages:    packages = packages.split(",")
            elif " " in packages:  packages = packages.split(" ")
            else:                  packages = [packages]
            print(f"Installing packages: {packages}")
            for package in packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("Executing main code...")
        try:
            exec(code_string)
        except Exception as e:
            print(f"Error executing generated code: {e}")
            return code_string, e
        return code_string, None
    def generate_code(self, prompt, temp, max_tokens):
        print(f"🎉Generating code for prompt")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a Python code generator. Respond only with executable Python code, no explanations or comments except for required pip installations at the top. Return the code within ```python and ``` strings. The first line should be commented out pip install statement"},
                {"role": "user", "content": f"Generate Python code to {prompt}. If you need to use any external libraries, include a comment at the top of the code listing the required pip installations."}
            ],
            max_tokens=max_tokens,
            temperature=temp,
        )
        print(f"Generated code: {response}")
        response = response.choices[0].message.content
        print(f"Generated code: {response}")
        code, error = self.parse_and_exec_code(response)
        return code, error
    def run(self, prompt: str, temp=0.7, max_tokens=4000) -> str:
        print(f"Code Generation Tool received: {prompt} with temp: {temp}, max_tokens: {max_tokens}")
        is_code = (prompt.strip().startswith("```python") or prompt.strip().startswith("#") or prompt.strip().startswith("import") or "def " in prompt or "class " in prompt or prompt.strip().endswith(":"))
        if is_code:
            print("Detected raw Python code input, executing directly...")
            code, error = self.parse_and_exec_code(prompt)
        else:
            print("Treating input as natural language prompt, generating code...")
            code, error = self.generate_code(prompt, temp, max_tokens)
        if error:
            return f"Code: {code}\n\nCode execution caused an error: {error}"
        return f"Code: {code}\n\n\nCode Executed Successfully"
