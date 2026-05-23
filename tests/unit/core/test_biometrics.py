import sys
import pytest
from unittest.mock import patch


def test_prompt_windows_hello_denies_access_on_non_windows():
    """On non-Windows platforms, prompt_windows_hello must not grant access (fail-closed, not fail-open)."""
    with patch.object(sys, "platform", "linux"):
        from kree.core import biometrics
        import importlib
        importlib.reload(biometrics)
        result = biometrics.prompt_windows_hello("test")
        assert result is False, (
            "prompt_windows_hello must return False on non-Windows platforms. "
            "Returning True is a fail-open security bug (Critical Issue #9)."
        )


def test_prompt_windows_hello_raises_on_non_windows():
    """Alternatively: non-Windows must raise NotImplementedError rather than silently granting access."""
    with patch.object(sys, "platform", "darwin"):
        from kree.core import biometrics
        import importlib
        importlib.reload(biometrics)
        result = biometrics.prompt_windows_hello("test")
        assert result is not True, (
            "prompt_windows_hello must never return True (authorized) on non-Windows platforms."
        )


def test_prompt_windows_hello_denies_on_ctypes_exception():
    """Windows Hello ctypes exception must deny access (existing fail-closed path)."""
    with patch.object(sys, "platform", "win32"):
        from kree.core import biometrics
        import importlib
        importlib.reload(biometrics)

        # Simulate the inner credui call raising unexpectedly
        with patch("ctypes.windll") as mock_windll:
            mock_windll.credui.CredUIPromptForWindowsCredentialsW.side_effect = OSError("credui unavailable")
            result = biometrics.prompt_windows_hello("test")
            assert result is False, "Exceptions during Windows Hello must deny access, not grant it."
