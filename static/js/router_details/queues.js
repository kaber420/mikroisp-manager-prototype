// static/js/router_details/queues.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS, state } from './config.js'; // Importamos 'state'

// --- RENDERIZADORES ---

function renderQueueTargetOptions(interfaces) {
    const datalist = document.getElementById('q-target-datalist');
    if (!datalist) return;
    datalist.innerHTML = '';
    interfaces?.forEach(iface => {
        datalist.innerHTML += `<option value="${iface.name}"></option>`;
    });
}

function renderParentQueues(queues) {
    // Clasificar colas
    const parentQueues = queues?.filter(q => q.comment && q.comment.includes('[PARENT]')) || [];

    // Renderizar la lista visual de colas padre
    DOM_ELEMENTS.parentQueueListDisplay.innerHTML = parentQueues.length === 0
        ? '<p class="text-text-secondary">No hay colas de infraestructura.</p>'
        : '';

    parentQueues.forEach(queue => {
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
    });

    // Poblar los <select> de "Cola Padre" solo con las colas de infraestructura
    const parentOptions = parentQueues.map(queue =>
        `<option value="${queue.name}">${queue.name} (${queue['max-limit'] || 'N/A'})</option>`
    ).join('');

    // Asumiendo que pueden existir múltiples selectores para colas padre
    const parentSelects = document.querySelectorAll('#add-plan-parent_queue, #lp-parent');
    parentSelects.forEach(select => {
        if (select) {
            const defaultValue = select.querySelector('option[value="none"], option[value=""]') ? select.querySelector('option[value="none"], option[value=""]').outerHTML : '';
            select.innerHTML = defaultValue + parentOptions;
        }
    });

    document.querySelectorAll('.delete-queue-btn').forEach(btn => btn.addEventListener('click', handleDeleteParentQueue));
}

// --- NUEVO: Renderizar planes locales ---
function renderLocalPlans(plans) {
    const tbody = DOM_ELEMENTS.localPlansTableBody;
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!plans || plans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="p-2 text-center text-text-secondary">No hay planes locales definidos.</td></tr>';
        return;
    }

    plans.forEach(plan => {
        tbody.innerHTML += `
            <tr class="hover:bg-surface-1">
                <td class="p-2">${plan.name}</td>
                <td class="p-2 font-mono text-xs">${plan.max_limit}</td>
                <td class="p-2 text-xs text-text-secondary">${plan.parent_queue || '-'}</td>
                <td class="p-2">
                    <button class="text-danger hover:text-red-400 delete-plan-btn" data-id="${plan.id}">
                        ${DOM_ELEMENTS.deleteIcon}
                    </button>
                </td>
            </tr>
        `;
    });

    document.querySelectorAll('.delete-plan-btn').forEach(btn =>
        btn.addEventListener('click', handleDeletePlan));
}

// --- MANEJADORES (HANDLERS) ---

const handleAddParentQueue = async (e) => {
    e.preventDefault();
    try {
        const formData = new FormData(DOM_ELEMENTS.addParentQueueForm);
        const isParent = formData.get('is_parent') === 'on';

        const payload = {
            name: formData.get('name'),
            max_limit: formData.get('max_limit'),
            target: formData.get('target'),
            comment: `Managed by µMonitor: ${formData.get('name')}`,
            is_parent: isParent
        };

        const response = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/add-simple-queue`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        DomUtils.updateFeedback(response.message || 'Cola Creada', true);
        DOM_ELEMENTS.addParentQueueForm.reset();
        document.getElementById('is-parent-checkbox').checked = true;

        loadQueuesData();
    } catch (err) {
        DomUtils.updateFeedback(err.message, false);
    }
};

const handleDeleteParentQueue = (e) => {
    const queueId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar esta cola?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/write/delete-simple-queue/${encodeURIComponent(queueId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Cola Eliminada', true);
            loadQueuesData();
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- NUEVO: Manejador para crear Plan Local ---
const handleCreateLocalPlan = async (e) => {
    e.preventDefault(); // <--- ¡IMPORTANTE! Evita el error SVG/XML

    DomUtils.updateFeedback("Procesando...", true);

    // 1. Obtener ID del router si no lo tenemos
    if (!state.routerId) {
        try {
            const routerData = await ApiClient.request(`/api/routers/${CONFIG.currentHost}`);
            if (routerData && routerData.id) {
                state.routerId = routerData.id;
            }
        } catch (err) {
            console.error("Error obteniendo ID del router:", err);
        }
    }

    if (!state.routerId) {
        DomUtils.updateFeedback("Error: No se pudo obtener el ID interno del router. Verifica la API.", false);
        return;
    }

    // 2. Preparar datos
    const formData = new FormData(DOM_ELEMENTS.createLocalPlanForm);
    const payload = {
        router_id: state.routerId,
        name: formData.get('name'),
        max_limit: formData.get('max_limit'),
        parent_queue: formData.get('parent_queue') || null,
        comment: "Creado desde µMonitor UI"
    };

    // 3. Enviar a la API
    try {
        await ApiClient.request('/api/plans', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        DomUtils.updateFeedback("Plan guardado correctamente", true);
        DOM_ELEMENTS.createLocalPlanForm.reset();
        loadQueuesData(); // Recargar listas
    } catch (err) {
        DomUtils.updateFeedback(`Error guardando plan: ${err.message}`, false);
    }
};

const handleDeletePlan = (e) => {
    const planId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute("¿Eliminar este plan local?", async () => {
        try {
            await ApiClient.request(`/api/plans/${planId}`, { method: 'DELETE' });
            loadQueuesData();
            DomUtils.updateFeedback("Plan eliminado", true);
        } catch (err) {
            DomUtils.updateFeedback(err.message, false);
        }
    });
};

// --- CARGADOR DE DATOS ---

export async function loadQueuesData(fullDetails) {
    try {
        // Si nos llegan los detalles completos, intentamos sacar el ID del router si viene ahí
        if (fullDetails && fullDetails.id) state.routerId = fullDetails.id; // Nota: fullDetails de /full-details no suele traer el ID raíz, pero lo dejamos por si acaso

        const data = fullDetails || await ApiClient.request(`/api/routers/${CONFIG.currentHost}/full-details`);
        renderParentQueues(data.simple_queues);
        renderQueueTargetOptions(data.interfaces);

        // Cargar también los planes locales desde la BD
        // Necesitamos el ID numérico para esto. Si no lo tenemos, lo intentamos buscar primero.
        if (!state.routerId) {
            const rData = await ApiClient.request(`/api/routers/${CONFIG.currentHost}`);
            state.routerId = rData.id;
        }

        if (state.routerId) {
            const localPlans = await ApiClient.request(`/api/plans/router/${state.routerId}`);
            renderLocalPlans(localPlans);
        }

    } catch (e) {
        console.error("Error cargando datos de colas/planes:", e);
    }
}

// --- INICIALIZADOR ---

export function initQueuesModule() {
    DOM_ELEMENTS.addParentQueueForm?.addEventListener('submit', handleAddParentQueue);
    // NUEVO: Registrar el listener para el formulario de planes locales
    DOM_ELEMENTS.createLocalPlanForm?.addEventListener('submit', handleCreateLocalPlan);
}