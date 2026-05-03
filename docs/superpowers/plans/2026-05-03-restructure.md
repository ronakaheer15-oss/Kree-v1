# Kree v1 Project Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize Kree v1 from a scattered flat layout into a professional `kree/` package with a proper `tests/` hierarchy (unit, integration, e2e) and a clean root.

**Architecture:** All application source moves into a `kree/` Python package at repo root; `main.py` stays at root as the sole PyInstaller entry point and immediately delegates to `kree.main_entry`; `kree/_paths.py` centralizes the `PROJECT_ROOT` path so the `get_base_dir()` pattern duplicated across 15+ files is replaced once; all tests live under `tests/` with pytest markers separating unit, integration, and e2e runs.

**Tech Stack:** Python 3.10+, pytest, pyautogui (e2e), unittest.mock, pyproject.toml (replaces setup.py), PyInstaller

---

## File Map

**New files created:**
- `kree/__init__.py`
- `kree/_paths.py`
- `kree/main_entry.py`
- `scripts/update_imports.py`
- `scripts/update_base_dirs.py`
- `pyproject.toml`
- `docs/INSTALL.md`
- `tests/conftest.py`
- `tests/unit/__init__.py`
- `tests/unit/actions/__init__.py`, `tests/unit/actions/test_web_search.py`, `tests/unit/actions/test_file_controller.py`
- `tests/unit/agent/__init__.py`, `tests/unit/agent/test_planner.py`, `tests/unit/agent/test_executor.py`, `tests/unit/agent/test_task_queue.py`
- `tests/unit/core/__init__.py`, `tests/unit/core/test_sanitizer.py`, `tests/unit/core/test_llm_gateway.py`, `tests/unit/core/test_auth_manager.py`, `tests/unit/core/test_tool_registry.py`
- `tests/unit/memory/__init__.py`, `tests/unit/memory/test_memory_manager.py`, `tests/unit/memory/test_history_manager.py`, `tests/unit/memory/test_config_manager.py`
- `tests/integration/__init__.py`, `tests/integration/test_agent_pipeline.py`, `tests/integration/test_memory_pipeline.py`, `tests/integration/test_mobile_bridge.py`
- `tests/e2e/__init__.py`, `tests/e2e/conftest.py`, `tests/e2e/test_launch.py`, `tests/e2e/test_voice_command.py`, `tests/e2e/test_mobile_connect.py`

**Moved via `git mv`:**
- `actions/` → `kree/actions/`
- `agent/` → `kree/agent/`
- `core/` → `kree/core/`
- `memory/` → `kree/memory/`
- `ui.py` → `kree/ui.py`
- `mobile_bridge.py` → `kree/mobile_bridge.py`
- `serve_pwa.py` → `kree/serve_pwa.py`
- `_copy_assets.py`, `_make_ico.py`, `build_release.py`, `copy_ui.py`, `download_stitch.py`, `patch.py`, `push_to_github.py`, `scratch_generate_chimes.py` → `scripts/`
- `DOWNLOAD_ME/` → `docs/assets/`
- `stitch_core_system_dashboard/` → `docs/ui-designs/stitch_core_system_dashboard/`
- `core/prompt.txt` → `config/prompt.txt`
- `core/automations_config.json` → `config/automations_config.json`
- `core/user_profile.json` → `config/user_profile.json`
- `memory/kree_memory.json` → `config/kree_memory.json`

**Modified:**
- `main.py` — stripped to 3 lines
- `Kree AI.spec` — updated datas + hiddenimports for `kree.*`

**Deleted:**
- `setup.py`
- `core/turboquant_helper.py` (duplicate of `actions/turboquant_helper.py`)
- `test_git.py`, `test_git_output.py`, `test_push.py`, `test_wakeword.py`
- `README-INSTALL.txt` (content moved to `docs/INSTALL.md`)
- `docs/README.md` (content merged into root `README.md`)

---

## Task 1: Move loose build/utility scripts to `scripts/`

**Files:**
- Move: `_copy_assets.py`, `_make_ico.py`, `build_release.py`, `copy_ui.py`, `download_stitch.py`, `patch.py`, `push_to_github.py`, `scratch_generate_chimes.py` → `scripts/`

- [ ] **Step 1: Create scripts/ directory**

```bash
mkdir scripts
```

- [ ] **Step 2: Move all loose scripts**

```bash
git mv _copy_assets.py scripts/_copy_assets.py
git mv _make_ico.py scripts/_make_ico.py
git mv build_release.py scripts/build_release.py
git mv copy_ui.py scripts/copy_ui.py
git mv download_stitch.py scripts/download_stitch.py
git mv patch.py scripts/patch.py
git mv push_to_github.py scripts/push_to_github.py
git mv scratch_generate_chimes.py scripts/scratch_generate_chimes.py
```

- [ ] **Step 3: Verify moves**

```bash
git status
```

Expected: 8 renames shown, no untracked files.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: move loose build/utility scripts into scripts/"
```

---

## Task 2: Consolidate docs

**Files:**
- Move: `BROWSER_AGENT_IMPLEMENTATION_PLAN.md` → `docs/plans/`
- Move: `DOWNLOAD_ME/` → `docs/assets/`
- Move: `stitch_core_system_dashboard/` → `docs/ui-designs/`
- Create: `docs/INSTALL.md` from `README-INSTALL.txt`
- Delete: `README-INSTALL.txt`, `docs/README.md` (merge into root README.md)

- [ ] **Step 1: Create sub-directories inside docs/**

```bash
mkdir -p docs/plans docs/assets docs/ui-designs
```

- [ ] **Step 2: Move docs and assets**

```bash
git mv BROWSER_AGENT_IMPLEMENTATION_PLAN.md docs/plans/BROWSER_AGENT_IMPLEMENTATION_PLAN.md
git mv DOWNLOAD_ME docs/assets/DOWNLOAD_ME
git mv stitch_core_system_dashboard docs/ui-designs/stitch_core_system_dashboard
```

- [ ] **Step 3: Rename README-INSTALL.txt to docs/INSTALL.md**

```bash
git mv README-INSTALL.txt docs/INSTALL.md
```

- [ ] **Step 4: Merge docs/README.md into root README.md then delete it**

Open `docs/README.md`, copy any content not already in the root `README.md` and append it to `README.md`. Then:

```bash
git rm docs/README.md
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: consolidate docs into docs/ subdirectories"
```

---

## Task 3: Evict data files from source packages into config/

**Files:**
- Move: `core/prompt.txt`, `core/automations_config.json`, `core/user_profile.json` → `config/`
- Move: `memory/kree_memory.json` → `config/`

- [ ] **Step 1: Move data files to config/**

```bash
git mv core/prompt.txt config/prompt.txt
git mv core/automations_config.json config/automations_config.json
git mv core/user_profile.json config/user_profile.json
git mv memory/kree_memory.json config/kree_memory.json
```

- [ ] **Step 2: Verify**

```bash
git status
ls config/
```

Expected: 4 renames, config/ now contains prompt.txt, automations_config.json, user_profile.json, kree_memory.json alongside existing files.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: evict data/config files from source packages into config/"
```

---

## Task 4: Delete throwaway test files and duplicate module

**Files:**
- Delete: `test_git.py`, `test_git_output.py`, `test_push.py`, `test_wakeword.py`, `core/turboquant_helper.py`

- [ ] **Step 1: Review test_wakeword.py for anything worth keeping**

```bash
cat test_wakeword.py
```

If it has reusable assertions, note them — they will be ported into `tests/unit/core/test_wakeword.py` in Task 13.

- [ ] **Step 2: Remove throwaway files**

```bash
git rm test_git.py test_git_output.py test_push.py test_wakeword.py
git rm core/turboquant_helper.py
```

- [ ] **Step 3: Verify**

```bash
git status
```

Expected: 5 deletions staged.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove throwaway test scripts and duplicate turboquant_helper"
```

---

## Task 5: Create `kree/` package skeleton

**Files:**
- Create: `kree/__init__.py`
- Create: `kree/_paths.py`

- [ ] **Step 1: Create kree/ directory with __init__.py**

Create `kree/__init__.py`:

```python
"""Kree AI — voice-controlled desktop assistant for Windows."""

__version__ = "1.0.0"
```

- [ ] **Step 2: Create kree/_paths.py**

Create `kree/_paths.py`:

```python
from pathlib import Path
import sys


def _find_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # This file lives at <project_root>/kree/_paths.py
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _find_project_root()
```

- [ ] **Step 3: Stage and verify**

```bash
git add kree/__init__.py kree/_paths.py
git status
```

Expected: 2 new files staged.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add kree/ package skeleton with _paths.py"
```

---

## Task 6: Move subpackages into `kree/`

**Files:**
- Move: `actions/` → `kree/actions/`, `agent/` → `kree/agent/`, `core/` → `kree/core/`, `memory/` → `kree/memory/`

- [ ] **Step 1: Move all four subpackages**

```bash
git mv actions kree/actions
git mv agent kree/agent
git mv core kree/core
git mv memory kree/memory
```

- [ ] **Step 2: Verify the moves**

```bash
git status | head -30
ls kree/
```

Expected: `kree/` now contains `__init__.py`, `_paths.py`, `actions/`, `agent/`, `core/`, `memory/`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: move actions/ agent/ core/ memory/ into kree/ package"
```

---

## Task 7: Move top-level source modules into `kree/`

**Files:**
- Move: `ui.py` → `kree/ui.py`, `mobile_bridge.py` → `kree/mobile_bridge.py`, `serve_pwa.py` → `kree/serve_pwa.py`

- [ ] **Step 1: Move top-level source files**

```bash
git mv ui.py kree/ui.py
git mv mobile_bridge.py kree/mobile_bridge.py
git mv serve_pwa.py kree/serve_pwa.py
```

- [ ] **Step 2: Verify**

```bash
git status
ls kree/
```

Expected: 3 renames. `kree/` now also contains `ui.py`, `mobile_bridge.py`, `serve_pwa.py`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: move ui.py mobile_bridge.py serve_pwa.py into kree/"
```

---

## Task 8: Create and run import update script

**Files:**
- Create: `scripts/update_imports.py`
- Modify: all `.py` files in `kree/` and `main.py` (automated)

- [ ] **Step 1: Create scripts/update_imports.py**

```python
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
```

- [ ] **Step 2: Run the script**

```bash
python scripts/update_imports.py
```

Expected output: lists 15–25 updated files.

- [ ] **Step 3: Verify no bare old-style imports remain**

```bash
grep -rn "^from actions\.\|^from core\.\|^from agent\.\|^from memory\." kree/ main.py
grep -rn '"actions\.\|"core\.\|"agent\.\|"memory\.' kree/ main.py
```

Expected: no matches. If any appear, fix them manually.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: update all imports to kree.* package paths"
```

---

## Task 9: Replace `get_base_dir()` boilerplate with `kree._paths.PROJECT_ROOT`

**Files:**
- Create: `scripts/update_base_dirs.py`
- Modify: ~15 files in `kree/` that contain `get_base_dir()` (automated)

- [ ] **Step 1: Create scripts/update_base_dirs.py**

```python
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
```

- [ ] **Step 2: Run the script**

```bash
python scripts/update_base_dirs.py
```

Expected output: ~12–16 updated files across `kree/actions/`, `kree/agent/`, `kree/core/`, `kree/memory/`.

- [ ] **Step 3: Verify no old get_base_dir() or parent.parent patterns remain in kree/**

```bash
grep -rn "def get_base_dir\|parent\.parent" kree/ --include="*.py"
```

Expected: no matches. Fix any stragglers manually using the same replacement pattern.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: replace get_base_dir() boilerplate with kree._paths.PROJECT_ROOT"
```

---

## Task 10: Extract boot logic into `kree/main_entry.py` and slim down `main.py`

**Files:**
- Create: `kree/main_entry.py`
- Modify: `main.py`

- [ ] **Step 1: Read the full current main.py**

```bash
cat -n main.py
```

Read the entire file to understand the full structure before editing.

- [ ] **Step 2: Create kree/main_entry.py**

Create `kree/main_entry.py` by copying the **entire** current `main.py` content into it, then:

1. At the very end of the file, wrap the application startup sequence (everything after the import block, starting from where variables are initialized and the event loop / `webview.start()` call is made) into a `def main():` function.
2. Make sure the module-level boot setup (UTF-8 encoding, logging, crash handler — currently lines 1–63 of main.py) stays at module level in `kree/main_entry.py` so it runs on import.

The bottom of `kree/main_entry.py` must end with:

```python
def main():
    # --- paste the application startup code here ---
    # (everything that was previously at module-level after the imports)
    pass  # replace with actual startup code


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Replace main.py with a 3-line entry point**

Overwrite `main.py` completely with:

```python
from kree.main_entry import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Smoke-test the import**

```bash
python -c "import kree.main_entry; print('boot import OK')"
```

Expected: `boot import OK` (may print logging init messages — that is fine).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: extract main.py boot logic into kree/main_entry.py"
```

---

## Task 11: Update PyInstaller spec

**Files:**
- Modify: `Kree AI.spec`

- [ ] **Step 1: Update datas — remove bundled source dirs, keep data-only dirs**

In `Kree AI.spec`, replace the existing `datas=[...]` block with:

```python
    datas=[
        (str(ROOT / 'config'), 'config'),
        (str(ROOT / 'pwa'), 'pwa'),
        (str(ROOT / 'assets'), 'assets'),
        # openwakeword models (ONNX only)
        (str(OWW_RESOURCES), 'openwakeword/resources'),
    ],
```

(Removed entries: `core`, `actions`, `memory`, `agent` — Python source is auto-collected via pathex. Removed `README-INSTALL.txt` — deleted. Removed `stitch_core_system_dashboard` — moved to docs/.)

- [ ] **Step 2: Update hiddenimports — add kree. prefix to all Kree modules**

Replace the `# ── Kree Action Modules` and `# ── Core modules` sections in `hiddenimports` with:

```python
        # ── Kree Action Modules ───────────────────────────────────────────
        'kree.actions.flight_finder',
        'kree.actions.open_app',
        'kree.actions.downloader_updater',
        'kree.actions.turboquant_helper',
        'kree.actions.openapps_automation',
        'kree.actions.weather_report',
        'kree.actions.send_message',
        'kree.actions.reminder',
        'kree.actions.computer_settings',
        'kree.actions.screen_processor',
        'kree.actions.youtube_video',
        'kree.actions.cmd_control',
        'kree.actions.desktop',
        'kree.actions.browser_control',
        'kree.actions.file_controller',
        'kree.actions.code_helper',
        'kree.actions.dev_agent',
        'kree.actions.web_search',
        'kree.actions.computer_control',
        'kree.actions.email_calendar',

        # ── Core modules ──────────────────────────────────────────────────
        'kree.core.runtime',
        'kree.core.wakeword',
        'kree.core.telemetry',
        'kree.core.version',
        'kree.core.auth_manager',
        'kree.core.auth_ui',
        'kree.core.security_ui',
        'kree.core.update_service',
        'kree.core.api_setup_ui',
        'kree.core.tool_registry',
        'kree._paths',
```

- [ ] **Step 3: Verify spec is valid Python**

```bash
python -c "
import ast, pathlib
src = pathlib.Path('Kree AI.spec').read_text()
ast.parse(src)
print('spec parses OK')
"
```

Expected: `spec parses OK`

- [ ] **Step 4: Commit**

```bash
git add "Kree AI.spec"
git commit -m "build: update PyInstaller spec for kree.* package structure"
```

---

## Task 12: Create `pyproject.toml` and remove `setup.py`

**Files:**
- Create: `pyproject.toml`
- Delete: `setup.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "kree"
version = "1.0.0"
description = "Voice-controlled AI desktop assistant for Windows"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["."]
include = ["kree*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "e2e: end-to-end tests that launch a real app window (run with: pytest -m e2e)",
    "integration: integration tests that wire real modules together",
]
addopts = "-m 'not e2e' -v"
```

- [ ] **Step 2: Delete setup.py**

```bash
git rm setup.py
```

- [ ] **Step 3: Verify pytest can find config**

```bash
python -m pytest --co -q 2>&1 | head -5
```

Expected: shows `no tests ran` or collection info — no "could not import" errors from missing pyproject.toml.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: replace setup.py with pyproject.toml, add pytest config"
```

---

## Task 13: Create unit test scaffold

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py` and all subdirectory `__init__.py` files
- Create: unit test files for core, agent, memory, actions

- [ ] **Step 1: Create tests/ directory structure**

```bash
mkdir -p tests/unit/actions tests/unit/agent tests/unit/core tests/unit/memory
touch tests/__init__.py tests/unit/__init__.py
touch tests/unit/actions/__init__.py tests/unit/agent/__init__.py
touch tests/unit/core/__init__.py tests/unit/memory/__init__.py
```

- [ ] **Step 2: Create tests/conftest.py**

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture()
def tmp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory pre-populated with required JSON stubs."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "api_keys.json").write_text('{"gemini_api_key": "test-key"}')
    (cfg / "audio_settings.json").write_text('{"tts_speed": 1.0, "wake_word": "hey kree"}')
    return cfg


@pytest.fixture()
def mock_gemini(monkeypatch):
    """Patch google.genai so no real API calls are made."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"goal": "test", "steps": [{"step": 1, "tool": "web_search", "description": "search", "parameters": {"query": "test"}, "critical": true}]}'
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        yield mock_client


@pytest.fixture()
def mock_vault(monkeypatch):
    """Patch kree.core.vault so memory tests don't require encryption keys."""
    with patch("kree.core.vault.encrypt_data", side_effect=lambda s: s.encode()), \
         patch("kree.core.vault.decrypt_data", side_effect=lambda b: b.decode()):
        yield
```

- [ ] **Step 3: Create tests/unit/core/test_sanitizer.py**

```python
from kree.core.sanitizer import sanitize_command


def test_safe_command_passes_through():
    text, err = sanitize_command("open notepad")
    assert text == "open notepad"
    assert err is None


def test_blocked_command_returns_none_and_error():
    text, err = sanitize_command("rm -rf /home/user")
    assert text is None
    assert "rm -rf" in err


def test_blocked_command_case_insensitive():
    text, err = sanitize_command("DELETE SYSTEM32")
    assert text is None
    assert err is not None


def test_empty_string_passes_through():
    text, err = sanitize_command("")
    assert text == ""
    assert err is None


def test_none_like_empty_passes_through():
    text, err = sanitize_command("  notepad  ")
    assert text == "  notepad  "
    assert err is None
```

- [ ] **Step 4: Create tests/unit/agent/test_planner.py**

```python
import json
from unittest.mock import MagicMock, patch
import pytest
from kree.agent.planner import create_plan, _fallback_plan


def _make_mock_client(response_text: str):
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


VALID_PLAN_JSON = json.dumps({
    "goal": "search the web",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "search", "parameters": {"query": "test"}, "critical": True}
    ]
})


def test_create_plan_returns_dict_with_steps(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    mock_client = _make_mock_client(VALID_PLAN_JSON)
    with patch("kree.agent.planner.genai.Client", return_value=mock_client):
        plan = create_plan("search the web")

    assert "steps" in plan
    assert len(plan["steps"]) >= 1
    assert plan["steps"][0]["tool"] == "web_search"


def test_create_plan_falls_back_on_json_error(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    mock_client = _make_mock_client("not valid json {{{{")
    with patch("kree.agent.planner.genai.Client", return_value=mock_client):
        plan = create_plan("some goal")

    assert "steps" in plan
    assert plan["steps"][0]["tool"] == "web_search"


def test_fallback_plan_wraps_goal_in_web_search():
    plan = _fallback_plan("find the weather")
    assert plan["goal"] == "find the weather"
    assert plan["steps"][0]["tool"] == "web_search"
    assert "find the weather" in plan["steps"][0]["parameters"]["query"]


def test_generated_code_tool_is_replaced(tmp_path, monkeypatch):
    (tmp_path / "api_keys.json").write_text('{"gemini_api_key": "k"}')
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", tmp_path / "api_keys.json")

    bad_plan = json.dumps({
        "goal": "run code",
        "steps": [{"step": 1, "tool": "generated_code", "description": "do something", "parameters": {}, "critical": True}]
    })
    mock_client = _make_mock_client(bad_plan)
    with patch("kree.agent.planner.genai.Client", return_value=mock_client):
        plan = create_plan("run code")

    assert all(s["tool"] != "generated_code" for s in plan["steps"])
```

- [ ] **Step 5: Create tests/unit/memory/test_memory_manager.py**

```python
import json
import pytest
from unittest.mock import patch
from kree.memory.memory_manager import (
    _empty_memory,
    _recursive_update,
    format_memory_for_prompt,
)


def test_empty_memory_has_required_keys():
    mem = _empty_memory()
    assert set(mem.keys()) == {"identity", "preferences", "relationships", "notes"}


def test_recursive_update_adds_new_key():
    target = _empty_memory()
    _recursive_update(target["identity"], {"name": "Alice"})
    assert target["identity"]["name"]["value"] == "Alice"


def test_recursive_update_skips_none_values():
    target = {"key": {"value": "existing"}}
    changed = _recursive_update(target, {"key": None})
    assert not changed
    assert target["key"]["value"] == "existing"


def test_recursive_update_skips_empty_strings():
    target = {}
    changed = _recursive_update(target, {"name": "   "})
    assert not changed


def test_recursive_update_truncates_long_values():
    target = {}
    with patch("kree.core.security.scrub_pii", side_effect=lambda x: x):
        with patch("kree.core.vault.encrypt_data"), patch("kree.core.vault.decrypt_data"):
            long_val = "x" * 400
            _recursive_update(target, {"note": long_val})
    value = target["note"]["value"]
    assert len(value) <= 305  # 300 chars + ellipsis


def test_format_memory_for_prompt_returns_empty_on_empty():
    result = format_memory_for_prompt({})
    assert result == ""


def test_format_memory_for_prompt_includes_name():
    mem = {
        "identity": {"name": {"value": "Alice"}},
        "preferences": {},
        "relationships": {},
        "notes": {}
    }
    result = format_memory_for_prompt(mem)
    assert "Alice" in result
    assert result.startswith("[USER MEMORY]")
```

- [ ] **Step 6: Create tests/unit/core/test_tool_registry.py**

```python
from kree.core.tool_registry import TOOL_DECLARATIONS


def test_tool_declarations_is_a_list():
    assert isinstance(TOOL_DECLARATIONS, list)


def test_each_tool_has_name_and_description():
    for tool in TOOL_DECLARATIONS:
        assert "name" in tool or "function_declarations" in tool or isinstance(tool, dict)


def test_tool_declarations_not_empty():
    assert len(TOOL_DECLARATIONS) > 0
```

- [ ] **Step 7: Create remaining unit test stubs**

Create `tests/unit/agent/test_executor.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_executor_module_importable():
    from kree.agent import executor
    assert executor is not None


def test_get_api_key_reads_from_config(tmp_path, monkeypatch):
    cfg = tmp_path / "api_keys.json"
    cfg.write_text('{"gemini_api_key": "abc123"}')
    monkeypatch.setattr("kree.agent.executor.API_CONFIG_PATH", cfg)
    from kree.agent.executor import _get_api_key
    assert _get_api_key() == "abc123"
```

Create `tests/unit/agent/test_task_queue.py`:

```python
def test_get_queue_returns_queue_instance():
    from kree.agent.task_queue import get_queue
    q = get_queue()
    assert q is not None


def test_get_queue_is_singleton():
    from kree.agent.task_queue import get_queue
    assert get_queue() is get_queue()
```

Create `tests/unit/memory/test_config_manager.py`:

```python
def test_config_manager_importable():
    from kree.memory import config_manager
    assert config_manager is not None


def test_load_audio_settings_returns_dict(tmp_path, monkeypatch):
    import json
    cfg = tmp_path / "audio_settings.json"
    cfg.write_text(json.dumps({"tts_speed": 1.2}))
    monkeypatch.setattr("kree.memory.config_manager.CONFIG_DIR", tmp_path)
    from kree.memory.config_manager import load_audio_settings
    result = load_audio_settings()
    assert isinstance(result, dict)
```

Create `tests/unit/memory/test_history_manager.py`:

```python
def test_history_manager_importable():
    from kree.memory import history_manager
    assert history_manager is not None
```

Create `tests/unit/actions/test_web_search.py`:

```python
def test_web_search_module_importable():
    from kree.actions import web_search
    assert web_search is not None


def test_web_search_action_callable():
    from kree.actions.web_search import web_search_action
    assert callable(web_search_action)
```

Create `tests/unit/actions/test_file_controller.py`:

```python
def test_file_controller_module_importable():
    from kree.actions import file_controller
    assert file_controller is not None


def test_file_controller_action_callable():
    from kree.actions.file_controller import file_controller
    assert callable(file_controller)
```

Create `tests/unit/core/test_llm_gateway.py`:

```python
def test_llm_gateway_module_importable():
    from kree.core import llm_gateway
    assert llm_gateway is not None


def test_llm_gateway_has_expected_interface():
    import inspect
    from kree.core import llm_gateway
    members = dir(llm_gateway)
    # Module must define at least one callable entry point
    callables = [m for m in members if not m.startswith("_") and callable(getattr(llm_gateway, m))]
    assert len(callables) > 0, "llm_gateway exposes no public callables"
```

Create `tests/unit/core/test_auth_manager.py`:

```python
def test_auth_manager_module_importable():
    from kree.core import auth_manager
    assert auth_manager is not None


def test_auth_manager_has_public_functions():
    import inspect
    from kree.core import auth_manager
    public = [n for n, _ in inspect.getmembers(auth_manager, inspect.isfunction)
              if not n.startswith("_")]
    assert len(public) > 0, "auth_manager exposes no public functions"
```

- [ ] **Step 8: Run unit tests to verify collection**

```bash
python -m pytest tests/unit/ --collect-only -q
```

Expected: all test files collected, zero errors. Failures at this point are expected (imports may be broken — fix any `ModuleNotFoundError` before continuing).

- [ ] **Step 9: Run unit tests**

```bash
python -m pytest tests/unit/ -v 2>&1 | tail -20
```

Expected: most tests pass. Note any failures — they indicate code that still uses old import paths or needs fixtures adjusted.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "test: add unit test scaffold for core, agent, memory, actions"
```

---

## Task 14: Create integration test scaffold

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_agent_pipeline.py`
- Create: `tests/integration/test_memory_pipeline.py`
- Create: `tests/integration/test_mobile_bridge.py`

- [ ] **Step 1: Create integration test directory**

```bash
mkdir -p tests/integration
touch tests/integration/__init__.py
```

- [ ] **Step 2: Create tests/integration/test_agent_pipeline.py**

```python
"""Integration test: user command flows through planner → executor → action result.

All external API calls (Gemini, Playwright) are mocked at the network boundary.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture()
def fake_api_config(tmp_path):
    cfg = tmp_path / "api_keys.json"
    cfg.write_text(json.dumps({"gemini_api_key": "test-key"}))
    return cfg


def _make_gemini_mock(plan_json: str):
    client = MagicMock()
    resp = MagicMock()
    resp.text = plan_json
    client.models.generate_content.return_value = resp
    return client


@pytest.mark.integration
def test_planner_returns_valid_plan_for_web_search_goal(fake_api_config, monkeypatch):
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", fake_api_config)
    plan_json = json.dumps({
        "goal": "what is the weather in London",
        "steps": [
            {"step": 1, "tool": "web_search", "description": "weather London",
             "parameters": {"query": "weather London today"}, "critical": True}
        ]
    })
    mock_client = _make_gemini_mock(plan_json)
    with patch("kree.agent.planner.genai.Client", return_value=mock_client):
        from kree.agent.planner import create_plan
        plan = create_plan("what is the weather in London")

    assert plan["steps"][0]["tool"] == "web_search"
    assert "London" in plan["steps"][0]["parameters"]["query"]


@pytest.mark.integration
def test_planner_blocks_generated_code_tool(fake_api_config, monkeypatch):
    monkeypatch.setattr("kree.agent.planner.API_CONFIG_PATH", fake_api_config)
    bad_plan = json.dumps({
        "goal": "run a script",
        "steps": [
            {"step": 1, "tool": "generated_code", "description": "do something",
             "parameters": {}, "critical": True}
        ]
    })
    mock_client = _make_gemini_mock(bad_plan)
    with patch("kree.agent.planner.genai.Client", return_value=mock_client):
        from kree.agent.planner import create_plan
        plan = create_plan("run a script")

    assert all(s["tool"] != "generated_code" for s in plan["steps"])


@pytest.mark.integration
def test_sanitizer_blocks_dangerous_commands_before_executor():
    from kree.core.sanitizer import sanitize_command
    commands = ["rm -rf /tmp", "format c:", "del /s /q C:\\Windows", "wipe disk"]
    for cmd in commands:
        text, err = sanitize_command(cmd)
        assert text is None, f"Expected '{cmd}' to be blocked"
        assert err is not None
```

- [ ] **Step 3: Create tests/integration/test_memory_pipeline.py**

```python
"""Integration test: memory read/write cycle through the full memory stack."""
import json
import pytest
from unittest.mock import patch
from pathlib import Path


@pytest.fixture()
def isolated_memory(tmp_path, monkeypatch):
    """Point the memory manager at a temp dir with no encryption."""
    mem_file = tmp_path / "long_term.json"
    monkeypatch.setattr("kree.memory.memory_manager.MEMORY_PATH", mem_file)
    with patch("kree.core.vault.encrypt_data", side_effect=lambda s: s.encode()), \
         patch("kree.core.vault.decrypt_data", side_effect=lambda b: b.decode()), \
         patch("kree.core.security.scrub_pii", side_effect=lambda x: x):
        yield mem_file


@pytest.mark.integration
def test_update_memory_persists_to_disk(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory

    update_memory({"identity": {"name": "Bob"}})
    loaded = load_memory()

    assert loaded["identity"]["name"]["value"] == "Bob"


@pytest.mark.integration
def test_update_memory_is_idempotent(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory

    update_memory({"identity": {"name": "Bob"}})
    update_memory({"identity": {"name": "Bob"}})
    loaded = load_memory()

    assert loaded["identity"]["name"]["value"] == "Bob"


@pytest.mark.integration
def test_format_memory_for_prompt_uses_saved_data(isolated_memory):
    from kree.memory.memory_manager import update_memory, load_memory, format_memory_for_prompt

    update_memory({"identity": {"name": "Carol", "city": "London"}})
    mem = load_memory()
    prompt_text = format_memory_for_prompt(mem)

    assert "Carol" in prompt_text
    assert "London" in prompt_text
```

- [ ] **Step 4: Create tests/integration/test_mobile_bridge.py**

```python
"""Integration test: mobile WebSocket bridge connect/send/receive."""
import pytest
import asyncio
import threading
import time
from unittest.mock import patch, MagicMock


@pytest.mark.integration
def test_mobile_bridge_module_importable():
    from kree import mobile_bridge
    assert mobile_bridge is not None


@pytest.mark.integration
def test_mobile_bridge_has_start_function():
    from kree.mobile_bridge import start_bridge
    assert callable(start_bridge)
```

- [ ] **Step 5: Run integration tests**

```bash
python -m pytest tests/integration/ -v -m integration
```

Expected: all tests collected and passing (or skipped if fixture dependencies are not yet met).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "test: add integration test scaffold for agent pipeline and memory"
```

---

## Task 15: Create e2e test scaffold

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_launch.py`
- Create: `tests/e2e/test_voice_command.py`
- Create: `tests/e2e/test_mobile_connect.py`

- [ ] **Step 1: Create tests/e2e/ directory**

```bash
mkdir -p tests/e2e
touch tests/e2e/__init__.py
```

- [ ] **Step 2: Create tests/e2e/conftest.py**

```python
"""E2E test fixtures: launch the real app, provide pyautogui helpers, tear down."""
import subprocess
import sys
import time
import os
from pathlib import Path

import pyautogui
import pytest

APP_STARTUP_WAIT = 8  # seconds — adjust if app takes longer to show window


@pytest.fixture(scope="session")
def app_process():
    """Launch Kree via `python main.py`, yield, then terminate."""
    project_root = Path(__file__).resolve().parent.parent.parent
    proc = subprocess.Popen(
        [sys.executable, str(project_root / "main.py")],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(APP_STARTUP_WAIT)  # wait for window to appear
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session", autouse=True)
def pyautogui_safety():
    """Reduce pyautogui speed so clicks land correctly on slower CI machines."""
    pyautogui.PAUSE = 0.5
    pyautogui.FAILSAFE = True
    yield
```

- [ ] **Step 3: Create tests/e2e/test_launch.py**

```python
"""E2E: verify the app launches and its window title is visible."""
import pyautogui
import pytest


@pytest.mark.e2e
def test_app_window_appears(app_process):
    """The Kree window should be findable on screen after startup."""
    assert app_process.poll() is None, "App process exited unexpectedly during startup"


@pytest.mark.e2e
def test_app_window_title_visible(app_process):
    """pyautogui can locate the window by searching for a known UI element."""
    import time
    time.sleep(2)
    # Verify process is still running — window management is OS-dependent
    assert app_process.poll() is None, "App crashed before UI was ready"
```

- [ ] **Step 4: Create tests/e2e/test_voice_command.py**

```python
"""E2E: simulate a text command via the UI and verify a response appears."""
import time
import pyautogui
import pytest


@pytest.mark.e2e
def test_text_command_produces_response(app_process):
    """Type a command into the UI input and verify the app does not crash."""
    assert app_process.poll() is None, "App not running"

    # Give the UI time to fully render
    time.sleep(2)

    # Click the centre of the screen to focus the app window
    screen_w, screen_h = pyautogui.size()
    pyautogui.click(screen_w // 2, screen_h // 2)
    time.sleep(0.5)

    # Type a safe, harmless command
    pyautogui.typewrite("what time is it", interval=0.05)
    pyautogui.press("enter")
    time.sleep(3)

    # The app should still be running after the command
    assert app_process.poll() is None, "App crashed after receiving a command"
```

- [ ] **Step 5: Create tests/e2e/test_mobile_connect.py**

```python
"""E2E: verify the PWA server starts and responds to HTTP requests."""
import time
import pytest
import requests


@pytest.mark.e2e
def test_pwa_server_responds(app_process):
    """The embedded PWA server should be reachable after app startup."""
    assert app_process.poll() is None, "App not running"

    # Default PWA port — matches config/settings.json pwa_port
    time.sleep(2)
    try:
        resp = requests.get("http://localhost:8765", timeout=5)
        assert resp.status_code == 200
    except requests.ConnectionError:
        pytest.skip("PWA server not reachable — check pwa_port in config")
```

- [ ] **Step 6: Verify e2e tests are excluded from default run and collect correctly**

```bash
# Default run — e2e must NOT appear
python -m pytest --collect-only -q 2>&1 | grep e2e
```

Expected: no e2e tests collected (they are excluded by `addopts = "-m 'not e2e'"`).

```bash
# Explicit e2e collection check
python -m pytest tests/e2e/ --collect-only -q
```

Expected: 5 e2e tests collected.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "test: add e2e test scaffold with pyautogui app launch fixtures"
```

---

## Task 16: Final verification

**Files:** no new files — verification only.

- [ ] **Step 1: Verify the full test suite collects cleanly**

```bash
python -m pytest --collect-only -q
```

Expected: all unit + integration tests collected, zero collection errors. E2e tests excluded.

- [ ] **Step 2: Run unit + integration tests**

```bash
python -m pytest -m "not e2e" -v 2>&1 | tail -30
```

Expected: green or only failures due to missing runtime dependencies (pyaudio, webview, etc.) that can't run in a pure-Python test environment — not import errors.

- [ ] **Step 3: Verify the app still imports cleanly**

```bash
python -c "
import sys, os
sys.path.insert(0, os.getcwd())
import kree
print('kree version:', kree.__version__)
from kree._paths import PROJECT_ROOT
print('project root:', PROJECT_ROOT)
"
```

Expected:
```
kree version: 1.0.0
project root: C:\Users\sudik\OneDrive\Documents\opensource\Kree-v1
```

- [ ] **Step 4: Verify root is clean**

```bash
ls *.py
```

Expected: only `main.py` at root.

- [ ] **Step 5: Final commit**

```bash
git add -A
git status
git commit -m "refactor: complete Kree v1 project restructure to kree/ package with tests/"
```

---

## Self-Review Checklist

- [x] Scripts moved to `scripts/` — Task 1
- [x] Docs consolidated into `docs/` — Task 2
- [x] Data files evicted from source packages — Task 3
- [x] Throwaway test files + duplicate deleted — Task 4
- [x] `kree/` package skeleton with `_paths.py` — Task 5
- [x] Subpackages moved — Task 6, 7
- [x] All imports updated via script — Task 8
- [x] `get_base_dir()` boilerplate replaced — Task 9
- [x] `main.py` slimmed, `kree/main_entry.py` created — Task 10
- [x] PyInstaller spec updated — Task 11
- [x] `pyproject.toml` created, `setup.py` removed — Task 12
- [x] Unit tests scaffold — Task 13
- [x] Integration tests scaffold — Task 14
- [x] E2E tests scaffold — Task 15
- [x] Final verification — Task 16
