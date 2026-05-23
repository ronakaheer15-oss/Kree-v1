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
