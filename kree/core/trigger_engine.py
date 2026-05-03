import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from kree._paths import PROJECT_ROOT

try:
    import psutil
except ImportError:
    psutil = None

class TriggerEngine:
    def __init__(self, callback):
        """
        callback: function(action_data, bypass_voice=False)
        Trigger engine will call this when a rule fires.
        """
        self.callback = callback
        self.running = False
        self._thread = None

        # Path resolution
        self.memory_path = PROJECT_ROOT / "memory" / "smart_triggers.json"
        
        self.triggers = []
        self._load_triggers()
        
    def _load_triggers(self):
        if self.memory_path.exists():
            try:
                data = json.loads(self.memory_path.read_text(encoding="utf-8"))
                self.triggers = data.get("triggers", [])
            except Exception as e:
                print(f"[TriggerEngine] Failed to load triggers: {e}")
                self.triggers = []

    def _save_triggers(self):
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.memory_path.write_text(
                json.dumps({"triggers": self.triggers}, indent=4), 
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[TriggerEngine] Failed to save triggers: {e}")

    def add_trigger(self, trigger_data: dict):
        """
        Add a trigger.
        Format:
        {
            "id": "cpu_spike_1",
            "name": "CPU Alert",
            "type": "system",
            "condition": {"metric": "cpu", "operator": ">=", "value": 90},
            "action": {"type": "speak", "payload": "Warning, CPU is running hot."},
            "silent": False,
            "cooldown_seconds": 300,
            "last_fired": 0
        }
        """
        trigger_data["last_fired"] = 0
        self.triggers.append(trigger_data)
        self._save_triggers()
        print(f"[TriggerEngine] Added trigger: {trigger_data.get('name')}")
        return f"Trigger added: {trigger_data.get('name')}"

    def remove_trigger(self, trigger_id: str):
        original_len = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.get("id") != trigger_id]
        if len(self.triggers) < original_len:
            self._save_triggers()
            return f"Removed trigger: {trigger_id}"
        return "Trigger not found."

    def list_triggers(self):
        return self.triggers

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[TriggerEngine] Started background monitoring.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        while self.running:
            now = time.time()
            for trigger in self.triggers:
                try:
                    self._evaluate_trigger(trigger, now)
                except Exception as e:
                    print(f"[TriggerEngine] Evaluation error on {trigger.get('id')}: {e}")
            
            # evaluate every 5 seconds
            time.sleep(5)

    def _evaluate_trigger(self, trigger: dict, now: float):
        # 1. Cooldown check
        last_fired = trigger.get("last_fired", 0)
        cooldown = trigger.get("cooldown_seconds", 300)
        if (now - last_fired) < cooldown:
            return # Still on cooldown
            
        t_type = trigger.get("type")
        cond = trigger.get("condition", {})
        
        fired = False
        
        # 2. System Evaluate (CPU/RAM)
        if t_type == "system" and psutil:
            metric = cond.get("metric")
            value = float(cond.get("value", 0))
            op = cond.get("operator", ">=")
            
            current_val = -1
            if metric == "cpu":
                current_val = psutil.cpu_percent(interval=None)
            elif metric == "ram":
                current_val = psutil.virtual_memory().percent
                
            if current_val != -1:
                if op == ">=" and current_val >= value: fired = True
                elif op == "<=" and current_val <= value: fired = True

        # 3. Time Evaluate
        elif t_type == "time":
            # Very basic time match (e.g. HH:MM)
            target_time = cond.get("time") # format "14:30"
            if target_time:
                current_time = datetime.now().strftime("%H:%M")
                if current_time == target_time:
                    fired = True

        # 4. Execute Action
        if fired:
            # Update cooldown immediately to prevent double fires
            trigger["last_fired"] = now
            self._save_triggers()
            
            action = trigger.get("action", {})
            silent = trigger.get("silent", False)
            
            print(f"[TriggerEngine] ⚡ Trigger FIRED: {trigger.get('name')}")
            
            if self.callback:
                self.callback(action, bypass_voice=silent)
