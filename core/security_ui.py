"""
Kree Aegis Security UI Strings
Rebuilt to match Kree's native Emerald Protocol Tailwind environment.
"""

LOCK_SCREEN_HTML = """
<!-- Background Layer -->
<div class="fixed inset-0 z-0 bg-[#09090b] pointer-events-none"></div>
<div class="fixed inset-0 z-0 opacity-[0.03] pointer-events-none" style="background-image:radial-gradient(circle at 1px 1px,#fff 1px,transparent 0);background-size:28px 28px;"></div>

<!-- Top Header -->
<header class="fixed top-0 w-full z-50 flex justify-between items-center px-6 h-14 bg-black/40 backdrop-blur-md border-b border-white/5">
    <div class="flex items-center gap-2">
        <span class="material-icons-outlined text-primary text-lg">lock</span>
        <span class="font-display font-bold tracking-[0.2em] text-primary uppercase text-sm shimmer">KREE AI SYSTEM</span>
    </div>
    <div class="flex items-center gap-4">
        <div class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-red-500 blink"></span>
            <span class="font-mono text-[10px] tracking-[0.2em] text-zinc-500 uppercase">SYSTEM LOCKED</span>
        </div>
        <span class="material-icons-outlined text-zinc-600 text-base">sensors</span>
    </div>
</header>

<!-- Main Content Canvas -->
<main class="relative z-10 flex flex-col items-center justify-center min-h-screen p-6 pt-20 pb-32">
    
    <!-- Centerpiece -->
    <div class="relative group mb-8 flex items-center justify-center">
        <!-- Pulsing Rings -->
        <div class="absolute w-40 h-40 rounded-full border border-primary/20 ring1 pointer-events-none"></div>
        <div class="absolute w-56 h-56 rounded-full border border-dashed border-primary/10 ring2 pointer-events-none"></div>
        
        <!-- Core Shield -->
        <div class="relative w-28 h-28 rounded-full bg-black flex items-center justify-center border border-primary/30 shadow-[0_0_40px_rgba(0,220,130,0.15)] z-10">
            <div class="absolute inset-0 rounded-full bg-[radial-gradient(ellipse_at_center,rgba(0,220,130,0.15)_0%,transparent_70%)] orb-glow pointer-events-none"></div>
            <div class="flex flex-col items-center">
                <span class="material-icons-outlined text-primary text-3xl mb-1 shimmer">shield</span>
                <div class="font-mono text-[8px] tracking-[0.3em] text-primary/60 uppercase">AES-256</div>
            </div>
        </div>
    </div>

    <!-- Glassmorphic Panel -->
    <div class="w-full max-w-sm bg-zinc-950/80 backdrop-blur-xl border border-white/5 p-6 rounded-2xl shadow-2xl relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary to-transparent opacity-50"></div>
        
        <div class="text-center mb-6">
            <h1 class="font-display text-xl font-bold tracking-widest text-white mb-1 uppercase">Aegis Protocol</h1>
            <p class="font-mono text-[9px] tracking-[0.15em] text-zinc-500 uppercase">Biometric & Cipher Verification</p>
        </div>

        <!-- PIN Dots -->
        <div class="mb-6 flex flex-col items-center">
            <div class="flex justify-center gap-3 mb-2" id="pin-dots-container">
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
                <div class="w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300"></div>
            </div>
            <label id="pin-status-text" class="font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase mt-3 text-center h-3">AEGIS MASTER PIN</label>
        </div>

        <!-- Numeric Grid -->
        <div class="grid grid-cols-3 gap-2.5 mb-5">
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">1</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">2</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">3</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">4</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">5</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">6</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">7</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">8</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">9</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition-all duration-200">
                <span class="material-icons-outlined text-[18px]">backspace</span>
            </button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">0</button>
            <button class="h-10 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center font-display text-xl text-zinc-400 hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-all duration-200">
                <span class="material-icons-outlined text-[18px]">face</span>
            </button>
        </div>

        <button class="w-full h-12 bg-primary text-black font-display font-bold uppercase tracking-[0.2em] rounded-xl shadow-[0_0_15px_rgba(0,220,130,0.3)] hover:shadow-[0_0_25px_rgba(0,220,130,0.5)] hover:bg-emerald-300 active:scale-[0.98] transition-all flex items-center justify-center gap-2 group">
            UNLOCK SYSTEM
            <span class="material-icons-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
        </button>
    </div>
</main>

<!-- Bottom Nav Bar -->
<nav class="fixed bottom-0 left-0 w-full z-50 flex justify-center items-center gap-12 px-8 pb-6 pt-6 bg-gradient-to-t from-black via-black/80 to-transparent pointer-events-none">
    <div class="pointer-events-auto flex items-center justify-center text-zinc-600 bg-zinc-900/50 w-12 h-12 rounded-full border border-white/5 hover:text-white hover:bg-white/10 transition cursor-pointer">
        <span class="material-icons-outlined">face</span>
    </div>
    <div class="pointer-events-auto flex items-center justify-center bg-primary text-black rounded-full w-14 h-14 shadow-[0_0_20px_rgba(0,220,130,0.3)] border border-primary/20 hover:scale-110 transition cursor-pointer">
        <span class="material-icons-outlined text-2xl">shield</span>
    </div>
    <div class="pointer-events-auto flex items-center justify-center text-zinc-600 bg-zinc-900/50 w-12 h-12 rounded-full border border-white/5 hover:text-white hover:bg-white/10 transition cursor-pointer">
        <span class="material-icons-outlined">power_settings_new</span>
    </div>
</nav>
"""

SETTINGS_MODAL_HTML = """
<!-- Dashboard Background -->
<div class="fixed inset-0 z-[99990] flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-md"></div>
    
    <div class="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-zinc-950 border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden">
        
        <!-- Header -->
        <div class="flex-shrink-0 flex items-center justify-between px-6 py-5 border-b border-white/5 bg-black/40">
            <div class="flex items-center gap-3">
                <span class="material-icons-outlined text-primary text-xl">admin_panel_settings</span>
                <h1 class="font-display font-bold text-white tracking-widest uppercase text-lg">AEGIS SECURITY MATRIX</h1>
            </div>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/10 text-zinc-500 hover:text-white transition">
                <span class="material-icons-outlined text-lg">close</span>
            </button>
        </div>

        <!-- Scrollable Content -->
        <div class="p-6 md:p-8 space-y-8 overflow-y-auto">
            
            <!-- SECTION: Master PIN -->
            <section>
                <div class="flex items-center gap-3 mb-4">
                    <span class="material-icons-outlined text-sm text-zinc-500">pin</span>
                    <label class="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Master Access Sequence</label>
                    <div class="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent"></div>
                </div>
                
                <div class="bg-black/30 rounded-xl border border-white/5 p-5 flex flex-col md:flex-row gap-6 items-end">
                    <div class="flex-1 w-full space-y-3">
                        <p class="text-[11px] font-mono text-zinc-400">Update your core access sequence to bypass biometrics.</p>
                        <div class="relative">
                            <input class="w-full bg-black border border-white/10 rounded-xl py-3 px-4 text-xl font-display tracking-[0.5em] focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-white placeholder-zinc-700" placeholder="••••••" type="password"/>
                        </div>
                    </div>
                    <button class="w-full md:w-auto h-14 flex-shrink-0 flex items-center justify-center gap-2 bg-white/5 hover:bg-primary/10 text-white hover:text-primary border border-white/10 hover:border-primary/30 font-display font-bold py-3 px-6 uppercase tracking-wider text-xs rounded-xl transition-all shadow-md">
                        <span class="material-icons-outlined text-[16px]">save</span>
                        Save Sequence
                    </button>
                </div>
            </section>

            <!-- SECTION: Toggles -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                <!-- Biometrics -->
                <div class="bg-black/30 p-5 rounded-xl border border-white/5 group hover:border-primary/30 transition shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]">
                    <div class="flex items-center justify-between mb-3">
                        <div class="flex items-center gap-2">
                            <span class="material-icons-outlined text-primary text-[18px] shimmer">face</span>
                            <label class="font-display font-bold text-sm uppercase tracking-widest text-white">CRYPTOGRAPHIC FACE ID</label>
                        </div>
                        <label class="relative inline-flex items-center cursor-pointer">
                            <input checked type="checkbox" class="sr-only peer">
                            <div class="w-9 h-5 bg-zinc-800 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-zinc-400 peer-checked:after:bg-black after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary border border-white/10"></div>
                        </label>
                    </div>
                    <p class="text-[10px] font-mono text-zinc-500 mb-4">Enable 3D neural-pattern facial recognition for instant, zero-touch decryption upon visual contact.</p>
                    <div class="flex items-center gap-2">
                        <div class="w-1.5 h-1.5 rounded-full bg-primary blink"></div>
                        <span class="text-[9px] font-mono text-primary uppercase tracking-widest">Scanning Active</span>
                    </div>
                </div>

                <!-- Timer -->
                <div class="bg-black/30 p-5 rounded-xl border border-white/5 group hover:border-primary/30 transition">
                    <div class="flex items-center gap-2 mb-3">
                        <span class="material-icons-outlined text-primary text-[18px]">timer</span>
                        <label class="font-display font-bold text-sm uppercase tracking-widest text-white">Auto-Lock Timer</label>
                    </div>
                    <div class="flex justify-between text-[9px] font-mono text-zinc-600 uppercase mb-2">
                        <span>Responsive</span>
                        <span class="text-primary font-bold">05:00M</span>
                        <span>Absolute</span>
                    </div>
                    <input class="w-full h-1 bg-zinc-800 rounded-full appearance-none accent-primary mb-3" max="5" min="1" type="range" value="4"/>
                    <p class="text-[9px] font-mono text-zinc-600 uppercase tracking-wider text-center mt-2">Session purge after 5m inactivity.</p>
                </div>
            </div>

        </div>
        
        <!-- Footer -->
        <div class="flex-shrink-0 bg-black/60 p-4 border-t border-white/5 flex justify-between items-center px-6">
            <div class="flex gap-4">
                <div class="text-[9px] font-mono text-zinc-600 uppercase"><span class="text-zinc-400">Protocol:</span> SHA-512_KREE</div>
                <div class="text-[9px] font-mono text-zinc-600 uppercase"><span class="text-zinc-400">Node:</span> ORBIT_772</div>
            </div>
            <div class="flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-primary blink"></span>
                <span class="text-[9px] font-mono text-primary font-bold uppercase tracking-widest">System Secured</span>
            </div>
        </div>
    </div>
</div>
"""

LOCK_SCREEN_JS = """
(function(){
    if (document.getElementById('kree-vault-lock')) return;
    
    var lockDiv = document.createElement('div');
    lockDiv.id = 'kree-vault-lock';
    // Use an ultra-high z-index to cover everything
    lockDiv.style.cssText = 'position:fixed;inset:0;z-index:999999;background:#0e0e10;overflow-y:auto;overflow-x:hidden;';
    lockDiv.innerHTML = `""" + LOCK_SCREEN_HTML.replace("`", "\\`").replace("${", "\\${") + """`;
    document.body.appendChild(lockDiv);
    
    // Wire up the Numpad
    let pinInput = "";
    const dotsContainer = lockDiv.querySelector('#pin-dots-container');
    const dots = dotsContainer.querySelectorAll('div');
    
    // Clear initial dots
    dots.forEach(d => {
        d.className = "w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300";
    });
    
    function updateDots() {
        dots.forEach((d, i) => {
            if (i < pinInput.length) {
                d.className = "w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_10px_rgba(0,220,130,0.8)] transition-all duration-300";
            } else {
                d.className = "w-2.5 h-2.5 rounded-full bg-zinc-800 transition-all duration-300";
            }
        });
    }
    
    const statusText = lockDiv.querySelector('#pin-status-text');

    function completeUnlock() {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.on_pin_unlocked) {
            window.pywebview.api.on_pin_unlocked();
        }
        lockDiv.style.transition = "opacity 0.4s ease-out";
        lockDiv.style.opacity = "0";
        setTimeout(() => lockDiv.remove(), 400);
    }
    
    let isSetupMode = false;
    let setupStep = 1;
    let firstPin = "";
    
    // Check if we are in SETUP mode
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.is_pin_setup_required().then(required => {
            if(required) {
                isSetupMode = true;
                if(statusText) statusText.textContent = "CREATE NEW MASTER PIN";
            }
        });
    }
    
    function handleInput(val) {
        if(val === 'backspace') {
            pinInput = pinInput.slice(0, -1);
        } else if(val === 'face') {
            if (!isSetupMode && window.pywebview && window.pywebview.api) {
                window.pywebview.api.trigger_biometrics().then(res => {
                    if(res) {
                        completeUnlock();
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
                
                if (isSetupMode) {
                    if (setupStep === 1) {
                        firstPin = pinInput;
                        pinInput = "";
                        setupStep = 2;
                        if(statusText) statusText.textContent = "CONFIRM NEW PIN";
                        updateDots();
                    } else {
                        if (pinInput === firstPin) {
                            window.pywebview.api.setup_master_pin(pinInput).then(() => {
                                completeUnlock();
                            });
                        } else {
                            if(statusText) {
                                statusText.textContent = "PIN MISMATCH. TRY AGAIN.";
                                statusText.style.color = "#ef4444";
                            }
                            setTimeout(() => {
                                if(statusText) {
                                    statusText.textContent = "CREATE NEW MASTER PIN";
                                    statusText.style.color = "";
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
                            completeUnlock();
                        } else {
                            if(statusText) {
                                statusText.textContent = "INVALID PIN";
                                statusText.style.color = "#ef4444";
                            }
                            pinInput = "";
                            updateDots();
                            setTimeout(() => {
                                if(statusText) {
                                    statusText.textContent = "AEGIS MASTER PIN";
                                    statusText.style.color = "";
                                }
                            }, 1500);
                        }
                    });
                }
            });
        } else {
            let val = btn.textContent.trim();
            if(btn.querySelector('.material-icons-outlined')) {
                val = btn.querySelector('.material-icons-outlined').textContent.trim();
            }
            if (['0','1','2','3','4','5','6','7','8','9','backspace','face'].includes(val)) {
                btn.addEventListener('click', () => handleInput(val));
            }
        }
    });

    // Keyboard Support
    document.addEventListener('keydown', function(e) {
        if (!document.getElementById('kree-vault-lock')) return;
        
        if (e.key >= '0' && e.key <= '9') {
            handleInput(e.key);
        } else if (e.key === 'Backspace') {
            handleInput('backspace');
        } else if (e.key === 'Enter') {
            const unlockBtn = Array.from(lockDiv.querySelectorAll('button')).find(b => b.textContent.includes('UNLOCK SYSTEM'));
            if (unlockBtn) unlockBtn.click();
        } else if (e.key.toLowerCase() === 'f') {
            // Quick hotkey 'F' for Face ID
            handleInput('face');
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
    
    const closeBtn = modDiv.querySelector('button .material-icons-outlined');
    if(closeBtn) {
        closeBtn.parentElement.addEventListener('click', () => modDiv.remove());
    } else {
        const btns = modDiv.querySelectorAll('button');
        if(btns.length > 0) btns[0].addEventListener('click', () => modDiv.remove());
    }
    
    const saveBtn = Array.from(modDiv.querySelectorAll('button')).find(b => b.textContent.includes('Save Sequence'));
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
