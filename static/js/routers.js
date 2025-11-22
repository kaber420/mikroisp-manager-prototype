// static/js/routers.js

document.addEventListener('alpine:init', () => {
    Alpine.data('routerManager', () => ({
        // State
        routers: [],
        allZones: [],
        isLoading: true,
        isRouterModalOpen: false,
        isProvisionModalOpen: false,
        currentRouter: {},
        currentProvisionTarget: { newUser: 'api-user', newPass: '' },
        routerError: '',
        provisionError: '',
        provisionSuccess: '',
        isProvisioning: false,
        isEditing: false,

        // --- INIT ACTUALIZADO ---
        async init() {
            this.isLoading = true;
            await this.loadData();
            this.isLoading = false;

            // NUEVO: Reactividad
            window.addEventListener('data-refresh-needed', () => {
                if (!this.isRouterModalOpen && !this.isProvisionModalOpen) {
                    console.log("⚡ Routers: Recargando estado...");
                    this.loadData();
                }
            });
        },

        // Methods
        async loadData() {
            try {
                const [routersRes, zonesRes] = await Promise.all([
                    fetch('/api/routers'),
                    fetch('/api/zonas')
                ]);
                if (!routersRes.ok) throw new Error('Failed to load routers.');
                if (!zonesRes.ok) throw new Error('Failed to load zones.');
                this.routers = await routersRes.json();
                this.allZones = await zonesRes.json();
            } catch (error) {
                console.error('Error loading data:', error);
                this.routerError = error.message; // Show error on main page if needed
            }
        },

        getZoneName(zoneId) {
            const zone = this.allZones.find(z => z.id === zoneId);
            return zone ? zone.nombre : 'Unassigned';
        },

        // Router Modal
        openRouterModal(router = null) {
            this.routerError = '';
            if (router) {
                this.isEditing = true;
                this.currentRouter = { 
                    ...router,
                    password: '' // Clear password for security
                };
            } else {
                this.isEditing = false;
                this.currentRouter = {
                    host: '',
                    zona_id: '',
                    api_port: 8728,
                    username: 'admin',
                    password: ''
                };
            }
            this.isRouterModalOpen = true;
        },

        closeRouterModal() {
            this.isRouterModalOpen = false;
            this.currentRouter = {};
        },

        async saveRouter() {
            this.routerError = '';
            if (!this.currentRouter.host || !this.currentRouter.zona_id || !this.currentRouter.username) {
                this.routerError = 'Please fill in all required fields.';
                return;
            }
            if (!this.isEditing && !this.currentRouter.password) {
                this.routerError = 'Password is required for a new router.';
                return;
            }

            const url = this.isEditing ? `/api/routers/${encodeURIComponent(this.currentRouter.host)}` : '/api/routers';
            const method = this.isEditing ? 'PUT' : 'POST';

            // Don't send an empty password when editing
            const body = { ...this.currentRouter };
            if (this.isEditing && !body.password) {
                delete body.password;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to save router.');
                }
                await this.loadData();
                this.closeRouterModal();
            } catch (error) {
                this.routerError = error.message;
            }
        },

        async deleteRouter(host, hostname) {
            if (!confirm(`Are you sure you want to delete router "${hostname || host}"?`)) return;

            try {
                const response = await fetch(`/api/routers/${encodeURIComponent(host)}`, { method: 'DELETE' });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to delete router.');
                }
                this.routers = this.routers.filter(r => r.host !== host);
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        },

        // Provisioning Modal
        openProvisionModal(router) {
            this.provisionError = '';
            this.provisionSuccess = '';
            this.isProvisioning = false;
            this.currentProvisionTarget = { 
                host: router.host, 
                hostname: router.hostname,
                newUser: 'api-user', 
                newPass: '' 
            };
            this.isProvisionModalOpen = true;
        },

        closeProvisionModal() {
            this.isProvisionModalOpen = false;
            this.currentProvisionTarget = { newUser: 'api-user', newPass: '' };
        },

        async handleProvisionSubmit() {
            this.provisionError = '';
            this.provisionSuccess = '';
            this.isProvisioning = true;

            // Validación de campos
            if (!this.currentProvisionTarget.newUser || !this.currentProvisionTarget.newPass) {
                this.provisionError = 'Username and password are required.';
                this.isProvisioning = false;
                return;
            }

            try {
                // PASO 1: Aprovisionar (Crear usuario API y Certificados)
                const host = this.currentProvisionTarget.host;
                
                const provResponse = await fetch(`/api/routers/${encodeURIComponent(host)}/provision`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        new_api_user: this.currentProvisionTarget.newUser,
                        new_api_password: this.currentProvisionTarget.newPass
                    })
                });

                if (!provResponse.ok) {
                    const err = await provResponse.json();
                    throw new Error(err.detail || 'Provisioning failed.');
                }
                
                // Mensaje intermedio para que el usuario sepa qué pasa
                this.provisionSuccess = 'Provisioned! Verifying connectivity...';
                
                // PASO 2: Conexión Automática (Auto-Check)
                // Llamamos al endpoint que acabamos de crear para llenar la DB
                const checkResponse = await fetch(`/api/routers/${encodeURIComponent(host)}/check`, {
                    method: 'POST'
                });

                if (!checkResponse.ok) {
                    throw new Error('Provisioned successfully, but initial connection failed. Please check manually.');
                }

                // PASO 3: Éxito Total y Actualización de UI
                this.provisionSuccess = 'Success! Router is Online.';
                
                // Recargamos la tabla de fondo para que aparezca el punto verde "Online"
                await this.loadData(); 
                
                // Cerramos el modal después de un breve retraso para que lean el mensaje
                setTimeout(() => {
                    this.closeProvisionModal();
                }, 1500);

            } catch (error) {
                this.provisionError = error.message;
                // Si falló en el paso 2, al menos recargamos para mostrar que ya está provisionado (aunque esté offline)
                if (error.message.includes('initial connection')) {
                     await this.loadData();
                }
            } finally {
                this.isProvisioning = false;
            }
        },
        
        isRouterProvisioned(router) {
            return router.api_port === router.api_ssl_port;
        }
    }));
});
