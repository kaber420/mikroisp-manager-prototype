// static/js/zonas.js

document.addEventListener('alpine:init', () => {
    
    Alpine.data('zoneManager', () => ({

        // --- ESTADO (STATE) ---
        zones: [],
        isLoading: true,
        isModalOpen: false,
        modalMode: 'add', // 'add' o 'edit'
        currentZone: { id: null, nombre: '' },
        error: '',
        API_BASE_URL: window.location.origin,

        // --- MÉTODOS (METHODS) ---
        
        /**
         * Inicializador (llamado por x-init)
         */
        init() {
            this.loadZones();
        },

        /**
         * Carga la lista de zonas desde la API.
         */
        async loadZones() {
            this.isLoading = true;
            try {
                const response = await fetch(`${this.API_BASE_URL}/api/zonas`);
                if (!response.ok) throw new Error('Failed to load zones');
                this.zones = await response.json();
            } catch (err) {
                console.error('Error loading zones:', err);
                alert('Could not load zones. Check the console.');
            } finally {
                this.isLoading = false;
            }
        },

        /**
         * Abre el modal en modo "Añadir".
         */
        openAddModal() {
            this.error = '';
            this.modalMode = 'add';
            this.currentZone = { id: null, nombre: '' };
            this.isModalOpen = true;
        },

        /**
         * Abre el modal en modo "Editar" con los datos de la zona.
         * @param {object} zone - El objeto de la zona seleccionada.
         */
        openEditModal(zone) {
            this.error = '';
            this.modalMode = 'edit';
            this.currentZone = { ...zone }; // Importante: ¡hacer una copia!
            this.isModalOpen = true;
        },

        /**
         * Cierra el modal.
         */
        closeModal() {
            this.isModalOpen = false;
            this.error = '';
        },

        /**
         * Lógica de guardado (Crear o Actualizar) llamada por @submit.
         */
        async saveZone() {
            this.error = '';

            // Validación
            if (!this.currentZone.nombre || this.currentZone.nombre.trim() === '') {
                this.error = 'Zone name cannot be empty.';
                return;
            }

            const isEditing = this.modalMode === 'edit';
            const url = isEditing 
                ? `${this.API_BASE_URL}/api/zonas/${this.currentZone.id}` 
                : `${this.API_BASE_URL}/api/zonas`;
            const method = isEditing ? 'PUT' : 'POST';
            const data = { nombre: this.currentZone.nombre };

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save zone');
                }

                this.closeModal();
                await this.loadZones(); // Recargamos la lista
            } catch (err) {
                this.error = `Error: ${err.message}`;
            }
        },
        
        /**
         * Borra una zona (con confirmación).
         * @param {object} zone - El objeto de la zona a borrar.
         */
        async deleteZone(zone) {
            if (confirm(`Are you sure you want to delete "${zone.nombre}"?`)) {
                try {
                    const response = await fetch(`${this.API_BASE_URL}/api/zonas/${zone.id}`, { method: 'DELETE' });
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to delete zone');
                    }
                    
                    this.zones = this.zones.filter(z => z.id !== zone.id);

                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            }
        }
    }));
});
