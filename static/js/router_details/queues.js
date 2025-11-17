// static/js/router_details/queues.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADOR ---

function renderQueueTargetOptions(interfaces) {
    const datalist = document.getElementById('q-target-datalist');
    if (!datalist) return;
    datalist.innerHTML = '';
    interfaces?.forEach(iface => {
        datalist.innerHTML += `<option value="${iface.name}"></option>`;
    });
}

function renderParentQueues(queues) {
    DOM_ELEMENTS.parentQueueListDisplay.innerHTML = (!queues || queues.length === 0) ? '<p class="text-text-secondary">No hay colas.</p>' : '';
    DOM_ELEMENTS.parentQueueSelect.innerHTML = '<option value="none">-- Sin Cola Padre --</option>';

    queues?.forEach(queue => {
        const bw = queue['max-limit'] || '0/0';
        DOM_ELEMENTS.parentQueueListDisplay.innerHTML += `
            <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                <span class="text-sm">${queue.name}</span>
                <div class="flex items-center gap-2">
                    <span class="text-warning font-mono text-xs">${bw}</span>
                    <button class="delete-queue-btn invisible group-hover:visible text-danger hover:text-red-400" 
                            data-id="${queue['.id'] || queue.id}">
                        ${DOM_ELEMENTS.deleteIcon}
                    </button>
                </div>
            </div>`;
        
        DOM_ELEMENTS.parentQueueSelect.innerHTML += `<option value="${queue.name}">${queue.name} (${bw})</option>`;
    });
    
    document.querySelectorAll('.delete-queue-btn').forEach(btn => btn.addEventListener('click', handleDeleteParentQueue));
}

// --- MANEJADORES (HANDLERS) ---

const handleAddParentQueue = async (e) => {
    e.preventDefault();
    try {
        const data = new FormData(DOM_ELEMENTS.addParentQueueForm);
        const dst = data.get('dst');
        const payload = {
            name: data.get('name'),
            max_limit: data.get('max_limit'),
            target: data.get('target'),
            comment: `Managed by µMonitor: ${data.get('name')}`
        };

        if (dst) {
            payload.dst = dst;
        }

        const response = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-simple-queue`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        DomUtils.updateFeedback(response.message || 'Cola Creada', true);
        DOM_ELEMENTS.addParentQueueForm.reset();
        loadQueuesData(); // Recargar
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleDeleteParentQueue = (e) => {
    const queueId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar esta cola?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-simple-queue/${encodeURIComponent(queueId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Cola Eliminada', true);
            loadQueuesData(); // Recargar
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- CARGADOR DE DATOS ---

export async function loadQueuesData(fullDetails) {
    try {
        const data = fullDetails || await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        renderParentQueues(data.simple_queues);
        renderQueueTargetOptions(data.interfaces);
    } catch (e) {
        console.error("Error cargando datos de colas:", e);
    }
}

// --- INICIALIZADOR ---

export function initQueuesModule() {
    DOM_ELEMENTS.addParentQueueForm?.addEventListener('submit', handleAddParentQueue);
    // El listener de borrado se añade en el render
}