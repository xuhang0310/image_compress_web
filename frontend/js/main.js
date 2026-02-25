import { CompressModule } from './modules/compress.js';
import { WatermarkModule } from './modules/watermark.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Modules
    const compressApp = new CompressModule();
    const watermarkApp = new WatermarkModule();

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.panel');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.dataset.tab;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update active panel
            panels.forEach(panel => {
                panel.classList.remove('active');
                if (panel.id === `${targetTab}-panel`) {
                    panel.classList.add('active');
                }
            });
        });
    });

    console.log('App initialized');
});
