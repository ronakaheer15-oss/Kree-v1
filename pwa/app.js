/* ═══════════════════════════════════════════════════════════
   Kree Companion v3 — Complete PWA Logic
   ═══════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────
let ws = null;
let connected = false;
let desktopIP = '';
let connectedSince = null;
let recentCommands = [];
let editingNoteId = null;
let speechRec = null;
let micStream = null;
let mediaRecorder = null;
let installPromptEvent = null;

const TABS = ['dashboard', 'notes', 'contacts', 'connect', 'files'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

// ── DOM Refs ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const mainContent = $('main-content');
const scanView = $('scan-view');
const offlineBanner = $('offline-banner');
const statusPill = $('status-pill');
const bottomNav = $('bottom-nav');
const tabEls = {};
TABS.forEach(t => tabEls[t] = $('tab-' + t));

// ═══════════════════════════════════════════════════════════
// ── IndexedDB ────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
let db = null;
const DB_NAME = 'KreeCompanion';
const DB_VERSION = 1;

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = e => {
      const d = e.target.result;
      if (!d.objectStoreNames.contains('notes')) {
        d.createObjectStore('notes', { keyPath: 'id' });
      }
      if (!d.objectStoreNames.contains('contacts')) {
        d.createObjectStore('contacts', { keyPath: 'id' });
      }
      if (!d.objectStoreNames.contains('transfers')) {
        d.createObjectStore('transfers', { keyPath: 'id' });
      }
    };
    req.onsuccess = e => { db = e.target.result; resolve(db); };
    req.onerror = e => reject(e.target.error);
  });
}

function dbGetAll(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function dbPut(store, item) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const req = tx.objectStore(store).put(item);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function dbDelete(store, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const req = tx.objectStore(store).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

function dbClear(store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    const req = tx.objectStore(store).clear();
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ═══════════════════════════════════════════════════════════
// ── Tab Navigation ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function switchTab(tabId) {
  // Hide scan view when connected
  scanView.style.display = connected ? 'none' : 'flex';

  TABS.forEach(t => {
    const el = tabEls[t];
    if (el) el.style.display = (connected && t === tabId) ? 'flex' : 'none';
  });

  bottomNav.querySelectorAll('.bnav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  if (mainContent) mainContent.scrollTop = 0;
}

// Bind bottom nav
document.addEventListener('DOMContentLoaded', () => {
  bottomNav.querySelectorAll('.bnav-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // OS detection
  const ua = navigator.userAgent;
  const os = /iphone|ipad|ipod/i.test(ua) ? 'iOS' : /android/i.test(ua) ? 'Android' : 'Unknown';
  const osEl = $('settings-os');
  if (osEl) osEl.textContent = os;

  // Battery API
  initBattery();

  // Init DB then load saved connection
  openDB().then(() => {
    renderNotes();
    renderContacts();
    
    // Read token from initial setup URL, save it, and scrub it from URL
    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
      localStorage.setItem('kree_auth_token', urlToken);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    // Auto-detect IP from hostname
    let defaultIP = window.location.hostname;
    if (!defaultIP || defaultIP === 'localhost' || defaultIP === '127.0.0.1') {
      defaultIP = localStorage.getItem('kree_desktop_ip') || '';
    }
    
    if (defaultIP) {
      $('connect-ip-input').value = defaultIP;
      connectToDesktop(defaultIP);
    }
    
    // PWA Install Prompt
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      installPromptEvent = e;
      const banner = $('install-banner');
      if (banner && !localStorage.getItem('kree_install_dismissed')) {
        banner.style.display = 'block';
      }
    });
    const installBtn = $('install-btn');
    if (installBtn) {
      installBtn.addEventListener('click', () => {
        if (installPromptEvent) {
          installPromptEvent.prompt();
          installPromptEvent.userChoice.then(() => {
            installPromptEvent = null;
            const banner = $('install-banner');
            if (banner) banner.style.display = 'none';
          });
        }
      });
    }
    
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  });

  // Connect button
  $('scan-btn').addEventListener('click', () => {
    const ip = $('connect-ip-input').value.trim();
    if (ip) connectToDesktop(ip);
  });
  $('connect-ip-input').addEventListener('keypress', e => {
    if (e.key === 'Enter') {
      const ip = $('connect-ip-input').value.trim();
      if (ip) connectToDesktop(ip);
    }
  });
});

// ═══════════════════════════════════════════════════════════
// ── WebSocket Connection ─────────────────────────────────
// ═══════════════════════════════════════════════════════════
function connectToDesktop(ip) {
  desktopIP = ip;
  localStorage.setItem('kree_desktop_ip', ip);
  $('connect-ip').textContent = ip;

  if (ws) { try { ws.close(); } catch(e){} }

  try {
    const wsUrl = `ws://${ip}:8443/`;
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';
  } catch(e) {
    showToast('Connection failed');
    return;
  }

  ws.onopen = () => {
    connected = true;
    connectedSince = new Date();
    updateConnectionUI(true);
    switchTab('dashboard');
    addConnectionLog('Connected');

    // Authenticate via payload message (token never in URL)
    const token = localStorage.getItem('kree_auth_token') || '';
    wsSend({ type: 'auth', token: token });

    // Send device info
    const ua = navigator.userAgent;
    const os = /iphone|ipad|ipod/i.test(ua) ? 'iOS' : /android/i.test(ua) ? 'Android' : 'Unknown';
    wsSend({ type: 'device_info', os: os, agent: ua.substring(0, 100) });

    // Sync data to desktop
    syncNotesToDesktop();
    syncContactsToDesktop();

    showToast('Connected to Kree Desktop');
  };

  ws.onmessage = evt => {
    try {
      const data = JSON.parse(evt.data);
      handleMessage(data);
    } catch(e) {}
  };

  ws.onclose = () => {
    connected = false;
    updateConnectionUI(false);
    updateKreeState('offline');
    addConnectionLog('Disconnected');

    // Auto-reconnect with exponential backoff
    const toggle = $('auto-reconnect-toggle');
    if (toggle && toggle.checked && desktopIP) {
      addConnectionLog('Reconnecting in 5s...');
      setTimeout(() => connectToDesktop(desktopIP), 5000);
    }
  };

  ws.onerror = () => {
    addConnectionLog('Connection error');
  };
}

function wsSend(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

function updateConnectionUI(isConnected) {
  statusPill.className = 'status-pill ' + (isConnected ? 'connected' : 'disconnected');
  statusPill.textContent = isConnected ? '● ONLINE' : '○ OFFLINE';
  offlineBanner.style.display = isConnected ? 'none' : (desktopIP ? 'flex' : 'none');
  scanView.style.display = isConnected ? 'none' : 'flex';

  // Show/hide tabs
  TABS.forEach(t => {
    if (tabEls[t]) tabEls[t].style.display = 'none';
  });
  if (isConnected) switchTab('dashboard');

  // Update connect tab
  const badge = $('connect-status-badge');
  if (badge) {
    badge.textContent = isConnected ? 'Connected' : 'Disconnected';
    badge.className = 'badge ' + (isConnected ? 'green' : 'red');
  }
  $('connect-since').textContent = isConnected && connectedSince
    ? connectedSince.toLocaleTimeString() : '--';

  // Disconnect buttons
  const dcBtns = [$('disconnect-btn'), $('disconnect-btn-connect')];
  dcBtns.forEach(b => { if(b) b.style.display = isConnected ? 'block' : 'none'; });

  // File bridge status
  const fbs = $('file-bridge-status');
  if (fbs) {
    fbs.textContent = isConnected ? 'Online' : 'Offline';
    fbs.className = 'badge ' + (isConnected ? 'green' : 'red');
  }
}

// ═══════════════════════════════════════════════════════════
// ── Message Router ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function handleMessage(data) {
  switch (data.type) {
    case 'system_stats': updateDashboardStats(data); break;
    case 'screen_frame': updateScreenFrame(data); break;
    case 'chat': addRecentCommand(data.text, 'kree'); break;
    case 'active_task': updateActiveTask(data); break;
    case 'notification': addNotification(data); kreeNotify(data.body || data.title || 'Notification'); break;
    case 'clipboard_sync': updateClipboard(data); break;
    case 'sync_notes': handleNotesSync(data); break;
    case 'sync_contacts': handleContactsSync(data); break;
    case 'file_transfer': handleFileReceive(data); break;
    case 'telemetry': updateTelemetry(data); break;
    case 'kree_state': updateKreeState(data.state); break;
    default: break;
  }
}

// ═══════════════════════════════════════════════════════════
// ── Voice Commands ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
let commandDictation = null;

function toggleVoiceCommand() {
  if (commandDictation) {
    stopVoiceCommand();
    return;
  }
  
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    showToast('Voice not supported on this browser');
    const btn = $('floating-mic-btn');
    if (btn) btn.classList.add('disabled');
    return;
  }
  
  commandDictation = new SpeechRec();
  commandDictation.continuous = false;
  commandDictation.interimResults = true;
  commandDictation.lang = 'en-US';
  
  const btn = $('floating-mic-btn');
  const overlay = $('voice-overlay-text');
  
  if (btn) btn.classList.add('pulsing');
  if (overlay) {
    overlay.style.display = 'block';
    overlay.textContent = 'Listening...';
  }
  
  let finalTranscript = '';
  let silenceTimer = null;
  
  const resetSilenceTimer = () => {
    clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
      stopVoiceCommand(finalTranscript);
    }, 5000);
  };
  
  commandDictation.onstart = () => { resetSilenceTimer(); };
  
  commandDictation.onresult = e => {
    resetSilenceTimer();
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) finalTranscript += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
    }
    if (overlay) overlay.textContent = finalTranscript || interim || 'Listening...';
  };
  
  commandDictation.onerror = (err) => {
    if (err.error === 'not-allowed') showToast('Microphone access denied or requires HTTPS');
    stopVoiceCommand();
  };
  commandDictation.onend = () => {
    if (finalTranscript) stopVoiceCommand(finalTranscript);
    else stopVoiceCommand();
  };
  
  try {
    commandDictation.start();
  } catch(e) {
    showToast('Voice requires secure context (HTTPS/localhost)');
    stopVoiceCommand();
  }
}

function stopVoiceCommand(sendText) {
  if (commandDictation) {
    try { commandDictation.stop(); } catch(e) {}
    commandDictation = null;
  }
  
  const btn = $('floating-mic-btn');
  if (btn) btn.classList.remove('pulsing');
  
  const overlay = $('voice-overlay-text');
  
  if (sendText && sendText.trim()) {
    if (overlay) overlay.textContent = sendText;
    setTimeout(() => {
      wsSend({ type: 'command', text: sendText.trim() });
      addRecentCommand(sendText.trim(), 'user');
      if (overlay) overlay.style.display = 'none';
      showToast('Command sent to Kree');
    }, 2000);
  } else {
    if (overlay) overlay.style.display = 'none';
  }
}

function sendTextCmd() {
  const input = $('kree-cmd-input');
  if (!input) return;
  const text = input.value.trim();
  if (text) {
    wsSend({ type: 'command', text: text });
    addRecentCommand(text, 'user');
    showToast('Command sent to Kree');
    input.value = '';
    input.blur();
  }
}

function handleCmdKey(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    sendTextCmd();
  }
}

// ═══════════════════════════════════════════════════════════
// ── Dashboard ────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function updateDashboardStats(data) {
  if (data.cpu) $('dash-cpu').textContent = data.cpu + '%';
  if (data.ram) $('dash-ram').textContent = data.ram + '%';
  if (data.uptime) $('dash-uptime').textContent = data.uptime;

  // Update latency on connect tab
  $('connect-latency').textContent = (data.latency || '<1') + 'ms';
}

function updateScreenFrame(data) {
  const img = $('desktop-screen-preview');
  const ph = $('screen-preview-placeholder');
  if (data.data && img) {
    img.src = 'data:image/jpeg;base64,' + data.data;
    img.style.display = 'block';
    if (ph) ph.style.display = 'none';
  }
}

function updateActiveTask(data) {
  const el = $('desktop-active-task');
  if (el) el.textContent = data.task || 'No active task';
}

function addRecentCommand(text, source) {
  if (!text) return;
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  recentCommands.unshift({ text, time, source });
  if (recentCommands.length > 10) recentCommands.pop();
  renderRecentCommands();
}

function renderRecentCommands() {
  const list = $('recent-commands');
  if (!list) return;
  if (recentCommands.length === 0) {
    list.innerHTML = '<div class="empty-state-sm">No commands yet</div>';
    return;
  }
  list.innerHTML = recentCommands.slice(0, 5).map(c =>
    '<div class="cmd-item"><span class="cmd-text">' + escHTML(c.text) + '</span><span class="cmd-time">' + c.time + '</span></div>'
  ).join('');
}

function addNotification(data) {
  const list = $('notification-list');
  if (!list) return;
  const empty = list.querySelector('.empty-state-sm');
  if (empty) empty.remove();
  const div = document.createElement('div');
  div.className = 'notif-item';
  div.innerHTML = '<div class="notif-title">' + escHTML(data.title || 'Notification') + '</div>' +
    '<div class="notif-body">' + escHTML(data.body || '') + '</div>';
  list.prepend(div);
  // Keep max 10
  while (list.children.length > 10) list.lastChild.remove();
}

function sendQuickAction(action) {
  wsSend({ type: 'quick_action', action: action });
  addRecentCommand(action + ' desktop', 'user');
  showToast('Sent: ' + action);
}

function updateTelemetry(data) {
  if (data.latency) $('connect-latency').textContent = data.latency + 'ms';
  const sig = $('signal-badge');
  if (sig) {
    const lat = parseInt(data.latency) || 0;
    sig.textContent = lat < 50 ? '● Strong' : lat < 200 ? '● Good' : '● Weak';
    sig.style.color = lat < 50 ? 'var(--primary)' : lat < 200 ? '#f59e0b' : 'var(--danger)';
  }
}

// Battery
function initBattery() {
  try {
    if (navigator.getBattery) {
      navigator.getBattery().then(battery => {
        const card = $('battery-card');
        const val = $('dash-battery');
        if (card && val) {
          card.style.display = 'block';
          const update = () => {
            val.textContent = Math.round(battery.level * 100) + '%';
          };
          update();
          battery.addEventListener('levelchange', update);
        }
      }).catch(() => {});
    }
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════════
// ── Notes ────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
async function renderNotes(filter) {
  const list = $('notes-list');
  if (!list || !db) return;

  let notes = await dbGetAll('notes');
  notes.sort((a, b) => (b.updated || 0) - (a.updated || 0));

  if (filter) {
    const f = filter.toLowerCase();
    notes = notes.filter(n => (n.title || '').toLowerCase().includes(f) || (n.body || '').toLowerCase().includes(f));
  }

  if (notes.length === 0) {
    list.innerHTML = '<div class="empty-state-sm">No notes yet — tap + to create one</div>';
    return;
  }

  list.innerHTML = notes.map(n => {
    const date = n.updated ? new Date(n.updated).toLocaleDateString() : '';
    return '<div class="note-card" onclick="editNote(\'' + n.id + '\')">' +
      '<div class="note-card-title">' + escHTML(n.title || 'Untitled') + '</div>' +
      '<div class="note-card-body">' + escHTML(n.body || '') + '</div>' +
      '<div class="note-card-meta"><span>' + date + '</span>' +
      '<button class="note-delete-btn" onclick="event.stopPropagation();deleteNote(\'' + n.id + '\')">DELETE</button></div>' +
    '</div>';
  }).join('');
}

function createNewNote() {
  editingNoteId = null;
  $('note-editor-title').value = '';
  $('note-editor-body').value = '';
  $('note-editor').style.display = 'block';
  $('note-editor-title').focus();
}

async function editNote(id) {
  const notes = await dbGetAll('notes');
  const note = notes.find(n => n.id === id);
  if (!note) return;
  editingNoteId = id;
  $('note-editor-title').value = note.title || '';
  $('note-editor-body').value = note.body || '';
  $('note-editor').style.display = 'block';
}

async function saveNote() {
  const title = $('note-editor-title').value.trim();
  const body = $('note-editor-body').value.trim();
  if (!title && !body) return;

  const note = {
    id: editingNoteId || ('note_' + Date.now()),
    title: title || 'Untitled',
    body: body,
    updated: Date.now()
  };

  await dbPut('notes', note);
  cancelNoteEditor();
  renderNotes();
  syncNotesToDesktop();
  showToast('Note saved');
}

function cancelNoteEditor() {
  $('note-editor').style.display = 'none';
  editingNoteId = null;
}

async function deleteNote(id) {
  await dbDelete('notes', id);
  renderNotes();
  syncNotesToDesktop();
  showToast('Note deleted');
}

function toggleNoteSearch() {
  const bar = $('note-search-bar');
  bar.style.display = bar.style.display === 'none' ? 'block' : 'none';
  if (bar.style.display === 'block') $('note-search-input').focus();
}

function filterNotes() {
  renderNotes($('note-search-input').value);
}

async function syncNotesToDesktop() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  const notes = await dbGetAll('notes');
  wsSend({ type: 'sync_notes', notes: notes });
}

async function handleNotesSync(data) {
  // Desktop always wins — overwrite local notes
  if (data.notes && Array.isArray(data.notes)) {
    await dbClear('notes');
    for (const n of data.notes) {
      await dbPut('notes', n);
    }
    renderNotes();
    showToast('Notes updated from desktop');
  }
}

// Voice to Note
function startVoiceNote() {
  try {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      // Fallback: just open editor
      createNewNote();
      return;
    }
    speechRec = new SpeechRec();
    speechRec.continuous = true;
    speechRec.interimResults = false;
    speechRec.lang = 'en-US';

    let transcript = '';
    $('voice-recording').style.display = 'flex';
    $('voice-recording').onclick = () => stopVoiceNote();

    speechRec.onresult = e => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          transcript += e.results[i][0].transcript + ' ';
        }
      }
    };

    speechRec.onerror = () => stopVoiceNote();
    speechRec.onend = () => {
      $('voice-recording').style.display = 'none';
      if (transcript.trim()) {
        editingNoteId = null;
        $('note-editor-title').value = 'Voice Note — ' + new Date().toLocaleTimeString();
        $('note-editor-body').value = transcript.trim();
        $('note-editor').style.display = 'block';
      }
    };
    speechRec.start();
  } catch(e) {
    createNewNote(); // Silent fallback
  }
}

function stopVoiceNote() {
  if (speechRec) {
    try { speechRec.stop(); } catch(e) {}
  }
  $('voice-recording').style.display = 'none';
}

// ═══════════════════════════════════════════════════════════
// ── Contacts ─────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
async function renderContacts(filter) {
  const list = $('contacts-list');
  if (!list || !db) return;

  let contacts = await dbGetAll('contacts');
  contacts.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  if (filter) {
    const f = filter.toLowerCase();
    contacts = contacts.filter(c => (c.name || '').toLowerCase().includes(f) || (c.phone || '').includes(f));
  }

  if (contacts.length === 0) {
    list.innerHTML = '<div class="empty-state-sm">No contacts — tap + to add</div>';
    return;
  }

  list.innerHTML = contacts.map(c => {
    const initials = (c.name || '?').charAt(0).toUpperCase();
    return '<div class="contact-card">' +
      '<div class="contact-avatar">' + initials + '</div>' +
      '<div class="contact-info"><div class="contact-name">' + escHTML(c.name) + '</div>' +
      '<div class="contact-phone">' + escHTML(c.phone || '') + '</div></div>' +
      '<div class="contact-actions">' +
      (c.phone ? '<button class="contact-action-btn call" onclick="callContact(\'' + escHTML(c.phone) + '\')"><svg viewBox="0 0 24 24"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg></button>' : '') +
      (c.phone ? '<button class="contact-action-btn msg" onclick="msgContact(\'' + escHTML(c.phone) + '\')"><svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/></svg></button>' : '') +
      '<button class="contact-action-btn del" onclick="deleteContact(\'' + c.id + '\')"><svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg></button>' +
      '</div></div>';
  }).join('');
}

function callContact(phone) { window.location.href = 'tel:' + phone; }
function msgContact(phone) { window.location.href = 'sms:' + phone; }

function showAddContact() {
  $('add-contact-form').style.display = 'block';
  $('new-contact-name').focus();
}
function hideAddContact() {
  $('add-contact-form').style.display = 'none';
  $('new-contact-name').value = '';
  $('new-contact-phone').value = '';
  $('new-contact-email').value = '';
}

async function saveContact() {
  const name = $('new-contact-name').value.trim();
  const phone = $('new-contact-phone').value.trim();
  const email = $('new-contact-email').value.trim();
  if (!name) { showToast('Name is required'); return; }

  const contact = {
    id: 'c_' + Date.now(),
    name, phone, email,
    created: Date.now()
  };
  await dbPut('contacts', contact);
  hideAddContact();
  renderContacts();
  syncContactsToDesktop();
  showToast('Contact saved');
}

async function deleteContact(id) {
  await dbDelete('contacts', id);
  renderContacts();
  syncContactsToDesktop();
  showToast('Contact deleted');
}

function toggleContactSearch() {
  const bar = $('contact-search-bar');
  bar.style.display = bar.style.display === 'none' ? 'block' : 'none';
  if (bar.style.display === 'block') $('contact-search-input').focus();
}

function filterContacts() {
  renderContacts($('contact-search-input').value);
}

async function syncContactsToDesktop() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  const contacts = await dbGetAll('contacts');
  wsSend({ type: 'sync_contacts', contacts: contacts });
  $('contacts-sync-text').textContent = 'Synced ' + contacts.length + ' contacts — ' + new Date().toLocaleTimeString();
}

async function handleContactsSync(data) {
  if (data.contacts && Array.isArray(data.contacts)) {
    // Merge: add any contacts from desktop not on phone
    const existing = await dbGetAll('contacts');
    const existingIds = new Set(existing.map(c => c.id));
    for (const c of data.contacts) {
      if (!existingIds.has(c.id)) {
        await dbPut('contacts', c);
      }
    }
    renderContacts();
    $('contacts-sync-text').textContent = 'Synced from desktop — ' + new Date().toLocaleTimeString();
  }
}

// ═══════════════════════════════════════════════════════════
// ── Clipboard Sync ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
async function syncClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      wsSend({ type: 'clipboard_sync', content: text });
      $('clipboard-content').textContent = text.substring(0, 200);
      const fc = $('clipboard-content-files');
      if (fc) fc.textContent = text.substring(0, 200);
      showToast('Clipboard synced to desktop');
    } else {
      showToast('Clipboard is empty');
    }
  } catch(e) {
    showToast('Clipboard access denied');
  }
}

function updateClipboard(data) {
  if (data.content) {
    const el = $('clipboard-content');
    if (el) el.textContent = data.content.substring(0, 200);
    const fc = $('clipboard-content-files');
    if (fc) fc.textContent = data.content.substring(0, 200);
    // Write to clipboard
    try {
      navigator.clipboard.writeText(data.content);
      showToast('Clipboard received from desktop');
    } catch(e) {}
  }
}

// ═══════════════════════════════════════════════════════════
// ── File Bridge ──────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;

  if (file.size > MAX_FILE_SIZE) {
    showToast('File too large — max 50MB');
    e.target.value = '';
    return;
  }

  sendFileToDesktop(file);
}

function sendFileToDesktop(file) {
  const progress = $('transfer-progress');
  const bar = $('transfer-bar');
  const fname = $('transfer-filename');
  const fsize = $('transfer-size');
  const fstatus = $('transfer-status');

  progress.style.display = 'block';
  fname.textContent = file.name;
  fsize.textContent = formatSize(file.size);
  fstatus.textContent = 'Reading file...';
  bar.style.width = '10%';

  const reader = new FileReader();
  reader.onprogress = e => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 50);
      bar.style.width = pct + '%';
    }
  };

  reader.onload = () => {
    fstatus.textContent = 'Sending...';
    bar.style.width = '60%';

    const base64 = reader.result.split(',')[1];
    wsSend({
      type: 'file_transfer',
      direction: 'phone_to_desktop',
      filename: file.name,
      size: file.size,
      mime: file.type,
      data: base64
    });

    bar.style.width = '100%';
    fstatus.textContent = 'Sent ✓';
    addTransferHistory(file.name, file.size, '→ Desktop');
    showToast('File sent to desktop');

    setTimeout(() => { progress.style.display = 'none'; }, 2000);
  };

  reader.onerror = () => {
    fstatus.textContent = 'Failed ✗';
    showToast('File read failed');
    setTimeout(() => { progress.style.display = 'none'; }, 2000);
  };

  reader.readAsDataURL(file);
}

let incomingTransfers = {};

function handleFileReceive(data) {
  if (data.direction !== 'desktop_to_phone') return;

  if (data.action === 'single') {
    finishFileReceive(data.filename, data.size, data.data, data.mime || 'application/octet-stream');
  } else if (data.action === 'start') {
    incomingTransfers[data.fileId] = { filename: data.filename, size: data.size, chunks: [] };
    const progress = $('transfer-progress');
    if (progress) {
      progress.style.display = 'block';
      $('transfer-filename').textContent = data.filename;
      $('transfer-size').textContent = formatSize(data.size);
      $('transfer-status').textContent = 'Receiving... 0%';
      $('transfer-bar').style.width = '0%';
    }
  } else if (data.action === 'chunk') {
    if (incomingTransfers[data.fileId]) {
      incomingTransfers[data.fileId].chunks.push({ index: data.index, data: data.data });
      const t = incomingTransfers[data.fileId];
      const rcvBytes = t.chunks.length * 512 * 1024;
      const pct = Math.min(Math.round((rcvBytes / t.size) * 100), 99);
      const bar = $('transfer-bar');
      if (bar) bar.style.width = pct + '%';
      $('transfer-status').textContent = 'Receiving... ' + pct + '%';
    }
  } else if (data.action === 'complete') {
    const t = incomingTransfers[data.fileId];
    if (t) {
      t.chunks.sort((a,b) => a.index - b.index);
      const fullBase64 = t.chunks.map(c => c.data).join('');
      finishFileReceive(t.filename, t.size, fullBase64, 'application/octet-stream');
      delete incomingTransfers[data.fileId];
      
      const progress = $('transfer-progress');
      if (progress) {
        $('transfer-status').textContent = 'Received ✓';
        $('transfer-bar').style.width = '100%';
        setTimeout(() => { progress.style.display = 'none'; }, 2000);
      }
    }
  }
}

function finishFileReceive(filename, size, base64Data, mime) {
  const list = $('received-files');
  const empty = list.querySelector('.empty-state-sm');
  if (empty) empty.remove();

  const blob = b64toBlob(base64Data, mime);
  const url = URL.createObjectURL(blob);

  const div = document.createElement('div');
  div.className = 'file-item';
  div.innerHTML =
    '<span class="file-icon">📄</span>' +
    '<span class="file-name">' + escHTML(filename || 'file') + '</span>' +
    '<span class="file-size">' + formatSize(size || 0) + '</span>' +
    '<a href="' + url + '" download="' + escHTML(filename || 'file') + '" class="file-download-btn">SAVE</a>';
  list.prepend(div);

  addTransferHistory(filename, size, '← Desktop');
  showToast('File received: ' + (filename || 'file'));
}

function addTransferHistory(name, size, direction) {
  const list = $('transfer-history');
  if (!list) return;
  const empty = list.querySelector('.empty-state-sm');
  if (empty) empty.remove();

  const div = document.createElement('div');
  div.className = 'file-item';
  div.innerHTML =
    '<span class="file-icon">📄</span>' +
    '<span class="file-name">' + escHTML(name || 'file') + '</span>' +
    '<span class="file-size">' + formatSize(size || 0) + '</span>' +
    '<span class="file-dir ' + (direction.includes('Desktop') ? 'up' : 'down') + '">' + direction + '</span>';
  list.prepend(div);

  // Keep max 20
  while (list.children.length > 20) list.lastChild.remove();
}

// ═══════════════════════════════════════════════════════════
// ── Connection Log ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function addConnectionLog(event) {
  const list = $('connection-log');
  if (!list) return;
  const empty = list.querySelector('.empty-state-sm');
  if (empty) empty.remove();

  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = 'log-item';
  div.innerHTML = '<span class="log-event">' + event + '</span><span class="log-time">' + time + '</span>';
  list.prepend(div);
  while (list.children.length > 20) list.lastChild.remove();
}

// ═══════════════════════════════════════════════════════════
// ── Disconnect ───────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
document.addEventListener('click', e => {
  if (e.target.id === 'disconnect-btn' || e.target.id === 'disconnect-btn-connect') {
    if (ws) ws.close();
    connected = false;
    desktopIP = '';
    localStorage.removeItem('kree_desktop_ip');
    updateConnectionUI(false);
    showToast('Disconnected');
  }
});

// ═══════════════════════════════════════════════════════════
// ── Clear All Data ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
async function clearAllData() {
  if (!confirm('Clear all Kree data? This cannot be undone.')) return;
  await dbClear('notes');
  await dbClear('contacts');
  await dbClear('transfers');
  localStorage.clear();
  renderNotes();
  renderContacts();
  showToast('All data cleared');
}

// ═══════════════════════════════════════════════════════════
// ── Utilities ────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function escHTML(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function b64toBlob(b64, mime) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], { type: mime });
}

// Toast
let toastTimer = null;
function showToast(msg) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2500);
}

// ═══════════════════════════════════════════════════════════
// ── Macro Triggers ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function triggerMacro(chainName) {
  wsSend({ type: 'command', text: 'trigger macro ' + chainName });
  addRecentCommand('Macro: ' + chainName, 'user');
  showToast('Macro fired: ' + chainName);
}

// ═══════════════════════════════════════════════════════════
// ── Kree State Indicator ─────────────────────────────────
// ═══════════════════════════════════════════════════════════
function updateKreeState(state) {
  const indicator = $('kree-state-indicator');
  const dot = $('state-dot');
  const label = $('state-label');
  if (!indicator) return;

  if (state === 'offline' || !state) {
    indicator.style.display = 'none';
    return;
  }

  indicator.style.display = 'flex';
  dot.className = 'state-dot';

  switch (state) {
    case 'listening':
      label.textContent = 'Kree is listening';
      break;
    case 'speaking':
      dot.classList.add('speaking');
      label.textContent = 'Kree is speaking';
      break;
    case 'executing':
      dot.classList.add('executing');
      label.textContent = 'Running task...';
      break;
    default:
      label.textContent = 'Kree: ' + state;
  }
}

// ═══════════════════════════════════════════════════════════
// ── Notification Fallback ────────────────────────────────
// ═══════════════════════════════════════════════════════════
function kreeNotify(message) {
  // Try native Notification API first
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      new Notification('Kree', { body: message, icon: 'icon-192.png' });
      return;
    } catch(e) {}
  }
  // Fallback: in-app toast banner
  showInAppBanner(message);
}

let bannerTimer = null;
function showInAppBanner(message) {
  const toast = $('notification-toast');
  const msgEl = $('toast-message');
  if (!toast || !msgEl) return;
  msgEl.textContent = message;
  toast.style.display = 'flex';
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => { toast.style.display = 'none'; }, 5000);
}
function hideToast() {
  const toast = $('notification-toast');
  if (toast) toast.style.display = 'none';
  clearTimeout(bannerTimer);
}

// ═══════════════════════════════════════════════════════════
// ── Install Prompt ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════
function dismissInstall() {
  const banner = $('install-banner');
  if (banner) banner.style.display = 'none';
  localStorage.setItem('kree_install_dismissed', '1');
}

// ═══════════════════════════════════════════════════════════
// ── Mobile Mic Streaming (Hold-to-Speak) ─────────────────
// ═══════════════════════════════════════════════════════════
async function startMicStream() {
  const btn = $('floating-mic-btn');
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(micStream, { mimeType: 'audio/webm;codecs=opus' });

    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
        // Send raw binary audio blob chunks to Kree desktop
        ws.send(e.data);
      }
    };

    mediaRecorder.start(100); // chunk every 100ms
    if (btn) btn.classList.add('streaming');
    showToast('Streaming voice to Kree...');
  } catch(e) {
    showToast('Mic access denied');
    if (btn) btn.classList.remove('streaming');
  }
}

function stopMicStream() {
  const btn = $('floating-mic-btn');
  if (btn) btn.classList.remove('streaming');

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    try { mediaRecorder.stop(); } catch(e) {}
  }
  if (micStream) {
    micStream.getTracks().forEach(t => t.stop());
    micStream = null;
  }
  mediaRecorder = null;
}
