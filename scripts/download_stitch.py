import os
import urllib.request
from pathlib import Path

BASE_DIR = Path(r"e:\Mark-XXX-main\Mark-XXX-main")
_STITCH = BASE_DIR.parent / "stitch_core_system_dashboard" / "stitch_core_system_dashboard"

files = {
    "core_system_dashboard_1": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ6Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpZCiVodG1sXzE2NjRjODEzMTZkZjRjYmFiMGMyZjAwMDMwY2ZhYjMxEgsSBxDu2f3JnQwYAZIBIgoKcHJvamVjdF9pZBIUQhIyNjAwMDUxNTE4NjIxMjU2OTc&filename=&opi=89354086",
    "core_system_dashboard_2": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ6Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpZCiVodG1sX2ViOTU5OTc1NjY3MjQyNTk4MGE3NDdmZDE2NWQ5ZGI0EgsSBxDu2f3JnQwYAZIBIgoKcHJvamVjdF9pZBIUQhIyNjAwMDUxNTE4NjIxMjU2OTc&filename=&opi=89354086",
    "minimized_control_widget": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ6Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpZCiVodG1sXzFiZjc1ZGRkMGQxMDQ3M2I4N2NjNGQ4YjNkZjk1ZDdiEgsSBxDu2f3JnQwYAZIBIgoKcHJvamVjdF9pZBIUQhIyNjAwMDUxNTE4NjIxMjU2OTc&filename=&opi=89354086"
}

for folder_name, url in files.items():
    folder_path = _STITCH / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    file_path = folder_path / "code.html"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with open(file_path, "wb") as f:
            f.write(response.read())
    print(f"Downloaded {folder_name}/code.html")
