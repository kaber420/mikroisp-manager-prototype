// static/js/router_details/overview.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, setCurrentRouterName } from './config.js';

/**
 * Carga los recursos del sistema y las estadísticas principales.
 */
export async function loadOverviewData() {
    // Cargar recursos del sistema
    try {
        const res = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/resources`);

        DOM_ELEMENTS.mainHostname.textContent = res.name || 'Router';
        DOM_ELEMENTS.resHost.textContent = CONFIG.currentHost;
        DOM_ELEMENTS.resFirmware.textContent = `RouterOS ${res.version || '...'}`;
        setCurrentRouterName(res.name ? res.name.split(' ')[0].replace(/[^a-zA-Z0-9_-]/g, '') : 'router');

        const isOnline = !!res.version;
        DOM_ELEMENTS.resStatusIndicator.className = `status-indicator ${isOnline ? 'status-online' : 'status-offline'}`;
        DOM_ELEMENTS.resStatusText.textContent = isOnline ? 'Online' : 'Offline';
        DOM_ELEMENTS.resStatusText.className = `text-${isOnline ? 'success' : 'danger'}`;

        DOM_ELEMENTS.resUptime.textContent = res.uptime || '--';
        const cpuLoad = res['cpu-load'] || 0;
        DOM_ELEMENTS.resCpuLoad.textContent = `${cpuLoad}%`;
        DOM_ELEMENTS.resCpuText.textContent = `${cpuLoad}%`;
        DOM_ELEMENTS.resCpuBar.style.width = `${cpuLoad}%`;

        if (res['total-memory'] && res['total-memory'] > 0) {
            const usedMemory = res['total-memory'] - (res['free-memory'] || 0);
            const memPercent = Math.round((usedMemory / res['total-memory']) * 100);
            DOM_ELEMENTS.resMemoryPerc.textContent = `${memPercent}%`;
            DOM_ELEMENTS.resMemoryText.textContent = `${DomUtils.formatBytes(usedMemory)} / ${DomUtils.formatBytes(res['total-memory'])}`;
            DOM_ELEMENTS.resMemoryBar.style.width = `${memPercent}%`;
        }

        // Disk Usage
        // Usamos los nuevos campos normalizados del backend ('total-disk' y 'free-disk')
        const totalDisk = res['total-disk'];
        const freeDisk = res['free-disk'];

        // Comprobamos si los valores no son nulos ni indefinidos (¡permitimos que sea 0!)
        if (totalDisk != null && freeDisk != null) {
            const usedDisk = totalDisk - freeDisk;
            // Evitamos la división por cero si totalDisk es 0
            const diskPercent = (totalDisk > 0) ? Math.round((usedDisk / totalDisk) * 100) : 0;
            DOM_ELEMENTS.resDiskText.textContent = `${DomUtils.formatBytes(usedDisk)} / ${DomUtils.formatBytes(totalDisk)}`;
            DOM_ELEMENTS.resDiskBar.style.width = `${diskPercent}%`;
        } else {
            // Si los valores son null/undefined (la API del router no los envió), mostramos N/A
            DOM_ELEMENTS.resDiskText.textContent = `N/A`;
            DOM_ELEMENTS.resDiskBar.style.width = `0%`;
        }

        DOM_ELEMENTS.infoModel.textContent = res.model || res['board-name'] || 'N/A';
        DOM_ELEMENTS.infoFirmware.textContent = res.version || 'N/A';
        DOM_ELEMENTS.infoPlatform.textContent = res.platform || 'N/A';
        DOM_ELEMENTS.infoCpu.textContent = res.cpu || 'N/A';
        DOM_ELEMENTS.infoSerial.textContent = res['serial-number'] || 'N/A';
        DOM_ELEMENTS.infoLicense.textContent = `Level ${res.nlevel || 'N/A'}`;
        DOM_ELEMENTS.infoCpuDetails.textContent = `${res['cpu-count'] || 'N/A'} cores / ${res['cpu-frequency'] || 'N/A'} MHz`;

        // Health info (optional)
        if (res.voltage && res.temperature && DOM_ELEMENTS.healthInfo) {
            DOM_ELEMENTS.healthInfo.style.display = 'block';
            DOM_ELEMENTS.resVoltage.textContent = `${res.voltage}V`;
            DOM_ELEMENTS.resTemperature.textContent = `${res.temperature}°C`;
        } else if (DOM_ELEMENTS.healthInfo) {
            DOM_ELEMENTS.healthInfo.style.display = 'none';
        }

        DomUtils.updateBackupNameInput();
    } catch (e) {
        console.error("Error en loadSystemResources:", e);
        DOM_ELEMENTS.mainHostname.textContent = `Error: ${CONFIG.currentHost}`;
        DOM_ELEMENTS.resStatusIndicator.className = 'status-indicator status-offline';
        DOM_ELEMENTS.resStatusText.textContent = 'Offline';
        DOM_ELEMENTS.resStatusText.className = 'text-danger';
    }
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