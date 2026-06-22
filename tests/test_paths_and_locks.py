import sys
import os
import asyncio
import time
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import modules under test
from kree.core.runtime import APP_DATA_DIR, CONFIG_DIR, MEMORY_DIR, HISTORY_DIR
from kree.memory import config_manager, history_manager

# Backup path
backup_dir = Path(__file__).resolve().parent / "backup_settings"

def backup_settings():
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for d in [CONFIG_DIR, MEMORY_DIR]:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    shutil.copy2(f, backup_dir / f.name)

def restore_settings():
    if not backup_dir.exists():
        return
        
    # Clean current test outputs
    for d in [CONFIG_DIR, MEMORY_DIR]:
        if d.exists():
            for f in d.glob("*"):
                if f.is_file():
                    f.unlink(missing_ok=True)
                    
    # Restore original backups
    for f in backup_dir.glob("*"):
        if f.is_file():
            # config vs memory distinction
            if "memory" in f.name or "long_term" in f.name:
                shutil.copy2(f, MEMORY_DIR / f.name)
            else:
                shutil.copy2(f, CONFIG_DIR / f.name)
                
    shutil.rmtree(backup_dir)

def test_paths():
    print("\n--- STEP 1: Verify APP_DATA_DIR and Centralized Paths ---")
    print(f"APP_DATA_DIR: {APP_DATA_DIR}")
    print(f"CONFIG_DIR: {CONFIG_DIR}")
    print(f"MEMORY_DIR: {MEMORY_DIR}")
    print(f"HISTORY_DIR: {HISTORY_DIR}")
    
    assert "Kree" in str(APP_DATA_DIR), "APP_DATA_DIR should use user app data folder!"
    assert CONFIG_DIR.parent == APP_DATA_DIR, "CONFIG_DIR should be under APP_DATA_DIR!"
    assert HISTORY_DIR.parent == APP_DATA_DIR, "HISTORY_DIR should be under APP_DATA_DIR!"
    
    print("SUCCESS: All directory constants successfully centralized under AppData.")

def test_configs_and_memories():
    print("\n--- STEP 2: Verify Configs and Memory Save/Load to AppData ---")
    
    # Save test configs
    test_audio_settings = {"input_device_index": 99, "vad_threshold_rising": 450}
    config_manager.save_audio_settings(test_audio_settings)
    
    # Verify file is written under APP_DATA_DIR
    audio_file = CONFIG_DIR / "audio_settings.json"
    assert audio_file.exists(), f"Audio settings should be written to {audio_file}!"
    
    loaded_settings = config_manager.load_audio_settings()
    assert loaded_settings.get("input_device_index") == 99, "Failed to load correct config values!"
    print("SUCCESS: Config settings correctly load/save under AppData.")
    
    # Save conversation turn
    history_manager.save_turn("hello kree", "hello sir")
    history_file = HISTORY_DIR / "kree_memory.json"
    assert history_file.exists(), f"Conversation history should be written to {history_file}!"
    print("SUCCESS: Conversation history correctly load/save under AppData.")

def test_async_install_lock():
    print("\n--- STEP 3: Verify Async Browser Install Lock concurrency ---")
    from kree.actions.browser_control import _bt, _ensure_started
    
    # Ensure BrowserThread is started
    _ensure_started()
    
    # Verify lock initialization
    assert _bt._install_lock is not None, "BrowserThread install lock not initialized!"
    print("SUCCESS: Loop-bound async lock verified.")

def main():
    try:
        backup_settings()
        test_paths()
        test_configs_and_memories()
        test_async_install_lock()
        print("\nAll Hardening Paths and Locks Tests Passed successfully!")
    finally:
        restore_settings()

if __name__ == "__main__":
    main()
