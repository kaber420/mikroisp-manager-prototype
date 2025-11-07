// static/js/zonas.js

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;

    const addZoneButton = document.getElementById('add-zone-button');
    const zoneModal = document.getElementById('zone-modal');
    const zoneForm = document.getElementById('zone-form');
    const cancelZoneButton = document.getElementById('cancel-zone-button');
    const zoneFormError = document.getElementById('zone-form-error-main');
    const modalTitle = document.getElementById('modal-title');
    const zoneIdInput = document.getElementById('zone-id');
    const zoneNameInput = document.getElementById('zone-name');
    const zoneListContainer = document.getElementById('zone-list-container');

    function openZoneModal(zone = null) {
        if (!zoneForm) return;
        formUtils.resetModalForm('zone-modal');
        
        if (zone) {
            modalTitle.textContent = 'Edit Zone Name';
            zoneIdInput.value = zone.id;
            zoneNameInput.value = zone.nombre;
        } else {
            modalTitle.textContent = 'Add New Zone';
            zoneIdInput.value = '';
        }
        zoneModal.classList.add('is-open');
    }
    
    function closeZoneModal() {
        if (zoneModal) {
            zoneModal.classList.remove('is-open');
        }
    }
    
    async function handleZoneFormSubmit(event) {
        event.preventDefault();
        formUtils.clearFormErrors(zoneForm);
        let isValid = true;
        const zoneName = zoneNameInput.value;

        if (!validators.isValidZoneName(zoneName)) {
            formUtils.showFieldError('zone-name', 'El nombre es requerido y solo puede contener letras, números, espacios y guiones.');
            isValid = false;
        }
        
        if (!isValid) return;

        const zoneId = zoneIdInput.value;
        const isEditing = !!zoneId;
        const url = isEditing ? `${API_BASE_URL}/api/zonas/${zoneId}` : `${API_BASE_URL}/api/zonas`;
        // Para editar, ahora solo actualizamos el nombre desde este modal simple
        const method = isEditing ? 'PUT' : 'POST';
        const data = { nombre: zoneName };

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to ${isEditing ? 'update' : 'create'} zone`);
            }
            closeZoneModal();
            loadZones();
        } catch (error) {
            if (zoneFormError) {
                zoneFormError.textContent = `Error: ${error.message}`;
                zoneFormError.classList.remove('hidden');
            }
        }
    }
    
    async function handleDeleteZone(zoneId, zoneName) {
        if (confirm(`Are you sure you want to delete the zone "${zoneName}"?\nThis will also delete ALL its documentation and infrastructure data.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/zonas/${zoneId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to delete zone');
                }
                loadZones();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }

    async function loadZones() {
        if (!zoneListContainer) return;
        zoneListContainer.innerHTML = '<p class="p-8 text-center text-text-secondary">Loading zones...</p>';
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas`);
            if (!response.ok) throw new Error('Failed to load zones');
            const zones = await response.json();
            
            if (zones.length === 0) {
                zoneListContainer.innerHTML = '<p class="p-8 text-center text-text-secondary">No zones found. Click "Add New Zone" to get started.</p>';
                return;
            }
            
            zoneListContainer.innerHTML = '';
            zones.forEach(zone => {
                const zoneRow = document.createElement('div');
                zoneRow.className = 'flex items-center justify-between p-4 border-b border-border-color last:border-b-0 hover:bg-surface-2';
                
                // --- INICIO DE CAMBIO: Botón de "Manage" ---
                zoneRow.innerHTML = `
                    <div class="flex items-center gap-4">
                        <div class="flex items-center justify-center rounded-lg bg-primary/20 text-primary shrink-0 size-10">
                            <span class="material-symbols-outlined">hub</span>
                        </div>
                        <p class="font-semibold text-text-primary">${zone.nombre}</p>
                    </div>
                    <div class="flex items-center gap-4">
                        <button title="Rename Zone" class="edit-btn text-text-secondary hover:text-primary"><span class="material-symbols-outlined">edit</span></button>
                        <button title="Delete Zone" class="delete-btn text-text-secondary hover:text-danger"><span class="material-symbols-outlined">delete</span></button>
                        <button title="Manage Zone" class="manage-btn flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded-md bg-surface-2 hover:bg-border-color">
                            <span class="material-symbols-outlined text-base">settings</span>
                            Manage
                        </button>
                    </div>
                `;
                zoneRow.querySelector('.edit-btn').onclick = () => openZoneModal(zone); // Modal para renombrar rápido
                zoneRow.querySelector('.delete-btn').onclick = () => handleDeleteZone(zone.id, zone.nombre);
                zoneRow.querySelector('.manage-btn').onclick = () => {
                    window.location.href = `/zona/${zone.id}`; // Navega a la página de detalles
                };
                // --- FIN DE CAMBIO ---
                zoneListContainer.appendChild(zoneRow);
            });
        } catch (error) {
            console.error('Error loading zones:', error);
            zoneListContainer.innerHTML = `<p class="p-8 text-center text-danger">${error.message}</p>`;
        }
    }

    if (addZoneButton) addZoneButton.addEventListener('click', () => openZoneModal());
    if (cancelZoneButton) cancelZoneButton.addEventListener('click', closeZoneModal);
    if (zoneForm) zoneForm.addEventListener('submit', handleZoneFormSubmit);
    if (zoneModal) zoneModal.addEventListener('click', (e) => { if (e.target === zoneModal) closeZoneModal(); });
    
    loadZones();
});