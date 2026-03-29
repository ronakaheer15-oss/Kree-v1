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
    _STITCH = BASE_DIR / "stitch_core_system_dashboard" / "stitch_core_system_dashboard"
else:
    # In dev, stitch is a peer to the project folder
    _STITCH = BASE_DIR.parent / "stitch_core_system_dashboard" / "stitch_core_system_dashboard"

_LIGHT_HTML  = _STITCH / "core_system_dashboard_1" / "code.html"
_DARK_HTML   = _STITCH / "core_system_dashboard_2" / "code.html"
_WIDGET_HTML = _STITCH / "minimized_control_widget" / "code.html"

_BOOT_HTML = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
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
    from core.api_setup_ui import API_SETUP_JS # type: ignore[import]
except ImportError:
    API_SETUP_JS = ""

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

    def on_send_message(self, text: str):
        print(f"[UI] JS triggered on_send_message with text: {text}")
        if text and self._owner.on_user_text:
            try:
                self._owner.write_log(f"You: {text}")
            except Exception:
                pass
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

    def on_api_setup_complete(self):
        self._owner._on_api_setup_complete()
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

    def __init__(self, face_path=None, size=None):
        self.speaking         = False
        self.status_text      = "INITIALISING"
        _audio_settings = cfg_load_audio_settings()
        self._mic_active      = bool(_audio_settings.get("mic_enabled", True))
        self._cam_active      = False
        self._dark_mode       = True
        self._on_user_text_cb = None
        self._main_win        = None
        self._widget_win      = None
        self._widget_visible   = False
        self._hotkey_thread_started = False
        self._api_key_ready   = self._api_keys_exist()
        self._lock_injected   = False
        self._is_unlocked     = False
        self._theme_switching = False
        self._disable_backend_camera_stream = False
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
        import core.vault as vault # type: ignore[import]
        return bool(vault.load_api_key(API_FILE))

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
        import core.vault as vault # type: ignore[import]
        vault.save_api_key(API_FILE, key)
        self._api_key_ready = True
        self.write_log("SYS: Kree is online.")

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
            self._main_win.show()  # type: ignore[union-attr]
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

    def _inject_lock_screen(self):
        if not LOCK_SCREEN_JS or self._lock_injected:
            if not LOCK_SCREEN_JS:
                self._is_unlocked = True
            return
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
        self._is_unlocked = True

    def _metrics_loop(self):
        """Background metrics update — runs in a daemon thread, never blocks UI."""
        try:
            psutil.cpu_percent(interval=0)   # baseline
        except Exception:
            pass
        time.sleep(4)
        while True:
            time.sleep(15)  # less frequent = less CPU pressure
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
                self.cached_procs = json.dumps(procs[:5])  # type: ignore[index]

                if self._main_win is not None:
                    self._eval(
                        f"if(typeof updateMetrics==='function')"
                        f"updateMetrics({cpu},{ram});"
                    )
            except Exception:
                pass

    def _restore_runtime_state(self):
        try:
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

            if not self._api_key_ready:
                self._inject_api_setup()
            else:
                self._inject_lock_screen()

            threading.Thread(target=self._metrics_loop, daemon=True).start()

        threading.Thread(target=_init_delayed, daemon=True).start()

    def run(self):
        """Start the webview event loop (blocks calling thread)."""
        self._main_win = webview.create_window(
            "Kree AI",
            html=_BOOT_HTML,
            width=1200,
            height=820,
            resizable=True,
            frameless=True,
            easy_drag=False,
            shadow=False,
            transparent=False,
            js_api=self._api,
        )
        self._start_hotkey_listener()
        webview.start(self._on_started, debug=False)


# Backward-compatible alias
JarvisUI = KreeUI