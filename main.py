from typing import List
import os
import time
import re
from pydantic import BaseModel
import dotenv
import sys

from openai import OpenAI
from e2b_code_interpreter import CodeInterpreter, ProcessExitException
import base64
import io
from PIL import Image
import matplotlib.pyplot as plt

dotenv.load_dotenv()

client = OpenAI()

class PythonNotebookCell(BaseModel):
    code: str
    pip_packages_required: List[str]
    
def ask_openai(prompt, model='o1-preview',path=None):
    # Caching the output of the prompt to a file because o1 goes brrr
    if path is not None and os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
        
    result = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    
    return result.choices[0].message.content

def extract_code(execution_plan):
    result = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert software engineer that receives an execution plan, and then creates a single Python script that does everything in the plan. It will be executed in a single Python notebook cell." },
            {"role": "user", "content": f"This is the plan I received, please write fully functional code that I can run in one notebook cell, and list all its dependencies: {execution_plan}"},
        ],
        response_format=PythonNotebookCell
    )
    
    return result.choices[0].message.parsed

def code_interpret(sandbox: CodeInterpreter, code: str):
  print("Running code interpreter...")
  exec = sandbox.notebook.exec_cell(
    code,
    on_stderr=lambda stderr: print("[Code Interpreter]", stderr),
    on_stdout=lambda stdout: print("[Code Interpreter]", stdout),
  )

  if exec.error:
    print("[Code Interpreter ERROR]", exec.error)
  else:
    return exec.results 

def display_png(png_data):
    image_data = base64.b64decode(png_data)

    # Create a BytesIO object
    image_buffer = io.BytesIO(image_data)

    # Open the image using PIL
    image = Image.open(image_buffer)

    # Display the image using matplotlib
    plt.imshow(image)
    plt.axis('off')  # Turn off axis
    plt.show()

def run_code(script: PythonNotebookCell):
    sandbox = CodeInterpreter(timeout=300)
    
    code_interpret(sandbox, "pip install " + " ".join(script.pip_packages_required))
    
    code_to_run = script.code
    waiting_for_answer = True
    
    while waiting_for_answer:
        try:
            results = code_interpret(sandbox, code_to_run)
            waiting_for_answer = False
        except ProcessExitException as e:        
            prompt = f"""
            Code Run: '{code_to_run}'
            Error: {str(e)}
            
            How can I fix this?
            """
        
            solution = ask_openai(
                prompt,
                model="gpt-4o"
            )
            
            script = extract_code(solution)
            
            code_to_run = script.code
            print(f"Suggested solution: {code_to_run}")

    print(results)
    for result in results:
        print(result)
        
        if hasattr(result, 'png'):
            display_png(result.png) 

def main(prompt = None):
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

    cleaned_prompt = re.sub(r'\W+', '_', prompt[:50]) 
    filename = "output_" + cleaned_prompt + ".md"
    path = f"./o1_outputs/{filename}"
    
    output = ask_openai(prompt, path=path)
    
    # Saving those o1 outputs
    with open(path, "w") as f:
        f.write(output)
    
    code_to_run = extract_code(output)
    
    run_code(code_to_run)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Join all arguments after the script name into a single string
        prompt = " ".join(sys.argv[1:])
        main(prompt)
    else:
        main()  # Run with the default prompt