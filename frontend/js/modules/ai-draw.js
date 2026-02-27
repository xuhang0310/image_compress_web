/**
 * AI Drawing Module - 文生图/以图生图
 */

export class AIDrawModule {
    constructor() {
        // State
        this.currentMode = 'txt2img'; // 'txt2img' or 'img2img'
        this.uploadedImage = null; // Base64 of uploaded image
        this.isGenerating = false;

        // DOM Elements
        this.elements = {};

        this.init();
    }

    init() {
        this.initializeElements();
        this.attachEventListeners();
        this.updateModeUI();
    }

    initializeElements() {
        this.elements = {
            // Tabs
            txt2imgTab: document.querySelector('[data-tab="txt2img"]'),
            img2imgTab: document.querySelector('[data-tab="img2img"]'),

            // Upload area (img2img only)
            uploadAreaContainer: document.getElementById('uploadAreaContainer'),
            uploadArea: document.getElementById('uploadArea'),
            fileInput: document.getElementById('img2imgFileInput'),
            imagePreviewContainer: document.getElementById('imagePreviewContainer'),
            imagePreview: document.getElementById('imagePreview'),
            removeImageBtn: document.getElementById('removeImageBtn'),
            strengthSlider: document.getElementById('strengthSlider'),
            strengthValue: document.getElementById('strengthValue'),

            // Common - Prompt
            promptInput: document.getElementById('promptInput'),
            negativePromptInput: document.getElementById('negativePromptInput'),

            // Size selection
            sizeOptions: document.getElementById('sizeOptions'),

            // Sliders
            stepsSlider: document.getElementById('stepsSlider'),
            stepsValue: document.getElementById('stepsValue'),
            cfgSlider: document.getElementById('cfgSlider'),
            cfgValue: document.getElementById('cfgValue'),

            // Seed
            seedInput: document.getElementById('seedInput'),
            randomSeedBtn: document.getElementById('randomSeedBtn'),

            // Generate button
            generateBtn: document.getElementById('generateBtn'),

            // Loading
            loadingContainer: document.getElementById('loadingContainer'),
            loadingText: document.getElementById('loadingText'),

            // Result
            resultGallery: document.getElementById('resultGallery'),
            resultImage: document.getElementById('resultImage'),
            errorMessage: document.getElementById('errorMessage'),
            errorText: document.getElementById('errorText'),

            // Result actions
            downloadBtn: document.getElementById('downloadBtn'),
            newGenerationBtn: document.getElementById('newGenerationBtn')
        };
    }

    attachEventListeners() {
        // Tab switching
        if (this.elements.txt2imgTab) {
            this.elements.txt2imgTab.addEventListener('click', () => this.switchMode('txt2img'));
        }
        if (this.elements.img2imgTab) {
            this.elements.img2imgTab.addEventListener('click', () => this.switchMode('img2img'));
        }

        // Size selection
        if (this.elements.sizeOptions) {
            this.elements.sizeOptions.addEventListener('click', (e) => {
                if (e.target.classList.contains('size-btn')) {
                    document.querySelectorAll('.size-btn').forEach(btn => btn.classList.remove('active'));
                    e.target.classList.add('active');
                }
            });
        }

        // Sliders with value display
        if (this.elements.stepsSlider && this.elements.stepsValue) {
            this.elements.stepsSlider.addEventListener('input', (e) => {
                this.elements.stepsValue.textContent = e.target.value;
            });
        }
        if (this.elements.cfgSlider && this.elements.cfgValue) {
            this.elements.cfgSlider.addEventListener('input', (e) => {
                this.elements.cfgValue.textContent = e.target.value;
            });
        }
        if (this.elements.strengthSlider && this.elements.strengthValue) {
            this.elements.strengthSlider.addEventListener('input', (e) => {
                this.elements.strengthValue.textContent = e.target.value;
            });
        }

        // Random seed
        if (this.elements.randomSeedBtn) {
            this.elements.randomSeedBtn.addEventListener('click', () => {
                this.elements.seedInput.value = Math.floor(Math.random() * 2147483647);
            });
        }

        // Img2Img upload
        if (this.elements.uploadArea) {
            this.elements.uploadArea.addEventListener('click', () => {
                this.elements.fileInput.click();
            });

            this.elements.uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.elements.uploadArea.classList.add('drag-over');
            });

            this.elements.uploadArea.addEventListener('dragleave', () => {
                this.elements.uploadArea.classList.remove('drag-over');
            });

            this.elements.uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                this.elements.uploadArea.classList.remove('drag-over');
                const files = e.dataTransfer.files;
                if (files.length > 0 && files[0].type.startsWith('image/')) {
                    this.handleImageUpload(files[0]);
                }
            });
        }

        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleImageUpload(e.target.files[0]);
                }
            });
        }

        // Remove image
        if (this.elements.removeImageBtn) {
            this.elements.removeImageBtn.addEventListener('click', () => {
                this.removeUploadedImages();
            });
        }

        // Generate button
        if (this.elements.generateBtn) {
            this.elements.generateBtn.addEventListener('click', () => this.handleGenerate());
        }

        // Download result
        if (this.elements.downloadBtn) {
            this.elements.downloadBtn.addEventListener('click', () => this.handleDownload());
        }

        // New generation
        if (this.elements.newGenerationBtn) {
            this.elements.newGenerationBtn.addEventListener('click', () => {
                this.elements.resultGallery.classList.remove('show');
            });
        }
    }

    switchMode(mode) {
        this.currentMode = mode;

        // Update tabs
        document.querySelectorAll('.ai-tabs .tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${mode}"]`).classList.add('active');

        this.updateModeUI();
    }

    updateModeUI() {
        if (this.currentMode === 'img2img') {
            // Show upload area and strength slider for img2img
            if (this.elements.uploadAreaContainer) {
                this.elements.uploadAreaContainer.style.display = 'block';
            }
        } else {
            // Hide upload area and strength slider for txt2img
            if (this.elements.uploadAreaContainer) {
                this.elements.uploadAreaContainer.style.display = 'none';
            }
        }
    }

    async handleImageUpload(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.uploadedImage = e.target.result;

                // Show preview
                if (this.elements.imagePreview) {
                    this.elements.imagePreview.src = e.target.result;
                }
                if (this.elements.imagePreviewContainer) {
                    this.elements.imagePreviewContainer.classList.add('show');
                }
                if (this.elements.uploadArea) {
                    this.elements.uploadArea.style.display = 'none';
                }

                resolve();
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    removeUploadedImages() {
        this.uploadedImage = null;
        if (this.elements.imagePreviewContainer) {
            this.elements.imagePreviewContainer.classList.remove('show');
        }
        if (this.elements.uploadArea) {
            this.elements.uploadArea.style.display = 'block';
        }
        if (this.elements.fileInput) {
            this.elements.fileInput.value = '';
        }
    }

    getSelectedSize() {
        const activeBtn = this.elements.sizeOptions?.querySelector('.size-btn.active');
        return activeBtn ? activeBtn.dataset.size : '1024x1024';
    }

    async handleGenerate() {
        const prompt = this.elements.promptInput?.value.trim();

        if (!prompt) {
            this.showError('请输入提示词');
            return;
        }

        if (this.currentMode === 'img2img' && !this.uploadedImage) {
            this.showError('请上传一张图片');
            return;
        }

        if (this.isGenerating) {
            return;
        }

        this.isGenerating = true;
        this.setGeneratingState(true);
        this.hideError();
        this.elements.resultGallery?.classList.remove('show');

        try {
            const selectedSize = this.getSelectedSize();
            const steps = parseInt(this.elements.stepsSlider?.value || '20');
            const cfg = parseFloat(this.elements.cfgSlider?.value || '7.5');
            const seed = this.elements.seedInput?.value ? parseInt(this.elements.seedInput.value) : null;
            const strength = parseFloat(this.elements.strengthSlider?.value || '0.75');

            const payload = {
                prompt: prompt,
                negative_prompt: this.elements.negativePromptInput?.value.trim() || '',
                size: selectedSize,
                num_inferences_steps: steps,
                guidance_scale: cfg,
                seed: seed
            };

            if (this.currentMode === 'img2img') {
                payload.image = this.uploadedImage;
                payload.strength = strength;
            }

            this.updateLoadingText('正在生成中，请稍候...');

            const response = await fetch('/api/ai/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success && data.image_url) {
                this.showResult(data.image_url);
            } else {
                throw new Error(data.error || '生成失败');
            }

        } catch (error) {
            console.error('生成失败:', error);
            this.showError(error.message);
        } finally {
            this.isGenerating = false;
            this.setGeneratingState(false);
        }
    }

    setGeneratingState(generating) {
        if (this.elements.generateBtn) {
            this.elements.generateBtn.disabled = generating;
            this.elements.generateBtn.innerHTML = generating
                ? '<i class="fas fa-spinner fa-spin"></i> 生成中...'
                : '<i class="fas fa-magic"></i> 生成';
        }
        if (this.elements.loadingContainer) {
            this.elements.loadingContainer.style.display = generating ? 'block' : 'none';
        }
    }

    updateLoadingText(text) {
        if (this.elements.loadingText) {
            this.elements.loadingText.textContent = text;
        }
    }

    showResult(imageUrl) {
        if (this.elements.resultImage) {
            this.elements.resultImage.src = imageUrl;
        }
        if (this.elements.resultGallery) {
            this.elements.resultGallery.classList.add('show');
        }
        if (this.elements.loadingContainer) {
            this.elements.loadingContainer.style.display = 'none';
        }
    }

    showError(message) {
        if (this.elements.errorText) {
            this.elements.errorText.textContent = message;
        }
        if (this.elements.errorMessage) {
            this.elements.errorMessage.classList.add('show');
        }
        if (this.elements.loadingContainer) {
            this.elements.loadingContainer.style.display = 'none';
        }
    }

    hideError() {
        if (this.elements.errorMessage) {
            this.elements.errorMessage.classList.remove('show');
        }
    }

    async handleDownload() {
        const imageUrl = this.elements.resultImage?.src;
        if (!imageUrl) return;

        try {
            // If it's a data URL, download directly
            if (imageUrl.startsWith('data:')) {
                this.downloadDataUrl(imageUrl, 'ai-generated-image.png');
            } else {
                // Fetch the image as blob
                const response = await fetch(imageUrl);
                const blob = await response.blob();
                const blobUrl = URL.createObjectURL(blob);
                this.downloadDataUrl(blobUrl, 'ai-generated-image.png');
                URL.revokeObjectURL(blobUrl);
            }
        } catch (error) {
            console.error('下载失败:', error);
            // Fallback: open in new tab
            window.open(imageUrl, '_blank');
        }
    }

    downloadDataUrl(dataUrl, filename) {
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
}

// Initialize the module when the page loads
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', () => {
        new AIDrawModule();
    });
}
