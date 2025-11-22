document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    
    // --- FUNCIÓN 1: Cargar Tops (Airtime y Señal) ---
    async function loadTopStats() {
        const topAirtimeList = document.getElementById('top-airtime-list');
        const topSignalList = document.getElementById('top-signal-list');
        if (!topAirtimeList || !topSignalList) return;

        // Efecto visual sutil de actualización
        topAirtimeList.style.opacity = '0.5';
        topSignalList.style.opacity = '0.5';
        
        try {
            const [airtimeRes, signalRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/stats/top-aps-by-airtime`),
                fetch(`${API_BASE_URL}/api/stats/top-cpes-by-signal`)
            ]);
            
            // Render Airtime
            if (airtimeRes.ok) {
                const topAirtime = await airtimeRes.json();
                topAirtimeList.innerHTML = ''; 
                if(topAirtime.length > 0) {
                    topAirtime.forEach(ap => { 
                        topAirtimeList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${ap.hostname || ap.host}</p><span class="text-sm font-bold text-warning">${(ap.airtime_total_usage / 10.0).toFixed(1)}%</span></div>`; 
                    });
                } else { 
                    topAirtimeList.innerHTML = `<div class="text-text-secondary text-sm">No data.</div>`; 
                }
            }
            
            // Render Signal
            if (signalRes.ok) {
                const topSignal = await signalRes.json();
                topSignalList.innerHTML = '';
                if(topSignal.length > 0) {
                    topSignal.forEach(cpe => { 
                        topSignalList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${cpe.cpe_hostname || cpe.cpe_mac}</p><span class="text-sm font-bold text-danger">${cpe.signal} dBm</span></div>`; 
                    });
                } else { 
                    topSignalList.innerHTML = `<div class="text-text-secondary text-sm">No data.</div>`;
                }
            }

        } catch (error) {
            console.error("Error loading top stats:", error);
        } finally {
            // Restaurar opacidad
            topAirtimeList.style.opacity = '1';
            topSignalList.style.opacity = '1';
        }
    }

    // --- FUNCIÓN 2: Cargar Datos Principales ---
    async function loadInitialData() {
        try {
            const [apsRes, cpeCountRes] = await Promise.all([ 
                fetch(`${API_BASE_URL}/api/aps`),
                fetch(`${API_BASE_URL}/api/stats/cpe-count`)
            ]);

            if (!apsRes.ok || !cpeCountRes.ok) throw new Error('Failed to load dashboard data');
            
            const allAps = await apsRes.json();
            const cpeCountData = await cpeCountRes.json();
            
            // Calcular Estadísticas
            let cpesOnline = 0;
            let apsOnline = 0;
            
            allAps.forEach(ap => { 
                if (ap.last_status === 'online') { 
                    apsOnline++;
                    if (ap.client_count != null) cpesOnline += ap.client_count;
                } 
            });

            const totalAps = allAps.length;
            const apsOffline = totalAps - apsOnline;
            const totalCpes = cpeCountData.total_cpes;
            const cpesOffline = totalCpes - cpesOnline;
            
            // Actualizar UI con transiciones
            updateStatWithTransition('total-aps', totalAps);
            updateStatWithTransition('aps-online', apsOnline);
            updateStatWithTransition('aps-offline', apsOffline);
            updateStatWithTransition('total-cpes', totalCpes);
            updateStatWithTransition('cpes-online', cpesOnline);
            updateStatWithTransition('cpes-offline', cpesOffline);
            
            loadTopStats(); 

        } catch (error) {
            console.error("Dashboard Load Error:", error);
        }
    }

    function updateStatWithTransition(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const newValueStr = String(newValue);
        if (element.textContent === newValueStr) return;
        
        element.style.transition = 'opacity 0.2s ease';
        element.style.opacity = '0.5';
        setTimeout(() => {
            element.textContent = newValueStr;
            element.style.opacity = '1';
        }, 200);
    }
    
    // --- INICIALIZACIÓN ---
    loadInitialData(); // 1. Carga inmediata al entrar

    // 2. ESCUCHA REACTIVA (Reemplazo del Polling)
    // Cuando el Monitor avisa por WebSocket (ws-client.js), actualizamos.
    window.addEventListener('data-refresh-needed', () => {
        console.log("⚡ Dashboard: Actualizando datos por evento en vivo...");
        loadInitialData();
    });
});