import re

with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix serve_pwa issue
text = text.replace('from serve_pwa import', 'from scripts.serve_pwa import')

# 2. Add local tool imports to the executing block
# A cleaner way is to simply regex replace the global tool function calls inside the `elif` blocks 
# to import the function dynamically right before using it.
# Wait, replacing 20 blocks is complex. Let's just comment out the block at the top, and we will place the whole block of imports at the TOP of the tool executing method (`async def handle_tool_call` or whatever).
# Let's find `def on_user_text` or where `elif name ==` is. It's actually inside `class JarvisLive` or the function returning `types.FunctionResponse`.
# Searching for `elif name == "flight_finder":` and we'll insert the imports above it. But easier: just put ALL the imports inside a lazy loading function and grab from `globals()`!

# Actual solution to avoid changing 20 calls:
# Create a dummy class or dict that lazy loads the imports when accessed!

lazy_loader = """
class LazyToolLoader:
    def __getattr__(self, name):
        import importlib
        module_map = {
            "flight_finder": ("actions.flight_finder", "flight_finder"),
            "open_app": ("actions.open_app", "open_app"),
            "downloader_updater": ("actions.downloader_updater", "downloader_updater"),
            "turboquant_helper": ("actions.turboquant_helper", "turboquant_helper"),
            "openapps_automation": ("actions.openapps_automation", "openapps_automation"),
            "weather_action": ("actions.weather_report", "weather_action"),
            "send_message": ("actions.send_message", "send_message"),
            "reminder": ("actions.reminder", "reminder"),
            "computer_settings": ("actions.computer_settings", "computer_settings"),
            "screen_process": ("actions.screen_processor", "screen_process"),
            "youtube_video": ("actions.youtube_video", "youtube_video"),
            "cmd_control": ("actions.cmd_control", "cmd_control"),
            "desktop_control": ("actions.desktop_control", "desktop_control"),
            "browser_control": ("actions.browser_control", "browser_control"),
            "file_controller": ("actions.file_controller", "file_controller"),
            "code_helper": ("actions.code_helper", "code_helper"),
            "dev_agent": ("actions.dev_agent", "dev_agent"),
            "web_search_action": ("actions.web_search", "web_search_action"),
            "computer_control": ("actions.computer_control", "computer_control"),
            "productivity_manager": ("actions.email_calendar", "productivity_manager")
        }
        if name in module_map:
            mod_name, func_name = module_map[name]
            mod = importlib.import_module(mod_name)
            return getattr(mod, func_name)
        raise AttributeError(f"Tool {name} not found")

lazy_tools = LazyToolLoader()
flight_finder = lazy_tools.flight_finder
open_app = lazy_tools.open_app
downloader_updater = lazy_tools.downloader_updater
turboquant_helper = lazy_tools.turboquant_helper
openapps_automation = lazy_tools.openapps_automation
weather_action = lazy_tools.weather_action
send_message = lazy_tools.send_message
reminder = lazy_tools.reminder
computer_settings = lazy_tools.computer_settings
screen_process = lazy_tools.screen_process
youtube_video = lazy_tools.youtube_video
cmd_control = lazy_tools.cmd_control
desktop_control = lazy_tools.desktop_control
browser_control = lazy_tools.browser_control
file_controller = lazy_tools.file_controller
code_helper = lazy_tools.code_helper
dev_agent = lazy_tools.dev_agent
web_search_action = lazy_tools.web_search_action
computer_control = lazy_tools.computer_control
productivity_manager = lazy_tools.productivity_manager
"""

import_block_start = 'from actions.flight_finder import flight_finder'
import_block_end = 'from actions.email_calendar   import productivity_manager  # type: ignore[import]'
if import_block_start in text and import_block_end in text:
    import_text = text[text.find(import_block_start) : text.find(import_block_end) + len(import_block_end)]
    text = text.replace(import_text, lazy_loader)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch successful!")
