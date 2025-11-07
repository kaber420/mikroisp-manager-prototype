/**
 * Objeto global de Utilidades de Formulario.
 * Contiene funciones para manipular el DOM (mostrar/ocultar errores, resetear).
 * Depende de 'validators.js' (aunque no directamente en este archivo).
 */
(function(window) {
    "use strict";

    /**
     * Muestra un mensaje de error para un campo específico.
     * Asume que el elemento de error tiene el ID: [fieldId] + "-error"
     * @param {string} fieldId - El ID del <input> o <select> que tiene el error.
     * @param {string} message - El mensaje de error a mostrar.
     */
    function showFieldError(fieldId, message) {
        const errorElement = document.getElementById(fieldId + '-error');
        const fieldElement = document.getElementById(fieldId);
        
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('hidden');
        }
        if (fieldElement) {
            // Añade un borde rojo para destacar el campo con error
            fieldElement.classList.add('border-danger', 'focus:border-danger', 'focus:ring-danger');
        }
    }

    /**
     * Oculta el mensaje de error para un campo específico.
     * @param {string} fieldId - El ID del <input> o <select>.
     */
    function clearFieldError(fieldId) {
        const errorElement = document.getElementById(fieldId + '-error');
        const fieldElement = document.getElementById(fieldId);

        if (errorElement) {
            errorElement.textContent = '';
            errorElement.classList.add('hidden');
        }
        if (fieldElement) {
            // Quita el borde rojo
            fieldElement.classList.remove('border-danger', 'focus:border-danger', 'focus:ring-danger');
        }
    }

    /**
     * Limpia todos los mensajes de error visibles dentro de un formulario.
     * @param {HTMLElement} formElement - El elemento <form> que se va a limpiar.
     */
    function clearFormErrors(formElement) {
        if (!formElement) return;

        // Ocultar el error principal del formulario (si existe)
        const mainError = formElement.querySelector('.form-error-main'); // Asumimos una clase común
        if (mainError) {
            mainError.classList.add('hidden');
            mainError.textContent = '';
        }

        // Limpiar todos los campos individuales
        const errorMessages = formElement.querySelectorAll('[id$="-error"]');
        errorMessages.forEach(errorEl => {
            errorEl.classList.add('hidden');
            errorEl.textContent = '';
        });
        
        // Quitar todos los bordes rojos
        const errorFields = formElement.querySelectorAll('.border-danger');
        errorFields.forEach(field => {
            field.classList.remove('border-danger', 'focus:border-danger', 'focus:ring-danger');
        });
    }

    /**
     * Resetea un formulario modal a su estado original.
     * @param {string} modalId - El ID del modal.
     */
    function resetModalForm(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        const form = modal.querySelector('form');
        if (form) {
            form.reset(); // Resetea los valores del formulario
            clearFormErrors(form); // Limpia los mensajes de error
        }
    }

    // Exponer las funciones en un objeto global 'formUtils'
    window.formUtils = {
        showFieldError,
        clearFieldError,
        clearFormErrors,
        resetModalForm
    };

})(window);