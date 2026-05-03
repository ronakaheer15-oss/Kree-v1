"""
Hardware Profile Analyzer
Determines the capability of the local machine to recommend or restrict AI models.
"""
import psutil
import subprocess

def get_vram_gb():
    """Attempt to get dedicated VRAM in GB using WMI."""
    try:
        # Ask WMI for AdapterRAM (works for many dedicated GPUs, but may cap at 4GB on 32-bit WMI queries)
        # A more reliable Windows way without 3rd party libs is using dxdiag or wmic
        output = subprocess.check_output(
            ["wmic", "path", "win32_VideoController", "get", "AdapterRAM"], 
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        lines = [line.strip() for line in output.split("\n") if line.strip() and line.strip().isdigit()]
        if not lines:
            return 0
        
        # Take the max RAM if multiple GPUs (e.g., integrated + dedicated)
        max_bytes = max(int(val) for val in lines)
        return round(max_bytes / (1024 ** 3), 1)
    except Exception:
        return 0

def get_system_ram_gb():
    return round(psutil.virtual_memory().total / (1024**3), 1)

def analyze_hardware():
    """
    Returns a hardware profile dictionary:
    tier: 'low', 'mid', 'high'
    vram_gb: float
    ram_gb: float
    recommended_mode: string
    """
    sys_ram = get_system_ram_gb()
    vram = get_vram_gb()
    
    tier = "low"
    recommended_mode = "CLOUD_GEMINI" # Always default low-end to cloud
    
    if vram >= 12 and sys_ram >= 32:
        tier = "high"
        recommended_mode = "LOCAL_APEX_31B"
    elif vram >= 8 and sys_ram >= 16:
        tier = "mid"
        recommended_mode = "LOCAL_CORE_26B"
    elif sys_ram >= 16:
        tier = "low" # Good RAM, poor GPU
        recommended_mode = "LOCAL_NEXUS_E4B"
        
    return {
        "ram_gb": sys_ram,
        "vram_gb": vram,
        "tier": tier,
        "recommended_mode": recommended_mode,
        "can_run_local": sys_ram > 8 # Minimum req even for Nexus
    }

if __name__ == "__main__":
    import json
    print(json.dumps(analyze_hardware(), indent=2))
