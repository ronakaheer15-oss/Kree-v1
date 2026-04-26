# Contributing to Kree AI

We welcome contributions! Please follow these guidelines to keep the codebase clean and stable.

## Branching Strategy

- **`main`**: The stable production branch. Code here must be tested and ready for release.
- **`dev`**: The active integration branch. New features and fixes are merged here first.
- **`feature/xyz`**: For developing new features. Branch off `dev`.
- **`fix/xyz`**: For bug fixes. Branch off `dev`.

## Development Workflow

1. **Branch**: Create a new branch from `dev`.
2. **Commit**: Keep commits atomic and descriptive.
3. **PR**: Open a Pull Request back to `dev`.
4. **Merge**: After review and testing, `dev` is merged into `main` for release.

## Code Standards

- **Naming**: Use `snake_case` for variables/functions and `PascalCase` for classes.
- **Docstrings**: Every module and public function must have a descriptive docstring.
- **Error Handling**: Use `try-except` blocks around sensitive operations (I/O, API calls). Log errors using the standard `logging` module; do not just `print`.
- **Type Hints**: Use Python type hints (`arg: str -> None`) to improve readability and tooling support.
- **UTF-8**: Always force UTF-8 for file and stdout operations to support multi-language characters and emojis.

## How to Add a New Module

To add a new capability (e.g., `actions/my_new_tool.py`):

1. **Implement Logic**:
   ```python
   def my_new_tool(parameters: dict, **kwargs):
       # Your logic here
       return "Success message"
   ```
2. **Register Tool**: Add the tool definition to `core/tool_registry.py`.
3. **Link to Master**: Add the module mapping to `LazyToolLoader` in `main.py`.
4. **Test**: Run Kree and verify the tool triggers correctly via voice/text.

## Communication Rhythm

- **Weekly Sync**: Every Tuesday for progress updates and roadmap alignment.
- **Daily Comms**: Use the **WhatsApp** developer group for quick questions.
- **Issue Tracking**: Use **GitHub Issues** for bugs and feature requests.
