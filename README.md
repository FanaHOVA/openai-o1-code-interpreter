# OpenAI O1 Code Interpreter

Simple hack to add code interpreting capabilities to OpenAI o1. It's able to display charts as outputs as well.

All code execution runs on [e2b](https://e2b.dev); you can modify `#code_interpret` to run locally instead (not recommended for safety reasons).

# Setup

- Add API keys to `.env` based on `.env.sample`
- Modify the code with a new prompt or pass it through the cli: `python main.py Create a report on the evolution of labor productivity in the United States, and what major technological shifts led to it`
- Outputs are saved to `o1_outputs` folder

TODOs:
- When a chart is created, automatically save it and match the name in the report. Right now I save the charts manually in the folder.