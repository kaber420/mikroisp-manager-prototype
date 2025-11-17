// static/js/router_details/network.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADORES ---

function renderIpAddresses(ips = []) {
    DOM_ELEMENTS.ipAddressList.innerHTML = '';
    ips.forEach(ip => {
        DOM_ELEMENTS.ipAddressList.innerHTML += `
            <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                <span>${ip.address} <strong>(${ip.interface})</strong></span>
                <button class="delete-ip-btn invisible group-hover:visible text-danger hover:text-red-400" 
                        data-address="${ip.address}">
                    ${DOM_ELEMENTS.deleteIcon}
                </button>
            </div>`;
    });
    document.querySelectorAll('.delete-ip-btn').forEach(btn => btn.addEventListener('click', handleDeleteIp));
}

function renderNatRules(rules = []) {
    DOM_ELEMENTS.natRulesList.innerHTML = '';
    rules.forEach(rule => {
        if (rule.action !== 'masquerade') return;
        DOM_ELEMENTS.natRulesList.innerHTML += `
             <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                <span>${rule.comment || 'NAT Rule'} <strong>(${rule['out-interface']})</strong></span>
                <button class="delete-nat-btn invisible group-hover:visible text-danger hover:text-red-400" 
                        data-comment="${rule.comment}">
                    ${DOM_ELEMENTS.deleteIcon}
                </button>
            </div>`;
    });
    document.querySelectorAll('.delete-nat-btn').forEach(btn => btn.addEventListener('click', handleDeleteNat));
}

// --- MANEJADORES (HANDLERS) ---

const handleAddIp = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addIpForm);
        const comment = "Managed by µMonitor";
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-ip`, {
            method: 'POST',
            body: JSON.stringify({ interface: data.get('interface'), address: data.get('address'), comment: comment })
        });
        DomUtils.updateFeedback('IP Añadida', true);
        DOM_ELEMENTS.addIpForm.reset();
        loadNetworkData(); // Recargar solo este módulo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleAddNat = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addNatForm);
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-nat`, {
            method: 'POST',
            body: JSON.stringify({ out_interface: data.get('out-interface'), comment: data.get('comment') })
        });
        DomUtils.updateFeedback('NAT Añadido', true);
        DOM_ELEMENTS.addNatForm.reset();
        loadNetworkData(); // Recargar solo este módulo
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleDeleteIp = (e) => {
    const address = e.currentTarget.dataset.address;
    DomUtils.confirmAndExecute(`¿Borrar la IP "${address}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-ip?address=${encodeURIComponent(address)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('IP Eliminada', true);
            loadNetworkData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleDeleteNat = (e) => {
    const comment = e.currentTarget.dataset.comment;
    DomUtils.confirmAndExecute(`¿Borrar la regla NAT "${comment}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-nat?comment=${encodeURIComponent(comment)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Regla NAT Eliminada', true);
            loadNetworkData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- CARGADOR DE DATOS ---

export async function loadNetworkData(fullDetails) {
    try {
        const data = fullDetails || await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        
        renderIpAddresses(data.ip_addresses);
        renderNatRules(data.nat_rules);
        // Nota: populateInterfaceSelects se llama desde interfaces.js,
        // pero como los datos están aquí, lo llamamos también.
        populateInterfaceSelects(data.interfaces);

    } catch (e) {
        console.error("Error cargando datos de Red:", e);
    }
}

// Re-usamos esta función aquí también
function populateInterfaceSelects(interfaces) {
    const selects = document.querySelectorAll('.interface-select');
    if (!selects.length) return;
    const options = interfaces.length ? '<option value="">Seleccionar...</option>' + interfaces
        .filter(i => ['ether', 'bridge', 'vlan'].includes(i.type))
        .map(i => `<option value="${i.name}">${i.name}</option>`).join('') : '<option value="">Error</option>';
    selects.forEach(s => s.innerHTML = options);
}

// --- INICIALIZADOR ---

export function initNetworkModule() {
    DOM_ELEMENTS.addIpForm?.addEventListener('submit', handleAddIp);
    DOM_ELEMENTS.addNatForm?.addEventListener('submit', handleAddNat);
}