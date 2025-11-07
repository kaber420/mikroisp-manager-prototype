document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let refreshIntervalId = null;
    
    // NOTA: allAps, allZones, currentFilter, y applyFilter han sido eliminados.
    
    async function loadTopStats() {
        const topAirtimeList = document.getElementById('top-airtime-list');
        const topSignalList = document.getElementById('top-signal-list');
        if (!topAirtimeList || !topSignalList) return;

        // Poner en estado de carga
        topAirtimeList.innerHTML = `<div class="text-text-secondary text-sm">Loading...</div>`;
        topSignalList.innerHTML = `<div class="text-text-secondary text-sm">Loading...</div>`;
        topAirtimeList.style.filter = 'blur(4px)';
        topAirtimeList.style.opacity = '0.6';
        topSignalList.style.filter = 'blur(4px)';
        topSignalList.style.opacity = '0.6';
        topAirtimeList.style.transition = 'filter 0.3s ease, opacity 0.3s ease';
        topSignalList.style.transition = 'filter 0.3s ease, opacity 0.3s ease';
        
        try {
            const [airtimeRes, signalRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/stats/top-aps-by-airtime`),
                fetch(`${API_BASE_URL}/api/stats/top-cpes-by-signal`)
            ]);
            
            // --- Carga de Airtime ---
            if (airtimeRes.ok) {
                const topAirtime = await airtimeRes.json();
                topAirtimeList.innerHTML = ''; // Limpiar "Loading..."
                if(topAirtime.length > 0) {
                    topAirtime.forEach(ap => { 
                        topAirtimeList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${ap.hostname 
                        || ap.host}</p><span class="text-sm font-bold text-warning">${(ap.airtime_total_usage / 10.0).toFixed(1)}%</span></div>`; 
                    });
                } else { 
                    topAirtimeList.innerHTML = `<div class="text-text-secondary text-sm">No airtime data available.</div>`; 
                }
            } else {
                 throw new Error('Failed to load top airtime');
            }
            
            // --- Carga de Signal ---
            if (signalRes.ok) {
                const topSignal = await signalRes.json();
                topSignalList.innerHTML = ''; // Limpiar "Loading..."
                if(topSignal.length > 0) {
                    topSignal.forEach(cpe => { 
                        topSignalList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${cpe.cpe_hostname || 
                        cpe.cpe_mac}</p><span class="text-sm font-bold text-danger">${cpe.signal} dBm</span></div>`; 
                    });
                } else { 
                    topSignalList.innerHTML = `<div class="text-text-secondary text-sm">No CPE signal data available.</div>`;
                }
            } else {
                throw new Error('Failed to load top signal');
            }

            // Quitar blur en éxito
            setTimeout(() => {
                topAirtimeList.style.filter = 'blur(0px)';
                topAirtimeList.style.opacity = '1';
                topSignalList.style.filter = 'blur(0px)';
                topSignalList.style.opacity = '1';
            }, 50);

        } catch (error) {
            console.error("Error loading top stats:", error);
            topAirtimeList.innerHTML = `<div class="text-danger text-sm">Error loading data.</div>`;
            topSignalList.innerHTML = `<div class="text-danger text-sm">Error loading data.</div>`;
            topAirtimeList.style.filter = 'blur(0px)';
            topAirtimeList.style.opacity = '1';
            topSignalList.style.filter = 'blur(0px)';
            topSignalList.style.opacity = '1';
        }
    }

    async function loadInitialData() {
        try {
            // --- INICIO DE CAMBIOS ---
            // 'zonesRes' ya no es necesario aquí
            const [apsRes, cpeCountRes] = await Promise.all([ 
                fetch(`${API_BASE_URL}/api/aps`),
                fetch(`${API_BASE_URL}/api/stats/cpe-count`)
            ]);

            // if (!zonesRes.ok) throw new Error(`Failed to load zones (${zonesRes.status})`); // Eliminado
            if (!apsRes.ok) throw new Error(`Failed to load APs (${apsRes.status})`);
            if (!cpeCountRes.ok) throw new Error(`Failed to load CPE count (${cpeCountRes.status})`);
            
            // allZones = await zonesRes.json(); // Eliminado
            const allAps = await apsRes.json(); // Se declara localmente
            const cpeCountData = await cpeCountRes.json();
            
            // El bloque 'nav' ha sido eliminado por completo
            
            // --- Calcular Estadísticas ---
            let cpesOnline = 0;
            let apsOnline = 0;
            
            allAps.forEach(ap => { 
                if (ap.last_status === 'online') { 
                    apsOnline++;
                    if (ap.client_count != null) { 
                        cpesOnline += ap.client_count;
                    } 
                } 
            });
            const totalAps = allAps.length;
            const apsOffline = totalAps - apsOnline;
            
            const totalCpes = cpeCountData.total_cpes;
            const cpesOffline = totalCpes - cpesOnline;
            
            updateStatWithTransition('total-aps', totalAps);
            updateStatWithTransition('aps-online', apsOnline);
            updateStatWithTransition('aps-offline', apsOffline);
            
            updateStatWithTransition('total-cpes', totalCpes);
            updateStatWithTransition('cpes-online', cpesOnline);
            updateStatWithTransition('cpes-offline', cpesOffline);
            
            // applyFilter() ha sido eliminado
            loadTopStats(); // Cargar los "Top 5"

        } catch (error) {
            console.error("Error loading initial data:", error);
            // Mostrar error en la UI para que el usuario sepa qué falló
            updateStatWithTransition('total-aps', 'ERR');
            updateStatWithTransition('aps-online', 'ERR');
            updateStatWithTransition('aps-offline', 'ERR');
            updateStatWithTransition('total-cpes', 'ERR');
            updateStatWithTransition('cpes-online', 'ERR');
            updateStatWithTransition('cpes-offline', 'ERR');
            
            const topAirtimeList = document.getElementById('top-airtime-list');
            const topSignalList = document.getElementById('top-signal-list');
            if(topAirtimeList) topAirtimeList.innerHTML = `<div class="text-danger text-sm">Failed to load data: ${error.message}</div>`;
            if(topSignalList) topSignalList.innerHTML = `<div class="text-danger text-sm">Failed to load data: ${error.message}</div>`;
        }
    }

    function updateStatWithTransition(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const currentValue = element.textContent;
        // Convertir newValue a string para la comparación
        const newValueStr = String(newValue);
        if (currentValue === newValueStr) return;
        
        element.style.transition = 'opacity 0.2s ease';
        element.style.opacity = '0.5';
        setTimeout(() => {
            element.textContent = newValueStr;
            element.style.opacity = '1';
        }, 200);
    }
    
    async function initializeDashboard() {
        await loadInitialData(); // Carga inicial
        
        // Configurar auto-refresco
        try {
            const settingsResponse = await fetch(`${API_BASE_URL}/api/settings`);
            if (!settingsResponse.ok) throw new Error('Failed to fetch settings');
            const settings = await settingsResponse.json();
            const refreshIntervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);
            
            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadInitialData, refreshIntervalSeconds * 1000);
                console.log(`Dashboard auto-refresh configured for every ${refreshIntervalSeconds} seconds.`);
            } else {
                console.log('Dashboard auto-refresh is disabled.');
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh, using default.", error);
            if (refreshIntervalId) clearInterval(refreshIntervalId);
            refreshIntervalId = setInterval(loadInitialData, 60000); // Default a 60s
        }
    }
    
    initializeDashboard();
});