// static/js/router_details/overview.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, setCurrentRouterName } from './config.js';

let liveSocket = null;

/**
 * Inicia la conexión WebSocket para el modo "En Vivo".
 */
export function initResourceStream() {
    // Determinar protocolo (ws:// o wss://) automáticamente
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/routers/${CONFIG.currentHost}/ws/resources`;

    // Limpieza previa por seguridad
    if (liveSocket) {
        liveSocket.close();
    }

    liveSocket = new WebSocket(wsUrl);

    liveSocket.onopen = () => {
        // Efecto visual: Indicador verde pulsante
        if (DOM_ELEMENTS.resStatusIndicator) {
            DOM_ELEMENTS.resStatusIndicator.className = 'status-indicator status-online animate-pulse shadow-[0_0_8px_#22c55e]';
        }
        if (DOM_ELEMENTS.resStatusText) {
            DOM_ELEMENTS.resStatusText.textContent = 'Live Stream';
            DOM_ELEMENTS.resStatusText.className = 'text-success font-bold';
        }
    };

    liveSocket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'resources') {
                updateDashboardUI(msg.data);
            }
        } catch (e) {
            console.error("Error procesando mensaje WS:", e);
        }
    };

    liveSocket.onclose = (event) => {
        // Si se cierra, mostramos estado offline
        if (DOM_ELEMENTS.resStatusIndicator) {
            DOM_ELEMENTS.resStatusIndicator.className = 'status-indicator status-offline';
        }
        if (DOM_ELEMENTS.resStatusText) {
            DOM_ELEMENTS.resStatusText.textContent = 'Stream Paused';
            DOM_ELEMENTS.resStatusText.className = 'text-text-secondary';
        }
        
        // Opcional: Reintentar conexión en 5s si no fue un cierre limpio
        if (!event.wasClean) {
            console.log("Conexión perdida, reintentando en 5s...");
            setTimeout(initResourceStream, 5000);
        }
    };
}

/**
 * Actualiza el DOM con los datos recibidos del Socket.
 */
function updateDashboardUI(data) {
    // 1. CPU
    const cpuLoad = parseInt(data.cpu_load || 0);
    if (DOM_ELEMENTS.resCpuLoad) DOM_ELEMENTS.resCpuLoad.textContent = `${cpuLoad}%`;
    if (DOM_ELEMENTS.resCpuText) DOM_ELEMENTS.resCpuText.textContent = `${cpuLoad}%`;
    
    if (DOM_ELEMENTS.resCpuBar) {
        DOM_ELEMENTS.resCpuBar.style.width = `${cpuLoad}%`;
        DOM_ELEMENTS.resCpuBar.className = `progress-value transition-all duration-500 ${
            cpuLoad > 80 ? 'bg-danger' : (cpuLoad > 50 ? 'bg-warning' : 'bg-primary')
        }`;
    }

    // 2. Memoria
    const totalMem = parseInt(data.total_memory || 0);
    const freeMem = parseInt(data.free_memory || 0);
    
    if (totalMem > 0) {
        const usedMem = totalMem - freeMem;
        const memPercent = Math.round((usedMem / totalMem) * 100);
        
        if (DOM_ELEMENTS.resMemoryPerc) DOM_ELEMENTS.resMemoryPerc.textContent = `${memPercent}%`;
        if (DOM_ELEMENTS.resMemoryText) DOM_ELEMENTS.resMemoryText.textContent = `${DomUtils.formatBytes(usedMem)} / ${DomUtils.formatBytes(totalMem)}`;
        if (DOM_ELEMENTS.resMemoryBar) DOM_ELEMENTS.resMemoryBar.style.width = `${memPercent}%`;
    }

    // 3. --- CORRECCIÓN: DISCO (Restaurado) ---
    const totalDisk = parseInt(data.total_disk || 0);
    const freeDisk = parseInt(data.free_disk || 0);

    if (totalDisk > 0) {
        const usedDisk = totalDisk - freeDisk;
        const diskPercent = Math.round((usedDisk / totalDisk) * 100);

        if (DOM_ELEMENTS.resDiskText) DOM_ELEMENTS.resDiskText.textContent = `${DomUtils.formatBytes(usedDisk)} / ${DomUtils.formatBytes(totalDisk)}`;
        if (DOM_ELEMENTS.resDiskBar) DOM_ELEMENTS.resDiskBar.style.width = `${diskPercent}%`;
    } else {
        if (DOM_ELEMENTS.resDiskText) DOM_ELEMENTS.resDiskText.textContent = "N/A";
        if (DOM_ELEMENTS.resDiskBar) DOM_ELEMENTS.resDiskBar.style.width = "0%";
    }

    // 4. Uptime
    if (DOM_ELEMENTS.resUptime) DOM_ELEMENTS.resUptime.textContent = data.uptime;

    // 5. --- CORRECCIÓN: HEALTH (Lógica estricta) ---
    // Verificamos si existe AL MENOS UN valor válido (no null, no undefined)
    const hasVoltage = data.voltage != null;
    const hasTemp = data.temperature != null;
    const hasCpuTemp = data.cpu_temperature != null;

    if (DOM_ELEMENTS.healthInfo) {
        if (hasVoltage || hasTemp || hasCpuTemp) {
            DOM_ELEMENTS.healthInfo.style.display = 'block';
            
            // Construimos el string de información dinámicamente
            let healthHtml = '';
            
            if (hasVoltage) {
                healthHtml += `<span class="mr-3">${data.voltage}V</span>`;
            }
            
            if (hasTemp) {
                healthHtml += `<span class="mr-3" title="Board Temp">${data.temperature}°C</span>`;
            }

            if (hasCpuTemp) {
                healthHtml += `<span class="text-text-secondary" title="CPU Temp">CPU: ${data.cpu_temperature}°C</span>`;
            }

            // Necesitamos un contenedor para inyectar esto, o usamos los IDs existentes
            // Si usas los IDs del template original:
            if (DOM_ELEMENTS.resVoltage) DOM_ELEMENTS.resVoltage.textContent = hasVoltage ? `${data.voltage}V` : '';
            
            // Para la temperatura, mostramos la de CPU si existe, si no la general
            if (DOM_ELEMENTS.resTemperature) {
                if (hasCpuTemp) {
                    DOM_ELEMENTS.resTemperature.textContent = `${data.cpu_temperature}°C (CPU)`;
                } else if (hasTemp) {
                    DOM_ELEMENTS.resTemperature.textContent = `${data.temperature}°C`;
                } else {
                    DOM_ELEMENTS.resTemperature.textContent = '';
                }
            }
            
        } else {
            // Si no hay ningún dato, ocultamos todo el bloque
            DOM_ELEMENTS.healthInfo.style.display = 'none';
        }
    }
}

/**
 * Carga inicial de datos ESTÁTICOS (Modelo, Firmware, Serial).
 * Estos no cambian, así que los pedimos una sola vez por HTTP normal.
 */
export async function loadOverviewData() {
    try {
        const res = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/resources`);

        DOM_ELEMENTS.mainHostname.textContent = res.name || 'Router';
        DOM_ELEMENTS.resHost.textContent = CONFIG.currentHost;
        DOM_ELEMENTS.resFirmware.textContent = `RouterOS ${res.version || '...'}`;
        
        // Guardamos el nombre limpio para usarlo en backups
        const cleanName = res.name ? res.name.split(' ')[0].replace(/[^a-zA-Z0-9_-]/g, '') : 'router';
        setCurrentRouterName(cleanName);

        DOM_ELEMENTS.infoModel.textContent = res.model || res['board-name'] || 'N/A';
        DOM_ELEMENTS.infoFirmware.textContent = res.version || 'N/A';
        DOM_ELEMENTS.infoPlatform.textContent = res.platform || 'N/A';
        DOM_ELEMENTS.infoCpu.textContent = res.cpu || 'N/A';
        DOM_ELEMENTS.infoSerial.textContent = res['serial-number'] || 'N/A';
        DOM_ELEMENTS.infoLicense.textContent = `Level ${res.nlevel || 'N/A'}`;
        DOM_ELEMENTS.infoCpuDetails.textContent = `${res['cpu-count'] || 'N/A'} cores / ${res['cpu-frequency'] || 'N/A'} MHz`;

        DomUtils.updateBackupNameInput();
        
    } catch (e) {
        console.error("Error carga estática:", e);
        DOM_ELEMENTS.mainHostname.textContent = `Error: ${CONFIG.currentHost}`;
    }
}

// Función para detener el WS al salir de la vista (si fuera necesario)
export function stopResourceStream() {
    if (liveSocket) liveSocket.close();
}

/**
 * Carga las estadísticas de PPP (Secretos, Activos) para el Overview.
 */
export async function loadOverviewStats() {
     const safeFetch = (url) => ApiClient.request(url).catch(err => {
        console.error(`Error fetching ${url}:`, err.message);
        return null; // No fallar todo si una petición falla
    });

    try {
        const [secrets, active] = await Promise.all([
            safeFetch(`/api/routers/${CONFIG.currentHost}/pppoe/secrets`),
            safeFetch(`/api/routers/${CONFIG.currentHost}/pppoe/active`)
        ]);

        DOM_ELEMENTS.resActiveUsers.textContent = active ? active.length : '0';
        DOM_ELEMENTS.resSecrets.textContent = secrets ? secrets.length : '0';

        if (DOM_ELEMENTS.pppoeSecretsList) {
            if (secrets) {
                DOM_ELEMENTS.pppoeSecretsList.innerHTML = secrets.length ? secrets.map(s => `<div class="text-xs flex justify-between p-1 hover:bg-surface-2 rounded"><span>${s.name}</span><span class="${s.disabled === 'true' ? 'text-danger' : 'text-success'}">${s.disabled === 'true' ? 'Disabled' : 'Active'}</span></div>`).join('') : '<p class="text-text-secondary text-xs">No hay secretos.</p>';
            } else {
                DOM_ELEMENTS.pppoeSecretsList.innerHTML = '<p class="text-danger text-xs">No se pudieron cargar los secretos.</p>';
            }
        }

        if (DOM_ELEMENTS.pppoeActiveList) {
            if (active) {
                DOM_ELEMENTS.pppoeActiveList.innerHTML = active.length ? active.map(c => `<div class="text-xs flex justify-between p-1 hover:bg-surface-2 rounded"><span>${c.name}</span><span>${c.address}</span></div>`).join('') : '<p class="text-text-secondary text-xs">No hay usuarios activos.</p>';
            } else {
                DOM_ELEMENTS.pppoeActiveList.innerHTML = '<p class="text-danger text-xs">No se pudieron cargar los usuarios activos (timeout).</p>';
            }
        }
    } catch (e) {
        console.error("Error en loadOverviewStats:", e);
    }
}
