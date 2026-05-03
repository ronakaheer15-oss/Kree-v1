import asyncio
import concurrent.futures

# Max 8 concurrent tasks to prevent GUI lockup
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

async def run_parallel_tasks(tasks, live_session=None):
    """
    Executes multiple automation functions concurrently in a background threadpool.
    As each task finishes, it injects the success narration dynamically into the live session.
    """
    loop = asyncio.get_event_loop()
    
    async def worker(task_dict):
        action = task_dict.get("action")
        narration = task_dict.get("narration")
        target = task_dict.get("target") or task_dict.get("url") or task_dict.get("setting")
        
        # Execute the underlying command in the thread pool
        def execute():
            try:
                if action == "open_app":
                    import kree.actions.open_app as o_app # type: ignore
                    return o_app.open_app(target)
                elif action == "browser_control":
                    import kree.actions.browser_control as bc # type: ignore
                    return bc.browser_action(url=target, action_type="navigate")
                elif action == "computer_settings":
                    import kree.actions.computer_settings as cs # type: ignore
                    return cs.computer_settings(target)
                return "Unknown action."
            except Exception as e:
                return str(e)
                
        result = await loop.run_in_executor(_executor, execute)
        
        # Push real-time narriation directly to voice
        if live_session and narration:
            try:
                await live_session.send(
                    input=f"[SYSTEM OVERRIDE] Task {target} just completed successfully. Say the following narration out loud naturally: '{narration}'"
                )
            except Exception:
                pass
                
        return result

    futures = [asyncio.create_task(worker(t)) for t in tasks]
    await asyncio.gather(*futures)

