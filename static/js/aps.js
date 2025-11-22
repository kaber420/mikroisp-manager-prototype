// static/js/aps.js

document.addEventListener('alpine:init', () => {
    Alpine.data('apManager', () => ({
        // State
        aps: [],
        allZones: [],
        isLoading: true,
        isModalOpen: false,

        // Test Connection State
        isTesting: false,
        testMessage: '',
        testStatus: '',

        // Edit State
        isEditing: false,
        originalHost: null, // Para guardar la IP original en caso de edición (ID)

        currentAp: {
            host: '',
            zona_id: '',
            username: 'ubnt',
            password: '',
            monitor_interval: ''
        },
        error: '',
        searchQuery: '',
        selectedZone: '',


        // Computed properties
        get filteredAps() {
            return this.aps.filter(ap => {
                const searchMatch = !this.searchQuery ||
                    (ap.hostname && ap.hostname.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (ap.host && ap.host.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (ap.mac && ap.mac.toLowerCase().includes(this.searchQuery.toLowerCase()));

                const zoneMatch = !this.selectedZone || ap.zona_id === parseInt(this.selectedZone);
                return searchMatch && zoneMatch;
            });
        },

        // Methods
        async init() {
            this.isLoading = true;
            await this.loadInitialData();
            this.isLoading = false;

            // ELIMINADO: this.startAutoRefresh(); 
            
            // NUEVO: Escucha Reactiva Global
            window.addEventListener('data-refresh-needed', () => {
                // Solo recargamos si el usuario NO está interactuando con un modal
                if (!this.isModalOpen && !this.isTesting) {
                    console.log("⚡ APs: Recargando lista por actualización en vivo.");
                    this.loadInitialData();
                } else {
                    console.log("⏳ APs: Actualización pausada (Usuario editando).");
                }
            });
        },

        async loadInitialData() {
            try {
                const [apsResponse, zonesResponse] = await Promise.all([
                    fetch('/api/aps'),
                    fetch('/api/zonas')
                ]);

                if (!apsResponse.ok) throw new Error('Failed to load APs.');
                if (!zonesResponse.ok) throw new Error('Failed to load zones.');

                this.aps = await apsResponse.json();
                this.allZones = await zonesResponse.json();

            } catch (error) {
                console.error('Error loading initial data:', error);
                this.error = error.message;
            }
        },

        async loadZonesForModal() {
            if (this.allZones.length === 0) {
                try {
                    const response = await fetch('/api/zonas');
                    if (!response.ok) throw new Error('Failed to load zones for modal.');
                    this.allZones = await response.json();
                } catch (error) {
                    console.error(error);
                    this.error = 'Could not load zones for the modal.';
                }
            }
        },

        resetModalState() {
            this.error = '';
            this.testMessage = '';
            this.testStatus = '';
            this.isTesting = false;
        },

        openModal(ap = null) {
            this.resetModalState();
            this.loadZonesForModal();

            if (ap) {
                // Lógica de EDICIÓN
                this.isEditing = true;
                this.originalHost = ap.host;
                // Copiamos los datos y limpiamos el password para no enviarlo si no se cambia
                this.currentAp = {
                    ...ap,
                    password: '' // Dejar en blanco para mantener la actual
                };
            } else {
                // Lógica de CREACIÓN
                this.isEditing = false;
                this.originalHost = null;
                this.currentAp = {
                    host: '',
                    zona_id: '',
                    username: 'ubnt',
                    password: '',
                    monitor_interval: ''
                };
            }
            this.isModalOpen = true;
        },

        async testConnection() {
            this.testMessage = '';
            this.testStatus = '';
            this.error = '';

            if (!this.currentAp.host || !this.currentAp.username || !this.currentAp.password) {
                this.testMessage = 'Host, Username, and Password are required for testing.';
                this.testStatus = 'error';
                return;
            }

            this.isTesting = true;

            try {
                const payload = {
                    host: this.currentAp.host,
                    username: this.currentAp.username,
                    password: this.currentAp.password,
                    zona_id: this.currentAp.zona_id || 0,
                    is_enabled: true
                };

                const response = await fetch('/api/aps/validate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (!response.ok) throw new Error(data.detail || 'Connection failed');

                this.testMessage = data.message;
                this.testStatus = 'success';

            } catch (error) {
                this.testMessage = error.message;
                this.testStatus = 'error';
            } finally {
                this.isTesting = false;
            }
        },

        closeModal() {
            this.isModalOpen = false;
            // Limpieza ligera, el reset completo se hace en openModal
            this.error = '';
        },

        async saveAp() {
            this.error = '';

            // Validación básica
            if (!this.currentAp.host || !this.currentAp.zona_id || !this.currentAp.username) {
                this.error = 'Please fill out all required fields (Host, Zone, Username).';
                return;
            }

            // En creación, el password es obligatorio
            if (!this.isEditing && !this.currentAp.password) {
                this.error = 'Password is required for new APs.';
                return;
            }

            // Determinar URL y Método
            const url = this.isEditing
                ? `/api/aps/${encodeURIComponent(this.originalHost)}`
                : '/api/aps';

            const method = this.isEditing ? 'PUT' : 'POST';

            // Preparar payload
            const payload = {
                ...this.currentAp,
                zona_id: parseInt(this.currentAp.zona_id),
                monitor_interval: this.currentAp.monitor_interval ? parseInt(this.currentAp.monitor_interval) : null
            };

            // Limpieza para actualización
            if (this.isEditing) {
                // No enviamos el host en el cuerpo si es una actualización (es la clave primaria en la URL)
                // Opcional: si permites cambiar la IP, el backend debe soportarlo, pero usualmente es mejor recrear.
                // Aquí asumimos que el host es inmutable en el body.
                delete payload.host;

                if (!payload.password) delete payload.password; // No enviar password vacío
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save AP.');
                }

                await this.loadInitialData(); // Refrescar tabla
                this.closeModal();

            } catch (error) {
                console.error('Save AP error:', error);
                this.error = error.message;
            }
        },

        async deleteAp(ap) {
            if (!confirm(`Are you sure you want to delete AP "${ap.hostname || ap.host}"?`)) return;

            try {
                const response = await fetch(`/api/aps/${encodeURIComponent(ap.host)}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to delete AP.');
                }

                // Optimista: eliminar de la lista local para respuesta instantánea
                this.aps = this.aps.filter(a => a.host !== ap.host);

            } catch (error) {
                console.error('Delete AP error:', error);
                alert(error.message);
            }
        },

        renderStatusBadge(status) {
            if (status === 'online') return `<div class="flex items-center gap-2"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
            if (status === 'offline') return `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
            return `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },
    }));
});
