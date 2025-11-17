// static/js/router_details/interfaces.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, state, setAllInterfaces } from './config.js';

// --- ESTADO LOCAL DEL MÓDULO ---
let allModuleInterfaces = [];
let allModuleIps = [];
let allModuleBridgePorts = [];
let currentInterfaceFilter = 'general';

// Definición de nuestros filtros
const FILTER_TYPES = {
    general: ['ether', 'bridge', 'vlan', 'wlan', 'bonding', 'loopback'],
    ppp: ['pppoe-out', 'pptp-out', 'l2tp-out', 'ovpn-out', 'sstp-out', 'ipip', 'gre', 'eoip', 'pppoe-in', 'pptp-in', 'l2tp-in']
};

// --- RENDERIZADORES ---

function renderInterfaces() {
    if (!DOM_ELEMENTS.interfacesTableBody) {
        console.error("Error: El <tbody> de la tabla de interfaces no existe en el DOM.");
        return;
    }
    
    DOM_ELEMENTS.interfacesTableBody.innerHTML = '';
    let filteredInterfaces;

    switch (currentInterfaceFilter) {
        case 'general':
            filteredInterfaces = allModuleInterfaces.filter(iface => FILTER_TYPES.general.includes(iface.type));
            break;
        case 'ppp':
            filteredInterfaces = allModuleInterfaces.filter(iface => FILTER_TYPES.ppp.includes(iface.type) && iface.name !== 'none');
            break;
        default:
            filteredInterfaces = allModuleInterfaces.filter(iface => iface.name !== 'none');
            break;
    }
    
    DOM_ELEMENTS.resInterfaces.textContent = filteredInterfaces.length;

    if (filteredInterfaces.length === 0) {
        const message = currentInterfaceFilter === 'ppp' 
            ? 'No hay túneles o clientes PPPoE conectados.' 
            : 'No se encontraron interfaces para este filtro.';
        DOM_ELEMENTS.interfacesTableBody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-text-secondary">${message}</td></tr>`;
        return;
    }

    filteredInterfaces.sort((a, b) => {
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.name.localeCompare(b.name);
    });

    const rowsHtml = filteredInterfaces.map(iface => {
        
        const ip = allModuleIps.find(i => i.interface === iface.name);
        const interfaceId = iface['.id'] || iface.id;
        const isDisabled = iface.disabled === 'true' || iface.disabled === true;
        const isActuallyRunning = (iface.running === 'true' || iface.running === true);
        
        const isRunning = isActuallyRunning && !isDisabled;
        const statusClass = isRunning ? 'status-online' : 'status-offline';
        
        const rowClass = isDisabled ? 'opacity-50' : '';

        const canBeDeleted = ['vlan', 'bridge', 'bonding'].includes(iface.type);
        const canBeDisabled = !['pppoe-out', 'pptp-out', 'l2tp-out'].includes(iface.type);
        const isManaged = iface.comment && iface.comment.includes('managed by umonitor');

        let actionButtons = '';
        
        if (isManaged && (iface.type === 'vlan' || iface.type === 'bridge')) {
            actionButtons += `<button class="btn-action-icon" data-action="edit" data-id="${interfaceId}" data-type="${iface.type}" title="Editar"><span class="material-symbols-outlined text-primary">edit</span></button>`;
        }

        if (canBeDisabled) {
            if (isDisabled) {
                actionButtons += `<button class="btn-action-icon" data-action="enable" data-id="${interfaceId}" data-type="${iface.type}" title="Habilitar"><span class="material-symbols-outlined text-success">play_circle</span></button>`;
            } else {
                actionButtons += `<button class="btn-action-icon" data-action="disable" data-id="${interfaceId}" data-type="${iface.type}" title="Deshabilitar"><span class="material-symbols-outlined text-warning">pause_circle</span></button>`;
            }
        }
        
        if (canBeDeleted) {
            actionButtons += `<button class="btn-action-icon" data-action="delete" data-id="${interfaceId}" data-type="${iface.type}" data-name="${iface.name}" title="Eliminar">${DOM_ELEMENTS.deleteIcon}</button>`;
        }

        const rxBytes = iface['rx-byte'] ? DomUtils.formatBytes(iface['rx-byte']) : '0 Bytes';
        const txBytes = iface['tx-byte'] ? DomUtils.formatBytes(iface['tx-byte']) : '0 Bytes';

        return `
            <tr class="${rowClass}">
                <td class="text-center"><span class="status-indicator ${statusClass}" title="${isDisabled ? 'Disabled' : (isActuallyRunning ? 'Up' : 'Down')}"></span></td>
                <td>${iface.name}</td>
                <td><span class="badge bg-light text-dark">${iface.type}</span></td>
                <td>${iface['mac-address'] || 'N/A'}</td>
                <td>${ip ? ip.address : '(Dinámica)'}</td>
                <td class="font-mono">${rxBytes}</td> <td class="font-mono">${txBytes}</td>
                <td>${iface.uptime || 'N/A'}</td>
                <td class="flex gap-1">${actionButtons}</td>
            </tr>
        `;
    }).join('');

    DOM_ELEMENTS.interfacesTableBody.innerHTML = rowsHtml;
}

export function populateInterfaceSelects(interfaces) {
    const selects = document.querySelectorAll('.interface-select');
    if (!selects.length) return;
    
    const options = interfaces.length ? '<option value="">Seleccionar...</option>' + interfaces
        .filter(i => ['ether', 'bridge', 'vlan', 'wlan'].includes(i.type)) 
        .map(i => `<option value="${i.name}">${i.name}</option>`).join('') : '<option value="">Error</option>';
    
    selects.forEach(s => s.innerHTML = options);
}

// --- MODAL LOGIC ---

function openVlanModal(vlan = null) {
    DOM_ELEMENTS.vlanForm.reset();
    const physicalInterfaces = state.allInterfaces.filter(i => ['ether', 'wlan', 'bonding'].includes(i.type));
    DOM_ELEMENTS.vlanInterfaceSelect.innerHTML = physicalInterfaces.map(i => `<option value="${i.name}">${i.name}</option>`).join('');

    if (vlan) {
        DOM_ELEMENTS.vlanModalTitle.textContent = 'Edit VLAN';
        DOM_ELEMENTS.vlanForm.querySelector('#vlan-id').value = vlan['.id'];
        DOM_ELEMENTS.vlanNameInput.value = vlan.name;
        DOM_ELEMENTS.vlanIdInput.value = vlan['vlan-id'];
        DOM_ELEMENTS.vlanInterfaceSelect.value = vlan.interface;
    } else {
        DOM_ELEMENTS.vlanModalTitle.textContent = 'Add VLAN';
    }
    DOM_ELEMENTS.vlanModal.classList.remove('hidden');
    DOM_ELEMENTS.vlanModal.classList.add('flex');
}

function closeVlanModal() {
    DOM_ELEMENTS.vlanModal.classList.add('hidden');
    DOM_ELEMENTS.vlanModal.classList.remove('flex');
}

function openBridgeModal(bridge = null) {
    DOM_ELEMENTS.bridgeForm.reset();
    const physicalInterfaces = state.allInterfaces.filter(i => ['ether', 'wlan', 'vlan'].includes(i.type));
    DOM_ELEMENTS.bridgePortsContainer.innerHTML = physicalInterfaces.map(i => `
        <label class="flex items-center space-x-2">
            <input type="checkbox" name="ports" value="${i.name}" class="rounded bg-background border-border-color text-primary focus:ring-primary">
            <span>${i.name}</span>
        </label>
    `).join('');

    if (bridge) {
        DOM_ELEMENTS.bridgeModalTitle.textContent = 'Edit Bridge';
        DOM_ELEMENTS.bridgeForm.querySelector('#bridge-id').value = bridge['.id'];
        DOM_ELEMENTS.bridgeNameInput.value = bridge.name;
        const assignedPorts = allModuleBridgePorts.filter(p => p.bridge === bridge.name).map(p => p.interface);
        DOM_ELEMENTS.bridgePortsContainer.querySelectorAll('input').forEach(input => {
            if (assignedPorts.includes(input.value)) {
                input.checked = true;
            }
        });
    } else {
        DOM_ELEMENTS.bridgeModalTitle.textContent = 'Add Bridge';
    }
    DOM_ELEMENTS.bridgeModal.classList.remove('hidden');
    DOM_ELEMENTS.bridgeModal.classList.add('flex');
}

function closeBridgeModal() {
    DOM_ELEMENTS.bridgeModal.classList.add('hidden');
    DOM_ELEMENTS.bridgeModal.classList.remove('flex');
}

// --- CARGADOR DE DATOS ---

async function refreshInterfaceData() {
    try {
        const data = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        
        allModuleInterfaces = data.interfaces || [];
        allModuleIps = data.ip_addresses || [];
        allModuleBridgePorts = data.bridge_ports || [];
        setAllInterfaces(allModuleInterfaces);
        
        renderInterfaces();
        populateInterfaceSelects(allModuleInterfaces); 

    } catch (e) {
        console.error("Error recargando datos de interfaces:", e);
        DomUtils.updateFeedback(`Error al recargar interfaces: ${e.message}`, false);
    }
}

export async function loadInterfacesData(fullDetails) {
    allModuleInterfaces = fullDetails.interfaces || [];
    allModuleIps = fullDetails.ip_addresses || [];
    allModuleBridgePorts = fullDetails.bridge_ports || [];
    setAllInterfaces(allModuleInterfaces);
    
    renderInterfaces();
    populateInterfaceSelects(allModuleInterfaces);
}


// --- MANEJADORES DE ACCIONES ---

async function handleInterfaceAction(action, interfaceId, interfaceName = '', interfaceType) {
    if (action === 'edit') {
        const item = allModuleInterfaces.find(i => i['.id'] === interfaceId);
        if (interfaceType === 'vlan') {
            openVlanModal(item);
        } else if (interfaceType === 'bridge') {
            openBridgeModal(item);
        }
        return;
    }

    const host = CONFIG.currentHost;
    let requestOptions = {};
    let successMessage = '';
    let confirmMessage = '';

    try {
        switch (action) {
            case 'disable':
                confirmMessage = `¿Estás seguro de que quieres DESHABILITAR la interfaz ${interfaceName}?`;
                requestOptions = { method: 'PATCH', body: JSON.stringify({ disable: true }) }; 
                successMessage = 'Interfaz deshabilitada con éxito.';
                break;
            case 'enable':
                confirmMessage = `¿Estás seguro de que quieres HABILITAR la interfaz ${interfaceName}?`;
                requestOptions = { method: 'PATCH', body: JSON.stringify({ disable: false }) };
                successMessage = 'Interfaz habilitada con éxito.';
                break;
            case 'delete':
                confirmMessage = `¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE la interfaz "${interfaceName}" (${interfaceId})?`;
                requestOptions = { method: 'DELETE' };
                successMessage = 'Interfaz eliminada con éxito.';
                break;
            default:
                return;
        }

        DomUtils.confirmAndExecute(confirmMessage, async () => {
           
            const encodedId = encodeURIComponent(interfaceId);
            const encodedType = encodeURIComponent(interfaceType);
            const url = `/api/routers/${host}/interfaces/${encodedId}?type=${encodedType}`;
            
            await ApiClient.request(url, requestOptions);
            
            DomUtils.updateFeedback(successMessage, true);
            await refreshInterfaceData(); 
        });

    } catch (e) {
        console.error(`Error en handleInterfaceAction (${action}):`, e);
        DomUtils.updateFeedback(`Error: ${e.message}`, false);
    }
}

async function handleVlanFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const id = formData.get('id');
    const data = {
        name: formData.get('name'),
        vlan_id: formData.get('vlan-id'),
        interface: formData.get('interface'),
        comment: 'managed by umonitor'
    };

    const url = id ? `/api/routers/${CONFIG.currentHost}/vlans/${id}` : `/api/routers/${CONFIG.currentHost}/vlans`;
    const method = id ? 'PUT' : 'POST';

    try {
        await ApiClient.request(url, { method, body: JSON.stringify(data) });
        closeVlanModal();
        await refreshInterfaceData();
        DomUtils.updateFeedback('VLAN saved successfully!', true);
    } catch (error) {
        DomUtils.updateFeedback(`Error saving VLAN: ${error.message}`, false);
    }
}

async function handleBridgeFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const id = formData.get('id');
    const name = formData.get('name');
    const ports = formData.getAll('ports');
    
    const data = {
        name: name,
        ports: ports,
        comment: 'managed by umonitor'
    };

    const url = id ? `/api/routers/${CONFIG.currentHost}/bridges/${id}` : `/api/routers/${CONFIG.currentHost}/bridges`;
    const method = id ? 'PUT' : 'POST';

    try {
        await ApiClient.request(url, { method, body: JSON.stringify(data) });
        closeBridgeModal();
        await refreshInterfaceData();
        DomUtils.updateFeedback('Bridge saved successfully!', true);
    } catch (error) {
        DomUtils.updateFeedback(`Error saving bridge: ${error.message}`, false);
    }
}

// --- INICIALIZADOR ---

export function initInterfacesModule() {
    if (DOM_ELEMENTS.interfaceFilterButtons) {
        DOM_ELEMENTS.interfaceFilterButtons.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (!button) return;
            const filter = button.dataset.filter;
            if (filter === currentInterfaceFilter) return;
            currentInterfaceFilter = filter;
            DOM_ELEMENTS.interfaceFilterButtons.querySelectorAll('button').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.filter === filter);
            });
            renderInterfaces();
        });
    }

    if (DOM_ELEMENTS.interfacesTableBody) {
        DOM_ELEMENTS.interfacesTableBody.addEventListener('click', (e) => {
            const button = e.target.closest('button[data-action]');
            if (!button) return;

            e.preventDefault();
            const action = button.dataset.action;
            const id = button.dataset.id;
            const name = button.dataset.name || id;
            const type = button.dataset.type; 

            handleInterfaceAction(action, id, name, type);
        });
    }

    // New event listeners
    DOM_ELEMENTS.addVlanBtn.addEventListener('click', () => openVlanModal());
    DOM_ELEMENTS.cancelVlanBtn.addEventListener('click', closeVlanModal);
    DOM_ELEMENTS.closeVlanModalBtn.addEventListener('click', closeVlanModal);
    DOM_ELEMENTS.vlanForm.addEventListener('submit', handleVlanFormSubmit);

    DOM_ELEMENTS.addBridgeBtn.addEventListener('click', () => openBridgeModal());
    DOM_ELEMENTS.cancelBridgeBtn.addEventListener('click', closeBridgeModal);
    DOM_ELEMENTS.closeBridgeModalBtn.addEventListener('click', closeBridgeModal);
    DOM_ELEMENTS.bridgeForm.addEventListener('submit', handleBridgeFormSubmit);
}
