import os
import re

PATTERNS = {
    "TODO_FIXME": re.compile(r'(TODO|FIXME)'),
    "MOCK": re.compile(r'mock_'),
    "CONSOLE_LOG": re.compile(r'console\.log'),
    "DEMO": re.compile(r'DEMO_')
}

IGNORE_DIRS = {'node_modules', 'venv', '.git', 'dist', '__pycache__', '.pytest_cache'}

def search_dir(path):
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            filepath = os.path.join(root, file)
            if filepath.endswith(('.jpg', '.png', '.gif', '.pyc', '.ico', '.svg', '.jsonl', '.md', '.pyo')):
                continue
            # Also ignore the search_audit.py itself
            if 'search_audit.py' in filepath:
                continue
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        for name, pattern in PATTERNS.items():
                            if pattern.search(line):
                                print(f"{name} | {filepath}:{i+1} | {line.strip()}")
            except Exception:
                pass

if __name__ == "__main__":
    search_dir("c:/Users/T.BHUVAN/OneDrive/Documents/Desktop/VIBE2SHIP")
