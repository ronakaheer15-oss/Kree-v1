import json
import math
from datetime import datetime, timezone
from threading import Lock

from kree.core.runtime import APP_DATA_DIR
MEMORY_PATH = APP_DATA_DIR / "memory" / "long_term.json"
_lock       = Lock()

MAX_VALUE_LENGTH = 300  

def _empty_memory() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "relationships": {},
        "notes":         {},
        "schema_version": 2
    }

def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _empty_memory()

    with _lock:
        try:
            import kree.core.vault as vault # type: ignore[import]
            raw_data = MEMORY_PATH.read_bytes()
            decrypted_json = vault.decrypt_data(raw_data)
            data = json.loads(decrypted_json)
            if isinstance(data, dict):
                if "schema_version" not in data:
                    data["schema_version"] = 2
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()


def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        import kree.core.vault as vault # type: ignore[import]
        json_str = json.dumps(memory, indent=2, ensure_ascii=False)
        encrypted_bytes = vault.encrypt_data(json_str)
        MEMORY_PATH.write_bytes(encrypted_bytes)

def _truncate_value(val: str) -> str:
    if not isinstance(val, str):
        val = str(val)
    
    # Aegis Security: Scrub PII before saving to disk
    import kree.core.security as security # type: ignore[import]
    val = security.scrub_pii(val)

    if len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val

def _calculate_score(entry: dict) -> float:
    if not isinstance(entry, dict):
        return 0.0
    
    importance = entry.get("importance", 5)
    access_count = entry.get("access_count", 0)
    
    # logarithmic access scoring
    log_access = math.log(access_count + 1)
    
    updated_at_str = entry.get("updated_at")
    recency_bonus = 0.0
    if updated_at_str:
        try:
            updated_dt = datetime.fromisoformat(updated_at_str)
            now_dt = datetime.now()
            if updated_dt.tzinfo is not None:
                now_dt = datetime.now(timezone.utc)
            delta = now_dt - updated_dt
            hours = delta.total_seconds() / 3600.0
            if hours < 0:
                hours = 0
            
            # Continuous decay: decays to 15 after 1 day, 3.75 after a week
            recency_bonus = 30.0 / (1.0 + hours / 24.0)
        except Exception:
            pass
            
    return (importance * 3) + log_access + recency_bonus

def _recursive_update(target: dict, updates: dict) -> bool:
    changed = False
    now_str = datetime.now().isoformat()

    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue

        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            # Determine incoming value and custom fields
            val_str = ""
            incoming_importance = None
            incoming_source = None
            if isinstance(value, dict):
                val_str = str(value.get("value", ""))
                incoming_importance = value.get("importance")
                incoming_source = value.get("source")
            else:
                val_str = str(value)

            new_value = _truncate_value(val_str)
            
            # Normalize existing entry if it's a string or legacy dict
            existing = target.get(key)
            if not isinstance(existing, dict):
                if existing:
                    existing = {"value": str(existing)}
                else:
                    existing = {}
            
            created_at = existing.get("created_at") or now_str
            importance = incoming_importance if incoming_importance is not None else existing.get("importance", 5)
            access_count = existing.get("access_count", 0)
            last_accessed = existing.get("last_accessed") or ""
            source = incoming_source or existing.get("source") or "conversation"
            
            new_entry = {
                "value": new_value,
                "created_at": created_at,
                "updated_at": now_str,
                "importance": importance,
                "access_count": access_count,
                "last_accessed": last_accessed,
                "source": source
            }

            if (key not in target or 
                existing.get("value") != new_value or 
                existing.get("importance") != importance or
                existing.get("source") != source):
                target[key] = new_entry
                changed = True

    return changed


def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()

    memory = load_memory()

    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print(f"[Memory] 💾 Saved: {list(memory_update.keys())}")

    return memory


def record_memory_access(injected_keys: list[tuple[str, str]]) -> None:
    if not injected_keys:
        return
        
    memory = load_memory()
    changed = False
    now_str = datetime.now().isoformat()
    
    for category, key in injected_keys:
        cat_dict = memory.get(category, {})
        if key in cat_dict and isinstance(cat_dict[key], dict):
            cat_dict[key]["access_count"] = cat_dict[key].get("access_count", 0) + 1
            cat_dict[key]["last_accessed"] = now_str
            changed = True
            print(f"[Memory] 📈 Incremented access for {category}/{key} (access_count: {cat_dict[key]['access_count']})")
            
    if changed:
        save_memory(memory)


def format_memory_for_prompt(memory: dict | None) -> tuple[str, list[tuple[str, str]]]:
    if not memory:
        return "", []

    lines = []
    injected_keys = []
    now_str = datetime.now().isoformat()
    memory_changed = False

    def get_val(item):
        if isinstance(item, dict):
            return item.get("value")
        return item

    # Identity (always injected entirely, normalize strings to dict if found)
    identity = memory.get("identity", {})
    name = get_val(identity.get("name"))
    age  = get_val(identity.get("age"))
    bday = get_val(identity.get("birthday"))
    city = get_val(identity.get("city"))
    
    if name: lines.append(f"Name: {name}")
    if age:  lines.append(f"Age: {age}")
    if bday: lines.append(f"Birthday: {bday}")
    if city: lines.append(f"City: {city}")

    # Helper to sort and pick top 5 for dynamic categories
    def get_top_entries(category: str) -> list[tuple[str, dict]]:
        nonlocal memory_changed
        category_dict = memory.get(category, {})
        scored = []
        for key, entry in category_dict.items():
            if not isinstance(entry, dict):
                normalized = {
                    "value": str(entry),
                    "created_at": now_str,
                    "updated_at": now_str,
                    "importance": 5,
                    "access_count": 0,
                    "last_accessed": "",
                    "source": "conversation"
                }
                category_dict[key] = normalized
                memory_changed = True
                entry = normalized
            
            score = _calculate_score(entry)
            scored.append((score, key, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(item[1], item[2]) for item in scored[:5]]

    # Preferences
    top_prefs = get_top_entries("preferences")
    for key, entry in top_prefs:
        val = entry.get("value")
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")
            injected_keys.append(("preferences", key))

    # Relationships
    top_rels = get_top_entries("relationships")
    for key, entry in top_rels:
        val = entry.get("value")
        if val:
            lines.append(f"{key.title()}: {val}")
            injected_keys.append(("relationships", key))

    # Notes
    top_notes = get_top_entries("notes")
    for key, entry in top_notes:
        val = entry.get("value")
        if val:
            lines.append(f"{key}: {val}")
            injected_keys.append(("notes", key))

    if memory_changed:
        save_memory(memory)

    if not lines:
        return "", []

    result = "[USER MEMORY]\n" + "\n".join(f"- {line}" for line in lines)
    if len(result) > 800:
        result = result[:797] + "…"

    return result + "\n", injected_keys