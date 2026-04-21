"""
Kree Dashboard UI — pywebview-based (v3, stable)
"""

import os, sys, json, time, threading, psutil, ctypes, platform  # type: ignore[import]
from pathlib import Path
from ctypes import wintypes

import webview  # type: ignore[import]
from memory.config_manager import (  # type: ignore[import]
    load_audio_settings as cfg_load_audio_settings,
    save_audio_settings as cfg_save_audio_settings,
)
from core.auth_ui import AUTH_FLOW_JS  # type: ignore[import]
from core.version import APP_VERSION  # type: ignore[import]

# ── Paths ────────────────────────────────────────────────────────────────────
# ── Paths ────────────────────────────────────────────────────────────────────
def get_base_dir():
    # If frozen (PyInstaller), use the temp _MEIPASS folder for resources
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) 
    # Otherwise use current source directory
    return Path(__file__).resolve().parent

BASE_DIR   = get_base_dir()

# Persist config (API keys) in the same folder as the .exe, not the temp folder
def get_exe_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

EXE_DIR = get_exe_dir()
CONFIG_DIR = EXE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

# _STITCH assets are bundled inside the app
if getattr(sys, "frozen", False):
    # In bundle, stitch is at root
    _STITCH = BASE_DIR / "stitch_core_system_dashboard"
else:
    # In dev, stitch is a peer to the project folder
    _STITCH = BASE_DIR.parent / "stitch_core_system_dashboard" / "stitch_core_system_dashboard"

_LIGHT_HTML  = _STITCH / "core_system_dashboard_1" / "code.html"
_DARK_HTML   = _STITCH / "core_system_dashboard_2" / "code.html"
_WIDGET_HTML = _STITCH / "minimized_control_widget" / "code.html"

_BOOT_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Kree AI</title>
    <style>
        html, body {
            margin: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: radial-gradient(circle at 50% 35%, #0f172a 0%, #05070d 60%, #02030a 100%);
            color: #d1d5db;
            font-family: Segoe UI, Arial, sans-serif;
        }
        .wrap {
            width: 100%;
            height: 100%;
            display: grid;
            place-items: center;
        }
        .card {
            text-align: center;
            padding: 24px 28px;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 14px;
            background: rgba(8, 12, 22, .55);
            box-shadow: 0 12px 40px rgba(0,0,0,.35);
            min-width: 300px;
        }
        .dot {
            width: 10px;
            height: 10px;
            margin: 0 auto 10px;
            border-radius: 999px;
            background: #00dc82;
            box-shadow: 0 0 14px rgba(0,220,130,.7);
            animation: pulse 1.15s ease-in-out infinite;
        }
        .title {
            font-weight: 700;
            font-size: 14px;
            letter-spacing: .18em;
            text-transform: uppercase;
            color: #00dc82;
        }
        .sub {
            margin-top: 8px;
            font-size: 12px;
            letter-spacing: .08em;
            color: #94a3b8;
            text-transform: uppercase;
        }
        @keyframes pulse {
            0%,100% { transform: scale(1); opacity: .75; }
            50% { transform: scale(1.3); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"card\">
            <div class=\"dot\"></div>
            <div class=\"title\">Kree AI</div>
            <div class=\"sub\">Initializing Core Systems</div>
        </div>
    </div>
</body>
</html>
"""

try:
    from core.security_ui import LOCK_SCREEN_JS, SETTINGS_MODAL_JS # type: ignore[import]
except ImportError:
    LOCK_SCREEN_JS = ""
    SETTINGS_MODAL_JS = ""

try:
    from core.update_service import (  # type: ignore[import]
        apply_update as update_apply_update,
        check_for_updates as update_check_for_updates,
        download_update as update_download_update,
        get_update_state as update_get_state,
        open_update_folder as update_open_folder,
        save_update_settings as update_save_settings,
    )
except ImportError:
    update_apply_update = None
    update_check_for_updates = None
    update_download_update = None
    update_get_state = None
    update_open_folder = None
    update_save_settings = None

try:
    from core.api_setup_ui import API_SETUP_JS # type: ignore[import]
except ImportError:
    API_SETUP_JS = ""

AUTO_UPDATE_POPUP_JS = """
setTimeout(() => {
    window.pywebview.api.check_for_updates().then((res) => {
        if(res && res.update_available) {
            const modDiv = document.createElement('div');
            modDiv.id = 'kree-auto-update-modal';
            modDiv.innerHTML = `
                <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" id="auto-update-bg">
                    <div class="bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 relative transform transition-all">
                        <div class="flex items-center space-x-3 mb-4">
                            <i class="material-icons text-[#00DC82] text-3xl">system_update</i>
                            <h2 class="text-xl font-bold text-white tracking-wide">Update Available</h2>
                        </div>
                        <p class="text-zinc-400 text-sm mb-5 leading-relaxed">
                            A new version of Kree AI (v${res.latest_version}) is available. Do you want to download and install it now?
                        </p>
                        <div class="bg-black/30 rounded-lg p-3 mb-6 text-xs text-zinc-500 font-mono border border-black/50">
                            Current: ${res.installed_version} &rarr; Latest: ${res.latest_version}
                        </div>
                        <div class="flex justify-end space-x-3 mt-6">
                            <button id="btn-update-later" class="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded-lg transition-colors font-medium">
                                Later
                            </button>
                            <button id="btn-update-now" class="px-5 py-2 bg-[#00DC82] hover:bg-[#00c978] text-black text-sm rounded-lg transition-colors font-bold shadow-lg shadow-[#00DC82]/20">
                                Download Now
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modDiv);

            document.getElementById('btn-update-later').onclick = () => {
                modDiv.remove();
            };
            
            const btnNow = document.getElementById('btn-update-now');
            btnNow.onclick = () => {
                btnNow.textContent = "Downloading...";
                btnNow.disabled = true;
                btnNow.classList.replace('bg-[#00DC82]', 'bg-zinc-700');
                btnNow.classList.remove('text-black');
                btnNow.classList.add('text-zinc-400', 'cursor-not-allowed', 'shadow-none');
                
                window.pywebview.api.download_update().then((dlRes) => {
                    if(dlRes && dlRes.status && dlRes.status.includes('downloaded')) {
                        btnNow.textContent = "Restart to Apply";
                        btnNow.classList.replace('bg-zinc-700', 'bg-[#00DC82]');
                        btnNow.classList.remove('text-zinc-400', 'cursor-not-allowed');
                        btnNow.classList.add('text-black', 'shadow-lg');
                        btnNow.disabled = false;
                        btnNow.onclick = () => {
                            window.pywebview.api.apply_update();
                        };
                    } else {
                        btnNow.textContent = "Download Failed";
                        setTimeout(() => modDiv.remove(), 2000);
                    }
                });
            };
        }
    });
}, 3000);
"""

SYSTEM_NAME = "Kree"
MAX_CHAT_HISTORY = 220
MAX_TRANSCRIPT_NODES = 180


# ── Bridge JS injected after every page load ──────────────────────────────────
_BRIDGE_JS = """
(function(){
  if (window.__kree_bridge_installed__) return;
  window.__kree_bridge_installed__ = true;

    function kreeScriptFont(text) {
        var t = String(text || '');
        // Sinhala block: U+0D80-U+0DFF
        if (/[\u0D80-\u0DFF]/.test(t)) {
            return '"Noto Sans Sinhala","Iskoola Pota","Nirmala UI","Segoe UI",sans-serif';
        }
        // Tamil block: U+0B80-U+0BFF
        if (/[\u0B80-\u0BFF]/.test(t)) {
            return '"Noto Sans Tamil","Latha","Nirmala UI","Segoe UI",sans-serif';
        }
        // Gujarati block: U+0A80-U+0AFF
        if (/[\u0A80-\u0AFF]/.test(t)) {
            return '"Noto Sans Gujarati","Shruti","Nirmala UI","Segoe UI",sans-serif';
        }
        // Devanagari block: U+0900-U+097F
        if (/[\u0900-\u097F]/.test(t)) {
            return '"Noto Sans Devanagari","Mangal","Nirmala UI","Segoe UI",sans-serif';
        }
        return '"Segoe UI","Nirmala UI",sans-serif';
    }

  // ── Fade-in animation for transcript ─────────────────────────────────────
  var _style = document.createElement('style');
    _style.textContent = '@keyframes kFadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}' +
        '@keyframes kreeSpin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}' +
        '@keyframes kreePulse{0%,100%{opacity:.65}50%{opacity:1}}';
  document.head && document.head.appendChild(_style);

    // ── Stitch-style Action Overlay + Logs ───────────────────────────────────
    function ensureActionOverlay() {
        var ov = document.getElementById('kree-action-overlay');
        if (ov) return ov;

        ov = document.createElement('div');
        ov.id = 'kree-action-overlay';
        ov.style.cssText = 'position:fixed;inset:0;z-index:999998;display:none;align-items:center;justify-content:center;padding:20px;background:radial-gradient(circle at 50% 50%,rgba(0,220,130,.08),transparent 55%);pointer-events:none;';

        ov.innerHTML =
            '<div style="width:min(460px,92vw);border:1px solid rgba(255,255,255,.1);border-radius:16px;overflow:hidden;background:rgba(8,10,16,.92);box-shadow:0 16px 60px rgba(0,0,0,.5);backdrop-filter:blur(8px);">' +
            '  <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.08);">' +
            '    <div style="width:16px;height:16px;border-radius:50%;border:2px solid rgba(0,220,130,.28);border-top-color:#00dc82;animation:kreeSpin .9s linear infinite;"></div>' +
            '    <div style="font:700 11px/1 monospace;letter-spacing:.16em;color:#00dc82;text-transform:uppercase;">Kree Action Running</div>' +
            '    <div id="kree-action-state" style="margin-left:auto;font:600 10px/1 monospace;letter-spacing:.12em;color:#a1a1aa;text-transform:uppercase;animation:kreePulse 1.6s ease-in-out infinite;">in progress</div>' +
            '  </div>' +
            '  <div style="padding:12px 14px 10px;">' +
            '    <div style="display:grid;grid-template-columns:88px 1fr;gap:6px 10px;font:11px/1.45 monospace;color:#e4e4e7;">' +
            '      <div style="color:#71717a;text-transform:uppercase;letter-spacing:.08em;">tool</div><div id="kree-action-tool">-</div>' +
            '      <div style="color:#71717a;text-transform:uppercase;letter-spacing:.08em;">app</div><div id="kree-action-app">-</div>' +
            '      <div style="color:#71717a;text-transform:uppercase;letter-spacing:.08em;">command</div><div id="kree-action-cmd" style="word-break:break-word;">-</div>' +
            '    </div>' +
            '    <div style="margin-top:10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(3,5,10,.75);">' +
            '      <div style="padding:7px 10px;border-bottom:1px solid rgba(255,255,255,.06);font:700 10px/1 monospace;letter-spacing:.13em;color:#a1a1aa;text-transform:uppercase;">Live Logs</div>' +
            '      <div id="kree-action-loglist" style="max-height:142px;overflow:auto;padding:8px 10px;display:flex;flex-direction:column;gap:6px;"></div>' +
            '    </div>' +
            '  </div>' +
            '</div>';

        document.body.appendChild(ov);
        return ov;
    }

    window.setActionLoading = function(on, toolName, appName, cmdText) {
        var ov = ensureActionOverlay();
        if (!ov) return;
        if (on) {
            ov.style.display = 'flex';
            var t = document.getElementById('kree-action-tool');
            var a = document.getElementById('kree-action-app');
            var c = document.getElementById('kree-action-cmd');
            var s = document.getElementById('kree-action-state');
            var logs = document.getElementById('kree-action-loglist');
            if (t) t.textContent = toolName || '-';
            if (a) a.textContent = appName || '-';
            if (c) c.textContent = cmdText || '-';
            if (s) s.textContent = 'in progress';
            if (logs) logs.innerHTML = '';
        } else {
            var s2 = document.getElementById('kree-action-state');
            if (s2) s2.textContent = 'completed';
            setTimeout(function(){ ov.style.display = 'none'; }, 700);
        }
    };

    window.pushActionLog = function(line) {
        var ov = ensureActionOverlay();
        if (!ov) return;
        var logs = document.getElementById('kree-action-loglist');
        if (!logs) return;
        var row = document.createElement('div');
        var now = new Date();
        row.style.cssText = 'font:11px/1.35 monospace;color:#d4d4d8;word-break:break-word;';
        row.textContent = '[' + String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0') + ':' + String(now.getSeconds()).padStart(2,'0') + '] ' + (line || '');
        logs.appendChild(row);
        while (logs.children.length > 30) logs.removeChild(logs.firstChild);
        logs.scrollTop = logs.scrollHeight;
    };

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
    var msgFont = kreeScriptFont(text);
    p.style.cssText = 'margin:0;line-height:1.62;font-family:' + msgFont + ';font-kerning:normal;text-rendering:optimizeLegibility;';
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
        while (c.children.length > 180) {
            c.removeChild(c.firstChild);
        }
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
    setInterval(refreshProcs, 15000);

    // ── Webcam in Visual Input (native smooth stream) ───────────────────────
    window.__kreeCamStream__ = null;

    function updateCameraButtons(active) {
        document.querySelectorAll('button').forEach(function(b){
            var ic = b.querySelector('.material-icons-outlined,.material-symbols-outlined,.material-icons');
            if (!ic) return;
            var txt = (ic.textContent || '').trim();
            if (txt === 'videocam' || txt === 'videocam_off') {
                ic.textContent = active ? 'videocam' : 'videocam_off';
                if (active) {
                    b.classList.add('bg-emerald-500/15', 'text-emerald-300', 'shadow-[0_0_14px_rgba(16,185,129,.35)]');
                    ic.classList.add('animate-pulse');
                } else {
                    b.classList.remove('bg-emerald-500/15', 'text-emerald-300', 'shadow-[0_0_14px_rgba(16,185,129,.35)]');
                    ic.classList.remove('animate-pulse');
                }
            }
        });
    }

    function waitForVideoFrame(videoEl, timeoutMs) {
        return new Promise(function(resolve){
            var done = false;
            function finish(ok) {
                if (done) return;
                done = true;
                resolve(ok);
            }

            var timer = setTimeout(function(){ finish(false); }, timeoutMs);
            function clear(ok) {
                clearTimeout(timer);
                finish(ok);
            }

            if (!videoEl) {
                clear(false);
                return;
            }

            if (videoEl.readyState >= 2 && videoEl.videoWidth > 0 && videoEl.videoHeight > 0) {
                clear(true);
                return;
            }

            videoEl.onloadeddata = function(){
                clear(videoEl.videoWidth > 0 && videoEl.videoHeight > 0);
            };
            videoEl.onplaying = function(){
                clear(videoEl.videoWidth > 0 && videoEl.videoHeight > 0);
            };
        });
    }

    async function startLocalCamera() {
        var camObj = document.getElementById('kree-webcam');
        var camOffline = document.getElementById('kree-cam-offline');
        if (!camObj || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            if (camOffline) camOffline.style.display = 'flex';
            return false;
        }
        if (window.__kreeCamStream__) {
            camObj.srcObject = window.__kreeCamStream__;
            camObj.style.display = 'block';
            if (camOffline) camOffline.style.display = 'none';
            return true;
        }
        try {
            var stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30, max: 30 } },
                audio: false
            });
            window.__kreeCamStream__ = stream;
            camObj.srcObject = stream;
            camObj.style.display = 'block';
            if (camOffline) camOffline.style.display = 'none';
            if (camObj.play) {
                try { await camObj.play(); } catch (e) {}
            }

            var hasFrame = await waitForVideoFrame(camObj, 1200);
            if (!hasFrame) {
                try { stream.getTracks().forEach(function(t){ t.stop(); }); } catch (e) {}
                window.__kreeCamStream__ = null;
                camObj.srcObject = null;
                camObj.style.display = 'none';
                if (camOffline) camOffline.style.display = 'flex';
                return false;
            }

            return true;
        } catch (e) {
            if (camOffline) camOffline.style.display = 'flex';
            camObj.style.display = 'none';
            return false;
        }
    }

    function stopLocalCamera() {
        var camObj = document.getElementById('kree-webcam');
        var camOffline = document.getElementById('kree-cam-offline');
        if (window.__kreeCamStream__) {
            window.__kreeCamStream__.getTracks().forEach(function(t){ t.stop(); });
            window.__kreeCamStream__ = null;
        }
        if (camObj) {
            camObj.pause && camObj.pause();
            camObj.srcObject = null;
            camObj.style.display = 'none';
        }
        var camImg = document.getElementById('kree-webcam-img');
        if (camImg) {
            camImg.style.display = 'none';
            camImg.removeAttribute('src');
        }
        if (camOffline) camOffline.style.display = 'flex';
    }

    // Backend fallback (JPEG frame updates) when local stream is unavailable.
    window.updateWebcam = function(b64) {
        var camObj = document.getElementById('kree-webcam');
        var camOffline = document.getElementById('kree-cam-offline');
        if (!camObj) return;

        // Never let backend JPEG fallback override a healthy local camera stream.
        if (window.__kreeCamStream__) {
            if (b64) return;
            if (camOffline) camOffline.style.display = 'none';
            camObj.style.display = 'block';
            return;
        }

        var camImg = document.getElementById('kree-webcam-img');
        if (!camImg) {
            camImg = document.createElement('img');
            camImg.id = 'kree-webcam-img';
            camImg.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none;';
            if (camObj.parentElement) camObj.parentElement.appendChild(camImg);
        }

        if (b64) {
            camObj.style.display = 'none';
            camImg.src = b64;
            camImg.style.display = 'block';
            if (camOffline) camOffline.style.display = 'none';
        } else if (!window.__kreeCamStream__) {
            camImg.style.display = 'none';
            camImg.removeAttribute('src');
            if (camOffline) camOffline.style.display = 'flex';
        }
    };

    window.setCameraState = async function(active) {
        var ok = false;
        if (active) ok = await startLocalCamera();
        else stopLocalCamera();
        if (window.pywebview && window.pywebview.api && window.pywebview.api.set_local_camera_ready) {
            window.pywebview.api.set_local_camera_ready(active ? !!ok : false);
        }
        updateCameraButtons(active && ok);
    };

  window.restoreHistory = function() {
      if(window.__KREE_HISTORY__ && window.appendTranscript) {
          var tContainer = document.getElementById('kree-transcript');
          if (tContainer) tContainer.innerHTML = '';
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
            'minimize':'minimize_app', 'remove':'minimize_app', 'crop_square':'maximize_app',
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
                                    else if(nStr.includes('videocam')) window.setCameraState(!!res);
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

        var camBootCheck = api('get_cam_state');
        if (camBootCheck && camBootCheck.then) {
            camBootCheck.then(function(active){ window.setCameraState(!!active); });
        }

    // Ensure history restore is bound
    window.addEventListener('load', window.restoreHistory);
    setTimeout(window.restoreHistory, 100);

    // Enter key
    var inp = document.querySelector('#kree-input,input[type="text"]');
    if (inp && !inp.__kw__) {
      inp.addEventListener('keydown',function(e){
        if(e.key==='Enter'&&this.value.trim()){
          var t=this.value.trim();
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
    function showToast(msg, bg) {
      if (document.getElementById('kree-toast')) return;
      var t = document.createElement('div');
      t.id = 'kree-toast';
      t.textContent = msg;
      var color = bg || "rgba(239, 68, 68, 0.9)";
      t.style.cssText = "position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:" + color + ";color:white;padding:10px 20px;border-radius:24px;font-family:monospace;font-size:12px;z-index:999999;box-shadow:0 8px 30px rgba(0,0,0,0.5);letter-spacing:0.1em;border:1px solid rgba(255,255,255,0.1);text-transform:uppercase;";
      document.body.appendChild(t);
      setTimeout(function() { t.style.transition='opacity 0.4s'; t.style.opacity='0'; setTimeout(function(){ t.remove(); }, 400); }, 3000);
    }
    window.showToast = showToast; // Expose to global scope
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

    def send_text(self, text: str):
        if callable(self._owner._on_user_text_cb):
            self._owner._on_user_text_cb(text)
        return "ok"

    def get_auth_state(self):
        from core.auth_manager import AuthManager
        api_ready = getattr(self._owner, '_api_key_ready', False)
        users = AuthManager.get_user_count()
        return {
            "hasUsers": users > 0,
            "hasActiveUser": bool(getattr(self._owner, '_active_user', None)),
            "apiReady": api_ready 
        }

    def create_user(self, handle, password, email="", name=""):
        from core.auth_manager import AuthManager
        try:
            return AuthManager.create_user(handle, password, email, name)
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def sign_in_user(self, handle, password):
        from core.auth_manager import AuthManager
        import os
        res = AuthManager.sign_in_user(handle, password)
        if res.get("ok"):
            self._owner._temp_password = password
            self._owner._active_user = res["user"]
            ak = AuthManager.get_user_api_key(res["user"]["user_id"], password)
            if ak: os.environ["KREE_ACTIVE_API_KEY"] = ak
        return res

    def set_user_pin(self, user_id, pin):
        from core.auth_manager import AuthManager
        return AuthManager.set_user_pin(user_id, pin)

    def verify_user_pin(self, user_id, pin):
        from core.auth_manager import AuthManager
        return AuthManager.verify_user_pin(user_id, pin)

    def save_user_api_key(self, user_id, key):
        from core.auth_manager import AuthManager
        import os
        pwd = getattr(self._owner, '_temp_password', "")
        res = AuthManager.save_user_api_key(user_id, key, pwd)
        if res.get("ok"):
            os.environ["KREE_ACTIVE_API_KEY"] = key
        if hasattr(self._owner, '_temp_password'):
            delattr(self._owner, '_temp_password')
        return res
        
    def on_auth_flow_complete(self):
        from core.auth_manager import AuthManager
        user = getattr(self._owner, '_active_user', None)
        if user:
            AuthManager.mark_login_complete(user["user_id"])
            if hasattr(self._owner, '_on_api_setup_complete'):
                self._owner._on_api_setup_complete()
            self._owner._auth_injected = True
            
            import os, json
            auth_ok_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "session_auth.json")
            try:
                os.makedirs(os.path.dirname(auth_ok_file), exist_ok=True)
                with open(auth_ok_file, 'w') as f:
                    json.dump({"user": user, "status": "unlocked"}, f)
            except Exception: pass
        return True

    def verify_session_pin(self, pin):
        """V4: Lightweight mid-session PIN re-verification for sensitive tools."""
        from core.auth_manager import AuthManager
        user = getattr(self._owner, '_active_user', None)
        if not user:
            return {"ok": False, "message": "No active user session."}
        result = AuthManager.verify_user_pin(user.get("user_id", ""), pin)
        if result.get("ok"):
            # Reset session timer on the JarvisLive instance (if connected)
            import time as _time
            # Walk up to find the JarvisLive instance that has the timer
            try:
                from main import JarvisLive
                # The owner is KreeUI, which doesn't have the timer.
                # We write a flag file that JarvisLive polls.
                import os, json
                flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "session_pin_ok.json")
                os.makedirs(os.path.dirname(flag_file), exist_ok=True)
                with open(flag_file, 'w') as f:
                    json.dump({"verified_at": _time.time()}, f)
            except Exception:
                pass
            return {"ok": True, "message": "PIN verified. Session refreshed."}
        return result

    def request_pin_challenge(self):
        """V4: Inject a lightweight PIN-only overlay for session re-verification."""
        js = """
(function(){
  if (document.getElementById('kree-pin-challenge')) return;
  var ov = document.createElement('div');
  ov.id = 'kree-pin-challenge';
  ov.style.cssText = 'position:fixed;inset:0;z-index:999998;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;backdrop-filter:blur(12px);';
  ov.innerHTML = '<div style="background:#0c0e14;border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:32px 36px;max-width:360px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.6);">' +
    '<div style="color:#00DC82;font-size:11px;font-weight:700;letter-spacing:.2em;margin-bottom:6px;text-transform:uppercase;">Session Verification</div>' +
    '<div style="color:#71717a;font-size:11px;margin-bottom:20px;">Confirm your PIN to continue</div>' +
    '<input id="challenge-pin" type="password" inputmode="numeric" maxlength="6" placeholder="000000" style="width:100%;padding:14px;background:#050709;border:1px solid rgba(255,255,255,.1);border-radius:12px;color:#fff;font-family:monospace;font-size:18px;letter-spacing:.4em;text-align:center;outline:none;box-sizing:border-box;" />' +
    '<div id="challenge-msg" style="margin-top:10px;font-size:10px;color:#71717a;min-height:16px;"></div>' +
    '<button id="challenge-btn" style="width:100%;margin-top:14px;padding:12px;background:#00DC82;color:#000;font-weight:700;font-size:12px;letter-spacing:.18em;border:none;border-radius:12px;cursor:pointer;text-transform:uppercase;">Verify PIN</button>' +
    '</div>';
  document.body.appendChild(ov);
  document.getElementById('challenge-btn').addEventListener('click', function(){
    var pin = document.getElementById('challenge-pin').value.trim();
    if (!pin || pin.length !== 6) { document.getElementById('challenge-msg').textContent = 'Enter your 6-digit PIN'; document.getElementById('challenge-msg').style.color = '#f87171'; return; }
    document.getElementById('challenge-msg').textContent = 'Verifying...';
    document.getElementById('challenge-msg').style.color = '#71717a';
    window.pywebview.api.verify_session_pin(pin).then(function(r){
      if (r && r.ok) { ov.style.transition='opacity .3s'; ov.style.opacity='0'; setTimeout(function(){ ov.remove(); }, 350); }
      else { document.getElementById('challenge-msg').textContent = (r && r.message) || 'Invalid PIN'; document.getElementById('challenge-msg').style.color = '#f87171'; }
    });
  });
  document.getElementById('challenge-pin').addEventListener('keydown', function(e){ if(e.key==='Enter') document.getElementById('challenge-btn').click(); });
  setTimeout(function(){ document.getElementById('challenge-pin').focus(); }, 100);
})();
""";
        try:
            self._owner._main_win.evaluate_js(js)
        except Exception:
            pass
        return "ok"

    def toggle_theme(self):
        try:
            threading.Timer(0.05, self._owner._toggle_theme).start()
        except Exception:
            pass
        return "ok"

    def get_pwa_url(self):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return f"http://{ip}:8765"
        except Exception:
            return "http://127.0.0.1:8765"

    def get_system_processes(self):
        """Return top processes by CPU usage for the desktop process monitor."""
        try:
            import psutil
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent']):
                try:
                    info = p.info
                    if info['cpu_percent'] and info['cpu_percent'] > 0:
                        procs.append({'name': info['name'], 'cpu': round(info['cpu_percent'], 1)})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x['cpu'], reverse=True)
            cpu_total = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            return {
                'processes': procs[:30],
                'cpu': round(cpu_total, 1),
                'ram': round(ram.percent, 1)
            }
        except ImportError:
            # psutil not installed — return placeholder
            return {'processes': [{'name': 'psutil not installed', 'cpu': 0}], 'cpu': '--', 'ram': '--'}
        except Exception as e:
            return {'processes': [{'name': f'Error: {e}', 'cpu': 0}], 'cpu': '--', 'ram': '--'}

    def send_mobile_command(self, cmd):
        """Send a command to the connected mobile device via the bridge."""
        try:
            import asyncio
            if hasattr(self._owner, 'mobile_bridge') and hasattr(self._owner, '_loop'):
                asyncio.run_coroutine_threadsafe(
                    self._owner.mobile_bridge.broadcast({'type': 'intent', 'action': 'open_app', 'target': cmd}),
                    self._owner._loop
                )
                return "sent"
        except Exception:
            pass
        return "no_bridge"

    def send_mobile_intent(self, action, target):
        """Send a specific intent (call, sms) to the connected mobile device."""
        try:
            import asyncio
            if hasattr(self._owner, 'mobile_bridge') and hasattr(self._owner, '_loop'):
                payload = {'type': 'intent', 'action': action}
                if action == 'call':
                    payload['number'] = target
                elif action == 'sms':
                    payload['number'] = target
                else:
                    payload['target'] = target
                asyncio.run_coroutine_threadsafe(
                    self._owner.mobile_bridge.broadcast(payload),
                    self._owner._loop
                )
                return "sent"
        except Exception:
            pass
        return "no_bridge"

    def lock_desktop(self):
        """Lock the Windows desktop."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "locked"
        except Exception:
            return "failed"

    def sleep_desktop(self):
        """Put the desktop to sleep."""
        try:
            import subprocess
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
            return "sleeping"
        except Exception:
            return "failed"

    def mute_desktop(self):
        """Toggle mute on Windows."""
        try:
            import ctypes
            WM_APPCOMMAND = 0x0319
            APPCOMMAND_VOLUME_MUTE = 0x80000
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, hwnd, APPCOMMAND_VOLUME_MUTE)
            return "toggled"
        except Exception:
            return "failed"

    def take_screenshot(self):
        """Take a screenshot and save to Desktop/Kree Bridge."""
        try:
            import os
            import mss
            from PIL import Image
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Kree Bridge")
            os.makedirs(desktop_dir, exist_ok=True)
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                from datetime import datetime
                fname = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                fpath = os.path.join(desktop_dir, fname)
                Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX").save(fpath, "PNG")
                return fpath
        except Exception:
            return "failed"

    def get_clipboard(self):
        """Read text from the system clipboard."""
        try:
            import ctypes
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.OpenClipboard(0)
            try:
                if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
                    data = user32.GetClipboardData(CF_UNICODETEXT)
                    text = ctypes.c_wchar_p(data).value
                    return text or ""
                return ""
            finally:
                user32.CloseClipboard()
        except Exception:
            return ""

    def set_clipboard(self, text):
        """Write text to the system clipboard."""
        try:
            import ctypes
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.OpenClipboard(0)
            try:
                user32.EmptyClipboard()
                encoded = text.encode('utf-16-le') + b'\x00\x00'
                h = kernel32.GlobalAlloc(0x0042, len(encoded))
                p = kernel32.GlobalLock(h)
                ctypes.memmove(p, encoded, len(encoded))
                kernel32.GlobalUnlock(h)
                user32.SetClipboardData(CF_UNICODETEXT, h)
            finally:
                user32.CloseClipboard()
            return "set"
        except Exception:
            return "failed"

    def save_bridge_file(self, filename, data_b64):
        """Save a file received from mobile to Desktop/Kree Bridge folder."""
        try:
            import os, base64
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Kree Bridge")
            os.makedirs(desktop_dir, exist_ok=True)
            fpath = os.path.join(desktop_dir, filename)
            with open(fpath, 'wb') as f:
                f.write(base64.b64decode(data_b64))
            return fpath
        except Exception:
            return "failed"

    def open_bridge_folder(self):
        """Open the Desktop/Kree Bridge folder."""
        try:
            import os
            import subprocess
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Kree Bridge")
            os.makedirs(desktop_dir, exist_ok=True)
            if hasattr(os, 'startfile'):
                os.startfile(desktop_dir)
            else:
                subprocess.Popen(['explorer', desktop_dir])
            return "opened"
        except Exception as e:
            return f"failed: {e}"

    def send_file_to_mobile(self, paths):
        """Streams selected files/zip to mobile over WebSocket."""
        try:
            import asyncio
            import os
            import base64
            from mobile_bridge import KreeMobileBridge
            
            def transmission_worker(file_paths):
                if not getattr(self._owner, 'mobile_bridge', None): return
                bridge = self._owner.mobile_bridge
                loop = getattr(self._owner, '_loop', None)
                if not bridge or not loop: return
                
                for path in file_paths:
                    if not os.path.isfile(path): continue
                    
                    filename = os.path.basename(path)
                    filesize = os.path.getsize(path)
                    import time
                    import uuid
                    if filesize < 10 * 1024 * 1024:
                        # Single blob for < 10MB
                        with open(path, 'rb') as f:
                            b64 = base64.b64encode(f.read()).decode('utf-8')
                        asyncio.run_coroutine_threadsafe(
                            bridge.broadcast({
                                'type': 'file_transfer',
                                'direction': 'desktop_to_phone',
                                'action': 'single',
                                'filename': filename,
                                'size': filesize,
                                'data': b64
                            }), loop
                        )
                    else:
                        # Chunked transfer for >= 10MB
                        file_id = str(uuid.uuid4())
                        asyncio.run_coroutine_threadsafe(
                            bridge.broadcast({
                                'type': 'file_transfer',
                                'direction': 'desktop_to_phone',
                                'action': 'start',
                                'fileId': file_id,
                                'filename': filename,
                                'size': filesize
                            }), loop
                        )
                        time.sleep(0.5)
                        
                        chunk_size = 512 * 1024  # 512KB
                        with open(path, 'rb') as f:
                            idx = 0
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk: break
                                b64_data = base64.b64encode(chunk).decode('utf-8')
                                asyncio.run_coroutine_threadsafe(
                                    bridge.broadcast({
                                        'type': 'file_transfer',
                                        'direction': 'desktop_to_phone',
                                        'action': 'chunk',
                                        'fileId': file_id,
                                        'index': idx,
                                        'data': b64_data
                                    }), loop
                                )
                                idx += 1
                                time.sleep(0.1)  # rate limit parsing
                                
                        asyncio.run_coroutine_threadsafe(
                            bridge.broadcast({
                                'type': 'file_transfer',
                                'direction': 'desktop_to_phone',
                                'action': 'complete',
                                'fileId': file_id
                            }), loop
                        )
            
            import threading
            threading.Thread(target=transmission_worker, args=(paths,), daemon=True).start()
            return "started_transmission"
        except Exception as e:
            return f"failed: {e}"

    def choose_file_to_send(self):
        """Prompt to select a file and send it to mobile."""
        import webview
        win = getattr(self._owner, '_main_win', None)
        if win:
            result = win.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
            if result:
                self.send_file_to_mobile(result)
                return "sending"
        return "cancelled"

    def choose_folder_to_send(self):
        """Prompt to select a folder, zip it, and send to mobile."""
        import webview
        win = getattr(self._owner, '_main_win', None)
        if win:
            result = win.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                folder_path = result[0]
                import threading
                def zip_and_send():
                    try:
                        import os
                        import zipfile
                        import tempfile
                        import time
                        
                        folder_name = os.path.basename(folder_path.rstrip('/\\'))
                        if not folder_name: folder_name = "Folder"
                        zip_name = f"{folder_name}.zip"
                        temp_dir = tempfile.gettempdir()
                        zip_path = os.path.join(temp_dir, zip_name)
                        
                        # Tell UI zipping started
                        self._eval("try{ showToast('Zipping folder on Desktop...', '#ffb800'); }catch(e){}")
                        
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, dirs, files in os.walk(folder_path):
                                for file in files:
                                    abs_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(abs_path, folder_path)
                                    zipf.write(abs_path, os.path.join(folder_name, rel_path))
                        
                        # Tell UI streaming
                        self._eval(f"try{{ showToast('Streaming {zip_name} to Mobile!', '#00dc82'); }}catch(e){{}}")
                        self.send_file_to_mobile([zip_path])
                    except Exception as e:
                        print(f"[JARVIS] Failed to zip folder: {e}")
                threading.Thread(target=zip_and_send, daemon=True).start()
                return "zipping"
        return "cancelled"

    # ── PWA Server Control ────────────────────────────────────────────────
    def get_pwa_status(self):
        """Return PWA server status for the Connect tab."""
        try:
            from serve_pwa import get_server_status, get_pwa_url
            status = get_server_status()
            status["url"] = get_pwa_url()
            return json.dumps(status)
        except ImportError:
            return json.dumps({"running": False, "error": "serve_pwa module not available"})
        except Exception as e:
            return json.dumps({"running": False, "error": str(e)})

    def reset_pwa_token(self):
        """Generate a new auth token, invalidating all connected devices."""
        try:
            from serve_pwa import reset_token, get_pwa_url
            new_token = reset_token()
            new_url = get_pwa_url()
            # Push new QR to UI
            try:
                import qrcode
                import io
                import base64
                qr = qrcode.QRCode(version=1, box_size=6, border=2)
                qr.add_data(new_url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="#00DC82", back_color="#0e0e10")
                buf = io.BytesIO()
                qr_img.save(buf, format='PNG')
                qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                self._owner._eval(f'''try{{
                    var qrEl=document.getElementById("kree-connect-qr");
                    if(qrEl){{qrEl.src="data:image/png;base64,{qr_b64}";}}
                    var urlEl=document.getElementById("kree-connect-url");
                    if(urlEl)urlEl.innerText="{new_url}";
                }}catch(e){{}}''')
            except Exception:
                pass
            return json.dumps({"ok": True, "url": new_url})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    def get_connected_devices(self):
        """Return list of currently connected mobile devices."""
        try:
            bridge = getattr(self._owner, 'mobile_bridge', None)
            if not bridge:
                return json.dumps([])
            devices = []
            import time
            for writer in list(bridge.clients):
                try:
                    peer = writer.get_extra_info('peername')
                    devices.append({
                        "ip": peer[0] if peer else "unknown",
                        "port": peer[1] if peer else 0,
                        "last_seen": time.strftime("%H:%M:%S"),
                    })
                except Exception:
                    pass
            return json.dumps(devices)
        except Exception:
            return json.dumps([])

    def lock_desktop(self):
        """Lock the Windows desktop."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "locked"
        except Exception:
            return "failed"

    def sleep_desktop(self):
        """Put the desktop to sleep."""
        try:
            import subprocess
            subprocess.Popen(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0', '1', '0'], shell=True)
            return "sleeping"
        except Exception:
            return "failed"

    def mute_desktop(self):
        """Toggle system mute."""
        try:
            import ctypes
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                current_mute = volume.GetMute()
                volume.SetMute(not current_mute, None)
                return "muted" if not current_mute else "unmuted"
            except ImportError:
                # Fallback: use keyboard simulation
                import subprocess
                subprocess.Popen(['powershell', '-Command', '(New-Object -ComObject WScript.Shell).SendKeys([char]173)'], shell=True)
                return "toggled"
        except Exception:
            return "failed"

    def take_screenshot(self):
        """Take a screenshot and save to Desktop."""
        try:
            import mss
            from PIL import Image
            import os
            from datetime import datetime
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"kree_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(desktop, filename)
            with mss.mss() as sct:
                sct.shot(output=filepath)
            return f"saved:{filepath}"
        except Exception as e:
            return f"failed:{e}"

    def get_clipboard(self):
        """Get current desktop clipboard text."""
        try:
            import subprocess
            result = subprocess.run(['powershell', '-Command', 'Get-Clipboard'], capture_output=True, text=True, timeout=3)
            return result.stdout.strip()
        except Exception:
            return ""

    def set_clipboard(self, text):
        """Set desktop clipboard text."""
        try:
            import subprocess
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
            return "ok"
        except Exception:
            return "failed"

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
        try:
            cfg_save_audio_settings({"mic_enabled": self._owner._mic_active})
        except Exception:
            pass
        return self._owner._mic_active

    def get_mic_state(self):
        return self._owner._mic_active

    def load_audio_settings(self):
        try:
            return cfg_load_audio_settings()
        except Exception:
            return {}

    def save_audio_settings(self, settings: dict):
        try:
            safe = dict(settings or {})
            cfg_save_audio_settings(safe)
            if "mic_enabled" in safe:
                self._owner._mic_active = bool(safe.get("mic_enabled"))
            return "ok"
        except Exception as e:
            return f"error: {e}"

    def list_audio_devices(self):
        devices = []
        try:
            import pyaudio  # type: ignore[import]

            p = pyaudio.PyAudio()
            try:
                count = p.get_device_count()
                for i in range(count):
                    try:
                        info = p.get_device_info_by_index(i)
                        if int(info.get("maxInputChannels", 0)) <= 0:
                            continue
                        devices.append({
                            "index": int(info.get("index", i)),
                            "name": str(info.get("name", "Unknown")),
                        })
                    except Exception:
                        continue
            finally:
                p.terminate()
        except Exception:
            pass
        return devices

    def on_cam_click(self):
        self._owner._set_camera_active(not self._owner._cam_active)
        return self._owner._cam_active

    def get_cam_state(self):
        return self._owner._cam_active

    def set_local_camera_ready(self, ready: bool):
        self._owner._set_local_camera_ready(bool(ready))
        return "ok"

    def on_call_click(self):
        self._owner._restore_from_widget()
        return "ok"

    def get_update_state(self):
        try:
            from core.update_service import get_update_state # type: ignore[import]
            return get_update_state()
        except:
            return {}

    def check_for_updates(self):
        try:
            from core.update_service import check_for_updates # type: ignore[import]
            return check_for_updates()
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def download_update(self, version: str):
        try:
            from core.update_service import download_update # type: ignore[import]
            return download_update(version)
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def apply_update(self, version: str):
        try:
            from core.update_service import apply_update # type: ignore[import]
            return apply_update(version)
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def open_update_folder(self):
        try:
            from core.update_service import open_update_folder # type: ignore[import]
            return open_update_folder()
        except:
            return False

    def save_update_server_url(self, url: str):
        try:
            from core.update_service import save_update_settings # type: ignore[import]
            return save_update_settings({"manifest_url": url})
        except:
            return {"ok": False}

    def on_send_message(self, text: str):
        print(f"[UI] JS triggered on_send_message with text: {text}")
        if text:
            # Gracefully wait if the backend hasn't bound the callback yet
            if not getattr(self._owner, 'on_user_text', None):
                print(f"[UI] Backend not ready yet, queuing or dropping text command.")
                return "backend_not_ready"
                
            # Removed optimistic UI write_log to avoid duplicate transcripts
            print(f"[UI] Found callback, starting thread...")
            threading.Thread(target=self._owner.on_user_text,
                             args=(text,), daemon=True).start()
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
        def _do_close():
            try:
                if self._owner._widget_win: self._owner._widget_win.destroy()
                if self._owner._main_win: self._owner._main_win.destroy()
            except Exception:
                pass
            
            from core.updater import run_installer_and_exit
            if not run_installer_and_exit():
                os._exit(0)
                
        threading.Timer(0.05, _do_close).start()
        return "ok"

    def save_api_key(self, key: str):
        self._owner._save_api_key(key)
        return "ok"

    def get_auth_state(self):
        return self._owner._get_auth_state()

    def create_user(self, handle: str, password: str, email: str = "", display_name: str = ""):
        return self._owner._create_user(handle, password, email, display_name)

    def sign_in_user(self, identifier: str, password: str):
        return self._owner._sign_in_user(identifier, password)

    def set_user_pin(self, user_id: str, pin: str):
        return self._owner._set_user_pin(user_id, pin)

    def verify_user_pin(self, user_id: str, pin: str):
        return self._owner._verify_user_pin(user_id, pin)

    def save_user_api_key(self, user_id: str, key: str):
        return self._owner._save_user_api_key(user_id, key)

    def on_api_setup_complete(self):
        self._owner._on_api_setup_complete()
        return "ok"

    def on_auth_flow_complete(self):
        self._owner._on_auth_flow_complete()
        return "ok"

    def set_analytics_enabled(self, enabled):
        self._owner._set_analytics_enabled(enabled)
        return "ok"

    def open_settings(self):
        try:
            self._owner._eval(SETTINGS_MODAL_JS)
        except Exception:
            pass
        return "ok"

    def get_update_state(self):
        if update_get_state is None:
            return {
                "app_name": "Kree AI",
                "installed_version": APP_VERSION,
                "update_available": False,
                "status": "Update service unavailable.",
            }
        return update_get_state()

    def save_update_server_url(self, manifest_url: str):
        if update_save_settings is None:
            return {"ok": False, "status": "Update service unavailable."}
        return {"ok": True, "state": update_save_settings({"manifest_url": str(manifest_url or "").strip()})}

    def check_for_updates(self, manifest_url: str = ""):
        if update_check_for_updates is None:
            return {"ok": False, "status": "Update service unavailable."}
        return update_check_for_updates(manifest_url or None)

    def download_update(self, manifest_url: str = ""):
        if update_download_update is None:
            return {"ok": False, "status": "Update service unavailable."}
        return update_download_update(manifest_url or None)

    def apply_update(self, download_path: str = ""):
        if update_apply_update is None:
            return {"ok": False, "status": "Update service unavailable."}
        return update_apply_update(download_path or None)

    def open_update_folder(self):
        if update_open_folder is None:
            return {"ok": False, "status": "Update service unavailable."}
        return update_open_folder()

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

    def is_unlock_trusted(self):
        import core.vault as vault # type: ignore[import]
        return vault.is_unlock_trusted()

    def on_pin_unlocked(self):
        self._owner._mark_unlocked()
        return "ok"


class _WidgetAPI:
    def __init__(self, owner):
        self._owner = owner

    def restore_from_widget(self):
        self._owner._restore_from_widget()
        return "ok"

    def on_mic_click(self):
        self._owner._mic_active = not self._owner._mic_active
        try:
            cfg_save_audio_settings({"mic_enabled": self._owner._mic_active})
        except Exception:
            pass
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

    def __init__(self, face_path=None, size=None, startup_hidden=False):
        self.speaking         = False
        self.status_text      = "INITIALISING"
        _audio_settings = cfg_load_audio_settings()
        self._mic_active      = bool(_audio_settings.get("mic_enabled", True))
        self._cam_active      = False
        self._dark_mode       = True
        self._main_win = None
        self._widget_win = None
        self._agent_image = face_path
        self._startup_hidden = startup_hidden
        self._widget_visible = False
        self._hotkey_thread_started = False
        self._api_key_ready   = False
        self._lock_injected   = False
        self._auth_injected   = False
        self._is_unlocked     = False
        self._theme_switching = False
        self._disable_backend_camera_stream = False
        self.cached_procs     = "[]"
        self.chat_history     = []
        self._active_user     = None
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
            if len(self.chat_history) > MAX_CHAT_HISTORY:
                self.chat_history = self.chat_history[-MAX_CHAT_HISTORY:]
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

    def wait_for_unlock(self):
        # Hard gate: assistant runtime must not start before unlock.
        while not self._is_unlocked:
            time.sleep(0.1)

    @property
    def window(self):
        return self._main_win

    # ── Internals ─────────────────────────────────────────────────────────────
    def _api_keys_exist(self):
        if not self._active_user:
            return False
        import core.auth_store as auth_store # type: ignore[import]
        return auth_store.user_has_api_key(str(self._active_user.get("user_id", "")))

    def _eval(self, js: str):
        try:
            if self._main_win:
                self._main_win.evaluate_js(js)  # type: ignore[union-attr]
        except Exception:
            pass

    @staticmethod
    def _js_escape(text: str) -> str:
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("'", "\\'")
        )

    def show_action_loading(self, tool_name: str, app_name: str = "", command_text: str = ""):
        t = self._js_escape(tool_name)
        a = self._js_escape(app_name)
        c = self._js_escape(command_text)
        self._eval(
            f"if(typeof setActionLoading==='function')setActionLoading(true,'{t}','{a}','{c}');"
        )

    def hide_action_loading(self):
        self._eval("if(typeof setActionLoading==='function')setActionLoading(false,'','','');")

    def push_action_log(self, line: str):
        msg = self._js_escape(line)
        self._eval(f"if(typeof pushActionLog==='function')pushActionLog('{msg}');")

    def _save_api_key(self, key: str):
        if not key:
            return
        if not self._active_user:
            return
        self._save_user_api_key(str(self._active_user.get("user_id", "")), key)

    def _get_auth_state(self):
        import core.auth_store as auth_store # type: ignore[import]
        state = auth_store.get_auth_state()
        self._active_user = state.get("active_user")
        if self._active_user:
            self._api_key_ready = bool(self._active_user.get("has_api_key"))
        return state

    def _create_user(self, handle: str, password: str, email: str = "", display_name: str = ""):
        import core.auth_store as auth_store # type: ignore[import]
        result = auth_store.create_user(handle, password, email, display_name)
        self._active_user = result.get("user")
        self._api_key_ready = bool(self._active_user and self._active_user.get("has_api_key"))
        return result

    def _sign_in_user(self, identifier: str, password: str):
        import core.auth_store as auth_store # type: ignore[import]
        result = auth_store.sign_in_user(identifier, password)
        self._active_user = result.get("user")
        self._api_key_ready = bool(self._active_user and self._active_user.get("has_api_key"))
        return result

    def _set_user_pin(self, user_id: str, pin: str):
        import core.auth_store as auth_store # type: ignore[import]
        result = auth_store.set_user_pin(user_id, pin)
        self._active_user = result.get("user")
        self._api_key_ready = bool(self._active_user and self._active_user.get("has_api_key"))
        return result

    def _verify_user_pin(self, user_id: str, pin: str):
        import core.auth_store as auth_store # type: ignore[import]
        result = auth_store.verify_user_pin(user_id, pin)
        self._active_user = result.get("user")
        self._api_key_ready = bool(self._active_user and self._active_user.get("has_api_key"))
        return result

    def _save_user_api_key(self, user_id: str, key: str):
        import core.auth_store as auth_store # type: ignore[import]
        result = auth_store.save_user_api_key(user_id, key)
        self._active_user = result.get("user")
        self._api_key_ready = True
        self.write_log("SYS: Kree is online.")
        return result

    def _on_auth_flow_complete(self):
        if self._active_user:
            self._api_key_ready = bool(self._active_user.get("has_api_key"))
        self._is_unlocked = True
        self._lock_injected = False
        
        # Trigger background auto-update check 3s after unlock
        self._eval(AUTO_UPDATE_POPUP_JS)

        # Inject version badge into dashboard
        try:
            import json
            skeys_path = BASE_DIR / "config" / "service_keys.json"
            if skeys_path.exists():
                with open(skeys_path, "r", encoding="utf-8") as f:
                    ver = json.load(f).get("kree_version", "1.0.0")
            else:
                ver = "1.0.0"
            self._eval(
                f"(function(){{"
                f"var el=document.querySelector('.shimmer');"
                f"if(el){{var vb=document.createElement('span');"
                f"vb.textContent='v{ver}';"
                f"vb.style.cssText='margin-left:8px;font-size:9px;color:#00dc82;opacity:0.6;letter-spacing:0.1em;';"
                f"el.parentElement.appendChild(vb);}}"
                f"}})();"
            )
        except Exception:
            pass

    def _set_analytics_enabled(self, enabled: bool):
        """Called from Identity Gate analytics opt-in UI."""
        try:
            from core.analytics import set_analytics_enabled
            set_analytics_enabled(bool(enabled))
        except Exception as e:
            print(f"[KREE] Analytics preference save failed: {e}")

    def _set_camera_active(self, active: bool):
        self._cam_active = bool(active)
        if not self._cam_active:
            self._disable_backend_camera_stream = False
            self._eval("if(typeof setCameraState==='function') setCameraState(false);")

    def _set_local_camera_ready(self, ready: bool):
        # If browser-native camera stream is active, skip backend OpenCV capture.
        self._disable_backend_camera_stream = bool(ready)

    def _toggle_theme(self):
        if self._theme_switching:
            return
        self._theme_switching = True
        self._dark_mode = not self._dark_mode
        if not self._is_unlocked:
            self._auth_injected = False
        html = _DARK_HTML if self._dark_mode else _LIGHT_HTML
        if self._main_win:
            try:
                self._main_win.load_url(html.as_uri())  # type: ignore[union-attr]
                threading.Timer(0.5, self._inject_bridge).start()
                threading.Timer(0.75, self._restore_runtime_state).start()
            except Exception:
                pass
            finally:
                threading.Timer(0.9, lambda: setattr(self, "_theme_switching", False)).start()

    def _minimize_to_widget(self):
        # Fade out main window before switching
        if self._main_win:
            try:
                self._eval(
                    "document.body.style.transition='opacity 0.25s ease';"
                    "document.body.style.opacity='0';"
                )
            except Exception:
                pass
            time.sleep(0.28)

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
        self._widget_visible = True

    def _restore_from_widget(self):
        if self._widget_win:
            self._widget_win.hide()  # type: ignore[union-attr]
        if self._main_win:
            # Pre-set opacity to 0 so the reveal feels smooth
            try:
                self._eval("document.body.style.opacity='0';")
            except Exception:
                pass
            self._main_win.show()  # type: ignore[union-attr]
            try:
                self._eval(
                    "document.body.style.transition='opacity 0.3s ease';"
                    "document.body.style.opacity='1';"
                )
            except Exception:
                pass
        self._widget_visible = False

    def _toggle_quick_launcher(self):
        if self._widget_visible:
            self._restore_from_widget()
        else:
            self._minimize_to_widget()

    def _start_hotkey_listener(self):
        if self._hotkey_thread_started or platform.system() != "Windows":
            return

        def _hotkey_loop():
            user32 = ctypes.windll.user32
            modifiers = 0x0001 | 0x0002  # MOD_ALT | MOD_CONTROL
            hotkey_id = 0xC001
            try:
                if not user32.RegisterHotKey(None, hotkey_id, modifiers, 0x20):
                    return
                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312 and msg.wParam == hotkey_id:
                        threading.Timer(0, self._toggle_quick_launcher).start()
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except Exception:
                pass
            finally:
                try:
                    user32.UnregisterHotKey(None, hotkey_id)
                except Exception:
                    pass

        threading.Thread(target=_hotkey_loop, daemon=True).start()
        self._hotkey_thread_started = True

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

    def _inject_api_setup(self):
        if not API_SETUP_JS:
            self._inject_api_key_dialog()
            return
        try:
            self._main_win.evaluate_js(API_SETUP_JS)  # type: ignore[union-attr]
        except Exception:
            pass

    def _inject_auth_flow(self):
        if self._auth_injected:
            return

        # ── Bypass: skip login + PIN when user toggled "Disable Lock Screen" ──
        try:
            from memory.config_manager import AUDIO_CONFIG_FILE  # type: ignore[import]
            import json as _json
            if AUDIO_CONFIG_FILE.exists():
                _st = _json.loads(AUDIO_CONFIG_FILE.read_text(encoding="utf-8"))
                if _st.get("disable_lock_screen", False):
                    # Auto-load last saved user so API key is still available
                    try:
                        import core.auth_store as auth_store  # type: ignore[import]
                        state = auth_store.get_auth_state()
                        self._active_user = state.get("active_user")
                        if self._active_user:
                            self._api_key_ready = bool(self._active_user.get("has_api_key"))
                    except Exception:
                        pass
                    self._auth_injected = True
                    self._is_unlocked = True
                    self._lock_injected = False
                    return
        except Exception:
            pass

        try:
            self._main_win.evaluate_js(AUTH_FLOW_JS)  # type: ignore[union-attr]
            self._auth_injected = True
        except Exception:
            pass

    def _inject_lock_screen(self):
        if not LOCK_SCREEN_JS or self._lock_injected:
            if not LOCK_SCREEN_JS:
                self._is_unlocked = True
            return
        
        try:
            from memory.config_manager import AUDIO_CONFIG_FILE # type: ignore[import]
            import json
            if AUDIO_CONFIG_FILE.exists():
                st = json.loads(AUDIO_CONFIG_FILE.read_text(encoding="utf-8"))
                if st.get("disable_lock_screen", False):
                    self._is_unlocked = True
                    self._lock_injected = False
                    return
        except Exception: pass

        try:
            from core.vault import is_unlock_trusted # type: ignore[import]
            if is_unlock_trusted():
                self._is_unlocked = True
                self._lock_injected = False
                return
        except Exception:
            pass
            
        try:
            self._main_win.evaluate_js(LOCK_SCREEN_JS) # type: ignore[union-attr]
            self._is_unlocked = False
            self._lock_injected = True
        except Exception:
            pass

    def _on_api_setup_complete(self):
        self._api_key_ready = self._api_keys_exist()
        self._inject_lock_screen()

    def _mark_unlocked(self):
        try:
            import core.vault as vault # type: ignore[import]
            vault.remember_unlock_session()
        except Exception:
            pass
        self._is_unlocked = True

    def _metrics_loop(self):
        """Background metrics update — runs in a daemon thread, never blocks UI."""
        try:
            psutil.cpu_percent(interval=0)   # baseline
            time.sleep(1)
        except Exception:
            pass
            
        while True:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                
                # V4 Optimization: Disabled full process iteration to eliminate UI stutter
                self.cached_procs = "[]"

                if self._main_win is not None:
                    self._eval(
                        f"if(typeof updateMetrics==='function')"
                        f"updateMetrics({cpu},{ram});"
                    )
            except Exception:
                pass
            time.sleep(3)  # Fast responsive updates without blocking

    def _restore_runtime_state(self):
        try:
            # Sync persistent log history into the UI display
            try:
                import memory.history_manager as hist
                saved = hist.load_memory()
                if saved and not self.chat_history:
                    for turn in saved:
                        if turn.get("user"):
                            self.chat_history.append({"role": "USER", "body": turn["user"]})
                        if turn.get("kree"):
                            self.chat_history.append({"role": "KREE", "body": turn["kree"]})
            except Exception as e:
                pass

            hist_raw = [{"r": m["role"], "b": m["body"]} for m in self.chat_history]
            hist_json = json.dumps(hist_raw).replace("'", "\\'")
            self._eval(
                f"window.__KREE_HISTORY__ = JSON.parse('{hist_json}');"
                f"if(typeof restoreHistory==='function') restoreHistory();"
            )
        except Exception:
            pass

        self._eval(
            f"if(typeof setSpeaking==='function')setSpeaking({'true' if self.speaking else 'false'});"
        )
        self._eval(
            f"if(typeof setCameraState==='function')setCameraState({'true' if self._cam_active else 'false'});"
        )
        self._eval(
            f"if(typeof setMicState==='function')setMicState({'true' if self._mic_active else 'false'});"
        )

    def _on_started(self):
        """Runs inside webview GUI thread after start()."""
        def _init_delayed():
            # Load the full dashboard after a tiny delay so window appears instantly.
            time.sleep(0.05)
            html = _DARK_HTML if self._dark_mode else _LIGHT_HTML
            try:
                if self._main_win:
                    self._main_win.load_url(html.as_uri())  # type: ignore[union-attr]
            except Exception:
                pass

            time.sleep(0.12)
            self._inject_bridge()

            self._restore_runtime_state()

            self._inject_auth_flow()

            threading.Thread(target=self._metrics_loop, daemon=True).start()

        threading.Thread(target=_init_delayed, daemon=True).start()

    def run(self):
        """Start the webview event loop (blocks calling thread)."""
        import os
        # Auto-grant camera and mic permissions in Edge WebView2 (Windows default)
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--use-fake-ui-for-media-stream --enable-features=WebRTC-H264WithOpenH264FFmpeg"
        
        self._main_win = webview.create_window(
            "Kree AI",
            html=_BOOT_HTML,
            width=1200,
            height=800,
            frameless=True,
            hidden=self._startup_hidden,
            shadow=False,
            transparent=False,
            js_api=self._api,
        )
        self._start_hotkey_listener()
        webview.start(self._on_started, debug=False)

    def wake(self):
        """Wake UI from sleeping tray state."""
        if self._main_win:
            try:
                self._main_win.show()
                # Try to restore focus
                self._main_win.restore()
            except Exception:
                pass

    def hibernate(self):
        """Send UI to sleeping tray state (hidden)."""
        if self._main_win:
            try:
                self._main_win.hide()
            except Exception:
                pass


# Backward-compatible alias
JarvisUI = KreeUI