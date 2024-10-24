# O1-Claude Code Interpreter

A powerful visualization tool that combines OpenAI's O1 for planning and Claude 3.5 Sonnet for code generation. This tool can create various data visualizations based on natural language prompts.

## How It Works

1. **O1 Model**: Creates a detailed execution plan from your prompt
2. **Claude 3.5 Sonnet**: Generates and debugs Python code based on O1's plan
3. **E2B**: Executes the code in a secure sandbox environment
4. **Output**: Generates visualizations and saves them automatically

All code execution runs on [e2b](https://e2b.dev) for safety. While local execution is possible by modifying `code_interpret`, it's not recommended.

## Setup

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt

Set up your API keys in .env:

- OPENAI_API_KEY=your_openai_key
- ANTHROPIC_API_KEY=your_anthropic_key
- E2B_API_KEY =your_e2b_key
(Use .env.sample as a template)

## Usage

### Run with a custom prompt:
python main.py "Create a visualization of market shares of self-driving vehicle manufacturers in 2022 vs 2023 vs 2024"

### VSCode
Click the "play" button in main.py to run with the default prompt.

Try these example prompts to see different visualization capabilities:

1. Historical Data:
Create a visualization of the growth of the Roman empire population and land under its control. Mark every important historical event along the way.

1. Market Analysis:
Create a visualization of market shares of self-driving vehicle manufacturers in 2022 vs 2023 vs 2024.

1. Economic Trends:
Create a report on the evolution of labor productivity in the United States, and what major technological shifts led to it.


## Output

- Generated visualizations are saved in the output/charts directory
- Each prompt creates its own cache file for faster subsequent runs
- Markdown reports with embedded charts are saved in the output directory

## Features

📊 Automated chart generation and saving
🔄 Smart caching system (prompt-specific)
📝 Markdown report generation
🎨 Support for various visualization types
🛠 Automatic error handling and code fixes

## Technical Details

- Uses OpenAI's O1 model for execution planning
- Uses Claude 3.5 Sonnet for code generation and debugging
- Supports matplotlib, pandas, and other Python visualization libraries
- Secure code execution via e2b sandbox