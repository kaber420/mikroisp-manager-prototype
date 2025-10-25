document.addEventListener('DOMContentLoaded', async () => {
    const API_BASE_URL = window.location.origin;
    const currentHost = window.location.pathname.split('/').pop();
    let charts = {};
    let isStopping = false;

    let backgroundRefreshIntervalId = null; 
    let refreshIntervalMs = 60000; 

    const deviceInfoCard = document.getElementById('device-info-card');
    const chartsCard = document.getElementById('charts-card');
    const clientListSection = document.getElementById('client-list-section');

    async function loadAndSetRefreshInterval() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/settings`);
            if (!response.ok) throw new Error('Failed to fetch settings');
            const settings = await response.json();
            const intervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);
            if (!isNaN(intervalSeconds) && intervalSeconds > 0) {
                refreshIntervalMs = intervalSeconds * 1000;
                console.log(`Intervalo de refresco de fondo establecido en: ${intervalSeconds} segundos.`);
            } else {
                console.warn(`Valor de intervalo no encontrado en settings. Usando por defecto: ${refreshIntervalMs / 1000}s.`);
            }
        } catch (error) {
            console.error('No se pudo cargar la configuración del intervalo. Usando valor por defecto.', error);
        }
    }

    function stopBackgroundRefresh() {
        if (backgroundRefreshIntervalId) {
            clearInterval(backgroundRefreshIntervalId);
            backgroundRefreshIntervalId = null;
            console.log('Refresco de fondo detenido.');
        }
    }

    function startBackgroundRefresh() {
        stopBackgroundRefresh();
        console.log(`Iniciando refresco de fondo cada ${refreshIntervalMs / 1000} segundos...`);
        backgroundRefreshIntervalId = setInterval(loadApDetails, refreshIntervalMs);
    }

    let diagnosticManager = {
        intervalId: null, timeoutId: null, countdownId: null,
        stop: function(shouldUpdateUI = true) {
            if (this.intervalId) clearInterval(this.intervalId);
            if (this.timeoutId) clearTimeout(this.timeoutId);
            if (this.countdownId) clearInterval(this.countdownId);
            this.intervalId = null; this.timeoutId = null; this.countdownId = null;
            if (shouldUpdateUI) {
                const toggle = document.getElementById('auto-refresh-toggle');
                const timerSpan = document.getElementById('refresh-timer');
                if (toggle) toggle.checked = false;
                if (timerSpan) timerSpan.textContent = '';
                document.getElementById('main-hostname').classList.remove('text-orange');
            }
            console.log('Diagnostic mode stopped.');
        }
    };

    function formatBytes(bytes) {
        if (bytes == null || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatThroughput(kbps) {
        if (kbps == null) return 'N/A';
        if (kbps < 1000) return `${kbps.toFixed(1)} kbps`;
        return `${(kbps / 1000).toFixed(1)} Mbps`;
    }

    // --- CAMBIO: Renombrado para consistencia ---
    function getCPEHealthStatus(cpe) {
        if (cpe.eth_plugged === false) return { colorClass: 'border-danger', label: 'Cable Unplugged', icon: 'power_off' };
        if (cpe.eth_speed != null && cpe.eth_speed < 100) return { colorClass: 'border-orange', label: `${cpe.eth_speed} Mbps Link`, icon: 'warning' };
        if (cpe.signal == null) return { colorClass: 'border-text-secondary', label: 'No Signal Data', icon: 'signal_cellular_off' };
        if (cpe.signal < -75) return { colorClass: 'border-warning', label: 'Weak Signal', icon: 'signal_cellular_1_bar' };
        return { colorClass: 'border-success', label: 'Good Signal', icon: 'signal_cellular_4_bar' };
    }

    function createChart(canvasId, type, labels, datasets, unit) {
        if (charts[canvasId]) { charts[canvasId].destroy(); }
        const ctx = document.getElementById(canvasId).getContext('2d');
        charts[canvasId] = new Chart(ctx, { type, data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: true, scales: { x: { type: 'time', time: { tooltipFormat: 'MMM d, HH:mm', unit }, grid: { color: 'rgba(51, 65, 85, 0.5)' }, ticks: { color: '#94A3B8', maxRotation: 20, autoSkip: true, maxTicksLimit: 6 } }, y: { beginAtZero: true, grid: { color: 'rgba(51, 65, 85, 0.5)' }, ticks: { color: '#94A3B8' } } }, plugins: { legend: { labels: { color: '#F1F5F9' } }, tooltip: { titleColor: '#F1F5F9', bodyColor: '#cbd5e1' } }, interaction: { intersect: false, mode: 'index' } } });
    }

    function updateChartsWithLiveData(apData) {
        const timestamp = Date.now();
        ['clientsChart', 'airtimeChart', 'throughputChart'].forEach(chartId => {
            const chart = charts[chartId];
            if (!chart) return;
            chart.data.labels.push(timestamp);
            if (chartId === 'clientsChart') { chart.data.datasets[0].data.push(apData.client_count); }
            else if (chartId === 'airtimeChart') { const airtime = apData.airtime_total_usage != null ? (apData.airtime_total_usage / 10.0) : null; chart.data.datasets[0].data.push(airtime); }
            else if (chartId === 'throughputChart') { chart.data.datasets[0].data.push(apData.total_throughput_rx); chart.data.datasets[1].data.push(apData.total_throughput_tx); }
            if (chart.data.labels.length > 30) { chart.data.labels.shift(); chart.data.datasets.forEach(dataset => dataset.data.shift()); }
            chart.update('quiet');
        });
    }

    function updatePageWithLiveData(ap) {
        document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-orange"><div class="size-2 rounded-full bg-orange"></div><span>Live</span></div>`;
        document.getElementById('detail-clients').textContent = ap.client_count != null ? ap.client_count : 'N/A';
        document.getElementById('detail-noise').textContent = ap.noise_floor != null ? `${ap.noise_floor} dBm` : 'N/A';
        const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
        const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
        const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
        document.getElementById('detail-airtime').textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
        document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_rx)} / ${formatThroughput(ap.total_throughput_tx)}`;
        document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_rx_bytes)} / ${formatBytes(ap.total_tx_bytes)}`;
        renderCPEList(ap.clients);
        updateChartsWithLiveData(ap);
    }

    async function refreshLiveData() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/live`);
            if (!response.ok) { document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Unreachable</span></div>`; return; }
            const apData = await response.json();
            updatePageWithLiveData(apData);
        } catch (error) {
            console.error("Error during live data refresh:", error);
            await stopDiagnosticMode();
        }
    }

    async function stopDiagnosticMode() {
        isStopping = true;
        diagnosticManager.stop(true);
        console.log('Saliendo del Modo Live, restaurando vista de historial...');
        try {
            await loadApDetails();
            const activePeriodButton = document.querySelector('.chart-button.active');
            const periodToLoad = activePeriodButton ? activePeriodButton.dataset.period : '24h';
            await loadChartData(periodToLoad);
            console.log('Vista de historial restaurada.');
            startBackgroundRefresh();
        } catch (error) {
            console.error('Ocurrió un error al restaurar la vista de historial:', error);
        }
        setTimeout(() => { isStopping = false; }, 500);
    }

    async function startDiagnosticMode() {
        stopBackgroundRefresh();
        diagnosticManager.stop(false);
        const DURATION_MINUTES = 5;
        let remaining = DURATION_MINUTES * 60;
        const timerSpan = document.getElementById('refresh-timer');
        const toggle = document.getElementById('auto-refresh-toggle');
        try {
            const apSettingsResponse = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`);
            if (!apSettingsResponse.ok) throw new Error("Could not fetch AP settings");
            const apSettings = await apSettingsResponse.json();
            const refreshIntervalSeconds = apSettings.monitor_interval;
            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                document.getElementById('main-hostname').classList.add('text-orange');
                Object.values(charts).forEach(chart => { chart.data.labels = []; chart.data.datasets.forEach(dataset => dataset.data = []); chart.update('quiet'); });
                await refreshLiveData();
                diagnosticManager.intervalId = setInterval(refreshLiveData, refreshIntervalSeconds * 1000);
                const countdown = () => { remaining--; const minutes = Math.floor(remaining / 60); const seconds = remaining % 60; timerSpan.textContent = `(${minutes}:${seconds.toString().padStart(2, '0')})`; if (remaining <= 0) { stopDiagnosticMode(); } };
                countdown();
                diagnosticManager.countdownId = setInterval(countdown, 1000);
                diagnosticManager.timeoutId = setTimeout(stopDiagnosticMode, DURATION_MINUTES * 60 * 1000);
            } else {
                alert('No specific monitor interval found for this AP. Please set a default in the edit menu.');
                if (toggle) toggle.checked = false;
            }
        } catch (error) {
            alert('Could not load AP settings to start diagnostic mode.');
            if (toggle) toggle.checked = false;
        }
    }

    function loadChartData(period = '24h') {
        if (chartsCard) {
            chartsCard.style.filter = 'blur(4px)';
            chartsCard.style.opacity = '0.6';
        }
        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/history?period=${period}`);
                if (!response.ok) throw new Error('Failed to fetch history');
                const data = await response.json();
                const labels = data.history.map(p => new Date(p.timestamp.endsWith('Z') ? p.timestamp : p.timestamp + 'Z'));
                const timeUnit = period === '24h' ? 'hour' : 'day';
                createChart('clientsChart', 'line', labels, [{ label: 'Clients', data: data.history.map(p => p.client_count), borderColor: '#3B82F6', tension: 0.2, fill: false, pointRadius: 0 }], timeUnit);
                createChart('airtimeChart', 'line', labels, [{ label: 'Airtime (%)', data: data.history.map(p => p.airtime_total_usage != null ? (p.airtime_total_usage / 10.0) : null), borderColor: '#EAB308', tension: 0.2, fill: false, pointRadius: 0 }], timeUnit);
                createChart('throughputChart', 'line', labels, [ { label: 'Download (kbps)', data: data.history.map(p => p.total_throughput_rx), borderColor: '#22C55E', tension: 0.2, fill: false, pointRadius: 0 }, { label: 'Upload (kbps)', data: data.history.map(p => p.total_throughput_tx), borderColor: '#F97316', tension: 0.2, fill: false, pointRadius: 0 } ], timeUnit);
            } catch (error) {
                console.error("Error loading chart data:", error);
            } finally {
                if (chartsCard) {
                    setTimeout(() => {
                        chartsCard.style.filter = 'blur(0px)';
                        chartsCard.style.opacity = '1';
                    }, 50);
                }
            }
        }, 300);
    }

    // --- CAMBIO: Renombrado para consistencia ---
    function renderCPEList(cpes) {
        const cpeListDiv = document.getElementById('client-list');
        if (!cpes || cpes.length === 0) { cpeListDiv.innerHTML = '<p class="text-text-secondary col-span-3">No CPEs are currently connected to this AP.</p>'; return; }
        cpeListDiv.innerHTML = '';
        cpes.forEach(cpe => { 
            const health = getCPEHealthStatus(cpe); 
            const card = document.createElement('div'); 
            card.className = `bg-surface-1 rounded-lg border-l-4 p-4 flex flex-col gap-3 transition-shadow hover:shadow-lg ${health.colorClass}`; 
            const t_rx = cpe.throughput_rx_kbps != null ? `${cpe.throughput_rx_kbps.toFixed(1)}` : 'N/A'; 
            const t_tx = cpe.throughput_tx_kbps != null ? `${cpe.throughput_tx_kbps.toFixed(1)}` : 'N/A'; 
            const chains = cpe.signal_chain0 != null && cpe.signal_chain1 != null ? `(${cpe.signal_chain0}/${cpe.signal_chain1})` : ''; 
            const c_dl = cpe.dl_capacity ? (cpe.dl_capacity / 1000).toFixed(0) : 'N/A'; 
            const c_ul = cpe.ul_capacity ? (cpe.ul_capacity / 1000).toFixed(0) : 'N/A'; 
            card.innerHTML = `<div class="flex justify-between items-start"><div><p class="font-bold text-text-primary">${cpe.cpe_hostname || 'Unnamed Device'}</p><p class="text-xs text-text-secondary font-mono">${cpe.ip_address || 'No IP'}</p></div><div class="flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full bg-black bg-opacity-20"><span class="material-symbols-outlined text-xs">${health.icon}</span><span>${health.label}</span></div></div><div class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-text-secondary"><span>Signal / Chains:</span><span class="font-semibold text-text-primary text-right">${cpe.signal || 'N/A'} dBm ${chains}</span><span>Noise Floor:</span><span class="font-semibold text-text-primary text-right">${cpe.noisefloor || 'N/A'} dBm</span><span>Capacity (DL/UL):</span><span class="font-semibold text-text-primary text-right">${c_dl} / ${c_ul} Mbps</span><span>Throughput (DL/UL):</span><span class="font-semibold text-text-primary text-right">${t_rx} / ${t_tx} kbps</span><span>Total Data (DL/UL):</span><span class="font-semibold text-text-primary text-right">${formatBytes(cpe.total_tx_bytes)} / ${formatBytes(cpe.total_rx_bytes)}</span><span>Cable Status:</span><span class="font-semibold text-text-primary text-right">${cpe.eth_speed != null ? `${cpe.eth_speed} Mbps` : 'N/A'}</span></div>`; 
            cpeListDiv.appendChild(card); 
        });
    }
    
    // --- CAMBIO: Renombrado para consistencia y endpoint actualizado ---
    async function loadCPEDataFromHistory() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}/cpes`);
            if (!response.ok) throw new Error('Failed to fetch CPEs');
            const cpes = await response.json();
            renderCPEList(cpes);
        } catch (error) {
            console.error("Error loading CPE data:", error);
            document.getElementById('client-list').innerHTML = '<p class="text-danger col-span-3">Failed to load CPE data.</p>';
        }
    }
    
    function loadApDetails() {
        if (deviceInfoCard) { deviceInfoCard.style.filter = 'blur(4px)'; deviceInfoCard.style.opacity = '0.6'; }
        if (clientListSection) { clientListSection.style.filter = 'blur(4px)'; clientListSection.style.opacity = '0.6'; }

        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`);
                if (!response.ok) throw new Error('AP not found');
                const ap = await response.json();
                document.title = `${ap.hostname || ap.host} - AP Details`;
                document.getElementById('breadcrumb-hostname').textContent = ap.hostname || ap.host;
                document.getElementById('main-hostname').textContent = ap.hostname || ap.host;
                document.getElementById('detail-host').textContent = ap.host || 'N/A';
                if (!diagnosticManager.intervalId) {
                    document.getElementById('detail-status').innerHTML = `<div class="flex items-center gap-2 font-semibold"><div class="size-2 rounded-full ${ap.last_status === 'online' ? 'bg-success' : 'bg-danger'}"></div><span>${ap.last_status ? ap.last_status.charAt(0).toUpperCase() + ap.last_status.slice(1) : 'Unknown'}</span></div>`;
                }
                document.getElementById('detail-model').textContent = ap.model || 'N/A';
                document.getElementById('detail-mac').textContent = ap.mac || 'N/A';
                document.getElementById('detail-firmware').textContent = ap.firmware || 'N/A';
                document.getElementById('detail-essid').textContent = ap.essid || 'N/A';
                const zonesRes = await fetch(`${API_BASE_URL}/api/zonas`);
                const zones = await zonesRes.json();
                const zone = zones.find(z => z.id === ap.zona_id);
                document.getElementById('detail-zona').textContent = zone ? zone.nombre : (ap.zona_nombre || 'N/A');
                document.getElementById('detail-clients').textContent = ap.client_count != null ? ap.client_count : 'N/A';
                document.getElementById('detail-noise').textContent = ap.noise_floor != null ? `${ap.noise_floor} dBm` : 'N/A';
                document.getElementById('detail-frequency').textContent = ap.frequency != null ? `${ap.frequency} MHz / ${ap.chanbw} MHz` : 'N/A';
                document.getElementById('detail-sats').textContent = ap.gps_sats != null ? ap.gps_sats : 'N/A';
                const airtimeTotal = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeTx = ap.airtime_tx_usage != null ? `${(ap.airtime_tx_usage / 10.0).toFixed(1)}%` : 'N/A';
                const airtimeRx = ap.airtime_rx_usage != null ? `${(ap.airtime_rx_usage / 10.0).toFixed(1)}%` : 'N/A';
                document.getElementById('detail-airtime').textContent = `${airtimeTotal} (Tx: ${airtimeTx} / Rx: ${airtimeRx})`;
                document.getElementById('detail-throughput').textContent = `${formatThroughput(ap.total_throughput_rx)} / ${formatThroughput(ap.total_throughput_tx)}`;
                document.getElementById('detail-total-data').textContent = `${formatBytes(ap.total_tx_bytes)} / ${formatBytes(ap.total_rx_bytes)}`;
                document.getElementById('detail-gps').textContent = ap.gps_lat && ap.gps_lon ? `${ap.gps_lat.toFixed(6)}, ${ap.gps_lon.toFixed(6)}` : 'N/A';
                document.getElementById('edit-ap-button').addEventListener('click', () => openEditModal(ap));
                document.getElementById('delete-ap-button').addEventListener('click', handleDelete);
                
                if (!diagnosticManager.intervalId) {
                    await loadCPEDataFromHistory();
                }
            } catch (error) {
                console.error("Error in loadApDetails:", error);
                document.getElementById('main-hostname').textContent = 'Error';
            } finally {
                setTimeout(() => {
                    if (deviceInfoCard) { deviceInfoCard.style.filter = 'blur(0px)'; deviceInfoCard.style.opacity = '1'; }
                    if (clientListSection) { clientListSection.style.filter = 'blur(0px)'; clientListSection.style.opacity = '1'; }
                }, 50);
            }
        }, 300);
    }

    async function handleEditFormSubmit(event) {
        event.preventDefault();
        const editApForm = document.getElementById('edit-ap-form');
        const formData = new FormData(editApForm);
        const data = { username: formData.get('username'), zona_id: parseInt(formData.get('zona_id'), 10) };
        const password = formData.get('password');
        if (password) { data.password = password; }
        const monitorInterval = formData.get('monitor_interval');
        if (monitorInterval) { data.monitor_interval = parseInt(monitorInterval, 10); }
        try {
            const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (!response.ok) throw new Error('Failed to update AP');
            closeEditModal();
            loadApDetails();
        } catch (error) {
            document.getElementById('edit-form-error').textContent = error.message;
            document.getElementById('edit-form-error').classList.remove('hidden');
        }
    }

    async function handleDelete() {
        const apHostname = document.getElementById('main-hostname').textContent;
        if (confirm(`Are you sure you want to delete the AP "${apHostname}" (${currentHost})?\nThis action cannot be undone.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/aps/${encodeURIComponent(currentHost)}`, { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to delete AP');
                alert('AP deleted successfully.');
                window.location.href = '/';
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }
    
    function openEditModal(apData){ 
        document.getElementById('edit-host').value = apData.host; 
        document.getElementById('edit-username').value = apData.username; 
        document.getElementById('edit-monitor_interval').value = apData.monitor_interval; 
        populateZoneSelect(document.getElementById('edit-zona_id'), apData.zona_id); 
        document.getElementById('edit-ap-modal').classList.add('is-open');
    }

    function closeEditModal(){ 
        document.getElementById('edit-ap-form').reset(); 
        document.getElementById('edit-form-error').classList.add('hidden'); 
        document.getElementById('edit-ap-modal').classList.remove('is-open'); 
    }

    async function populateZoneSelect(selectElement, selectedId){ 
        try { 
            const response = await fetch(`${API_BASE_URL}/api/zonas`); 
            const zones = await response.json(); 
            selectElement.innerHTML = ''; 
            zones.forEach(zone => { const option = document.createElement('option'); option.value = zone.id; option.textContent = zone.nombre; if(zone.id === selectedId) { option.selected = true; } selectElement.appendChild(option); }); 
        } catch(error) { 
            console.error('Failed to load zones for modal:', error); 
        } 
    }
    
    // --- Initial Setup ---
    console.log("--- DOMContentLoaded ---");

    document.querySelectorAll('.chart-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.chart-button').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            loadChartData(button.dataset.period);
        });
    });

    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.checked = false;
        autoRefreshToggle.addEventListener('change', async () => {
            if (isStopping) return;
            if (autoRefreshToggle.checked) {
                await startDiagnosticMode();
            } else {
                await stopDiagnosticMode();
            }
        });
    }

    await loadAndSetRefreshInterval();
    loadApDetails();
    loadChartData('24h');
    startBackgroundRefresh();

    const editCancelButton = document.getElementById('edit-cancel-button');
    const editApForm = document.getElementById('edit-ap-form');
    
    if (editCancelButton && editApForm) {
        editCancelButton.addEventListener('click', closeEditModal);
        editApForm.addEventListener('submit', handleEditFormSubmit);
    } else {
        console.error("Los elementos del formulario de edición no se encontraron. La funcionalidad de edición puede fallar.");
    }
    
    console.log("--- Initialization Finished ---");
});