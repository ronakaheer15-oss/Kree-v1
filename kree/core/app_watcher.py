import asyncio
import psutil

from kree.core.live_prompts import app_trigger_prompt

async def watch_processes(live_session=None):
    """
    Background loop that polls new PIDs every 10s.
    If a known trigger app is opened by the user independently, Kree will organically respond.
    """
    print("[JARVIS] 👁️ App Watcher started")
    
    # Initialize baseline PIDs
    try:
        previous_pids = set(psutil.pids())
    except Exception:
        previous_pids = set()
    
    while True:
        await asyncio.sleep(10)
        if not live_session:
            continue
            
        try:
            current_pids = set(psutil.pids())
        except Exception:
            continue
            
        new_pids = current_pids - previous_pids
        previous_pids = current_pids
        
        if not new_pids:
            continue
            
        new_apps = set()
        for pid in new_pids:
            try:
                p = psutil.Process(pid)
                name = p.name()
                if name:
                    new_apps.add(name.lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                pass
        
        if not new_apps:
            continue
            
        try:
            import kree.core.automations as autos
            for app_name in new_apps:
                trigger_speech = autos.get_app_trigger(app_name)
                if trigger_speech:
                    # Inject response silently to live_session
                    print(f"[JARVIS] 👁️ App Detected: {app_name}. Firing trigger!")
                    try:
                        await live_session.send(
                            input=app_trigger_prompt(app_name, trigger_speech)
                        )
                    except Exception:
                        pass
        except Exception:
            pass
