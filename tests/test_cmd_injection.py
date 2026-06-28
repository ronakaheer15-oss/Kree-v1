"""Quick validation for cmd_control injection protection."""
import sys
sys.path.insert(0, r"e:\Kree-v1-main")
from kree.actions.cmd_control import _is_safe

TESTS = [
    # (command, expected_safe)
    # MUST BLOCK:
    ("dir & del /q C:\\*",     False),
    ("calc | powershell",     False),
    ("whoami ; shutdown",     False),
    ("echo hello `whoami`",   False),
    ("ipconfig && net user",  False),
    ("dir || format C:",      False),
    # MUST ALLOW:
    ("ipconfig",              True),
    ("notepad",               True),
    ("explorer",              True),
    ("tasklist",              True),
    ("dir",                   True),
    ("systeminfo",            True),
    ("ver",                   True),
    ("time /t",               True),
]

passed = 0
for cmd, expected in TESTS:
    safe, reason = _is_safe(cmd)
    ok = safe == expected
    passed += ok
    status = "PASS" if ok else "FAIL"
    print(f"  {status}: '{cmd}' -> safe={safe} (expected={expected}) {reason}")

print(f"\n{passed}/{len(TESTS)} tests passed")
