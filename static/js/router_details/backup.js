// static/js/router_details/backup.js
import { ApiClient, DomUtils } from './utils.js';
import { CONFIG, DOM_ELEMENTS } from './config.js';

// --- RENDERIZADOR ---

function renderBackupFiles(files) {
    DOM_ELEMENTS.backupFilesList.innerHTML = (!files || files.length === 0) ? '<p class="text-text-secondary col-span-full">No hay backups.</p>' : '';
    files?.forEach(file => {
        const isBackup = file.type === 'backup';
        const card = document.createElement('div');
        card.className = `bg-surface-2 rounded-md p-2 flex justify-between items-center`;
        card.style.borderLeft = `4px solid ${isBackup ? CONFIG.COLORS.BACKUP : CONFIG.COLORS.RSC}`;

        card.innerHTML = `
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate" title="${file.name}">${file.name}</p>
                <p class="text-xs text-text-secondary ml-2">${DomUtils.formatBytes(file.size)}</p>
            </div>
            <button data-id="${file['.id'] || file.id}"
                    class="delete-backup-btn flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold
                           bg-danger/10 text-danger
                           hover:bg-danger hover:text-white
                           transition-colors">
                <span class="material-symbols-outlined text-sm">delete</span>
                <span>Delete</span>
            </button>
        `;
        DOM_ELEMENTS.backupFilesList.appendChild(card);
    });
    document.querySelectorAll('.delete-backup-btn').forEach(btn => btn.addEventListener('click', handleDeleteBackupFile));
}

// --- MANEJADORES (HANDLERS) ---

const handleCreateBackup = async (name, type) => {
    try {
        await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/create-backup`, {
            method: 'POST',
            body: JSON.stringify({ backup_name: name, backup_type: type })
        });
        DomUtils.updateFeedback('Backup creado', true);
        setTimeout(loadBackupData, 2000); // Recarga después de 2 segundos
    } catch (e) { DomUtils.updateFeedback(e.message, false); }
};

const handleCreateBackupForm = (e) => {
    e.preventDefault();
    const backupNameEl = DOM_ELEMENTS.backupNameInput;
    if (backupNameEl && backupNameEl.value) {
        handleCreateBackup(backupNameEl.value, e.submitter.dataset.type);
    } else {
        DomUtils.updateFeedback('El nombre del backup no puede estar vacío.', false);
    }
};

const handleDeleteBackupFile = (e) => {
    const fileId = e.currentTarget.dataset.id;
    DomUtils.confirmAndExecute('¿Borrar este archivo de backup del router?', async () => {
        try {
            await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/files/${encodeURIComponent(fileId)}`, { method: 'DELETE' });
            DomUtils.updateFeedback('Archivo Eliminado', true);
            loadBackupData(); // Recarga
        } catch (err) { DomUtils.updateFeedback(err.message, false); }
    });
};

// --- CARGADOR DE DATOS ---

export async function loadBackupData() {
    try {
        const files = await ApiClient.request(`/api/routers/${CONFIG.currentHost}/system/files`);
        renderBackupFiles(files);
    } catch (e) {
        console.error("Error en loadBackupData:", e);
        DOM_ELEMENTS.backupFilesList.innerHTML = `<p class="text-danger">${e.message}</p>`;
    }
}

// --- INICIALIZADOR ---

export function initBackupModule() {
    DOM_ELEMENTS.createBackupForm?.addEventListener('submit', handleCreateBackupForm);
    // El listener de borrado se añade en el render
}