document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    const zonaId = window.location.pathname.split('/').pop();
    let zonaData = null;

    // --- Element Cache ---
    const mainZoneName = document.getElementById('main-zonaname');
    const noteModal = document.getElementById('note-modal');
    const noteModalTitle = document.getElementById('note-modal-title');
    const noteForm = document.getElementById('note-form');
    const noteIdInput = document.getElementById('note-id');
    const noteTitleInput = document.getElementById('note-title');
    const noteEditor = document.getElementById('note-editor');
    const notePreview = document.getElementById('note-preview');
    const noteIsEncryptedInput = document.getElementById('note-is-encrypted');
    const notesListContainer = document.getElementById('notes-list');

    // --- Tab Switching Logic ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const tabName = button.getAttribute('data-tab');
            tabPanels.forEach(panel => {
                if (panel.id === `tab-${tabName}`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });

    // --- Data Loading & Rendering ---
    async function loadAllDetails() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/details`);
            if (!response.ok) throw new Error('Zone not found');
            zonaData = await response.json();
            
            renderGeneralInfo();
            renderInfraInfo();
            renderDocuments();
            renderNotes();
        } catch (error) {
            mainZoneName.textContent = 'Error';
            alert(`Failed to load zone details: ${error.message}`);
        }
    }

    function renderGeneralInfo() {
        if (!zonaData) return;
        mainZoneName.textContent = zonaData.nombre;
        document.getElementById('zona-nombre').value = zonaData.nombre;
        document.getElementById('zona-coordenadas').value = zonaData.coordenadas_gps || '';
        document.getElementById('zona-direccion').value = zonaData.direccion || '';
    }
    
    function renderInfraInfo() {
        if (!zonaData || !zonaData.infraestructura) return;
        const infra = zonaData.infraestructura;
        document.getElementById('infra-ip').value = infra.direccion_ip_gestion || '';
        document.getElementById('infra-gateway').value = infra.gateway_predeterminado || '';
        document.getElementById('infra-dns').value = infra.servidores_dns || '';
        document.getElementById('infra-vlans').value = infra.vlans_utilizadas || '';
        document.getElementById('infra-equipos').value = infra.equipos_criticos || '';
        document.getElementById('infra-mantenimiento').value = infra.proximo_mantenimiento || '';
    }
    
    function renderDocuments() {
        const gallery = document.getElementById('document-gallery');
        gallery.innerHTML = '';
        if (!zonaData || zonaData.documentos.length === 0) {
            gallery.innerHTML = '<p class="text-text-secondary">No documents uploaded for this zone.</p>';
            return;
        }

        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4';
        
        zonaData.documentos.forEach(doc => {
            const isImage = doc.tipo === 'image';
            const fileUrl = `/uploads/zonas/${doc.zona_id}/${doc.nombre_guardado}`;
            
            const card = document.createElement('div');
            card.className = 'bg-surface-2 rounded-lg p-3 text-center space-y-2';
            card.innerHTML = `
                <div class="flex items-center justify-center h-24 bg-background rounded-md">
                    ${isImage ? 
                        `<img src="${fileUrl}" alt="${doc.descripcion || 'Image'}" class="max-h-full max-w-full object-contain">` :
                        `<span class="material-symbols-outlined text-5xl text-text-secondary">description</span>`
                    }
                </div>
                <p class="text-sm font-medium truncate" title="${doc.nombre_original}">${doc.nombre_original}</p>
                <div class="flex justify-center gap-2">
                    <a href="${fileUrl}" target="_blank" class="text-primary hover:underline text-xs">View</a>
                    <a href="${fileUrl}" download="${doc.nombre_original}" class="text-primary hover:underline text-xs">Download</a>
                    <button data-doc-id="${doc.id}" class="delete-doc-btn text-danger hover:underline text-xs">Delete</button>
                </div>
            `;
            grid.appendChild(card);
        });
        gallery.appendChild(grid);
    }

    function renderNotes() {
        if (!zonaData || !zonaData.notes) return;
        notesListContainer.innerHTML = '';

        if (zonaData.notes.length === 0) {
            notesListContainer.innerHTML = '<p class="text-text-secondary">No notes for this zone yet.</p>';
            return;
        }

        zonaData.notes.forEach(note => {
            const card = document.createElement('div');
            card.className = 'bg-surface-1 rounded-lg border border-border-color p-4 flex justify-between items-start';
            
            const contentPreview = note.is_encrypted 
                ? '<p class="text-text-secondary italic">This note is encrypted.</p>'
                : marked.parse(note.content.substring(0, 200) + (note.content.length > 200 ? '...' : ''));

            card.innerHTML = `
                <div class="prose prose-invert max-w-none">
                    <h4 class="font-bold text-lg mb-2 flex items-center gap-2">
                        ${note.is_encrypted ? '<span class="material-symbols-outlined text-base">lock</span>' : ''}
                        ${note.title}
                    </h4>
                    <div class="text-sm text-text-secondary">${contentPreview}</div>
                </div>
                <div class="flex-shrink-0 ml-4">
                    <button data-note-id="${note.id}" class="edit-note-btn text-primary hover:underline text-sm">Edit</button>
                    <button data-note-id="${note.id}" class="delete-note-btn text-danger hover:underline text-sm ml-2">Delete</button>
                </div>
            `;
            notesListContainer.appendChild(card);
        });
    }

    // --- Modal Logic ---
    function openNoteModal(note = null) {
        noteForm.reset();
        if (note) {
            noteModalTitle.textContent = 'Edit Note';
            noteIdInput.value = note.id;
            noteTitleInput.value = note.title;
            noteEditor.value = note.content;
            noteIsEncryptedInput.checked = note.is_encrypted;
        } else {
            noteModalTitle.textContent = 'New Note';
            noteIdInput.value = '';
        }
        notePreview.innerHTML = marked.parse(noteEditor.value);
        noteModal.classList.remove('hidden');
        noteModal.classList.add('flex');
    }

    function closeNoteModal() {
        noteModal.classList.add('hidden');
        noteModal.classList.remove('flex');
    }

    // --- Event Listeners ---
    document.getElementById('new-note-btn').addEventListener('click', () => openNoteModal());
    document.getElementById('cancel-note-btn').addEventListener('click', closeNoteModal);
    document.getElementById('close-note-modal-btn').addEventListener('click', closeNoteModal);

    noteEditor.addEventListener('input', () => {
        notePreview.innerHTML = marked.parse(noteEditor.value);
    });

    notesListContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            const noteToEdit = zonaData.notes.find(n => n.id === noteId);
            openNoteModal(noteToEdit);
        }
        if (e.target.classList.contains('delete-note-btn')) {
            const noteId = parseInt(e.target.getAttribute('data-note-id'));
            if (confirm('Are you sure you want to delete this note?')) {
                deleteNote(noteId);
            }
        }
    });

    // --- Form Submissions & API Calls ---
    noteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const noteId = noteIdInput.value;
        const data = {
            title: noteTitleInput.value,
            content: noteEditor.value,
            is_encrypted: noteIsEncryptedInput.checked,
        };

        const url = noteId 
            ? `${API_BASE_URL}/api/zonas/notes/${noteId}`
            : `${API_BASE_URL}/api/zonas/${zonaId}/notes`;
        const method = noteId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to save note');
            }
            
            closeNoteModal();
            await loadAllDetails(); // Reload all data to get the updated notes list
            alert('Note saved successfully!');

        } catch (error) {
            alert(`Error saving note: ${error.message}`);
        }
    });

    async function deleteNote(noteId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/notes/${noteId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to delete note');
            }
            await loadAllDetails();
            alert('Note deleted successfully!');
        } catch (error) {
            alert(`Error deleting note: ${error.message}`);
        }
    }

    document.getElementById('form-general').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        
        try {
            await fetch(`${API_BASE_URL}/api/zonas/${zonaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            alert('General info saved!');
            loadAllDetails();
        } catch (error) {
            alert(`Error saving: ${error.message}`);
        }
    });

    document.getElementById('form-infra').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        data.zona_id = zonaId; // La API lo requiere en el body
        
        try {
            await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/infraestructura`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            alert('Infrastructure data saved!');
            loadAllDetails();
        } catch (error) {
            alert(`Error saving: ${error.message}`);
        }
    });

    document.getElementById('form-docs').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas/${zonaId}/documentos`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to upload');
            }
            e.target.reset();
            alert('File uploaded successfully!');
            loadAllDetails();
        } catch (error) {
            alert(`Error uploading file: ${error.message}`);
        }
    });
    
    // --- Event Delegation for Delete Buttons ---
    document.getElementById('document-gallery').addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-doc-btn')) {
            const docId = e.target.getAttribute('data-doc-id');
            if (confirm('Are you sure you want to delete this document?')) {
                try {
                    await fetch(`${API_BASE_URL}/api/documentos/${docId}`, { method: 'DELETE' });
                    alert('Document deleted.');
                    loadAllDetails();
                } catch (error) {
                    alert(`Error deleting document: ${error.message}`);
                }
            }
        }
    });

    // Initial Load
    loadAllDetails();
});