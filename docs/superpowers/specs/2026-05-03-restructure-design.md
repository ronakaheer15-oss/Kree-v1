# Kree v1 — Project Restructure Design

**Date:** 2026-05-03
**Status:** Approved
**Scope:** Folder structure overhaul + full test suite scaffolding

---

## Context

Kree is a Windows-only voice-controlled AI desktop assistant distributed exclusively as a PyInstaller `.exe`. The current repo has source code, build scripts, data files, and test files all scattered at the root level with no clear package boundary. The goal is a clean, professional structure with a proper `kree/` package, a `tests/` hierarchy covering unit, integration, and e2e layers, and a tidy root.

---

## Decisions

- **No `src/` layout** — unnecessary complexity for a pure `.exe` distribution; PyInstaller works cleanest with a flat package at root.
- **Test framework:** pytest
- **E2E driver:** pyautogui (real window opened via subprocess)
- **External API mocking:** `unittest.mock` at unit + integration layers; real app launched for e2e

---

## Root Structure

```
Kree-v1/
├── kree/                  # all application source code
├── tests/                 # all tests
├── scripts/               # build & utility scripts (moved from root)
├── assets/                # icons, sounds, fonts (unchanged)
├── config/                # runtime config + data files (json/txt evicted from src)
├── pwa/                   # mobile companion web app (unchanged)
├── installer/             # Inno Setup scripts (unchanged)
├── docs/                  # documentation (consolidated)
├── main.py                # PyInstaller entry point (stays at root)
├── pyproject.toml         # replaces setup.py; defines project metadata + pytest config
├── requirements.txt       # unchanged
├── build_kree.bat         # unchanged
├── Kree AI.spec           # paths updated only
├── version_info.txt       # stays at root (PyInstaller needs it)
└── README.md
```

### Scripts moved to `scripts/`
`_copy_assets.py`, `_make_ico.py`, `build_release.py`, `copy_ui.py`, `download_stitch.py`, `patch.py`, `push_to_github.py`, `scratch_generate_chimes.py`

### Existing root test files
`test_git.py`, `test_git_output.py`, `test_push.py`, `test_wakeword.py` — these are throwaway scripts, not structured tests. They will be deleted. `test_wakeword.py` content will be reviewed and ported into `tests/unit/core/test_wakeword.py` if it contains anything reusable.

### Data files evicted from source packages → `config/`
`core/prompt.txt`, `core/automations_config.json`, `core/user_profile.json`, `memory/kree_memory.json`

### Docs consolidated
- `README-INSTALL.txt` → `docs/INSTALL.md`
- `BROWSER_AGENT_IMPLEMENTATION_PLAN.md` → `docs/plans/`
- `stitch_core_system_dashboard/` → `docs/ui-designs/`
- `DOWNLOAD_ME/` images → `docs/assets/`
- `docs/README.md` merged into root `README.md`

---

## `kree/` Package

```
kree/
├── __init__.py
├── main_entry.py          # boot logic extracted from main.py
├── ui.py
├── mobile_bridge.py
├── serve_pwa.py
├── actions/               # all tool modules (browser, files, code, etc.)
├── agent/                 # planner, executor, error_handler, task_queue
├── core/                  # auth, security, updates, telemetry, runtime, etc.
│   └── helpers/           # cpu/ram optimizer, onnx runner, mmap loader
└── memory/                # memory_manager, history_manager, config_manager
```

All imports updated from `from core.x import ...` → `from kree.core.x import ...` etc.

**Duplicate resolved:** `turboquant_helper.py` exists in both `actions/` and `core/`. The `core/` copy will be deleted; `actions/turboquant_helper.py` is the canonical one.

---

## `tests/` Structure

```
tests/
├── conftest.py                    # shared fixtures, mock factories
├── unit/
│   ├── actions/                   # one test file per action module
│   ├── agent/                     # test_planner, test_executor, test_task_queue
│   ├── core/                      # test_sanitizer, test_llm_gateway, test_tool_registry, test_auth_manager
│   └── memory/                    # test_memory_manager, test_history_manager, test_config_manager
├── integration/
│   ├── test_agent_pipeline.py     # command → planner → executor → action (mocked network)
│   ├── test_memory_pipeline.py    # full read/write cycle
│   └── test_mobile_bridge.py     # WebSocket connect/send/receive
└── e2e/
    ├── conftest.py                # launches app via subprocess, pyautogui setup/teardown
    ├── test_launch.py             # app opens, dashboard renders
    ├── test_voice_command.py      # simulates input → response visible in UI
    └── test_mobile_connect.py    # QR code appears, PWA server responds
```

### Test rules
- **Unit:** mock all external APIs (Gemini, Playwright, audio, filesystem where needed)
- **Integration:** real module chains, mocked at network boundary
- **E2E:** real `python main.py` subprocess + pyautogui; tests are marked `@pytest.mark.e2e` and excluded from default `pytest` run (run explicitly with `pytest -m e2e`)

---

## `pyproject.toml` responsibilities
- Project metadata (name, version, dependencies)
- pytest configuration: `testpaths = ["tests"]`, markers for `e2e` and `integration`
- Replaces `setup.py`

---

## PyInstaller `.spec` changes
- Update all `pathex`, `datas`, and `hiddenimports` entries that reference old module paths to use `kree.*` paths
- Entry script remains `main.py` at root

---

## Out of scope
- Further splitting `core/` into sub-domains (auth/, security/, etc.) — deferred to a later refactor
- CI/CD pipeline setup
- Filling out test implementations beyond scaffolding
