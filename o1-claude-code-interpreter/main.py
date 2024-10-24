from typing import List
import os
import re
import dotenv
import sys
import base64
import io
import uuid

from PIL import Image
import matplotlib.pyplot as plt
from openai import OpenAI
from anthropic import Anthropic
from e2b_code_interpreter import Sandbox
from pydantic import BaseModel

# Set base directory to the project root
BASE_DIR = "/Users/terezatizkova/Developer/openai-o1-code-interpreter-2"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Initialize both clients
dotenv.load_dotenv()
openai_client = OpenAI()
anthropic_client = Anthropic()


class PythonNotebookCell(BaseModel):
    code: str
    pip_packages_required: List[str]


def ask_openai(prompt, model="o1-preview", path=None):
    # Keep original O1 function for planning
    if path is not None and os.path.exists(path):
        with open(path, "r") as f:
            return f.read()

    result = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    
    content = result.choices[0].message.content
    
    if path is not None:
        with open(path, "w") as f:
            f.write(content)
    
    return content


def ask_claude(prompt):
    """New function to interact with Claude 3.5 Sonnet"""
    message = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    return message.content[0].text


def extract_code(execution_plan):
    """Modified to use Claude for code generation"""
    prompt = """You are an expert software engineer. I will give you an execution plan, and you need to create a single Python script that does everything in the plan. It will be executed in a single Python notebook cell.

Please respond with:
1. A list of required pip packages
2. The complete Python code

Plan: {execution_plan}

Format your response like this:
PACKAGES:
package1
package2

CODE:
[your code here]"""

    response = ask_claude(prompt.format(execution_plan=execution_plan))
    
    # Parse Claude's response
    try:
        # Split response into packages and code sections
        packages_section = response.split("PACKAGES:")[1].split("CODE:")[0].strip()
        code_section = response.split("CODE:")[1].strip()
        
        # Convert packages string to list
        pip_packages = [pkg.strip() for pkg in packages_section.split('\n') if pkg.strip()]
        
        return PythonNotebookCell(
            code=code_section,
            pip_packages_required=pip_packages
        )
    except Exception as e:
        print(f"Error parsing Claude's response: {e}")
        # Fallback with minimal requirements
        return PythonNotebookCell(
            code=response,
            pip_packages_required=["pandas", "matplotlib"]
        )


def fix_code_with_claude(code, error):
    """New function to use Claude for error fixing"""
    prompt = f"""The following Python code has an error. Please fix it and return only the corrected code.

Code:
{code}

Error:
{error}

Please analyze the error and provide the complete corrected code. Return only the code, no explanations."""

    return ask_claude(prompt)


def code_interpret(sandbox: Sandbox, code: str):
    print("Running code interpreter...")
    return sandbox.run_code(
        code,
        on_stderr=lambda stderr: print("[Code Interpreter]", stderr),
        on_stdout=lambda stdout: print("[Code Interpreter]", stdout),
    )


def save_and_display_png(png_data):
    """Save PNG to file and display it"""
    image_data = base64.b64decode(png_data)
    image_buffer = io.BytesIO(image_data)
    image = Image.open(image_buffer)
    
    base_filename = "output"
    chart_filename = os.path.join(CHARTS_DIR, f"{base_filename}.png")
    
    counter = 1
    while os.path.exists(chart_filename):
        chart_filename = os.path.join(CHARTS_DIR, f"{base_filename}_{counter}.png")
        counter += 1
    
    image.save(chart_filename)
    print(f"Chart saved as: {chart_filename}")
    
    plt.imshow(image)
    plt.axis("off")
    plt.show()
    
    return chart_filename


def update_markdown_with_charts(markdown_path, chart_files):
    if not os.path.exists(markdown_path):
        return
        
    with open(markdown_path, 'r') as f:
        content = f.read()
    
    content += "\n\n## Generated Charts\n"
    for chart_file in chart_files:
        rel_path = os.path.relpath(chart_file, os.path.dirname(markdown_path))
        content += f"\n![Chart]({rel_path})\n"
    
    with open(markdown_path, 'w') as f:
        f.write(content)


def run_code(script: PythonNotebookCell):
    sandbox = Sandbox(timeout=300)
    chart_files = []

    code_interpret(sandbox, "pip install " + " ".join(script.pip_packages_required))

    code_to_run = script.code

    while True:
        execution = code_interpret(sandbox, code_to_run)
        if execution.error is None:
            results = execution.results
            break

        # Use Claude to fix errors
        fixed_code = fix_code_with_claude(
            code_to_run,
            f"{execution.error.name}: {execution.error.value}\n{execution.error.traceback}"
        )
        code_to_run = fixed_code
        print(f"Claude suggested fix: {code_to_run}")

    print(results)
    for result in results:
        print(result)

        if hasattr(result, "png"):
            chart_file = save_and_display_png(result.png)
            chart_files.append(chart_file)
    
    return chart_files


def main(prompt=None):
    if prompt is None:
        # prompt = """
        # I want to create a visualization of the growth of the Roman empire population and land under its control. 
        # Mark every important historical event along the way; if you don't have data on the population between two events, just keep it flat.
        # """
        prompt = """
        I want to create a visualization of market shares of self-driving vehicle manufacturers in 2022 vs 2023 vs 2024. 
        """

    prompt = f"""
    {prompt}
    You have access to a code interpreter that can run python code; display the charts in the notebook.
    """

    output = ask_openai(prompt, path=os.path.join(OUTPUT_DIR, "output.md"))
    code_to_run = extract_code(output)
    chart_files = run_code(code_to_run)
    update_markdown_with_charts(os.path.join(OUTPUT_DIR, "output.md"), chart_files)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        main(prompt)
    else:
        main()