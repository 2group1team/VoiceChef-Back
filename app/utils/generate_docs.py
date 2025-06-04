from fastapi import FastAPI
from pathlib import Path

def generate_markdown_from_app(app: FastAPI, file_path: str = "docs/api.md"):
    lines = ["# 📘 Voice Chef API Documentation\n"]
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        methods = ", ".join(route.methods - {"HEAD", "OPTIONS"})
        summary = getattr(route, "summary", "")
        path = route.path
        lines.append(f"## `{methods}` {path}")
        if summary:
            lines.append(f"**{summary}**\n")
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(file_path).write_text("\n".join(lines), encoding="utf-8")
