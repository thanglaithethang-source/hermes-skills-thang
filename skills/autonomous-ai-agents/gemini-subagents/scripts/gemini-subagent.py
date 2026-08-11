#!/usr/bin/env python3
"""Gemini 3.5 Flash sub-agent via Google AI API with function calling.

Usage: python gemini-subagent.py "prompt" --key API_KEY [--workdir DIR]

Model: gemini-3.5-flash
Max turns: 15
Tools: read_file, write_file, run_command, list_dir, task_done
"""
import json, os, sys, subprocess
from urllib.request import Request, urlopen

MODEL = "gemini-3.5-flash"
BASE = "https://generativelanguage.googleapis.com/v1beta"
MAX_TURNS = 15

TOOLS = [{
    "functionDeclarations": [
        {"name": "read_file", "description": "Read a file contents",
         "parameters": {"type": "object", "properties": {
             "path": {"type": "string"}}, "required": ["path"]}},
        {"name": "write_file", "description": "Write or create a file",
         "parameters": {"type": "object", "properties": {
             "path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"]}},
        {"name": "run_command", "description": "Run a shell command and return output",
         "parameters": {"type": "object", "properties": {
             "command": {"type": "string"}}, "required": ["command"]}},
        {"name": "list_dir", "description": "List files in a directory",
         "parameters": {"type": "object", "properties": {
             "path": {"type": "string"}}, "required": ["path"]}},
        {"name": "task_done", "description": "Call this when the task is complete",
         "parameters": {"type": "object", "properties": {
             "summary": {"type": "string"}}, "required": ["summary"]}}
    ]}]

def call_gemini(api_key, contents, system_instruction):
    body = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "tools": TOOLS,
        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}}
    }
    req = Request(
        f"{BASE}/models/{MODEL}:generateContent?key={api_key}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urlopen(req, timeout=120).read())

def execute_tool(call, workdir):
    name = call["name"]
    args = call.get("args", {})
    workdir = os.path.abspath(workdir)
    try:
        if name == "read_file":
            path = args["path"]
            if not os.path.isabs(path) or not os.path.exists(path):
                path = os.path.join(workdir, path)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[:8000]
        elif name == "write_file":
            path = args["path"]
            if not os.path.isabs(path) or (os.path.dirname(path) and
                not os.path.exists(os.path.dirname(path))):
                path = os.path.join(workdir, path)
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return f"Written: {path}"
        elif name == "run_command":
            r = subprocess.run(args["command"], shell=True,
                             capture_output=True, text=True,
                             cwd=workdir, timeout=120,
                             env={**os.environ})
            return (r.stdout + r.stderr)[:8000] or "(no output)"
        elif name == "list_dir":
            path = args["path"]
            if not os.path.isabs(path) or not os.path.exists(path):
                path = os.path.join(workdir, path)
            return "\n".join(sorted(os.listdir(path)))[:8000]
        elif name == "task_done":
            return args["summary"]
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error: {e}"

def run(prompt, api_key, workdir="."):
    system_instruction = (
        "You are a coding sub-agent. Execute tasks using tools. "
        "Make reasonable assumptions — do NOT ask questions. "
        "When finished, call task_done with a summary."
    )
    contents = [{"role": "user",
                 "parts": [{"text": f"WORKDIR: {os.path.abspath(workdir)}\n\n{prompt}"}]}]
    last_text = ""

    for turn in range(MAX_TURNS):
        resp = call_gemini(api_key, contents, system_instruction)

        # Check for errors
        if "candidates" not in resp:
            err = resp.get("error", {}).get("message", str(resp))
            return f"API_ERROR: {err}"

        parts = resp["candidates"][0]["content"]["parts"]
        function_calls = []
        for p in parts:
            if "functionCall" in p:
                function_calls.append(p["functionCall"])
            elif "text" in p:
                last_text = p["text"]

        if not function_calls:
            # Push agent to finish with task_done
            if turn < MAX_TURNS - 1:
                contents.append({"role": "model", "parts": parts})
                contents.append({"role": "user", "parts": [
                    {"text": "Call task_done with a summary of what you accomplished."}]})
                continue
            return last_text or "(max turns, no task_done)"

        # Execute tools
        tool_results = []
        for fc in function_calls:
            result = execute_tool(fc, workdir)
            tool_results.append({
                "functionResponse": {
                    "name": fc["name"],
                    "response": {"result": result}
                }
            })
            if fc["name"] == "task_done":
                return result

        contents.append({"role": "model", "parts": parts})
        contents.append({"role": "user", "parts": tool_results})

    return last_text or "(max turns)"

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Gemini 3.5 Flash sub-agent")
    ap.add_argument("prompt", help="Task description")
    ap.add_argument("--key", required=True, help="Google AI API key")
    ap.add_argument("--workdir", default=".", help="Working directory")
    args = ap.parse_args()
    print(run(args.prompt, args.key, args.workdir))
