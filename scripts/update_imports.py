#!/usr/bin/env python3
"""Update all module imports from old flat paths to kree.* package paths.

Run from project root: python scripts/update_imports.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (pattern, replacement) pairs — order matters, more specific first
REPLACEMENTS = [
    # from X.y import  →  from kree.X.y import
    (r'\bfrom actions\.', 'from kree.actions.'),
    (r'\bfrom core\.', 'from kree.core.'),
    (r'\bfrom agent\.', 'from kree.agent.'),
    (r'\bfrom memory\.', 'from kree.memory.'),
    # from ui import / from mobile_bridge import / from serve_pwa import
    (r'\bfrom ui import\b', 'from kree.ui import'),
    (r'\bfrom mobile_bridge import\b', 'from kree.mobile_bridge import'),
    (r'\bfrom serve_pwa import\b', 'from kree.serve_pwa import'),
    # import X.y  →  import kree.X.y
    (r'\bimport actions\.', 'import kree.actions.'),
    (r'\bimport core\.', 'import kree.core.'),
    (r'\bimport agent\.', 'import kree.agent.'),
    (r'\bimport memory\.', 'import kree.memory.'),
    # lazy string-based imports inside LazyToolLoader and similar
    (r'"actions\.', '"kree.actions.'),
    (r'"core\.', '"kree.core.'),
    (r'"agent\.', '"kree.agent.'),
    (r'"memory\.', '"kree.memory.'),
]


def update_file(path: Path) -> bool:
    try:
        original = path.read_text(encoding='utf-8')
    except Exception:
        return False
    updated = original
    for pattern, replacement in REPLACEMENTS:
        updated = re.sub(pattern, replacement, updated)
    if updated != original:
        path.write_text(updated, encoding='utf-8')
        return True
    return False


targets = list((ROOT / 'kree').rglob('*.py')) + [ROOT / 'main.py']
changed = []
for py_file in targets:
    if '__pycache__' in py_file.parts:
        continue
    if update_file(py_file):
        changed.append(py_file.relative_to(ROOT))

print(f"Updated {len(changed)} files:")
for f in sorted(changed):
    print(f"  {f}")
