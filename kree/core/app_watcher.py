import asyncio
import time
import psutil

async def watch_processes(live_session=None):
    """
    Background loop that polls psutil.process_iter() every 5-10s.
    If a known trigger app is opened by the user independently, Kree will organically respond.
    """
    print("[JARVIS] 👁️ App Watcher started")
    
    previous_apps = set()
    
    # Do an initial poll to populate baseline so we don't trigger everything on boot
    try:
        for p in psutil.process_iter(['name']):
            try:
                name = p.info.get('name')
                if name:
                    previous_apps.add(name.lower())
            except Exception: pass
    except Exception:
        pass

    while True:
        await asyncio.sleep(8)
        if not live_session:
            continue
            
        current_apps = set()
        try:
            for p in psutil.process_iter(['name']):
                try:
                    name = p.info.get('name')
                    if name:
                        current_apps.add(name.lower())
                except Exception: pass
        except Exception:
            pass
            
        new_apps = current_apps - previous_apps
        previous_apps = current_apps
        
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
                            input=f"[SYSTEM OVERRIDE] The user just manually opened {app_name}. Say the following line naturally out loud: '{trigger_speech}'"
                        )
                    except Exception as e:
                        pass
        except Exception as e:
            pass
