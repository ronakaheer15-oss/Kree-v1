"""
Kree Dashboard UI — pywebview-based (v3, stable)
"""

import os, sys, json, time, threading, psutil  # type: ignore[import]
from pathlib import Path

import webview  # type: ignore[import]

# ── Paths ────────────────────────────────────────────────────────────────────
def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_STITCH      = BASE_DIR.parent / "stitch_core_system_dashboard" / "stitch_core_system_dashboard"
_LIGHT_HTML  = _STITCH / "core_system_dashboard_1" / "code.html"
_DARK_HTML   = _STITCH / "core_system_dashboard_2" / "code.html"
_WIDGET_HTML = _STITCH / "minimized_control_widget" / "code.html"

try:
    from core.security_ui import LOCK_SCREEN_JS, SETTINGS_MODAL_JS # type: ignore[import]
except ImportError:
    LOCK_SCREEN_JS = ""
    SETTINGS_MODAL_JS = ""

SYSTEM_NAME = "Kree"


# ── Bridge JS injected after every page load ──────────────────────────────────
_BRIDGE_JS = """
(function(){
  if (window.__kree_bridge_installed__) return;
  window.__kree_bridge_installed__ = true;

  // ── Fade-in animation for transcript ─────────────────────────────────────
  var _style = document.createElement('style');
  _style.textContent = '@keyframes kFadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}';
  document.head && document.head.appendChild(_style);

  // ── Transcript ────────────────────────────────────────────────────────────
  window.appendTranscript = function(role, text) {
    var c = document.getElementById('kree-transcript') ||
            document.querySelector('.overflow-y-auto');
    if (!c) return;
    var w = document.createElement('div');
    w.style.cssText = 'display:flex;flex-direction:column;' +
      (role==='user'?'align-items:flex-end;':'align-items:flex-start;') +
      'margin-bottom:14px;animation:kFadeIn .25s ease;';

    var b = document.createElement('div');
    b.style.cssText = role === 'user'
      ? 'background:rgba(0,220,130,.13);border:1px solid rgba(0,220,130,.22);color:#e5e7eb;' +
        'font-size:13px;padding:9px 14px;border-radius:16px 16px 4px 16px;max-width:88%;'
      : 'background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.09);color:#d1d5db;' +
        'font-size:13px;padding:9px 14px;border-radius:16px 16px 16px 4px;max-width:88%;';

    if (role !== 'user') {
      var lbl = document.createElement('div');
      lbl.style.cssText = 'font-size:9px;letter-spacing:.14em;text-transform:uppercase;' +
        'color:#a855f7;margin-bottom:4px;opacity:.7;font-family:monospace;';
      lbl.textContent = 'Kree AI';
      b.appendChild(lbl);
    }
    var p = document.createElement('p');
    p.style.cssText = 'margin:0;line-height:1.55;';
    p.textContent = text;
    b.appendChild(p);
    w.appendChild(b);

    var now = new Date();
    var h = now.getHours(), m = now.getMinutes();
    var ap = h>=12?'PM':'AM'; h=h%12||12;
    var ts = document.createElement('span');
    ts.style.cssText = 'font-size:9px;color:#3f3f46;margin-top:3px;font-family:monospace;' +
      'text-transform:uppercase;letter-spacing:.07em;transition:opacity .2s;opacity:0;';
    ts.textContent = (role==='user'?'You':'Kree') + ' \\u2022 ' +
      h+':'+String(m).padStart(2,'0')+' '+ap;
    w.appendChild(ts);
    w.addEventListener('mouseenter',function(){ ts.style.opacity='1'; });
    w.addEventListener('mouseleave',function(){ ts.style.opacity='0'; });
    c.appendChild(w);
    c.scrollTop = c.scrollHeight;
  };

  // ── Speaking animation ────────────────────────────────────────────────────
  window.setSpeaking = function(val) {
    var orb = document.querySelector('.orb-container');
    if (orb) orb.style.animationDuration = val ? '1.8s' : '6s';
  };

  // ── Metrics (ID-based — no class collision) ───────────────────────────────
  window.updateMetrics = function(cpu, ram) {
    var ce=document.getElementById('kree-cpu-val'), re=document.getElementById('kree-ram-val');
    var cb=document.getElementById('kree-cpu-bar'), rb=document.getElementById('kree-ram-bar');
    if(ce) ce.textContent = Math.round(cpu);
    if(re) re.textContent = Math.round(ram);
    if(cb) cb.style.width = Math.min(100,Math.round(cpu))+'%';
    if(rb) rb.style.width = Math.min(100,Math.round(ram))+'%';
  };

  // ── Process table refresh ─────────────────────────────────────────────────
  function refreshProcs() {
    if (!window.pywebview || !window.pywebview.api) return;
    window.pywebview.api.get_processes().then(function(raw) {
      var tb = document.getElementById('kree-procs-body');
      if (!tb || !raw) return;
      var procs;
      try { procs = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch(e) { return; }
      if(tb) {
        tb.innerHTML = '';
        procs.forEach(p => {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td class="py-2.5 max-w-[120px] truncate" title="'+p.name+'">'+p.name+'</td>'+
            '<td class="text-right '+(p.cpu>20?'text-primary font-bold':'')+'">'+p.cpu.toFixed(1)+'%</td>'+
            '<td class="text-right">'+p.mem.toFixed(1)+'%</td>';
          tb.appendChild(tr);
        });
      }
    }).catch(function(){});
  }
  setTimeout(refreshProcs, 2000);
  setInterval(refreshProcs, 8000);

  // ── Webcam in Visual Input ────────────────────────────────────────────────
  window.updateWebcam = function(b64) {
    var camObj = document.getElementById('kree-webcam');
    var camOffline = document.getElementById('kree-cam-offline');
    if(camObj) {
      if(b64) {
         camObj.src = b64;
         camObj.style.display = 'block';
         if(camOffline) camOffline.style.display = 'none';
      } else {
         camObj.style.display = 'none';
         if(camOffline) camOffline.style.display = 'flex';
      }
    }
  };

  window.restoreHistory = function() {
      if(window.__KREE_HISTORY__ && window.appendTranscript) {
          window.__KREE_HISTORY__.forEach(function(m){ window.appendTranscript(m.r, m.b); });
          window.__KREE_HISTORY__ = null;
      }
  };

  // ── Button wiring ─────────────────────────────────────────────────────────
  function api(m) {
    var a = Array.prototype.slice.call(arguments,1);
    if (window.pywebview && window.pywebview.api && window.pywebview.api[m])
      return window.pywebview.api[m].apply(null,a);
  }

  function wireUI() {
    // Traffic-light dots in header
    var dots = document.querySelectorAll('header .w-3.h-3.rounded-full');
    var acts = ['close_app','minimize_to_widget','toggle_theme'];
    dots.forEach(function(d,i){
      if(!d.__kw__ && acts[i]){
        d.style.cursor='pointer';
        (function(a){ d.addEventListener('click',function(){ api(a); }); })(acts[i]);
        d.__kw__=true;
      }
    });

    // Icon-named buttons
    var iconMap = {
      'brightness_6':'toggle_theme', 'close':'minimize_to_widget',
      'minimize':'minimize_app', 'crop_square':'maximize_app',
      'mic':'on_mic_click', 'mic_off':'on_mic_click',
      'videocam':'on_cam_click', 'videocam_off':'on_cam_click',
      'call':'on_call_click', 'settings':'open_settings'
    };

    function updateMicUI(res) {
        document.querySelectorAll('button').forEach(function(b) {
            if (b.textContent.trim().includes('LISTEN') || b.textContent.trim().includes('LISTENING')) {
                if(res) {
                    b.innerHTML = '<span class="material-icons-outlined animate-pulse text-red-900">mic</span> LISTENING...';
                    b.classList.add('bg-emerald-300');
                } else {
                    b.innerHTML = '<span class="material-icons-outlined">mic</span> LISTEN';
                    b.classList.remove('bg-emerald-300');
                }
            } else {
                var ic = b.querySelector('.material-icons-outlined');
                if (ic && (ic.textContent==='mic' || ic.textContent==='mic_off')) {
                    ic.textContent = res ? 'mic' : 'mic_off';
                }
            }
        });
    }

    document.querySelectorAll('button').forEach(function(btn) {
      if (btn.__kw__) return;
      if (btn.textContent.trim().includes('LISTEN')) {
        btn.addEventListener('click',function() { 
            var p = api('on_mic_click'); 
            if(p && p.then) p.then(updateMicUI);
        });
        btn.__kw__=true; return;
      }
      var ic = btn.querySelector('.material-icons-outlined,.material-symbols-outlined,.material-icons');
      if (!ic) return;
      var n = ic.textContent.trim();
      if (n === 'send') {
        btn.addEventListener('click', function(){
          var inp = document.querySelector('#kree-input,input[type="text"]');
          if (inp && inp.value.trim()) {
            var t=inp.value.trim();
            window.appendTranscript('user',t);
            api('on_send_message',t);
            inp.value='';
          }
        });
        btn.__kw__=true;
      } else if (iconMap[n]) {
        (function(a, iconNode, nStr){ 
          btn.addEventListener('click',function(e){ 
            e.preventDefault(); 
            var p = api(a); 
            if(p && p.then){
              p.then(function(res){
                if(typeof res === 'boolean'){
                  if(nStr.includes('mic')) updateMicUI(res);
                  else if(nStr.includes('videocam')) iconNode.textContent = res ? 'videocam' : 'videocam_off';
                }
              });
            }
          }); 
        })(iconMap[n], ic, n);
        btn.__kw__=true;
      }
    });

    document.querySelectorAll('.material-icons-outlined').forEach(function(s) {
        if(s.textContent.trim() === 'download') {
            s.addEventListener('click', function() {
                var c = document.getElementById('kree-transcript');
                if(!c) return;
                var text = Array.from(c.querySelectorAll('p')).map(p => p.textContent).join('\\n');
                var blob = new Blob([text], {type: "text/plain"});
                var a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = "kree_transcript.txt";
                a.click();
            });
        }
    });

    // On boot, fetch actual mic state to sync the UI:
    var bootCheck = api('get_mic_state');
    if (bootCheck && bootCheck.then) bootCheck.then(updateMicUI);

    // Ensure history restore is bound
    window.addEventListener('load', window.restoreHistory);
    setTimeout(window.restoreHistory, 100);

    // Enter key
    var inp = document.querySelector('#kree-input,input[type="text"]');
    if (inp && !inp.__kw__) {
      inp.addEventListener('keydown',function(e){
        if(e.key==='Enter'&&this.value.trim()){
          var t=this.value.trim();
          window.appendTranscript('user',t);
          api('on_send_message',t);
          this.value='';
        }
      });
      inp.__kw__=true;
    }
  }

  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',wireUI);
  else wireUI();

  // ── Offline Module Toast Injector ─────────────────────────────────────────
  window.addEventListener('load', function() {
    function showToast(msg) {
      if (document.getElementById('kree-toast')) return;
      var t = document.createElement('div');
      t.id = 'kree-toast';
      t.textContent = msg;
      t.style.cssText = "position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:rgba(239, 68, 68, 0.9);color:white;padding:10px 20px;border-radius:24px;font-family:monospace;font-size:12px;z-index:999999;box-shadow:0 8px 30px rgba(0,0,0,0.5);letter-spacing:0.1em;border:1px solid rgba(255,255,255,0.1);text-transform:uppercase;";
      document.body.appendChild(t);
      setTimeout(function() { t.style.transition='opacity 0.4s'; t.style.opacity='0'; setTimeout(function(){ t.remove(); }, 400); }, 2000);
    }
    document.querySelectorAll('button, .cursor-pointer').forEach(function(b) {
      // Ignore functional buttons and layout shells
      if (b.__kw__ || b.id || b.onclick || !b.textContent.trim() || b.closest('.btn-row') || b.textContent.trim() === 'close') return;
      b.addEventListener('click', function(e) {
         showToast("System Feature Locked: " + b.textContent.trim().substring(0, 15));
      });
    });
  });

})();
"""

_API_KEY_DIALOG_JS = """
(function(){
  if (document.getElementById('kree-setup')) return;
  var ov = document.createElement('div');
  ov.id = 'kree-setup';
  ov.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.88);' +
    'display:flex;align-items:center;justify-content:center;';
  ov.innerHTML = '<div style="background:#121214;border:1px solid #27272a;border-radius:16px;' +
    'padding:32px 40px;max-width:400px;width:90%;text-align:center;">' +
    '<div style="color:#00DC82;font-size:14px;font-weight:700;letter-spacing:.15em;' +
    'margin-bottom:8px;">\\u25c8 INITIALISATION REQUIRED</div>' +
    '<div style="color:#666;font-size:12px;margin-bottom:24px;">Enter your Gemini API key.</div>' +
    '<input id="k-inp" type="password" placeholder="AIza..." ' +
    'style="width:100%;padding:10px 14px;background:#0a0a0a;border:1px solid #333;' +
    'border-radius:8px;color:#ccc;font-family:monospace;font-size:13px;outline:none;' +
    'margin-bottom:16px;box-sizing:border-box;" />' +
    '<button id="k-btn" style="width:100%;padding:10px;background:#00DC82;color:#000;' +
    'font-weight:700;font-size:13px;border:none;border-radius:8px;cursor:pointer;">' +
    '\\u25b8 INITIALISE SYSTEMS</button></div>';
  document.body.appendChild(ov);
  document.getElementById('k-btn').addEventListener('click', function(){
    var key = document.getElementById('k-inp').value.trim();
    if (!key) return;
    window.pywebview && window.pywebview.api && window.pywebview.api.save_api_key(key);
    ov.remove();
  });
})();
"""


# ── JS APIs ───────────────────────────────────────────────────────────────────
class _DashboardAPI:
    def __init__(self, owner):
        self._owner = owner

    def toggle_theme(self):
        try:
            threading.Timer(0.05, self._owner._toggle_theme).start()
        except Exception:
            pass
        return "ok"

    def minimize_app(self):
        if self._owner._main_win:
            self._owner._main_win.minimize()
        return "ok"

    def maximize_app(self):
        if self._owner._main_win:
            self._owner._main_win.toggle_fullscreen()
        return "ok"

    def minimize_to_widget(self):
        threading.Timer(0.05, self._owner._minimize_to_widget).start()
        return "ok"

    def restore_from_widget(self):
        threading.Timer(0.05, self._owner._restore_from_widget).start()
        return "ok"

    def on_mic_click(self):
        self._owner._mic_active = not self._owner._mic_active
        return self._owner._mic_active

    def get_mic_state(self):
        return self._owner._mic_active

    def on_cam_click(self):
        self._owner._cam_active = not self._owner._cam_active
        return self._owner._cam_active

    def on_call_click(self):
        return "ok"

    def on_send_message(self, text: str):
        print(f"[UI] JS triggered on_send_message with text: {text}")
        if text and self._owner.on_user_text:
            print(f"[UI] Found callback, starting thread...")
            threading.Thread(target=self._owner.on_user_text,
                             args=(text,), daemon=True).start()
        else:
            print(f"[UI] ERROR: missing callback! text='{text}', cb={self._owner.on_user_text}")
        return "ok"

    def get_cpu(self):
        try:
            return str(psutil.cpu_percent(interval=0))
        except Exception:
            return "0"

    def get_ram(self):
        try:
            return str(psutil.virtual_memory().percent)
        except Exception:
            return "0"

    def get_processes(self):
        return getattr(self._owner, "cached_procs", "[]")

    def close_app(self):
        threading.Timer(0.05, lambda: os._exit(0)).start()
        return "ok"

    def save_api_key(self, key: str):
        self._owner._save_api_key(key)
        return "ok"

    def open_settings(self):
        try:
            self._owner._eval(SETTINGS_MODAL_JS)
        except Exception:
            pass
        return "ok"

    def is_pin_setup_required(self):
        import core.vault as vault # type: ignore[import]
        return not vault.is_master_pin_set()
        
    def setup_master_pin(self, pin: str):
        import core.vault as vault # type: ignore[import]
        vault.setup_master_pin(pin)
        return True
        
    def verify_master_pin(self, pin: str):
        import core.vault as vault # type: ignore[import]
        return vault.verify_master_pin(pin)
        
    def trigger_biometrics(self):
        # Allow Windows Hello as fallback if configured or active
        import core.biometrics as bio # type: ignore[import]
        return bio.prompt_windows_hello("Unlock Kree Aegis Matrix")


class _WidgetAPI:
    def __init__(self, owner):
        self._owner = owner

    def restore_from_widget(self):
        self._owner._restore_from_widget()
        return "ok"

    def on_mic_click(self):
        self._owner._mic_active = not self._owner._mic_active
        return self._owner._mic_active

    def on_cam_click(self):
        self._owner._cam_active = not self._owner._cam_active
        return self._owner._cam_active

    def on_call_click(self):
        return "ok"


# ── Main UI class ─────────────────────────────────────────────────────────────
class KreeUI:
    """
    Pywebview-based Kree Dashboard.
    Same public interface as old JarvisUI:
        write_log(text), start_speaking(), stop_speaking(), wait_for_api_key()
    """

    def __init__(self, face_path=None, size=None):
        self.speaking         = False
        self.status_text      = "INITIALISING"
        self._mic_active      = True
        self._cam_active      = False
        self._dark_mode       = True
        self._on_user_text_cb = None
        self._main_win        = None
        self._widget_win      = None
        self._api_key_ready   = self._api_keys_exist()
        self.cached_procs     = "[]"
        self.chat_history     = []
        self._api             = _DashboardAPI(self)

    # ── Public API ────────────────────────────────────────────────────────────
    def write_log(self, text: str):
        if self._main_win is None:
            return
        tl = text.lower()
        if tl.startswith("you:"):
            role, body = "user", text[4:].strip()  # type: ignore[index]
        elif tl.startswith(("jarvis:", "kree:", "ai:", "sys:")):
            colon = text.index(":")
            role, body = "ai", text[colon + 1:].strip()  # type: ignore[index]
        else:
            role, body = "ai", text.strip()

        safe = body.replace("\\", "\\\\").replace("`", "\\`") \
                   .replace("${", "\\${").replace("\n", " ").replace("'", "\\'")
        try:
            self.chat_history.append({"role": role, "body": safe})
            if self._main_win is not None:
                self._main_win.evaluate_js(  # type: ignore[union-attr]
                    f"if(typeof appendTranscript==='function')"
                    f"appendTranscript('{role}',`{safe}`);"
                )
        except Exception:
            pass

    @property
    def on_user_text(self):
        return self._on_user_text_cb

    @on_user_text.setter
    def on_user_text(self, cb):
        self._on_user_text_cb = cb

    def start_speaking(self):
        self.speaking    = True
        self.status_text = "SPEAKING"
        self._eval("if(typeof setSpeaking==='function')setSpeaking(true);")

    def stop_speaking(self):
        self.speaking    = False
        self.status_text = "ONLINE"
        self._eval("if(typeof setSpeaking==='function')setSpeaking(false);")

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    # ── Internals ─────────────────────────────────────────────────────────────
    def _api_keys_exist(self):
        import core.vault as vault # type: ignore[import]
        return bool(vault.load_api_key(API_FILE))

    def _eval(self, js: str):
        try:
            if self._main_win:
                self._main_win.evaluate_js(js)  # type: ignore[union-attr]
        except Exception:
            pass

    def _save_api_key(self, key: str):
        if not key:
            return
        import core.vault as vault # type: ignore[import]
        vault.save_api_key(API_FILE, key)
        self._api_key_ready = True
        self.write_log("SYS: Kree is online.")

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        html = _DARK_HTML if self._dark_mode else _LIGHT_HTML
        if self._main_win:
            try:
                self._main_win.load_url(html.as_uri())  # type: ignore[union-attr]
                threading.Timer(1.2, self._inject_bridge).start()
            except Exception:
                pass

    def _minimize_to_widget(self):
        if self._widget_win is None:
            self._widget_win = webview.create_window(
                "",
                url=_WIDGET_HTML.as_uri(),
                width=340,
                height=60,
                resizable=False,
                frameless=True,
                easy_drag=True,
                background_color='#0e0e10',
                on_top=True,
                js_api=_WidgetAPI(self)
            )
        if self._main_win:
            self._main_win.hide()  # type: ignore[union-attr]
        if self._widget_win:
            self._widget_win.show()  # type: ignore[union-attr]

    def _restore_from_widget(self):
        if self._widget_win:
            self._widget_win.hide()  # type: ignore[union-attr]
        if self._main_win:
            self._main_win.show()  # type: ignore[union-attr]

    def _inject_bridge(self):
        try:
            self._main_win.evaluate_js(_BRIDGE_JS)  # type: ignore[union-attr]
        except Exception:
            pass

    def _inject_api_key_dialog(self):
        try:
            self._main_win.evaluate_js(_API_KEY_DIALOG_JS)  # type: ignore[union-attr]
        except Exception:
            pass

    def _inject_lock_screen(self):
        if not LOCK_SCREEN_JS: return
        try:
            self._main_win.evaluate_js(LOCK_SCREEN_JS) # type: ignore[union-attr]
        except Exception:
            pass

    def _metrics_loop(self):
        """Background metrics update — runs in a daemon thread, never blocks UI."""
        try:
            psutil.cpu_percent(interval=0)   # baseline
        except Exception:
            pass
        time.sleep(3)
        while True:
            time.sleep(8)  # less frequent = less CPU pressure
            try:
                cpu = psutil.cpu_percent(interval=0)
                ram = psutil.virtual_memory().percent
                
                procs = []
                for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                    try:
                        procs.append({
                            'name': (p.info['name'] or '?')[:22],
                            'cpu':  round(p.info['cpu_percent'] or 0, 1),
                            'mem':  round(p.info['memory_percent'] or 0, 1),
                        })
                    except Exception:
                        pass
                procs.sort(key=lambda x: x['cpu'], reverse=True)
                self.cached_procs = json.dumps(procs[:6])  # type: ignore[index]

                if self._main_win is not None:
                    self._eval(
                        f"if(typeof updateMetrics==='function')"
                        f"updateMetrics({cpu},{ram});"
                    )
            except Exception:
                pass

    def _on_started(self):
        """Runs inside webview GUI thread after start()."""
        def _init_delayed():
            # Inject the lock screen immediately over the UI while it's loading
            self._inject_lock_screen()
            time.sleep(1.2)
            self._inject_bridge()
            
            # Pass chat history as a JSON object into the window scope safely
            import json
            try:
                hist_raw = [{"r": m["role"], "b": m["body"]} for m in self.chat_history]
                hist_json = json.dumps(hist_raw).replace("'", "\\'")
                self._eval(f"window.__KREE_HISTORY__ = JSON.parse('{hist_json}'); if(typeof restoreHistory==='function') restoreHistory();")
            except Exception:
                pass

            if not self._api_key_ready:
                # Wait for lock screen to clear or just layer it under
                self._inject_api_key_dialog()
            threading.Thread(target=self._metrics_loop, daemon=True).start()

        threading.Thread(target=_init_delayed, daemon=True).start()

    def run(self):
        """Start the webview event loop (blocks calling thread)."""
        html = _DARK_HTML if self._dark_mode else _LIGHT_HTML
        self._main_win = webview.create_window(
            "Kree",
            url=html.as_uri(),
            width=1200,
            height=820,
            resizable=True,
            frameless=True,
            easy_drag=True,
            shadow=True,
            transparent=True,
            js_api=self._api,
        )
        webview.start(self._on_started, debug=False)


# Backward-compatible alias
JarvisUI = KreeUI