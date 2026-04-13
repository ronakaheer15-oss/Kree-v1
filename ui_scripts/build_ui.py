import os
import re

def extract_body(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    body_match = re.search(r"<body.*?>(.*?)</body>", content, re.DOTALL | re.IGNORECASE)
    if body_match:
        html = body_match.group(1).strip()
    else:
        html = content
    html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
    return html

script_dir = os.path.dirname(os.path.abspath(__file__))
lock_html = extract_body(os.path.join(script_dir, "lock.html"))
settings_html = extract_body(os.path.join(script_dir, "settings.html"))

template = r'''"""
Kree Aegis Security UI Strings
Auto-generated from Stitch MCP HTML outputs.
"""

LOCK_SCREEN_HTML = """
__LOCK_HTML__
"""

SETTINGS_MODAL_HTML = """
__SETTINGS_HTML__
"""

LOCK_SCREEN_JS = """
(function(){
    if (document.getElementById('kree-vault-lock')) return;
    
    var lockDiv = document.createElement('div');
    lockDiv.id = 'kree-vault-lock';
    // Use an ultra-high z-index to cover everything
    lockDiv.style.cssText = 'position:fixed;inset:0;z-index:999999;background:#0e0e10;';
    lockDiv.innerHTML = `""" + LOCK_SCREEN_HTML.replace("`", "\\`").replace("${", "\\${") + """`;
    document.body.appendChild(lockDiv);
    
    // Wire up the Numpad
    let pinInput = "";
    const dots = lockDiv.querySelectorAll('.w-3.h-3.rounded-full');
    
    // Clear initial dots
    dots.forEach(d => {
        d.className = "w-3 h-3 rounded-full bg-surface-container-highest transition-all duration-300";
    });
    
    function updateDots() {
        dots.forEach((d, i) => {
            if (i < pinInput.length) {
                d.className = "w-3 h-3 rounded-full bg-primary shadow-[0_0_8px_#46fa9c] transition-all duration-300";
            } else {
                d.className = "w-3 h-3 rounded-full bg-surface-container-highest transition-all duration-300";
            }
        });
    }
    
    const statusText = lockDiv.querySelector('label.font-label, label') || lockDiv.querySelector('.tracking-[0.2em]');
    if (statusText) statusText.id = 'pin-status-text';
    
    let isSetupMode = false;
    let setupStep = 1;
    let firstPin = "";
    
    // Check if we are in SETUP mode
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.is_pin_setup_required().then(required => {
            if(required) {
                isSetupMode = true;
                if(document.getElementById('pin-status-text')) document.getElementById('pin-status-text').textContent = "CREATE NEW MASTER PIN";
            }
        });
    }
    
    function handleInput(val) {
        if(val === 'backspace') {
            pinInput = pinInput.slice(0, -1);
        } else if(val === 'fingerprint') {
            if (!isSetupMode && window.pywebview && window.pywebview.api) {
                window.pywebview.api.trigger_biometrics().then(res => {
                    if(res) {
                        lockDiv.style.opacity = '0';
                        setTimeout(()=>lockDiv.remove(), 400);
                    }
                });
            }
        } else {
            if(pinInput.length < 6) pinInput += val;
        }
        updateDots();
    }
    
    const btns = lockDiv.querySelectorAll('button');
    btns.forEach(btn => {
        if(btn.textContent.trim().includes('UNLOCK SYSTEM')) {
            btn.addEventListener('click', () => {
                if(pinInput.length < 4) return; // Wait until 4 to 6 chars
                const statusEl = document.getElementById('pin-status-text');
                
                if (isSetupMode) {
                    if (setupStep === 1) {
                        firstPin = pinInput;
                        pinInput = "";
                        setupStep = 2;
                        if(statusEl) statusEl.textContent = "CONFIRM NEW PIN";
                        updateDots();
                    } else {
                        if (pinInput === firstPin) {
                            window.pywebview.api.setup_master_pin(pinInput).then(() => {
                                lockDiv.style.opacity = '0';
                                setTimeout(()=>lockDiv.remove(), 400);
                            });
                        } else {
                            if(statusEl) {
                                statusEl.textContent = "PIN MISMATCH. TRY AGAIN.";
                                statusEl.style.color = "#ff716c";
                            }
                            setTimeout(() => {
                                if(statusEl) {
                                    statusEl.textContent = "CREATE NEW MASTER PIN";
                                    statusEl.style.color = "";
                                }
                                pinInput = "";
                                firstPin = "";
                                setupStep = 1;
                                updateDots();
                            }, 1500);
                        }
                    }
                } else {
                    // Login Mode
                    window.pywebview.api.verify_master_pin(pinInput).then(isValid => {
                        if(isValid) {
                            lockDiv.style.transition = "opacity 0.4s ease-out";
                            lockDiv.style.opacity = "0";
                            setTimeout(() => lockDiv.remove(), 400);
                        } else {
                            if(statusEl) {
                                statusEl.textContent = "INVALID PIN";
                                statusEl.style.color = "#ff716c";
                            }
                            pinInput = "";
                            updateDots();
                            setTimeout(() => {
                                if(statusEl) {
                                    statusEl.textContent = "AEGIS MASTER PIN";
                                    statusEl.style.color = "";
                                }
                            }, 1500);
                        }
                    });
                }
            });
        } else {
            let val = btn.textContent.trim();
            if(btn.querySelector('.material-symbols-outlined')) {
                val = btn.querySelector('.material-symbols-outlined').textContent.trim();
            }
            if (['0','1','2','3','4','5','6','7','8','9','backspace','fingerprint'].includes(val)) {
                btn.addEventListener('click', () => handleInput(val));
            }
        }
    });
})();
"""

SETTINGS_MODAL_JS = """
(function(){
    if (document.getElementById('kree-settings-modal')) return;
    
    var modDiv = document.createElement('div');
    modDiv.id = 'kree-settings-modal';
    modDiv.style.cssText = 'position:fixed;inset:0;z-index:999990;';
    modDiv.innerHTML = `""" + SETTINGS_MODAL_HTML.replace("`", "\\`").replace("${", "\\${") + """`;
    document.body.appendChild(modDiv);
    
    const closeBtn = modDiv.querySelector('button .material-symbols-outlined');
    if(closeBtn) {
        closeBtn.parentElement.addEventListener('click', () => modDiv.remove());
    } else {
        const btns = modDiv.querySelectorAll('button');
        if(btns.length > 0) btns[0].addEventListener('click', () => modDiv.remove());
    }
    
    const saveBtn = Array.from(modDiv.querySelectorAll('button')).find(b => b.textContent.includes('SAVE NEW ACCESS KEY'));
    const pinInp = modDiv.querySelector('input[type="password"]');
    if (saveBtn && pinInp) {
        saveBtn.addEventListener('click', () => {
            const newPin = pinInp.value.trim();
            if (newPin.length >= 4) {
                if(window.pywebview && window.pywebview.api) {
                    window.pywebview.api.setup_master_pin(newPin).then(() => {
                        pinInp.value = "";
                        pinInp.placeholder = "SAVED SECURELY";
                        setTimeout(() => pinInp.placeholder = "••••••", 2000);
                    });
                }
            }
        });
    }
})();
"""
'''

py_code = template.replace("__LOCK_HTML__", lock_html)
py_code = py_code.replace("__SETTINGS_HTML__", settings_html)

core_dir = os.path.join(os.path.dirname(script_dir), "core")
output_path = os.path.join(core_dir, "security_ui.py")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(py_code)

print("Generated core/security_ui.py")
