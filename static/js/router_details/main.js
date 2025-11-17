// static/js/router_details/main.js
import { ApiClient } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js'; // Importa DOM_ELEMENTS
import { DomUtils } from './utils.js'; // Importa DomUtils

// Importar los inicializadores y cargadores/renderizadores de cada módulo
import { loadOverviewData, loadOverviewStats } from './overview.js';
// AHORA IMPORTAMOS EL NUEVO MÓDULO DE RED
import { initInterfacesModule, loadInterfacesData } from './interfaces.js';
import { initNetworkModule, loadNetworkData } from './network.js'; // <-- NUEVA LÍNEA
import { initPppModule, loadPppData } from './ppp.js';
import { initQueuesModule, loadQueuesData } from './queues.js';
import { initUsersModule, loadUsersData } from './users.js';
import { initBackupModule, loadBackupData } from './backup.js';

/**
 * Carga los datos de /full-details UNA SOLA VEZ y los distribuye
 * a los módulos que los necesitan.
 */
async function loadFullDetailsData() {
    try {
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        
        // Distribuir los datos a los módulos
        loadInterfacesData(data); // Renderiza la lista de interfaces
        loadNetworkData(data);    // <-- NUEVA LÍNEA: Renderiza IPs y NATs
        loadPppData(data);        // Renderiza perfiles, pools, servidores
        loadQueuesData(data);       // Renderiza colas
        
        // (loadInterfacesData y loadNetworkData ya llaman a populateInterfaceSelects)

    } catch (e) {
        console.error("Error fatal cargando /full-details:", e);
        DomUtils.updateFeedback(`Error al cargar datos del router: ${e.message}`, false);
    }
}

/**
 * Punto de entrada principal
 */
document.addEventListener('DOMContentLoaded', async () => {
    
    // 1. Inicializar todos los módulos (asociar eventos a formularios)
    initInterfacesModule();
    initNetworkModule(); // <-- NUEVA LÍNEA
    initPppModule();
    initQueuesModule();
    initUsersModule();
    initBackupModule();

    // 2. Cargar los datos
    
    // Carga la pestaña de Overview (Recursos + Stats de PPP)
    await loadOverviewData();
    await loadOverviewStats(); 
    
    // Carga todos los datos de /full-details y renderiza 4 pestañas
    await loadFullDetailsData();
    
    // Carga los datos restantes (Usuarios y Backups)
    Promise.all([
        loadUsersData(),
        loadBackupData()
    ]);
});