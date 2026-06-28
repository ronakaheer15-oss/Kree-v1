import ctypes
from ctypes import wintypes
import sys

def prompt_windows_hello(message: str = "Aegis Face ID Verification Required.") -> bool:
    """Invokes the native Windows Hello (Face ID / PIN) security prompt."""
    if sys.platform != "win32":
        return False  # Non-Windows has no Windows Hello; deny access rather than grant it
        
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

        auth_buffer = ctypes.c_void_p()
        auth_buffer_size = wintypes.DWORD(0)
        auth_package = wintypes.DWORD(0)
        save = wintypes.BOOL(False)

        # Call CredUIPromptForWindowsCredentialsW natively
        auth_error = ctypes.windll.credui.CredUIPromptForWindowsCredentialsW( # type: ignore
            ctypes.byref(credui_info),
            0,
            ctypes.byref(auth_package),
            None,
            0,
            ctypes.byref(auth_buffer), 
            ctypes.byref(auth_buffer_size), 
            None, 
            ctypes.byref(save),
            1 # CREDUIWIN_ENUMERATE_CURRENT_USER
        )

        if auth_error == 0:
            max_len = 256
            username = ctypes.create_unicode_buffer(max_len)
            domain = ctypes.create_unicode_buffer(max_len)
            password = ctypes.create_unicode_buffer(max_len)
            username_len = wintypes.DWORD(max_len)
            domain_len = wintypes.DWORD(max_len)
            password_len = wintypes.DWORD(max_len)

            unpack_ok = ctypes.windll.credui.CredUnPackAuthenticationBufferW(
                0,
                auth_buffer,
                auth_buffer_size,
                username,
                ctypes.byref(username_len),
                domain,
                ctypes.byref(domain_len),
                password,
                ctypes.byref(password_len)
            )

            # Free the allocated auth buffer
            ctypes.windll.ole32.CoTaskMemFree(auth_buffer)

            if not unpack_ok:
                return False

            # Validate the credentials using LogonUserW
            token = wintypes.HANDLE()
            logon_ok = ctypes.windll.advapi32.LogonUserW(
                username.value,
                domain.value,
                password.value,
                2, # LOGON32_LOGON_INTERACTIVE
                0, # LOGON32_PROVIDER_DEFAULT
                ctypes.byref(token)
            )

            if logon_ok:
                ctypes.windll.kernel32.CloseHandle(token)
                return True
            else:
                last_err = ctypes.windll.kernel32.GetLastError()
                print(f"[SECURITY] LogonUserW failed with error code: {last_err}")
                return False
        else:
            print(f"[SECURITY] Windows Hello returned error code: {auth_error}")
            return False

    except Exception as e:
        print(f"[SECURITY] Windows Hello initialization failed: {e}")
        return False
