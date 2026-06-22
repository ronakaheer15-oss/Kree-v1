import sys
import os
import json
import shutil
from pathlib import Path

sys.path.insert(0, r"e:\Kree-v1-main")

import kree.core.vault as vault

# Temporary test file path
temp_config_dir = Path("e:/Kree-v1-main/tests/scratch_config")
temp_config_dir.mkdir(parents=True, exist_ok=True)
api_file = temp_config_dir / "api_keys.json"

# Define mock hardware IDs
legacy_wmic_id = "A926C52C-7490-11E8-9C82-90324BAF9EFB"
modern_registry_id = "a0e3c22f-5c6c-4c46-a9c6-737c8e9eaa02"

# 1. Simulate old version of application (using WMIC UUID)
print("\n--- STEP 1: Simulate Legacy Vault Encryption (WMIC UUID) ---")
vault._get_wmic_uuid = lambda: legacy_wmic_id
vault._get_registry_guid = lambda: None
vault.get_machine_id = lambda: legacy_wmic_id

# Save vault with the old key
original_key = "GEMINI_TEST_API_KEY_12345"
vault.save_api_key(api_file, original_key)
print("Vault saved using legacy WMIC UUID key.")

# Verify old vault content
with open(api_file, "rb") as f:
    encrypted_data_old = f.read()
assert len(encrypted_data_old) > 0
print(f"Encrypted payload length: {len(encrypted_data_old)}")

# 2. Simulate upgrade to new version (using Registry MachineGuid)
print("\n--- STEP 2: Simulate Application Upgrade (Using Registry MachineGuid) ---")
vault._get_wmic_uuid = lambda: legacy_wmic_id
vault._get_registry_guid = lambda: modern_registry_id
vault.get_machine_id = lambda: modern_registry_id

# Try loading the API key under the upgraded system
decrypted_key = vault.load_api_key(api_file)
print(f"Decrypted loaded key: {decrypted_key}")
assert decrypted_key == original_key, "Decrypted key must match original key!"
print("SUCCESS: Legacy vault was successfully decrypted after upgrade!")

# Verify migration (should have automatically re-encrypted with modern key)
with open(api_file, "rb") as f:
    encrypted_data_new = f.read()

# Let's verify that the new file content is indeed decrypted successfully under ONLY modern key
vault._get_wmic_uuid = lambda: None
vault._get_registry_guid = lambda: modern_registry_id
vault.get_machine_id = lambda: modern_registry_id

decrypted_after_migration = vault.load_api_key(api_file)
print(f"Decrypted after migration: {decrypted_after_migration}")
assert decrypted_after_migration == original_key
print("SUCCESS: Vault was successfully migrated/re-encrypted to the new Registry MachineGuid key!")

# Clean up
if temp_config_dir.exists():
    shutil.rmtree(temp_config_dir)

print("\nAll Vault Migration Compatibility Tests Passed successfully!")
