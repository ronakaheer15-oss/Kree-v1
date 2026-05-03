"""
Kree API Setup UI Strings
Premium Stitch-inspired aesthetic for initial cognitive activation.
"""

API_SETUP_HTML = """
<div class="fixed inset-0 z-0 bg-[#09090b] pointer-events-none"></div>
<div class="fixed inset-0 z-0 opacity-[0.03] pointer-events-none" style="background-image:radial-gradient(circle at 1px 1px,#fff 1px,transparent 0);background-size:28px 28px;"></div>

<header class="fixed top-0 w-full z-50 flex justify-between items-center px-6 h-14 bg-black/40 backdrop-blur-md border-b border-white/5">
    <div class="flex items-center gap-2">
        <span class="material-icons-outlined text-primary text-lg">psychology</span>
        <span class="font-display font-bold tracking-[0.2em] text-primary uppercase text-sm">COGNITIVE INITIALIZATION</span>
    </div>
    <div class="flex items-center gap-4">
        <div class="flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-accent blink"></span>
            <span class="font-mono text-[10px] tracking-[0.2em] text-zinc-500 uppercase">Awaiting Activation</span>
        </div>
    </div>
</header>

<main class="relative z-10 flex flex-col items-center justify-center min-h-screen p-6">
    <div class="w-full max-w-md bg-zinc-950/80 backdrop-blur-2xl border border-white/10 p-8 rounded-3xl shadow-2xl relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-primary to-transparent opacity-80"></div>
        
        <div class="text-center mb-8">
            <div class="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                <span class="material-icons-outlined text-primary text-3xl">api</span>
            </div>
            <h1 class="font-display text-2xl font-bold tracking-widest text-white mb-2 uppercase">Kree Core Activation</h1>
            <p class="font-mono text-[10px] tracking-[0.1em] text-zinc-500 uppercase leading-relaxed">Cognitive matrices require a Gemini API Key to initialize high-level reasoning and speech protocols.</p>
        </div>

        <div class="space-y-6">
            <div class="relative group">
                <label class="block font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-600 mb-2 ml-1">Universal Intelligence Key</label>
                <div class="relative">
                    <input id="gemini-api-input" type="password" placeholder="AIza..." 
                        class="w-full bg-black/60 border border-white/10 rounded-2xl py-4 px-5 text-zinc-200 font-mono text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-all placeholder-zinc-800"/>
                    <span class="absolute right-5 top-1/2 -translate-y-1/2 material-icons-outlined text-zinc-700 group-focus-within:text-primary transition-colors">vpn_key</span>
                </div>
            </div>

            <button id="activate-btn" class="w-full h-14 bg-primary text-black font-display font-bold uppercase tracking-[0.2em] rounded-2xl shadow-[0_0_20px_rgba(0,220,130,0.3)] hover:shadow-[0_0_35px_rgba(0,220,130,0.5)] hover:bg-emerald-300 active:scale-[0.97] transition-all flex items-center justify-center gap-3">
                ACTIVATE COGNITION
                <span id="btn-icon" class="material-icons-outlined text-lg">bolt</span>
            </button>
            
            <p id="setup-status" class="text-center font-mono text-[9px] tracking-[0.1em] text-zinc-600 uppercase h-4"></p>
        </div>
    </div>
</main>
"""

API_SETUP_JS = """
(function(){
    if (document.getElementById('kree-api-setup')) return;
    
    var setupDiv = document.createElement('div');
    setupDiv.id = 'kree-api-setup';
    setupDiv.style.cssText = 'position:fixed;inset:0;z-index:9999999;background:#09090b;opacity:0;transition:opacity 0.6s ease-out;';
    setupDiv.innerHTML = `""" + API_SETUP_HTML.replace("`", "\\`").replace("${", "\\${") + """`;
    document.body.appendChild(setupDiv);
    
    // Quick fade in
    requestAnimationFrame(() => setupDiv.style.opacity = '1');
    
    const input = document.getElementById('gemini-api-input');
    const btn = document.getElementById('activate-btn');
    const status = document.getElementById('setup-status');
    const btnIcon = document.getElementById('btn-icon');
    
    function setStatus(msg, isError = false) {
        status.textContent = msg;
        status.style.color = isError ? '#ef4444' : '#00DC82';
    }

    btn.addEventListener('click', function() {
        const key = input.value.trim();
        if (!key) {
            setStatus("API Key cannot be empty.", true);
            return;
        }
        
        btn.disabled = true;
        btn.style.opacity = '0.7';
        btnIcon.textContent = 'sync';
        btnIcon.classList.add('animate-spin');
        setStatus("Verifying Cognitive Bridge...");

        // Call the backend API
        if (window.pywebview && window.pywebview.api && window.pywebview.api.save_api_key) {
            window.pywebview.api.save_api_key(key);
            
            // Artificial delay for premium feel + ensuring write completion
            setTimeout(() => {
                setStatus("Activation Successful. Transitioning to Aegis Layer.");
                setupDiv.style.opacity = '0';
                setTimeout(() => {
                    setupDiv.remove();
                    // Tell backend we are ready for the lock screen
                    if (window.pywebview.api.on_api_setup_complete) {
                        window.pywebview.api.on_api_setup_complete();
                    }
                }, 600);
            }, 1200);
        } else {
            setStatus("System Bridge Offline. Contact Admin.", true);
            btn.disabled = false;
            btn.style.opacity = '1';
            btnIcon.textContent = 'bolt';
            btnIcon.classList.remove('animate-spin');
        }
    });
    
    // Enter key support
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') btn.click();
    });
})();
"""
