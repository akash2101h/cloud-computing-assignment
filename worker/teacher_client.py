import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = "phi3.5"
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 100, "stop": ["\n\n", "Command:", "Note:"]}


def load_prompt(path="prompts/teacher_prompt.txt"):
    with open(path, encoding="utf-8") as f:
        return f.read()


def ask_teacher(prompt_template, text, url=OLLAMA_URL):
    """Return the teacher's exact reply for one command."""
    prompt = prompt_template.replace("{command}", text)
    r = requests.post(
        f"{url}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False, "options": OPTIONS},
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["response"]
