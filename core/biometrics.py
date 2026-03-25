import ctypes
from ctypes import wintypes
import sys
import time

def prompt_windows_hello(message: str = "Aegis Face ID Verification Required.") -> bool:
    """Invokes the native Windows Hello (Face ID / PIN) security prompt."""
    if sys.platform != "win32":
        return True # Fallback for Mac/Linux
        
    try:
        class CREDUI_INFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hwndParent", wintypes.HWND),
                ("pszMessageText", wintypes.LPCWSTR),
                ("pszCaptionText", wintypes.LPCWSTR),
                ("hbmBanner", wintypes.HBITMAP),
            ]
        
        credui_info = CREDUI_INFO()
        credui_info.cbSize = ctypes.sizeof(CREDUI_INFO) # type: ignore
        credui_info.hwndParent = None # type: ignore
        credui_info.pszMessageText = message # type: ignore
        credui_info.pszCaptionText = "Project Aegis Security" # type: ignore
        credui_info.hbmBanner = None # type: ignore

        # Call CredUIPromptForWindowsCredentialsW natively
        auth_error = ctypes.windll.credui.CredUIPromptForWindowsCredentialsW( # type: ignore
            ctypes.byref(credui_info),
            0,
            ctypes.byref(wintypes.DWORD(0)),
            None,
            0,
            ctypes.byref(ctypes.c_void_p()), 
            ctypes.byref(ctypes.c_void_p()), 
            ctypes.byref(wintypes.DWORD(0)), 
            ctypes.byref(wintypes.BOOL(0)),
            1 # CREDUIWIN_ENUMERATE_CURRENT_USER
        )

        if auth_error == 0:
            return True
        else:
            print(f"[SECURITY] Windows Hello returned error code: {auth_error}")
            return False

    except Exception as e:
        print(f"[SECURITY] Windows Hello initialization failed: {e}")
        return False
