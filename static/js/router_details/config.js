// static/js/router_details/config.js

/**
 * Configuración estática de la aplicación.
 */
export const CONFIG = {
    API_BASE_URL: window.location.origin,
    currentHost: window.location.pathname.split('/').pop(),
    COLORS: {
        BACKUP: '#3B82F6',
        RSC: '#F97316',
        SUCCESS: '#22C55E',
        DANGER: '#EF4444',
        WARNING: '#EAB308',
        PRIMARY: '#3B82F6'
    }
};

/**
 * Referencias a elementos del DOM cacheados.
 */
export const DOM_ELEMENTS = {
    // Headers
    mainHostname: document.getElementById('main-hostname'),
    // Feedback
    formFeedback: document.getElementById('form-feedback'),
    // Listas de Datos
    interfacesTableBody: document.getElementById('interfaces-table-body'),
    interfaceFilterButtons: document.getElementById('interface-filter-buttons'),
    ipAddressList: document.getElementById('ip-address-list'),
    natRulesList: document.getElementById('nat-rules-list'),
    pppProfileList: document.getElementById('ppp-profile-list'),
    ipPoolList: document.getElementById('ip-pool-list'),
    pppoeServerList: document.getElementById('pppoe-server-list'),
    parentQueueListDisplay: document.getElementById('parent-queue-list-display'),
    pppoeSecretsList: document.getElementById('pppoe-secrets-list'),
    pppoeActiveList: document.getElementById('pppoe-active-list'),
    backupFilesList: document.getElementById('backup-files-list'),
    routerUsersList: document.getElementById('router-users-list'),

    // --- NUEVO: Tabla para planes locales ---
    localPlansTableBody: document.getElementById('local-plans-table-body'),

    // Formularios
    addIpForm: document.getElementById('add-ip-form'),
    addNatForm: document.getElementById('add-nat-form'),
    addPppoeForm: document.getElementById('add-pppoe-form'),
    addParentQueueForm: document.getElementById('add-parent-queue-form'),

    // Este es el formulario de la pestaña PPP (RouterOS profiles)
    addPlanForm: document.getElementById('add-plan-form'),

    // --- NUEVO: Formulario de Planes Locales (Pestaña Queues) ---
    createLocalPlanForm: document.getElementById('create-local-plan-form'),

    createBackupForm: document.getElementById('create-backup-form'),
    addRouterUserForm: document.getElementById('add-router-user-form'),
    // Inputs
    backupNameInput: document.getElementById('backup-name'),
    parentQueueSelect: document.getElementById('add-plan-parent_queue'),
    appUserSelect: document.getElementById('app-user-select'),
    // Overview Stats
    resUptime: document.getElementById('res-uptime'),
    resCpuLoad: document.getElementById('res-cpu-load'),
    resCpuBar: document.getElementById('res-cpu-bar'),
    resCpuText: document.getElementById('res-cpu-text'),
    resMemoryPerc: document.getElementById('res-memory-perc'),
    resMemoryText: document.getElementById('res-memory-text'),
    resMemoryBar: document.getElementById('res-memory-bar'),
    resDiskText: document.getElementById('res-disk-text'),
    resDiskBar: document.getElementById('res-disk-bar'),
    resHost: document.getElementById('res-host'),
    resFirmware: document.getElementById('res-firmware'),
    resStatusIndicator: document.getElementById('res-status-indicator'),
    resStatusText: document.getElementById('res-status-text'),
    resInterfaces: document.getElementById('res-interfaces'),
    resActiveUsers: document.getElementById('res-active-users'),
    resSecrets: document.getElementById('res-secrets'),
    // Overview Info
    infoModel: document.getElementById('info-model'),
    infoFirmware: document.getElementById('info-firmware'),
    infoPlatform: document.getElementById('info-platform'),
    infoCpu: document.getElementById('info-cpu'),
    infoSerial: document.getElementById('info-serial'),
    infoLicense: document.getElementById('info-license'),
    infoCpuDetails: document.getElementById('info-cpu-details'),
    // Health
    healthInfo: document.getElementById('health-info'),
    resVoltage: document.getElementById('res-voltage'),
    resTemperature: document.getElementById('res-temperature'),
    // Modals
    vlanModal: document.getElementById('vlan-modal'),
    vlanModalTitle: document.getElementById('vlan-modal-title'),
    vlanForm: document.getElementById('vlan-form'),
    vlanIdInput: document.getElementById('vlan-id-input'),
    vlanNameInput: document.getElementById('vlan-name'),
    vlanInterfaceSelect: document.getElementById('vlan-interface'),

    bridgeModal: document.getElementById('bridge-modal'),
    bridgeModalTitle: document.getElementById('bridge-modal-title'),
    bridgeForm: document.getElementById('bridge-form'),
    bridgeNameInput: document.getElementById('bridge-name'),
    bridgePortsContainer: document.getElementById('bridge-ports'),

    // Buttons
    addVlanBtn: document.getElementById('add-vlan-btn'),
    addBridgeBtn: document.getElementById('add-bridge-btn'),
    cancelVlanBtn: document.getElementById('cancel-vlan-btn'),
    closeVlanModalBtn: document.getElementById('close-vlan-modal-btn'),
    cancelBridgeBtn: document.getElementById('cancel-bridge-btn'),
    closeBridgeModalBtn: document.getElementById('close-bridge-modal-btn'),
    // Iconos
    deleteIcon: `<span class="material-symbols-outlined text-base">delete</span>`
};

/**
 * Estado global de la aplicación.
 */
export let state = {
    allInterfaces: [],
    currentRouterName: 'router',
    routerId: null // <--- NUEVO: Para guardar el ID de la BD
};

/**
 * Actualiza el estado global de las interfaces.
 * @param {Array} newInterfaces - El nuevo array de interfaces.
 */
export function setAllInterfaces(newInterfaces) {
    state.allInterfaces = newInterfaces;
}

/**
 * Actualiza el estado global del nombre del router.
 * @param {string} newName - El nuevo nombre del router.
 */
export function setCurrentRouterName(newName) {
    state.currentRouterName = newName;
}