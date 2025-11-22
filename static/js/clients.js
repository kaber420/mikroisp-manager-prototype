document.addEventListener('alpine:init', () => {
    Alpine.data('clientManager', () => ({
        // --- STATE ---
        allClients: [],
        isLoading: true,
        isModalOpen: false,
        currentTab: 'info',
        
        // Filtering
        searchQuery: '',
        statusFilter: 'all',

        // Modal State
        isEditing: false,
        currentClient: {},
        currentService: {},
        clientError: '',
        serviceError: '',

        // CPE State
        assignedCpes: [],
        unassignedCpes: [],
        selectedCpeToAssign: '',

        // Service State
        routersForSelect: [],
        profilesForSelect: [],
        pppoePasswordVisible: false,
        servicePlans: [],
        selectedPlan: null,
        
        // --- COMPUTED ---
        get filteredClients() {
            return this.allClients.filter(client => {
                const statusMatch = this.statusFilter === 'all' || client.service_status === this.statusFilter;
                const searchMatch = !this.searchQuery ||
                    client.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
                    (client.address && client.address.toLowerCase().includes(this.searchQuery.toLowerCase())) ||
                    (client.phone_number && client.phone_number.includes(this.searchQuery.toLowerCase()));
                return statusMatch && searchMatch;
            });
        },

        // --- METHODS ---
        // --- INIT ACTUALIZADO ---
        async init() {
            this.isLoading = true;
            await this.loadClients();
            this.isLoading = false;

            // NUEVO: Reactividad
            window.addEventListener('data-refresh-needed', () => {
                if (!this.isModalOpen) {
                    console.log("⚡ Clients: Recargando datos...");
                    this.loadClients();
                }
            });
        },

        async loadClients() {
            try {
                this.allClients = await (await fetch('/api/clients')).json();
            } catch (error) {
                console.error('Failed to load clients', error);
                alert('Error: Could not load clients.');
            }
        },

        // Modal Management
        async openClientModal(client = null) {
            this.resetModalState();
            if (client) {
                this.isEditing = true;
                this.currentClient = { ...client };
                await this.loadDataForModal(client.id);
            } else {
                this.isEditing = false;
                this.currentClient = { service_status: 'active' };
            }
            this.isModalOpen = true;
        },

        closeClientModal() {
            this.isModalOpen = false;
            this.resetModalState();
            this.loadClients();
        },
        
        resetModalState() {
            this.currentTab = 'info';
            this.isEditing = false;
            this.currentClient = {};
            this.currentService = {};
            this.clientError = '';
            this.serviceError = '';
            this.assignedCpes = [];
            this.unassignedCpes = [];
            this.routersForSelect = [];
            this.profilesForSelect = [];
            this.pppoePasswordVisible = false;
            this.servicePlans = []; 
            this.selectedPlan = null;
        },

        async loadDataForModal(clientId) {
            const promises = [
                this.loadAssignedCpes(clientId),
                this.loadUnassignedCpes(),
                this.loadRoutersForSelect(),
                this.loadServicePlans(),
                this.loadClientService(clientId)
            ];
            await Promise.all(promises);
        },

        switchTab(tabName) {
            if (tabName === 'service' && !this.isEditing) return;
            this.currentTab = tabName;
        },

        // Client Form (Tab 1)
        async saveClient() {
            this.clientError = '';
            if (!this.currentClient.name) {
                this.clientError = 'Client name is required.';
                return;
            }

            const url = this.isEditing ? `/api/clients/${this.currentClient.id}` : '/api/clients';
            const method = this.isEditing ? 'PUT' : 'POST';
            
            try {
                const response = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.currentClient)
                });
                if (!response.ok) throw new Error((await response.json()).detail);

                const savedClient = await response.json();
                await this.loadClients();

                if (!this.isEditing) {
                    this.isEditing = true;
                    this.currentClient = savedClient;
                    this.currentService.pppoe_username = savedClient.name.trim().replace(/\s+/g, '.').toLowerCase();
                    await this.loadDataForModal(savedClient.id);
                    this.switchTab('service');
                } else {
                    this.closeClientModal();
                }
            } catch (error) {
                this.clientError = error.message;
            }
        },
        
        async deleteClient(clientId, clientName) {
            if (!confirm(`Are you sure you want to delete client "${clientName}"?`)) return;
            try {
                const response = await fetch(`/api/clients/${clientId}`, { method: 'DELETE' });
                if (!response.ok) throw new Error((await response.json()).detail);
                this.allClients = this.allClients.filter(c => c.id !== clientId);
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        },

        // CPE Management
        async loadAssignedCpes(clientId) {
            try {
                this.assignedCpes = await (await fetch(`/api/clients/${clientId}/cpes`)).json();
            } catch (e) { console.error('Failed to load assigned CPEs'); }
        },
        async loadUnassignedCpes() {
            try {
                this.unassignedCpes = await (await fetch('/api/cpes/unassigned')).json();
            } catch (e) { console.error('Failed to load unassigned CPEs'); }
        },
        async assignCpe() {
            if (!this.selectedCpeToAssign) return;
            try {
                await fetch(`/api/cpes/${this.selectedCpeToAssign}/assign/${this.currentClient.id}`, { method: 'POST' });
                await this.loadAssignedCpes(this.currentClient.id);
                await this.loadUnassignedCpes();
                await this.loadClients(); 
                this.selectedCpeToAssign = '';
            } catch (error) { alert(`Error: ${error.message}`); }
        },
        async unassignCpe(cpeMac) {
            if (!confirm('Unassign this CPE?')) return;
            try {
                await fetch(`/api/cpes/${cpeMac}/unassign`, { method: 'POST' });
                await this.loadAssignedCpes(this.currentClient.id);
                await this.loadUnassignedCpes();
                await this.loadClients();
            } catch (error) { alert(`Error: ${error.message}`); }
        },

        // Service Form (Tab 2)
        async loadClientService(clientId) {
            try {
                const services = await (await fetch(`/api/clients/${clientId}/services`)).json();
                if (services && services.length > 0) {
                    this.currentService = services[0];
                    if (this.currentService.service_type === 'pppoe') {
                        if (this.currentService.router_host) {
                            await this.handleRouterChange();
                            this.currentService.profile_name = services[0].profile_name;
                        }
                    } else if (this.currentService.service_type === 'simple_queue') {
                        this.handlePlanChange();
                    }
                } else {
                     this.currentService.pppoe_username = this.currentClient.name.trim().replace(/\s+/g, '.').toLowerCase();
                }
            } catch (e) { console.error('Failed to load client service', e); }
        },

        async loadRoutersForSelect() {
            try {
                const allRouters = await (await fetch('/api/routers')).json();
                this.routersForSelect = allRouters;
            } catch (e) { console.error('Failed to load routers'); }
        },

        async handleRouterChange() {
            const host = this.currentService.router_host;
            this.profilesForSelect = [];
            if (!host) return;
            try {
                this.profilesForSelect = await (await fetch(`/api/routers/${host}/pppoe/profiles`)).json();
            } catch (e) { console.error('Failed to load profiles'); }
        },

        async loadServicePlans() {
            try {
                const response = await fetch('/api/plans');
                if(response.ok) {
                    this.servicePlans = await response.json(); 
                } else {
                    console.error('API endpoint /api/plans failed with status:', response.status);
                    this.servicePlans = [];
                }
            } catch (e) { 
                console.error('Failed to load service plans', e); 
                this.servicePlans = [];
            }
        },

        detectClientIp() {
            if (this.assignedCpes && this.assignedCpes.length > 0) {
                const cpe = this.assignedCpes.find(c => c.ip_address && c.ip_address !== '0.0.0.0');
                return cpe ? cpe.ip_address : null;
            }
            return null;
        },

        handlePlanChange() {
            if (!Array.isArray(this.servicePlans)) return;
            if (!this.currentService.plan_id) {
                this.selectedPlan = null;
                return;
            }
            this.selectedPlan = this.servicePlans.find(p => p.id == this.currentService.plan_id);
        },

        async saveService() {
            this.serviceError = '';
            const { router_host, service_type } = this.currentService;

            if (!router_host || !service_type) {
                this.serviceError = 'Router and Service Type are required.';
                return;
            }

            try {
                let routerResourceId = '';
                let profileNameOrPlan = '';
                let targetIp = null;

                // LÓGICA SIMPLE QUEUE (Usa BD Plans)
                if (service_type === 'simple_queue') {
                    if (!this.selectedPlan) {
                        this.serviceError = 'Please select a Service Plan.';
                        return;
                    }
                    targetIp = this.detectClientIp();
                    if (!targetIp) {
                        this.serviceError = 'Client needs an assigned CPE with an IP address to create a queue.';
                        return;
                    }

                    const queuePayload = {
                        name: this.currentClient.name,
                        target: targetIp,
                        max_limit: this.selectedPlan.max_limit,
                        parent: this.selectedPlan.parent_queue || 'none',
                        comment: `Client-ID:${this.currentClient.id} | Plan:${this.selectedPlan.name}`
                    };

                    const routerRes = await fetch(`/api/routers/${router_host}/write/add-simple-queue`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(queuePayload)
                    });
                    
                    if (!routerRes.ok) throw new Error(`Router Error: ${(await routerRes.json()).detail}`);
                    
                    const newQueue = await routerRes.json();
                    routerResourceId = newQueue.id || newQueue['.id'] || targetIp; 
                    profileNameOrPlan = this.selectedPlan.name;

                // LÓGICA PPPoE (Usa Router Profiles)
                } else if (service_type === 'pppoe') {
                    const { pppoe_username, password, profile_name } = this.currentService;
                    if (!pppoe_username || !password) {
                        this.serviceError = 'PPPoE Username and Password are required.';
                        return;
                    }
                    
                    // CORRECCIÓN: Usamos 'username' en lugar de 'name'
                    const pppoePayload = {
                        username: pppoe_username,
                        password: password,
                        service: 'pppoe',
                        profile: profile_name || 'default',
                        comment: `Client-ID: ${this.currentClient.id}`
                    };

                    // CORRECCIÓN: Endpoint correcto para PPPoE
                    const routerRes = await fetch(`/api/routers/${router_host}/pppoe/secrets`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(pppoePayload)
                    });

                    if (!routerRes.ok) {
                        const err = await routerRes.json().catch(() => ({ detail: 'Unknown Router Error' }));
                        throw new Error(`Router Error: ${err.detail}`);
                    }
                    
                    const newSecret = await routerRes.json();
                    routerResourceId = newSecret['.id'];
                    profileNameOrPlan = pppoePayload.profile;
                }

                const serviceData = {
                    router_host,
                    service_type,
                    pppoe_username: service_type === 'pppoe' ? this.currentService.pppoe_username : this.currentClient.name,
                    router_secret_id: routerResourceId,
                    profile_name: profileNameOrPlan,
                    plan_id: this.currentService.plan_id || null,
                    ip_address: targetIp,
                    suspension_method: service_type === 'pppoe' ? 'pppoe_secret_disable' : 'simple_queue_remove'
                };

                const serviceRes = await fetch(`/api/clients/${this.currentClient.id}/services`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(serviceData)
                });

                if (!serviceRes.ok) throw new Error(`API Error: ${(await serviceRes.json()).detail}`);

                alert('Service saved successfully!');
                this.closeClientModal();

            } catch (error) {
                console.error(error);
                this.serviceError = error.message;
            }
        },
        
        getStatusBadgeClass(status) {
            return {
                'active': 'bg-success/20 text-success',
                'pendiente': 'bg-warning/20 text-warning',
                'suspended': 'bg-danger/20 text-danger',
                'cancelled': 'bg-surface-2 text-text-secondary'
            }[status] || 'bg-surface-2 text-text-secondary';
        }
    }));
});