TOOL_DECLARATIONS = [
    {
        "name": "trigger_macro",
        "description": (
            "Triggers a complex multi-app macro chain concurrently (e.g. 'work session', 'gaming session'). "
            "Use this precisely when the user asks to initiate a 'session' or complex workflow."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "chain_name": {
                    "type": "STRING",
                    "description": "The logical name of the chain (e.g. 'work session')"
                }
            },
            "required": ["chain_name"]
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "openapps_automation",
        "description": (
            "Controls OpenApps as an optional automation and multi-tasking engine. "
            "Use this for simulated app workflows, benchmark tasks, or parallel agent tasks. "
            "Do NOT replace native app opening with this tool. "
            "User phrase alias: 'Start Kree automation environment'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "launch_env | start_kree_automation_environment | run_task | run_parallel_tasks | run_preset | open_and_delegate | list_apps | list_agents | list_tasks | license_info | stop | status"
                },
                "app": {
                    "type": "STRING",
                    "description": "Optional OpenApps app name for launch_env (todo|calendar|maps|messenger|code_editor)"
                },
                "theme": {
                    "type": "STRING",
                    "description": "Optional UI theme for launch_env: dark | light"
                },
                "agent": {
                    "type": "STRING",
                    "description": "Agent config for run_task/run_parallel_tasks, e.g. GPT-5-1"
                },
                "task_name": {
                    "type": "STRING",
                    "description": "OpenApps benchmark task name for run_task"
                },
                "headless": {
                    "type": "BOOLEAN",
                    "description": "Set false to watch the run in a visible browser"
                },
                "timeout": {
                    "type": "INTEGER",
                    "description": "Timeout in seconds for run_task"
                },
                "extra": {
                    "type": "STRING",
                    "description": "Optional extra CLI overrides for run_parallel_tasks"
                },
                "preset": {
                    "type": "STRING",
                    "description": "Preset name for run_preset (e.g. codex_github_app_builder)"
                },
                "prompt": {
                    "type": "STRING",
                    "description": "Prompt for preset automation, e.g. app requirements for Codex"
                },
                "targets": {
                    "type": "STRING",
                    "description": "Apps/sites to open for open_and_delegate. Example: 'codex and github and vscode'"
                },
                "delegate_app": {
                    "type": "STRING",
                    "description": "Where to send instruction for open_and_delegate. Example: codex"
                },
                "fallback": {
                    "type": "STRING",
                    "description": "For missing native app: ask | download | browser"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "downloader_updater",
        "description": (
            "Downloads files and installs/updates software. "
            "Use this when user asks to download, install, update, upgrade, or check available updates."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "download_file | download | install_app | update_app | update_all | check_updates | auto"
                },
                "url": {
                    "type": "STRING",
                    "description": "URL for download_file"
                },
                "destination": {
                    "type": "STRING",
                    "description": "Optional destination path for downloads"
                },
                "target": {
                    "type": "STRING",
                    "description": "App name or winget ID for install_app/update_app/download"
                },
                "query": {
                    "type": "STRING",
                    "description": "Natural language request for auto action (e.g., 'download github' or 'update vscode')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "turboquant_helper",
        "description": (
            "Reports whether TurboQuant and HuggingFace-style tooling are available, "
            "prepares cache directories, and returns loader environment hints. Use this when the user asks about TurboQuant or future local model setup."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "status | prepare_cache | environment | export"
                },
                "model_id": {
                    "type": "STRING",
                    "description": "Optional HuggingFace model id such as meta-llama/Llama-3.1-8B-Instruct"
                },
                "cache_root": {
                    "type": "STRING",
                    "description": "Optional cache root path for TurboQuant/HF assets"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "session_trace",
        "description": (
            "Captures, summarizes, or exports the current Kree session trace. "
            "Use when the user asks to save a trace, export a session log, inspect recent events, or review what Kree did."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "summary | export | status"
                },
                "label": {
                    "type": "STRING",
                    "description": "Optional filename label for exports"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Optional maximum number of events to include"
                }
            },
            "required": ["action"]
        }
    },
{
    "name": "web_search",
    "description": "Searches the web for any information.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query":  {"type": "STRING", "description": "Search query"},
            "mode":   {"type": "STRING", "description": "search (default) or compare"},
            "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
            "aspect": {"type": "STRING", "description": "price | specs | reviews"}
        },
        "required": ["query"]
    }
},
    {
        "name": "weather_report",
        "description": "Gets real-time weather information for a city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
    "name": "youtube_video",
    "description": (
        "Controls YouTube. Use for: playing videos, summarizing a video's content, "
        "getting video info, or showing trending videos."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "play | summarize | get_info | trending (default: play)"
            },
            "query":  {"type": "STRING", "description": "Search query for play action"},
            "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
            "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
            "url":    {"type": "STRING", "description": "Video URL for get_info action"},
        },
        "required": []
    }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {
                    "type": "STRING",
                    "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"
                },
                "text": {
                    "type": "STRING",
                    "description": "The question or instruction about the captured image"
                }
            },
            "required": ["text"]
        }
    },
    {
    "name": "computer_settings",
    "description": (
        "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
        "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
        "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
        "ALSO use for repeated actions: 'refresh 10 times', 'reload page 5 times' → action: reload_n, value: 10. "
        "Use for ANY single computer control command — even if repeated N times. "
        "NEVER route simple computer commands to agent_task."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "The action to perform (if known). For repeated reload: 'reload_n'"},
            "description": {"type": "STRING", "description": "Natural language description of what to do"},
            "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, number of times, etc."}
        },
        "required": []
    }
},
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, finding cheapest products, "
            "booking flights, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": (
            "Manages files and folders. Use for: listing files, creating/deleting/moving/copying "
            "files, reading file contents, finding files by name or extension, checking disk usage, "
            "organizing the desktop, getting file info."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Runs CMD/terminal commands by understanding natural language. "
            "Use when user wants to: find large files, check disk space, list processes, "
            "get system info, navigate folders, check network, find files by name, "
            "or do ANYTHING in the command line they don't know how to do themselves."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task":    {"type": "STRING", "description": "Natural language description of what to do. Example: 'find the 10 largest files on C drive'"},
                "visible": {"type": "BOOLEAN", "description": "Open visible CMD window so user can see. Default: true"},
                "command": {"type": "STRING", "description": "Optional: exact command if already known"},
            },
            "required": ["task"]
        }
    },
    {
        "name": "desktop_control",
        "description": (
            "Controls the desktop. Use for: changing wallpaper, organizing desktop files, "
            "cleaning the desktop, listing desktop contents, or ANY other desktop-related task "
            "the user describes in natural language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language description of any desktop task"},
            },
            "required": ["action"]
        }
    },
    {
    "name": "code_helper",
    "description": (
        "Writes, edits, explains, runs, or self-builds code files. "
        "Use for ANY coding request: writing a script, fixing a file, "
        "editing existing code, running a file, or building and testing automatically."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
            "description": {"type": "STRING", "description": "What the code should do, or what change to make"},
            "language":    {"type": "STRING", "description": "Programming language (default: python)"},
            "output_path": {"type": "STRING", "description": "Where to save the file (full path or filename)"},
            "file_path":   {"type": "STRING", "description": "Path to existing file for edit / explain / run / build"},
            "code":        {"type": "STRING", "description": "Raw code string for explain"},
            "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
            "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
        },
        "required": ["action"]
    }
    },
    {
    "name": "dev_agent",
    "description": (
        "Builds complete multi-file projects from scratch. "
        "Plans structure, writes all files, installs dependencies, "
        "opens VSCode, runs the project, and fixes errors automatically. "
        "Use for any project larger than a single script."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description":  {"type": "STRING", "description": "What the project should do"},
            "language":     {"type": "STRING", "description": "Programming language (default: python)"},
            "project_name": {"type": "STRING", "description": "Optional project folder name"},
            "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
        },
        "required": ["description"]
    }
    },
    {
    "name": "agent_task",
    "description": (
        "Executes complex multi-step tasks that require MULTIPLE DIFFERENT tools. "
        "Always respond to the user in the language they spoke. "
        "Examples: 'research X and save to file', 'find files and organize them', "
        "'fill a form on a website', 'write and test code'. "
        "DO NOT use for simple computer commands like volume, refresh, close, scroll, "
        "minimize, screenshot, restart, shutdown — use computer_settings for those. "
        "DO NOT use if the task can be done with a single tool call."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "goal": {
                "type": "STRING",
                "description": "Complete description of what needs to be accomplished"
            },
            "priority": {
                "type": "STRING",
                "description": "low | normal | high (default: normal)"
            }
        },
        "required": ["goal"]
    }
},
    {
    "name": "computer_control",
    "description": (
        "Direct computer control: type text, click buttons, use keyboard shortcuts, "
        "scroll, move mouse, take screenshots, fill forms, find elements on screen. "
        "Use when the user wants to interact with any app on the computer directly. "
        "Can generate random data for forms or use user's real info from kree.memory."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
            "text":        {"type": "STRING", "description": "Text to type or paste"},
            "x":           {"type": "INTEGER", "description": "X coordinate for click/move"},
            "y":           {"type": "INTEGER", "description": "Y coordinate for click/move"},
            "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
            "key":         {"type": "STRING", "description": "Single key to press e.g. 'enter'"},
            "direction":   {"type": "STRING", "description": "Scroll direction: up | down | left | right"},
            "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
            "seconds":     {"type": "NUMBER", "description": "Seconds to wait"},
            "title":       {"type": "STRING", "description": "Window title for focus_window"},
            "description": {"type": "STRING", "description": "Element description for screen_find/screen_click"},
            "type":        {"type": "STRING", "description": "Data type for random_data: name|email|username|password|phone|birthday|address"},
            "field":       {"type": "STRING", "description": "Field for user_data: name|email|city"},
            "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            "path":        {"type": "STRING", "description": "Save path for screenshot"},
        },
        "required": ["action"]
    }
},

{
    "name": "flight_finder",
    "description": (
        "Searches for flights on Google Flights and speaks the best options. "
        "Use when user asks about flights, plane tickets, uçuş, bilet, etc."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "origin":       {"type": "STRING",  "description": "Departure city or airport code"},
            "destination":  {"type": "STRING",  "description": "Arrival city or airport code"},
            "date":         {"type": "STRING",  "description": "Departure date (any format)"},
            "return_date":  {"type": "STRING",  "description": "Return date for round trips"},
            "passengers":   {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
            "cabin":        {"type": "STRING",  "description": "economy | premium | business | first"},
            "save":         {"type": "BOOLEAN", "description": "Save results to Notepad"},
        },
        "required": ["origin", "destination", "date"]
    }
},
{
    "name": "smart_trigger",
    "description": (
        "Creates or removes autonomous background triggers for Kree. "
        "Use when user says 'remind me every 10 mins', 'tell me if CPU goes over 90%', "
        "'watch my downloads folder', etc. "
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":         {"type": "STRING", "description": "create | remove"},
            "name":           {"type": "STRING", "description": "A short distinct name for the trigger"},
            "trigger_type":   {"type": "STRING", "description": "system | time | file"},
            "metric":         {"type": "STRING", "description": "cpu | ram | time (e.g. 14:30) | dir_path"},
            "operator":       {"type": "STRING", "description": ">= | <= | =="},
            "value":          {"type": "STRING", "description": "Threshold value, e.g. '90' or '14:30'"},
            "action_to_take": {"type": "STRING", "description": "Natural language command Kree will execute when fired"},
            "silent":         {"type": "BOOLEAN", "description": "If true, Kree will execute silently unless it involves speaking (default: true)"},
            "id_to_remove":   {"type": "STRING", "description": "ID of trigger to remove (if action=remove)"}
        },
        "required": ["action"]
    }
},
{
    "name": "file_controller",
    "description": (
        "Advanced file & folder management automation. "
        "Use for bulk rename, organizing downloads, finding duplicates, etc."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "organize | rename_bulk | find_duplicates | move | delete"},
            "path":        {"type": "STRING", "description": "Target directory path (default: Downloads or Desktop if not specified)"},
            "pattern":     {"type": "STRING", "description": "Regex or glob pattern for renaming/finding"},
            "destination": {"type": "STRING", "description": "Destination directory"}
        },
        "required": ["action"]
    }
},
{
    "name": "browser_control",
    "description": (
        "Automates browser actions in the background. "
        "Use for filling forms, logging into sites, web scraping, or downloading files via URL."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "search | form_fill | scrape | navigate"},
            "url":    {"type": "STRING", "description": "Target website URL"},
            "query":  {"type": "STRING", "description": "Search query or specific data to find/scrape"},
            "form_data": {"type": "STRING", "description": "JSON string of data to fill into forms"}
        },
        "required": ["action"]
    }
},
{
    "name": "productivity_manager",
    "description": (
        "Manages emails and calendar events. "
        "Use when user wants to read inbox, draft emails, send emails, or schedule meetings. "
        "ALWAYS use action='draft_email' first if asked to compose or send an email, to allow user confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "read_inbox | draft_email | send_email | schedule_meeting"},
            "to": {"type": "STRING", "description": "Recipient name/address"},
            "subject": {"type": "STRING", "description": "Email subject"},
            "body": {"type": "STRING", "description": "Email content"},
            "title": {"type": "STRING", "description": "Meeting title"},
            "time": {"type": "STRING", "description": "Meeting time or date"}
        },
        "required": ["action"]
    }
}
]

