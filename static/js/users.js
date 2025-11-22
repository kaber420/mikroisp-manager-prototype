// static/js/users.js
document.addEventListener('alpine:init', () => {
    
    Alpine.data('userManager', () => ({
        
        // --- ESTADO (STATE) ---
        users: [],
        isLoading: true,
        isModalOpen: false,
        modalMode: 'add',
        
        currentUser: {
            username: '',
            password: '',
            role: 'admin',
            telegram_chat_id: '',
            receive_alerts: false,
            receive_announcements: false,
            disabled: false
        },
        errors: {
            username: null,
            password: null,
            telegram_chat_id: null,
            general: null
        },
        API_BASE_URL: window.location.origin,
        
        // --- MÉTODOS (METHODS) ---
        init() {
            this.loadUsers();
        },

        async loadUsers() {
            this.isLoading = true;
            this.errors = {}; 
            try {
                const response = await fetch(`${this.API_BASE_URL}/api/users`);
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || 'Failed to load users');
                }
                this.users = await response.json();
            } catch (err) {
                console.error('Error loading users:', err);
                this.errors.general = `Failed to load users: ${err.message}`;
            } finally {
                this.isLoading = false;
            }
        },
        
        _createEmptyUser() {
            return {
                username: '',
                password: '',
                role: 'admin',
                telegram_chat_id: '', 
                receive_alerts: false,
                receive_announcements: false,
                disabled: false
            };
        },

        openAddModal() {
            this.errors = {}; 
            this.modalMode = 'add';
            this.currentUser = this._createEmptyUser(); 
            this.isModalOpen = true;
        },

        openEditModal(user) {
            this.errors = {}; 
            this.modalMode = 'edit';
            this.currentUser = { 
                ...user, 
                password: '', 
                telegram_chat_id: user.telegram_chat_id || '' 
            };
            this.isModalOpen = true;
        },

        closeModal() {
            this.isModalOpen = false;
            this.errors = {}; 
        },

        _validate() {
            this.errors = {}; 
            const user = this.currentUser;

            if (this.modalMode === 'add') {
                if (!validators.isRequired(user.username)) {
                    this.errors.username = 'Username is required.';
                } else if (user.username.length < 3) {
                    this.errors.username = 'Must be at least 3 characters.';
                }
                
                if (!validators.isRequired(user.password)) {
                    this.errors.password = 'Password is required.';
                } else if (user.password.length < 6) {
                    this.errors.password = 'Must be at least 6 characters.';
                }
            }

            if (this.modalMode === 'edit' && user.password && user.password.length < 6) {
                this.errors.password = 'New password must be at least 6 characters.';
            }

            if (user.telegram_chat_id && isNaN(parseInt(user.telegram_chat_id, 10))) {
                this.errors.telegram_chat_id = 'Must be a numeric ID.';
            }
            
            return !Object.values(this.errors).some(error => error);
        },

        async saveUser() {
            if (!this._validate()) {
                return; 
            }

            const isEditing = this.modalMode === 'edit';
            const url = isEditing 
                ? `${this.API_BASE_URL}/api/users/${this.currentUser.username}`
                : `${this.API_BASE_URL}/api/users`;
            const method = isEditing ? 'PUT' : 'POST';

            const data = {
                role: this.currentUser.role,
                telegram_chat_id: this.currentUser.telegram_chat_id || null, 
                receive_alerts: this.currentUser.receive_alerts,
                receive_announcements: this.currentUser.receive_announcements,
                disabled: this.currentUser.disabled,
            };

            if (isEditing) {
                if (this.currentUser.password) {
                    data.password = this.currentUser.password;
                }
            } else {
                data.username = this.currentUser.username;
                data.password = this.currentUser.password;
            }

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to save user');
                }
                
                this.closeModal();
                await this.loadUsers(); 
            } catch (err) {
                this.errors.general = `Error: ${err.message}`;
            }
        },

        async deleteUser(user) {
            if (confirm(`Are you sure you want to delete user "${user.username}"?`)) {
                try {
                    const response = await fetch(`${this.API_BASE_URL}/api/users/${user.username}`, { method: 'DELETE' });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to delete user');
                    }
                    
                    this.users = this.users.filter(u => u.username !== user.username);

                } catch (err) {
                    alert(`Error: ${err.message}`);
                }
            }
        }
    }));
});