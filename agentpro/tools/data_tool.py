# agentpro/tools/data_tool.py
import re
import os
import io
import sys
import pandas as pd
import traceback
import contextlib
from .base import LLMTool
class DataScienceTool(LLMTool):
    name: str = "Data Science Tool"
    description: str = (
        "A tool for analyzing and manipulating one or more CSV datasets using pandas. "
    "You can ask complex queries involving filters, joins, aggregations, selection, manipulation, data Q/A etc."
    )
    arg: str = (
        "A natural language string describing a data task such as "
        "'Join employee.csv and department.csv to find average salary per department'. "
        "CSV files mentioned in the prompt must exist."
    )
    def __init__(self, client_details: dict = None, model_name: str = '', temp: float = 0.1, max_tokens: int = 1500, **data):
        super().__init__(client_details=client_details, model_name=model_name, **data)
        print(f"Using model: {self.model} for data tool")
        self.temperature = temp
        self.max_tokens = max_tokens
    def extract_csv_paths(self, prompt: str) -> list:
        csv_pattern = r"[a-zA-Z0-9_\-/\\]+\.csv"
        all_paths = re.findall(csv_pattern, prompt)
        valid_paths = [p for p in all_paths if os.path.exists(p)]
        return valid_paths
    def get_csv_schemas(self, csv_dir: str, max_rows=5) -> tuple[str, dict]:
        schema_text = ""
        dataframes = {}
        for filename in os.listdir(csv_dir):
            if filename.endswith(".csv"):
                path = os.path.join(csv_dir, filename)
                df_name = f"df_{os.path.splitext(filename)[0].replace('-', '_').replace(' ', '_')}"
                try:
                    df = pd.read_csv(path)
                    info_buffer = io.StringIO()
                    df.info(buf=info_buffer)
                    sample = df.head(max_rows).to_markdown(index=False)
                    schema_text += (
                        f"📄 {filename} → `{df_name}`\n\n"
                        f"Columns and Types:\n```\n{info_buffer.getvalue()}```\n\n"
                        f"Sample Rows:\n{sample}\n\n---\n\n"
                    )
                    dataframes[df_name] = df
                except Exception as e:
                    schema_text += f"⚠️ Could not load {filename}: {e}\n\n"
        if not dataframes:
            raise FileNotFoundError(f"No valid CSV files loaded from: {csv_dir}")
        return schema_text, dataframes
    def get_csv_schemas_from_paths(self, paths: list[str], max_rows=5) -> tuple[str, dict]:
        schema_text = ""
        dataframes = {}
        for path in paths:
            filename = os.path.basename(path)
            df_name = f"df_{os.path.splitext(filename)[0].replace('-', '_').replace(' ', '_')}"
            try:
                df = pd.read_csv(path)
                info_buffer = io.StringIO()
                df.info(buf=info_buffer)
                sample = df.head(max_rows).to_markdown(index=False)
                schema_text += (
                    f"📄 {filename} → `{df_name}`\n\n"
                    f"Columns and Types:\n```\n{info_buffer.getvalue()}```\n\n"
                    f"Sample Rows:\n{sample}\n\n---\n\n"
                )
                dataframes[df_name] = df
            except Exception as e:
                schema_text += f"⚠️ Could not load {filename}: {e}\n\n"
        if not dataframes:
            raise FileNotFoundError("CSV files found in prompt, but none could be loaded.")
        return schema_text, dataframes
    def generate_code(self, task: str, schema_context: str, temp:float, max_tok:int) -> str:
        prompt = (
            f"You are a data scientist. The following DataFrames are available:\n\n"
            f"{schema_context}\n\n"
            f"Task: {task}\n\n"
            f"Write pandas code that solves the task using the DataFrames above. "
            f"Do NOT read CSVs — assume they are already loaded as variables. "
            f"End your code with a final expression that returns the result, like a variable or value."
            f" Use print() to ensure the result is visible in the output."
            f" Output code only inside ```python code blocks."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": (
                    "You are a Python data analyst. Use pandas and numpy only. "
                    "Do not import CSVs, the DataFrames are already loaded with names like df_employees or df_states. "
                    "Always use print() to show the final result. Output executable Python code only."
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=temp if temp else self.temperature,
            max_tokens=max_tok if max_tok else self.max_tokens
        )
        return response.choices[0].message.content
    def extract_code(self, response: str) -> str:
        match = re.search(r'```python\s*([\s\S]*?)\s*```', response)
        return match.group(1).strip() if match else None
    def execute_code(self, code: str, dataframes: dict) -> str:
        print("⚙️ Executing code...")
        output = io.StringIO()
        exec_scope = {"pd": pd, **dataframes}
        final_expr = None
        if "\n" in code:
            *body, last = code.strip().split("\n")
            if not last.strip().startswith(("print", "#", "import", "from")):
                final_expr = last
                code = "\n".join(body)
        try:
            with contextlib.redirect_stdout(output):
                exec(code, {}, exec_scope)
                if final_expr:
                    result = eval(final_expr, {}, exec_scope)
                    print(result)
        except Exception:
            return f"Code:\n{code}\n\nExecution failed:\n{traceback.format_exc()}"
        return f"Code Executed Successfully:\n\nCode:\n{code}\n\nOutput:\n{output.getvalue()}"
    def run(self, prompt: str, temperature: float = None, max_tokens: int = None) -> str:
        print(f"📥 DataScienceTool received: {prompt}")
        try:
            csv_paths = self.extract_csv_paths(prompt)
            if not csv_paths:
                return "❌ No valid CSV file paths found in the prompt."
            schema_context, dataframes = self.get_csv_schemas_from_paths(csv_paths)
            llm_response = self.generate_code(prompt, schema_context, temperature, max_tokens)
            print(f"📤 LLM response: {llm_response}")
            code = self.extract_code(llm_response)
            if not code:
                return f"❌ Could not extract Python code.\nResponse was:\n{llm_response}"
            return self.execute_code(code, dataframes)
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"❌ Tool failed: {str(e)}"