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
from e2b_code_interpreter import Sandbox
from pydantic import BaseModel


dotenv.load_dotenv()

client = OpenAI()    

# Create output directories if they don't exist
os.makedirs("o1_outputs", exist_ok=True)
os.makedirs("o1_outputs/charts", exist_ok=True)


class PythonNotebookCell(BaseModel):
    code: str
    pip_packages_required: List[str]


def ask_openai(prompt, model="o1-preview", path=None):
    # Caching the output of the prompt to a file because o1 goes brrr
    if path is not None and os.path.exists(path):
        with open(path, "r") as f:
            return f.read()

    result = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    content = result.choices[0].message.content
    
    # Save the output if path is provided
    if path is not None:
        with open(path, "w") as f:
            f.write(content)
    
    return content


def extract_code(execution_plan):
    result = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert software engineer that receives an execution plan, and then creates a single Python script that does everything in the plan. It will be executed in a single Python notebook cell.",
            },
            {
                "role": "user",
                "content": f"This is the plan I received, please write fully functional code that I can run in one notebook cell, and list all its dependencies: {execution_plan}",
            },
        ],
        response_format=PythonNotebookCell,
    )

    return result.choices[0].message.parsed


def code_interpret(sandbox: Sandbox, code: str):
    print("Running code interpreter...")
    return sandbox.run_code(
        code,
        on_stderr=lambda stderr: print("[Code Interpreter]", stderr),
        on_stdout=lambda stdout: print("[Code Interpreter]", stdout),
    )


def save_and_display_png(png_data, base_filename):
    """Save PNG to file and display it"""
    image_data = base64.b64decode(png_data)
    
    # Create a BytesIO object
    image_buffer = io.BytesIO(image_data)
    
    # Open the image using PIL
    image = Image.open(image_buffer)
    
    # Save the image
    chart_filename = f"o1_outputs/charts/{base_filename}_{str(uuid.uuid4())[:8]}.png"
    image.save(chart_filename)
    print(f"Chart saved as: {chart_filename}")
    
    # Display the image using matplotlib
    plt.imshow(image)
    plt.axis("off")  # Turn off axis
    plt.show()
    
    return chart_filename


def update_markdown_with_charts(markdown_path, chart_files):
    """Update markdown file to include references to saved charts"""
    if not os.path.exists(markdown_path):
        return
        
    with open(markdown_path, 'r') as f:
        content = f.read()
    
    # Add chart references at the end of the file
    content += "\n\n## Generated Charts\n"
    for chart_file in chart_files:
        content += f"\n![Chart]({os.path.relpath(chart_file, os.path.dirname(markdown_path))})\n"
    
    with open(markdown_path, 'w') as f:
        f.write(content)


def run_code(script: PythonNotebookCell, base_filename: str):
    sandbox = Sandbox(timeout=300)
    chart_files = []

    code_interpret(sandbox, "pip install " + " ".join(script.pip_packages_required))

    code_to_run = script.code

    while True:
        execution = code_interpret(sandbox, code_to_run)
        if execution.error is None:
            results = execution.results
            break
        prompt = f"""
        Code Run: '{code_to_run}'
        Error: {execution.error.name}, {execution.error.value}
        Traceback: {execution.error.traceback}
        How can I fix this?
        """

        solution = ask_openai(prompt, model="gpt-4o")

        script = extract_code(solution)

        code_to_run = script.code
        print(f"Suggested solution: {code_to_run}")

    print(results)
    for result in results:
        print(result)

        if hasattr(result, "png"):
            chart_file = save_and_display_png(result.png, base_filename)
            chart_files.append(chart_file)
    
    return chart_files


def main(prompt=None):
    if prompt is None:
        prompt = """
        I want to create a visualization of the growth of the Roman empire population and land under its control. 
        Mark every important historical event along the way; if you don't have data on the population between two events, just keep it flat.
        """

    # Remember the system it has code interpreter
    prompt = f"""
    {prompt}
    You have access to a code interpreter that can run python code; display the charts in the notebook.
    """

    cleaned_prompt = re.sub(r"\W+", "_", prompt[:50])
    base_filename = cleaned_prompt.lower()
    markdown_path = f"./o1_outputs/{base_filename}.md"

    output = ask_openai(prompt, path=markdown_path)
    code_to_run = extract_code(output)
    
    # Run code and get list of saved chart files
    chart_files = run_code(code_to_run, base_filename)
    
    # Update markdown with chart references
    update_markdown_with_charts(markdown_path, chart_files)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Join all arguments after the script name into a single string
        prompt = " ".join(sys.argv[1:])
        main(prompt)
    else:
        main()  # Run with the default prompt