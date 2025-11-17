// static/js/router_details/users.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADORES ---

function renderRouterUsers(users) {
    DOM_ELEMENTS.routerUsersList.innerHTML = (!users || users.length === 0) ? '<p class="text-text-secondary">No hay usuarios.</p>' : '';
    users?.forEach(user => {
        // Asumiendo que no se puede borrar 'admin' o el usuario 'api-user'
        const isSystem = user.name === 'admin' || user.name === 'api-user'; 
        const delBtn = isSystem ? '' : `<button class="delete-user-btn invisible group-hover:visible text-danger hover:text-red-400" data-id="${user['.id'] || user.id}">${DOM_ELEMENTS.deleteIcon}</button>`;
        DOM_ELEMENTS.routerUsersList.innerHTML += `
            <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                <span class="font-semibold text-sm">${user.name} (${user.group})</span>
                ${delBtn}
            </div>`;
    });
    document.querySelectorAll('.delete-user-btn').forEach(btn => btn.addEventListener('click', handleDeleteRouterUser));
}

function populateAppUsers(users) {
    if (!DOM_ELEMENTS.appUserSelect) return;
    DOM_ELEMENTS.appUserSelect.innerHTML = '<option value="">Copiar de App...</option>' + users.map(u => `<option value="${u.username}">${u.username}</option>`).join('');
}


// --- MANEJADORES (HANDLERS) ---

const handleAddRouterUser = async (e) => {
    e.preventDefault();
    try {
        const u = document.getElementById('router-user-name').value;
        const p = document.getElementById('router-user-password').value;
        const g = document.getElementById('router-user-group').value;
        if (!u || !p || !g) {
            DomUtils.updateFeedback('Todos los campos son requeridos.', false);
            return;
        }
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users`, {
            method: 'POST',
            body: JSON.stringify({ username: u, password: p, group: g })
        });
        DomUtils.updateFeedback('Usuario creado', true);
        DOM_ELEMENTS.addRouterUserForm.reset();
        loadUsersData(); // Recargar
    } catch (err) { DomUtils.updateFeedback(err.message, false); }
};

const handleDeleteRouterUser = (e) => {
    const userId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar Usuario del Router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/users/${encodeURIComponent(userId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Usuario Eliminado', true);
            loadUsersData(); // Recargar
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

const handleAppUserSelectChange = () => {
    const userNameInput = document.getElementById('router-user-name');
    if (DOM_ELEMENTS.appUserSelect.value && userNameInput) {
        userNameInput.value = DOM_ELEMENTS.appUserSelect.value;
    }
};

// --- CARGADOR DE DATOS ---

export async function loadUsersData() {
    const safeFetch = (url) => ApiClient.request(url).catch(err => {
        console.error(`Error fetching ${url}:`, err.message);
        return null;
    });

    try {
        const [routerUsers, appUsers] = await Promise.all([
            safeFetch(`/api/routers/${CONFIG.currentHost}/system/users`),
            safeFetch('/api/users')
        ]);
        
        if (routerUsers) renderRouterUsers(routerUsers);
        if (appUsers) populateAppUsers(appUsers);
        
    } catch (e) {
        console.error("Error en loadUsersData:", e);
    }
}

// --- INICIALIZADOR ---

export function initUsersModule() {
    DOM_ELEMENTS.addRouterUserForm?.addEventListener('submit', handleAddRouterUser);
    DOM_ELEMENTS.appUserSelect?.addEventListener('change', handleAppUserSelectChange);
}