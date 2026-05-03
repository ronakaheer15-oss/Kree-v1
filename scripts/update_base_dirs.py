#!/usr/bin/env python3
"""Replace all get_base_dir() / BASE_DIR boilerplate with kree._paths.PROJECT_ROOT.

Run from project root: python scripts/update_base_dirs.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pattern 1: function definition + BASE_DIR = get_base_dir() (most files)
# Matches the whole function block through the BASE_DIR assignment
PATTERN_FUNC = re.compile(
    r'def get_base_dir\b.*?'          # function def
    r'return Path\(__file__\).*?\n'   # return statement
    r'\n*'                             # optional blank lines
    r'BASE_DIR\s*=\s*get_base_dir\(\)',
    re.DOTALL
)

# Pattern 2: one-liner style A  (web_search.py)
PATTERN_A = re.compile(
    r'BASE_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\.parent'
    r'\s+if\s+not\s+getattr\(sys,\s*["\']frozen["\'],\s*False\)\s+'
    r'else\s+Path\(sys\.executable\)\.parent'
)

# Pattern 3: one-liner style B  (analytics.py)
PATTERN_B = re.compile(
    r'BASE_DIR\s*=\s*Path\(sys\.executable\)\.parent'
    r'\s+if\s+getattr\(sys,\s*["\']frozen["\'],\s*False\)\s+'
    r'else\s+Path\(__file__\)\.resolve\(\)\.parent\.parent'
)

REPLACEMENT = 'from kree._paths import PROJECT_ROOT\nBASE_DIR = PROJECT_ROOT'


def update_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return False
    updated = text
    updated = PATTERN_FUNC.sub(REPLACEMENT, updated)
    updated = PATTERN_A.sub(REPLACEMENT, updated)
    updated = PATTERN_B.sub(REPLACEMENT, updated)
    if updated != text:
        path.write_text(updated, encoding='utf-8')
        return True
    return False


changed = []
for py_file in (ROOT / 'kree').rglob('*.py'):
    if '__pycache__' in py_file.parts:
        continue
    if update_file(py_file):
        changed.append(py_file.relative_to(ROOT))

print(f"Updated {len(changed)} files:")
for f in sorted(changed):
    print(f"  {f}")
