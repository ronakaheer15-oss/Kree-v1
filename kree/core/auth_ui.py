AUTH_FLOW_JS = """
(function(){
  if (document.getElementById('kree-auth-overlay')) return;

  var overlay = document.createElement('div');
  overlay.id = 'kree-auth-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;z-index:999999;background:#05070b;overflow:hidden;';
  overlay.innerHTML = `
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,.12),_transparent_40%),linear-gradient(180deg,#05070b_0%,#070a11_100%)]"></div>
    <div class="absolute inset-0 opacity-[0.03] pointer-events-none" style="background-image:radial-gradient(circle at 1px 1px,#fff 1px,transparent 0);background-size:28px 28px;"></div>
    <main class="relative z-10 flex min-h-screen items-center justify-center p-4 md:p-8">
      <div class="w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/10 bg-zinc-950/95 shadow-[0_30px_120px_rgba(0,0,0,.7)] backdrop-blur-2xl">
        <div class="grid lg:grid-cols-[1.05fr_.95fr]">
          <aside class="relative overflow-hidden border-b border-white/5 lg:border-b-0 lg:border-r border-white/5 bg-gradient-to-br from-black via-zinc-950 to-emerald-950/30 p-8 md:p-10 lg:p-12">
            <div class="absolute inset-0 opacity-[0.07] pointer-events-none" style="background-image:linear-gradient(135deg,rgba(255,255,255,.08)_25%,transparent_25%,transparent_50%,rgba(255,255,255,.08)_50%,rgba(255,255,255,.08)_75%,transparent_75%,transparent);background-size:24px 24px;"></div>
            <div class="relative flex h-full flex-col justify-between gap-10">
              <div>
                <div class="flex items-center gap-3 mb-8">
                  <div class="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 shadow-[0_0_24px_rgba(16,185,129,.2)]">
                    <span class="material-icons-outlined text-primary text-2xl">shield</span>
                  </div>
                  <div>
                    <div class="font-display text-xs font-bold tracking-[0.35em] text-primary uppercase">KREE IDENTITY GATE</div>
                    <div class="mt-1 font-mono text-[10px] tracking-[0.2em] text-zinc-500 uppercase">Cloud-backed onboarding shell</div>
                  </div>
                </div>
                <h1 class="max-w-xl font-display text-4xl font-black tracking-tight text-white md:text-5xl">
                  One sign-in, one personal PIN, one API key.
                </h1>
                <p class="mt-5 max-w-xl text-sm leading-7 text-zinc-400 md:text-base">
                  This flow is the first pass of the multi-user architecture. It keeps account identity, PIN setup, and API ownership separate so Kree can grow beyond a single machine profile.
                </p>
              </div>
              <div class="grid grid-cols-3 gap-3 text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                <div class="rounded-2xl border border-white/5 bg-white/5 px-4 py-4">
                  <div class="text-primary font-semibold">Login</div>
                  <div class="mt-1">Sign in or create an account</div>
                </div>
                <div class="rounded-2xl border border-white/5 bg-white/5 px-4 py-4">
                  <div class="text-primary font-semibold">PIN</div>
                  <div class="mt-1">Set or verify a 6-digit PIN</div>
                </div>
                <div class="rounded-2xl border border-white/5 bg-white/5 px-4 py-4">
                  <div class="text-primary font-semibold">API</div>
                  <div class="mt-1">Attach the user API key</div>
                </div>
              </div>
            </div>
          </aside>
          <section class="p-8 md:p-10 lg:p-12">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="font-display text-lg font-bold tracking-widest text-white uppercase">Account Access</div>
                <div id="auth-subtitle" class="mt-1 font-mono text-[10px] tracking-[0.18em] text-zinc-500 uppercase">Secure sign in</div>
              </div>
              <div class="rounded-full border border-white/10 bg-white/5 px-3 py-2 font-mono text-[10px] tracking-[0.2em] text-zinc-400 uppercase" id="auth-user-chip">No user</div>
            </div>

            <div class="mt-6 flex items-center gap-2" id="auth-stepbar">
              <div class="h-1.5 flex-1 rounded-full bg-primary"></div>
              <div class="h-1.5 flex-1 rounded-full bg-white/10"></div>
              <div class="h-1.5 flex-1 rounded-full bg-white/10"></div>
            </div>

            <div id="auth-message" class="mt-4 min-h-[1.25rem] font-mono text-[10px] tracking-[0.18em] text-zinc-500 uppercase"></div>

            <div id="auth-login-panel" class="mt-6 space-y-5">
              <div class="flex rounded-2xl border border-white/5 bg-black/30 p-1">
                <button id="tab-signin" class="flex-1 rounded-xl bg-primary px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-black uppercase">Sign in</button>
                <button id="tab-signup" class="flex-1 rounded-xl px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-zinc-400 uppercase">Create account</button>
              </div>

              <div id="signin-form" class="space-y-4">
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Email or handle</label>
                  <input id="signin-identifier" type="text" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="you@example.com or kree-user" />
                </div>
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Password</label>
                  <input id="signin-password" type="password" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="••••••••" />
                </div>
                <button id="signin-btn" class="w-full rounded-2xl bg-primary px-5 py-4 font-display text-xs font-bold tracking-[0.24em] text-black uppercase transition hover:bg-emerald-300">Continue</button>
              </div>

              <div id="signup-form" class="hidden space-y-4">
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Display name</label>
                  <input id="signup-display" type="text" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="Kree Operator" />
                </div>
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Handle</label>
                  <input id="signup-handle" type="text" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="kree-user" />
                </div>
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Email</label>
                  <input id="signup-email" type="email" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="you@example.com" />
                </div>
                <div>
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Password</label>
                  <input id="signup-password" type="password" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="Create a strong password" />
                </div>
                <button id="signup-btn" class="w-full rounded-2xl border border-primary/30 bg-primary/10 px-5 py-4 font-display text-xs font-bold tracking-[0.24em] text-primary uppercase transition hover:bg-primary/15">Create account</button>
              </div>
            </div>

            <div id="auth-pin-panel" class="mt-6 hidden space-y-5">
              <div class="rounded-2xl border border-white/5 bg-black/30 p-5">
                <div class="font-display text-sm font-bold tracking-[0.22em] text-white uppercase" id="pin-title">Create your 6-digit PIN</div>
                <div class="mt-2 text-[11px] leading-6 text-zinc-500" id="pin-help">The bootstrap PIN is temporary. Set your own PIN before continuing.</div>
                <div class="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
                  <input id="pin-input" type="password" inputmode="numeric" maxlength="6" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-lg tracking-[0.5em] text-white outline-none transition focus:border-primary/50" placeholder="000000" />
                  <input id="pin-confirm" type="password" inputmode="numeric" maxlength="6" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-lg tracking-[0.5em] text-white outline-none transition focus:border-primary/50" placeholder="Confirm" />
                </div>
                <button id="pin-btn" class="mt-4 w-full rounded-2xl bg-primary px-5 py-4 font-display text-xs font-bold tracking-[0.24em] text-black uppercase transition hover:bg-emerald-300">Save PIN</button>
              </div>
            </div>

            <div id="auth-api-panel" class="mt-6 hidden space-y-5">
              <div class="rounded-2xl border border-white/5 bg-black/30 p-5">
                <div class="font-display text-sm font-bold tracking-[0.22em] text-white uppercase">Add your API key</div>
                <div class="mt-2 text-[11px] leading-6 text-zinc-500">This key is stored per user and is used after sign-in for that account only.</div>
                <div class="mt-5">
                  <label class="mb-2 block font-mono text-[9px] tracking-[0.2em] text-zinc-500 uppercase">Gemini API key</label>
                  <input id="api-input" type="password" class="w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-4 font-mono text-sm text-white outline-none transition focus:border-primary/50" placeholder="AIza..." />
                </div>
                <button id="api-btn" class="mt-4 w-full rounded-2xl bg-primary px-5 py-4 font-display text-xs font-bold tracking-[0.24em] text-black uppercase transition hover:bg-emerald-300">Save API key</button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>`;
  document.body.appendChild(overlay);

  var state = {
    stage: 'auth',
    authTab: 'signin',
    activeUser: null,
    currentUserId: null,
    pinMode: 'setup',
    needsApiKey: false
  };

  function api(name) {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api[name]) return null;
    var args = Array.prototype.slice.call(arguments, 1);
    return window.pywebview.api[name].apply(null, args);
  }

  function setMessage(text, isError) {
    var message = document.getElementById('auth-message');
    if (!message) return;
    message.textContent = text || '';
    message.style.color = isError ? '#f87171' : '#6b7280';
  }

  function setUserChip(label) {
    var chip = document.getElementById('auth-user-chip');
    if (chip) chip.textContent = label || 'No user';
  }

  function setSubtitle(text) {
    var subtitle = document.getElementById('auth-subtitle');
    if (subtitle) subtitle.textContent = text || 'Secure sign in';
  }

  function showPanels(loginVisible, pinVisible, apiVisible) {
    document.getElementById('auth-login-panel').classList.toggle('hidden', !loginVisible);
    document.getElementById('auth-pin-panel').classList.toggle('hidden', !pinVisible);
    document.getElementById('auth-api-panel').classList.toggle('hidden', !apiVisible);
  }

  function showAuthForm(tabName) {
    var signinForm = document.getElementById('signin-form');
    var signupForm = document.getElementById('signup-form');
    var signinTab = document.getElementById('tab-signin');
    var signupTab = document.getElementById('tab-signup');
    if (signinForm) signinForm.classList.toggle('hidden', tabName !== 'signin');
    if (signupForm) signupForm.classList.toggle('hidden', tabName !== 'signup');
    if (signinTab && signupTab) {
      signinTab.className = tabName === 'signin'
        ? 'flex-1 rounded-xl bg-primary px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-black uppercase'
        : 'flex-1 rounded-xl px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-zinc-400 uppercase';
      signupTab.className = tabName === 'signup'
        ? 'flex-1 rounded-xl bg-primary px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-black uppercase'
        : 'flex-1 rounded-xl px-4 py-3 font-display text-[11px] font-bold tracking-[0.22em] text-zinc-400 uppercase';
    }
  }

  function setStepbar(index) {
    var bars = document.querySelectorAll('#auth-stepbar > div');
    bars.forEach(function(bar, barIndex) {
      if (barIndex <= index) {
        bar.className = 'h-1.5 flex-1 rounded-full bg-primary';
      } else {
        bar.className = 'h-1.5 flex-1 rounded-full bg-white/10';
      }
    });
  }

  function renderStage(stage, payload) {
    state.stage = stage;
    payload = payload || {};
    var user = payload.user || state.activeUser;
    if (user) {
      state.activeUser = user;
      state.currentUserId = user.user_id || null;
      setUserChip(user.display_name || user.handle || 'Active user');
    }

    if (stage === 'auth') {
      setSubtitle(state.authTab === 'signup' ? 'Create a Kree account' : 'Secure sign in');
      setStepbar(0);
      showPanels(true, false, false);
      showAuthForm(state.authTab);
      setMessage(payload.message || '');
      return;
    }

    if (stage === 'pin_setup') {
      setSubtitle('Set your personal PIN');
      setStepbar(1);
      showPanels(false, true, false);
      var pinTitle = document.getElementById('pin-title');
      var pinHelp = document.getElementById('pin-help');
      if (pinTitle) pinTitle.textContent = 'Create your 6-digit PIN';
      if (pinHelp) pinHelp.textContent = 'Your bootstrap PIN is temporary. Set a personal 6-digit PIN to continue.';
      document.getElementById('pin-confirm').classList.remove('hidden');
      setMessage(payload.message || '');
      return;
    }

    if (stage === 'pin_verify') {
      setSubtitle('Verify your PIN');
      setStepbar(1);
      showPanels(false, true, false);
      var pinTitleVerify = document.getElementById('pin-title');
      var pinHelpVerify = document.getElementById('pin-help');
      if (pinTitleVerify) pinTitleVerify.textContent = 'Enter your PIN';
      if (pinHelpVerify) pinHelpVerify.textContent = 'Use your personal PIN to continue into Kree.';
      document.getElementById('pin-confirm').classList.add('hidden');
      setMessage(payload.message || '');
      return;
    }

    if (stage === 'api_setup') {
      setSubtitle('Attach your API key');
      setStepbar(2);
      showPanels(false, false, true);
      setMessage(payload.message || '');
      return;
    }

    if (stage === 'complete') {
      completeFlow(payload.message || 'Access granted.');
    }
  }

  function completeFlow(message) {
    // Show analytics opt-in before final dismiss (only on first run)
    if (!state._analyticsAsked) {
      state._analyticsAsked = true;
      
      // Hide all panels and show analytics opt-in
      showPanels(false, false, false);
      setSubtitle('One more thing');
      setStepbar(3);
      
      var container = document.getElementById('auth-api-panel').parentElement;
      var analyticsPanel = document.createElement('div');
      analyticsPanel.id = 'auth-analytics-panel';
      analyticsPanel.innerHTML = `
        <div class="mt-6">
          <div class="flex items-center gap-3 mb-4">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl border border-primary/20 bg-primary/10">
              <span class="material-icons-outlined text-primary text-xl">insights</span>
            </div>
            <div>
              <div class="text-white font-bold text-sm tracking-wide">Help Improve Kree</div>
              <div class="text-zinc-500 text-xs font-mono mt-0.5">Anonymous usage data only</div>
            </div>
          </div>
          <p class="text-zinc-400 text-sm leading-relaxed mb-6">
            Send anonymous usage data to help improve Kree for everyone.<br>
            <span class="text-zinc-500 text-xs">No personal data is collected — just which features you use and crash reports.</span>
          </p>
          <div class="flex gap-3">
            <button id="analytics-yes-btn" class="flex-1 rounded-xl border border-primary/30 bg-primary/10 py-3 font-mono text-xs font-bold tracking-widest text-primary uppercase hover:bg-primary/20 transition">Yes, help improve Kree</button>
            <button id="analytics-no-btn" class="flex-1 rounded-xl border border-white/10 bg-white/5 py-3 font-mono text-xs font-bold tracking-widest text-zinc-500 uppercase hover:bg-white/10 transition">No thanks</button>
          </div>
        </div>
      `;
      container.appendChild(analyticsPanel);
      
      document.getElementById('analytics-yes-btn').addEventListener('click', function(){
        if (window.pywebview && window.pywebview.api && window.pywebview.api.set_analytics_enabled) {
          window.pywebview.api.set_analytics_enabled(true);
        }
        analyticsPanel.remove();
        _dismissOverlay(message);
      });
      document.getElementById('analytics-no-btn').addEventListener('click', function(){
        if (window.pywebview && window.pywebview.api && window.pywebview.api.set_analytics_enabled) {
          window.pywebview.api.set_analytics_enabled(false);
        }
        analyticsPanel.remove();
        _dismissOverlay(message);
      });
      return;
    }
    _dismissOverlay(message);
  }

  function _dismissOverlay(message) {
    setMessage(message || 'Access granted.');
    if (window.pywebview && window.pywebview.api && window.pywebview.api.on_auth_flow_complete) {
      window.pywebview.api.on_auth_flow_complete().then(function(){
        overlay.style.transition = 'opacity .35s ease';
        overlay.style.opacity = '0';
        setTimeout(function(){
          overlay.remove();
        }, 380);
      });
    } else {
      overlay.remove();
    }
  }

  function applyResult(result, fallbackStage) {
    if (!result || result.ok === false) {
      setMessage((result && result.message) || 'Authentication failed.', true);
      return;
    }
    if (result.user) {
      state.activeUser = result.user;
      state.currentUserId = result.user.user_id || null;
      setUserChip(result.user.display_name || result.user.handle || 'Active user');
    }
    if (result.state && result.state.active_user) {
      state.activeUser = result.state.active_user;
      state.currentUserId = result.state.active_user_id || null;
    }
    if (result.next_stage) {
      renderStage(result.next_stage, result);
      return;
    }
    renderStage(fallbackStage || state.stage, result);
  }

  function refreshInitialState() {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.get_auth_state) {
      renderStage('auth', { message: 'Waiting for backend bridge...' });
      return;
    }
    window.pywebview.api.get_auth_state().then(function(result) {
      state.authTab = result && result.has_users === false ? 'signup' : 'signin';
      showAuthForm(state.authTab);
      if (result && result.active_user) {
        state.activeUser = result.active_user;
        state.currentUserId = result.active_user_id || result.active_user.user_id || null;
        setUserChip(result.active_user.display_name || result.active_user.handle || 'Active user');
      }
      renderStage('auth', result || {});
    });
  }

  document.getElementById('tab-signin').addEventListener('click', function(){
    state.authTab = 'signin';
    showAuthForm(state.authTab);
    renderStage('auth', { message: '' });
  });

  document.getElementById('tab-signup').addEventListener('click', function(){
    state.authTab = 'signup';
    showAuthForm(state.authTab);
    renderStage('auth', { message: '' });
  });

  document.getElementById('signin-btn').addEventListener('click', function(){
    var identifier = document.getElementById('signin-identifier').value.trim();
    var password = document.getElementById('signin-password').value;
    if (!identifier || !password) {
      setMessage('Enter your handle or email and password.', true);
      return;
    }
    setMessage('Signing in...');
    api('sign_in_user', identifier, password).then(function(result){
      applyResult(result, 'auth');
    });
  });

  document.getElementById('signup-btn').addEventListener('click', function(){
    var displayName = document.getElementById('signup-display').value.trim();
    var handle = document.getElementById('signup-handle').value.trim();
    var email = document.getElementById('signup-email').value.trim();
    var password = document.getElementById('signup-password').value;
    if (!handle || !password) {
      setMessage('Choose a handle and password to create the account.', true);
      return;
    }
    setMessage('Creating account...');
    api('create_user', handle, password, email, displayName).then(function(result){
      applyResult(result, 'pin_setup');
    });
  });

  document.getElementById('pin-btn').addEventListener('click', function(){
    var pin = document.getElementById('pin-input').value.trim();
    var confirmPin = document.getElementById('pin-confirm').classList.contains('hidden') ? pin : document.getElementById('pin-confirm').value.trim();
    if (!state.currentUserId) {
      setMessage('No active user session.', true);
      return;
    }
    if (!pin || pin.length !== 6) {
      setMessage('Enter a 6-digit PIN.', true);
      return;
    }
    if (!document.getElementById('pin-confirm').classList.contains('hidden') && pin !== confirmPin) {
      setMessage('PINs do not match.', true);
      return;
    }

    if (state.stage === 'pin_setup') {
      setMessage('Saving PIN...');
      api('set_user_pin', state.currentUserId, pin).then(function(result){
        applyResult(result, 'api_setup');
      });
      return;
    }

    setMessage('Verifying PIN...');
    api('verify_user_pin', state.currentUserId, pin).then(function(result){
      if (!result || result.ok === false) {
        setMessage((result && result.message) || 'Invalid PIN.', true);
        return;
      }
      if (result.next_stage) {
        applyResult(result, result.next_stage);
      } else {
        applyResult(result, 'api_setup');
      }
    });
  });

  document.getElementById('api-btn').addEventListener('click', function(){
    var key = document.getElementById('api-input').value.trim();
    if (!state.currentUserId) {
      setMessage('No active user session.', true);
      return;
    }
    if (!key) {
      setMessage('API key cannot be empty.', true);
      return;
    }
    setMessage('Saving API key...');
    api('save_user_api_key', state.currentUserId, key).then(function(result){
      if (!result || result.ok === false) {
        setMessage((result && result.message) || 'Could not save API key.', true);
        return;
      }
      renderStage('complete', result);
    });
  });

  document.addEventListener('keydown', function(e){
    if (e.key === 'Enter') {
      if (!document.getElementById('auth-login-panel').classList.contains('hidden')) {
        if (state.authTab === 'signup') {
          document.getElementById('signup-btn').click();
        } else {
          document.getElementById('signin-btn').click();
        }
        return;
      }
      if (!document.getElementById('auth-pin-panel').classList.contains('hidden')) {
        document.getElementById('pin-btn').click();
        return;
      }
      if (!document.getElementById('auth-api-panel').classList.contains('hidden')) {
        document.getElementById('api-btn').click();
      }
    }
  });

  refreshInitialState();
})();
"""