document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;

    // --- Referencias a Elementos del DOM ---
    const addUserButton = document.getElementById('add-user-button');
    const userModal = document.getElementById('user-modal');
    const userForm = document.getElementById('user-form');
    const cancelUserButton = document.getElementById('cancel-user-button');
    const userFormError = document.getElementById('user-form-error');
    const modalTitle = document.getElementById('modal-title');
    const userListContainer = document.getElementById('user-list-container');
    
    // --- Referencias a los campos del formulario ---
    const userFormMode = document.getElementById('user-form-mode');
    const usernameInput = document.getElementById('user-username');
    const roleInput = document.getElementById('user-role');
    const passwordInput = document.getElementById('user-password');
    const passwordHelpText = document.getElementById('password-help-text');
    const telegramIdInput = document.getElementById('user-telegram_chat_id');
    const receiveAlertsCheckbox = document.getElementById('user-receive_alerts');
    const receiveAnnouncementsCheckbox = document.getElementById('user-receive_announcements');
    const disabledCheckbox = document.getElementById('user-disabled');


    // --- Funciones del Modal ---
    function openUserModal(user = null) {
        if (!userForm) return;
        userForm.reset();
        userFormError.classList.add('hidden');

        if (user) { // Modo Edición
            modalTitle.textContent = 'Edit User';
            userFormMode.value = 'edit';
            usernameInput.value = user.username;
            usernameInput.readOnly = true; // No permitir cambiar el nombre de usuario
            usernameInput.classList.add('cursor-not-allowed', 'bg-surface-2');
            
            passwordInput.placeholder = 'Leave blank to keep current password';
            passwordInput.required = false;
            passwordHelpText.classList.add('hidden');

            // Poblar el resto de los campos
            roleInput.value = user.role;
            telegramIdInput.value = user.telegram_chat_id || '';
            receiveAlertsCheckbox.checked = user.receive_alerts;
            receiveAnnouncementsCheckbox.checked = user.receive_announcements;
            disabledCheckbox.checked = user.disabled;

        } else { // Modo Creación
            modalTitle.textContent = 'Add New User';
            userFormMode.value = 'create';
            usernameInput.readOnly = false;
            usernameInput.classList.remove('cursor-not-allowed', 'bg-surface-2');
            
            passwordInput.placeholder = 'Enter a strong password';
            passwordInput.required = true;
            passwordHelpText.classList.remove('hidden');
        }
        userModal.classList.add('is-open');
    }

    function closeUserModal() {
        if (userModal) {
            userModal.classList.remove('is-open');
        }
    }
    
    // --- Lógica de la API ---
    async function handleUserFormSubmit(event) {
        event.preventDefault();
        const mode = userFormMode.value;
        const username = usernameInput.value;
        const isEditing = mode === 'edit';

        const url = isEditing ? `${API_BASE_URL}/api/users/${username}` : `${API_BASE_URL}/api/users`;
        const method = isEditing ? 'PUT' : 'POST';

        const data = {
            role: roleInput.value,
            telegram_chat_id: telegramIdInput.value || null,
            receive_alerts: receiveAlertsCheckbox.checked,
            receive_announcements: receiveAnnouncementsCheckbox.checked,
            disabled: disabledCheckbox.checked,
        };
        
        // Solo incluir el nombre de usuario y contraseña si estamos creando
        if (!isEditing) {
            data.username = username;
            data.password = passwordInput.value;
        } else if (passwordInput.value) {
            // Incluir contraseña solo si se ha introducido una nueva en modo edición
            data.password = passwordInput.value;
        }
        
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to ${isEditing ? 'update' : 'create'} user`);
            }
            closeUserModal();
            loadUsers();
        } catch (error) {
            userFormError.textContent = `Error: ${error.message}`;
            userFormError.classList.remove('hidden');
        }
    }
    
    async function handleDeleteUser(username) {
        if (confirm(`Are you sure you want to delete the user "${username}"?\nThis action cannot be undone.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/users/${username}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to delete user');
                }
                loadUsers();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }

    async function loadUsers() {
        if (!userListContainer) return;
        userListContainer.innerHTML = '<p class="p-8 text-center text-text-secondary">Loading users...</p>';
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/users`);
            if (!response.ok) throw new Error('Failed to load users');
            const users = await response.json();
            
            if (users.length === 0) {
                userListContainer.innerHTML = '<p class="p-8 text-center text-text-secondary">No users found. Click "Add New User" to get started.</p>';
                return;
            }
            
            userListContainer.innerHTML = ''; // Limpiar
            users.forEach(user => {
                const userRow = document.createElement('div');
                userRow.className = 'flex items-center justify-between p-4 border-b border-border-color last:border-b-0 hover:bg-surface-2';
                
                const roleBadge = `<span class="text-xs font-semibold px-2 py-1 rounded-full bg-primary/20 text-primary">${user.role}</span>`;
                const disabledBadge = user.disabled ? `<span class="text-xs font-semibold px-2 py-1 rounded-full bg-danger/20 text-danger">Disabled</span>` : '';
                const notificationIcon = (user.receive_alerts || user.receive_announcements) ? `<span class="material-symbols-outlined text-success text-base" title="Notifications enabled">notifications_active</span>` : `<span class="material-symbols-outlined text-text-secondary text-base" title="Notifications disabled">notifications_off</span>`;

                userRow.innerHTML = `
                    <div class="flex items-center gap-4">
                        <div class="flex items-center justify-center rounded-full bg-surface-2 shrink-0 size-10">
                            <span class="material-symbols-outlined">person</span>
                        </div>
                        <div>
                            <p class="font-semibold text-text-primary">${user.username}</p>
                            <div class="flex items-center gap-2 mt-1">
                                ${roleBadge}
                                ${disabledBadge}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-4">
                        ${notificationIcon}
                        <button title="Edit User" class="edit-btn text-text-secondary hover:text-primary"><span class="material-symbols-outlined">edit</span></button>
                        <button title="Delete User" class="delete-btn text-text-secondary hover:text-danger"><span class="material-symbols-outlined">delete</span></button>
                    </div>
                `;
                userRow.querySelector('.edit-btn').onclick = () => openUserModal(user);
                userRow.querySelector('.delete-btn').onclick = () => handleDeleteUser(user.username);
                userListContainer.appendChild(userRow);
            });
        } catch (error) {
            console.error('Error loading users:', error);
            userListContainer.innerHTML = `<p class="p-8 text-center text-danger">${error.message}</p>`;
        }
    }

    // --- Event Listeners ---
    if (addUserButton) addUserButton.addEventListener('click', () => openUserModal());
    if (cancelUserButton) cancelUserButton.addEventListener('click', closeUserModal);
    if (userForm) userForm.addEventListener('submit', handleUserFormSubmit);
    if (userModal) userModal.addEventListener('click', (e) => { if (e.target === userModal) closeUserModal(); });
    
    // Carga inicial de los usuarios
    loadUsers();
});