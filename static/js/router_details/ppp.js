// static/js/router_details/ppp.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADORES ---

function renderPppProfiles(profiles) {
    DOM_ELEMENTS.pppProfileList.innerHTML = (!profiles || profiles.length === 0) ? '<p class="text-text-secondary col-span-full">No hay planes PPPoE.</p>' : '';
    profiles?.forEach(profile => {
        const isManaged = profile.comment && profile.comment.includes('µMonitor');
        const rateLimit = profile['rate-limit'] ? profile['rate-limit'] : 'N/A';
        const profileCard = document.createElement('div');
        profileCard.className = `bg-surface-2 rounded-lg p-4 border-l-4 border-primary transition-all hover:shadow-md`;
        profileCard.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h4 class="font-bold text-lg text-text-primary">${profile.name}</h4>
                ${isManaged ? `<button class="delete-plan-btn text-text-secondary hover:text-danger" title="Eliminar plan" data-plan="${profile.name}" data-id="${profile['.id'] || profile.id}">${DOM_ELEMENTS.deleteIcon}</button>` : ''}
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-text-secondary">Velocidad:</span>
                <span class="font-mono font-semibold text-text-primary">${rateLimit}</span>
            </div>
        `;
        DOM_ELEMENTS.pppProfileList.appendChild(profileCard);
    });
    document.querySelectorAll('.delete-plan-btn').forEach(btn => btn.addEventListener('click', handleDeletePlan));
}

function renderIpPools(pools) {
    DOM_ELEMENTS.ipPoolList.innerHTML = (!pools || pools.length === 0) ? '<p class="text-text-secondary">No hay pools.</p>' : '';
    pools?.forEach(pool => {
        DOM_ELEMENTS.ipPoolList.innerHTML += `<div class="flex justify-between items-center text-sm"><span>${pool.name}</span><span class="text-text-secondary font-mono">${pool.ranges}</span></div>`;
    });
}

function renderPppoeServers(servers) {
    DOM_ELEMENTS.pppoeServerList.innerHTML = '';
    servers?.forEach(server => {
        DOM_ELEMENTS.pppoeServerList.innerHTML += `
            <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                <span>${server['service-name']} <strong>(${server.interface})</strong></span>
                <button class="delete-pppoe-btn invisible group-hover:visible text-danger hover:text-red-400" 
                        data-service="${server['service-name']}">
                    ${DOM_ELEMENTS.deleteIcon}
                </button>
            </div>`;
    });
    document.querySelectorAll('.delete-pppoe-btn').forEach(btn => btn.addEventListener('click', handleDeletePppoe));
}

function populateIpPoolSelects(pools) {
    const datalist = document.getElementById('ip-pool-datalist');
    if (datalist && pools) {
        datalist.innerHTML = pools
            .map(pool => `<option value="${pool.name}">${pool.name} (${pool.ranges})</option>`)
            .join('');
    }
}

// --- MANEJADORES (HANDLERS) ---

const handleAddPppoe = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addPppoeForm);
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-pppoe-server`, {
            method: 'POST',
            body: JSON.stringify({ service_name: data.get('service_name'), interface: data.get('interface'), default_profile: 'default' })
        });
        DomUtils.updateFeedback('Servidor PPPoE Añadido', true);
        DOM_ELEMENTS.addPppoeForm.reset();
        loadPppData(); // Recargar
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleAddPlan = async (e) => {
    e.preventDefault();
    try {
        const formData = new FormData(DOM_ELEMENTS.addPlanForm);
        const data = Object.fromEntries(formData);
        data.comment = "Managed by µMonitor";
        if (data.parent_queue === "none") delete data.parent_queue;
        
        // Lógica para pool
        const poolInputValue = data.pool_input;
        delete data.pool_input;
        // Valida si es un rango (contiene guion y punto) o un nombre de pool existente
        if (poolInputValue && poolInputValue.includes('.') && poolInputValue.includes('-')) {
            data.pool_range = poolInputValue;
        } else if (poolInputValue) {
            data.remote_address = poolInputValue;
        }

        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/create-plan`, { method: 'POST', body: JSON.stringify(data) });
        DomUtils.updateFeedback('Plan Creado', true);
        DOM_ELEMENTS.addPlanForm.reset();
        loadPppData(); // Recargar
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleDeletePppoe = (e) => {
    const service = e.currentTarget.dataset.service;
    DomUtils.confirmAndExecute(`¿Borrar el servidor PPPoE "${service}"?`, async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-pppoe-server?service_name=${encodeURIComponent(service)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Servidor PPPoE Eliminado', true);
            loadPppData(); // Recargar
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleDeletePlan = (e) => {
    const planName = e.currentTarget.dataset.plan; // El nombre base, ej. "Plan-5M"
    DomUtils.confirmAndExecute(`¿Borrar el Plan "${planName}"? Esto eliminará el perfil y el pool asociado.`, async () => {
        try {
            // El API endpoint espera el nombre base, no el "profile-..."
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-plan?plan_name=${encodeURIComponent(planName)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Plan Eliminado', true);
            loadPppData(); // Recargar
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- CARGADOR DE DATOS ---

export async function loadPppData(fullDetails) {
    try {
        const data = fullDetails || await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        
        renderPppProfiles(data.ppp_profiles);
        renderIpPools(data.ip_pools);
        renderPppoeServers(data.pppoe_servers);
        populateIpPoolSelects(data.ip_pools);

    } catch (e) {
        console.error("Error cargando datos de PPP:", e);
    }
}

// --- INICIALIZADOR ---

export function initPppModule() {
    DOM_ELEMENTS.addPppoeForm?.addEventListener('submit', handleAddPppoe);
    DOM_ELEMENTS.addPlanForm?.addEventListener('submit', handleAddPlan);
    // Los listeners de borrado se añaden en los render
}