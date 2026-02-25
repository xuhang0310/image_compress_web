/**
 * Utility functions
 */

export const Utils = {
    // Show Toast Notification
    showToast(message, title = '提示', delay = 5000) {
        const toastElement = document.getElementById('toastAlert');
        const toastTitleElement = document.getElementById('toastTitle');
        const toastBodyElement = document.getElementById('toastBody');
        
        if (!toastElement || !toastTitleElement || !toastBodyElement) {
            console.error('Toast elements not found');
            return;
        }

        // Set title and message
        toastTitleElement.textContent = title;
        toastBodyElement.innerHTML = message;
        
        // Create Bootstrap Toast instance and show
        const bsToast = new bootstrap.Toast(toastElement, {
            delay: delay
        });
        
        bsToast.show();
    },

    // Format bytes to human readable string
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
};
