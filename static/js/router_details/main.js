// static/js/router_details/main.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- IMPORTAR LA NUEVA FUNCIÓN initResourceStream ---
import { loadOverviewData, loadOverviewStats, initResourceStream } from './overview.js';

// ... (resto de imports: interfaces, network, ppp, etc.) ...
import { initInterfacesModule, loadInterfacesData } from './interfaces.js';
import { initNetworkModule, loadNetworkData } from './network.js';
import { initPppModule, loadPppData } from './ppp.js';
import { initQueuesModule, loadQueuesData } from './queues.js';
import { initUsersModule, loadUsersData } from './users.js';
import { initBackupModule, loadBackupData } from './backup.js';

async function loadFullDetailsData() {
    // ... (código existente de loadFullDetailsData sin cambios) ...
    try {
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        loadInterfacesData(data);
        loadNetworkData(data);
        loadPppData(data);
        loadQueuesData(data);
    } catch (e) {
        console.error("Error fatal cargando /full-details:", e);
        DomUtils.updateFeedback(`Error al cargar datos del router: ${e.message}`, false);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    
    // 1. Inicializar módulos
    initInterfacesModule();
    initNetworkModule();
    initPppModule();
    initQueuesModule();
    initUsersModule();
    initBackupModule();

    // 2. Carga de Datos
    
    // A. Datos Estáticos (HTTP una sola vez)
    await loadOverviewData();
    
    // B. ¡ENCENDER EL STREAM WEBSOCKET! (Nuevo)
    // Esto hará que las barras de CPU/RAM cobren vida
    initResourceStream(); 

    await loadOverviewStats(); // Stats de PPP (podríamos mover esto a WS en el futuro)
    await loadFullDetailsData(); // Tablas pesadas
    
    Promise.all([
        loadUsersData(),
        loadBackupData()
    ]);
});