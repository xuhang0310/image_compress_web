import { Utils } from '../utils.js';

export class CompressModule {
    constructor() {
        // Global variables state
        this.currentFolderPath = '';
        this.currentFiles = [];
        this.selectedFiles = [];
        this.isSortedBySize = false;
        this.isFilterEnabled = false;

        // DOM Elements
        this.elements = {};

        this.init();
    }

    init() {
        this.initializeElements();
        this.attachEventListeners();
        this.loadDefaultSettings();
    }

    initializeElements() {
        this.elements = {
            folderPathInput: document.getElementById('folderPath'),
            browseFolderBtn: document.getElementById('browseFolderBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            targetSizeInput: document.getElementById('targetSize'),
            qualityInput: document.getElementById('quality'),
            formatSelect: document.getElementById('format'),
            fileListDiv: document.getElementById('fileList'),
            compressBtn: document.getElementById('compressBtn'),
            cancelBtn: document.getElementById('cancelBtn'),
            progressContainer: document.getElementById('progressContainer'),
            progressBar: document.getElementById('progressBar'),
            statusMessage: document.getElementById('statusMessage'),
            progressDetails: document.getElementById('progressDetails'),
            resultMessage: document.getElementById('resultMessage'),
            resultText: document.getElementById('resultText'),
            selectAllBtn: document.getElementById('selectAllBtn'),
            deselectAllBtn: document.getElementById('deselectAllBtn'),
            invertSelectionBtn: document.getElementById('invertSelectionBtn'),
            selectedCountSpan: document.getElementById('selectedCount'),
            filterToggle: document.getElementById('filterToggle'),
            sortBySizeBtn: document.getElementById('sortBySizeBtn'),
            
            // Rename Modal
            renameModal: document.getElementById('renameModal'),
            currentFileNameSpan: document.getElementById('currentFileName'),
            currentFilePathInput: document.getElementById('currentFilePath'),
            newFileNameInput: document.getElementById('newFileName'),
            confirmRenameBtn: document.getElementById('confirmRename'),
            cancelRenameBtn: document.getElementById('cancelRename'),
            closeRenameModalSpan: document.querySelector('.close-rename-modal')
        };
    }

    attachEventListeners() {
        const els = this.elements;
        if (!els.browseFolderBtn) return; // Guard if elements are missing

        els.browseFolderBtn.addEventListener('click', () => this.handleBrowseFolder());
        els.refreshBtn.addEventListener('click', () => this.loadFolderContents());
        els.selectAllBtn.addEventListener('click', () => this.handleSelectAll());
        els.deselectAllBtn.addEventListener('click', () => this.handleDeselectAll());
        els.invertSelectionBtn.addEventListener('click', () => this.handleInvertSelection());
        els.filterToggle.addEventListener('change', (e) => this.handleFilterToggle(e));
        els.sortBySizeBtn.addEventListener('click', () => this.handleSortBySize());
        els.compressBtn.addEventListener('click', () => this.handleCompress());
        els.cancelBtn.addEventListener('click', () => this.handleCancel());
        
        // Rename Modal
        els.confirmRenameBtn.addEventListener('click', () => this.handleConfirmRename());
        els.cancelRenameBtn.addEventListener('click', () => this.hideRenameModal());
        els.closeRenameModalSpan.addEventListener('click', () => this.hideRenameModal());
        
        window.addEventListener('click', (event) => {
            if (event.target === els.renameModal) {
                this.hideRenameModal();
            }
        });
    }

    async handleBrowseFolder() {
        try {
            // Use native file picker to select folder
            const input = document.createElement('input');
            input.type = 'file';
            input.webkitdirectory = true;
            input.directory = true;
            input.multiple = true;

            input.onchange = async (e) => {
                const files = Array.from(e.target.files).filter(f =>
                    f.type.startsWith('image/')
                );

                if (files.length === 0) {
                    Utils.showToast('文件夹中未找到图片文件', 'warning');
                    return;
                }

                // Try to get folder path from the first file
                // Note: file.path works in Electron or some browser environments
                const firstFile = files[0];
                const filePath = firstFile.path;
                
                if (filePath) {
                    // Extract directory path
                    // Handle both Windows and Unix separators
                    const separator = filePath.includes('\\') ? '\\' : '/';
                    const folderPath = filePath.substring(0, filePath.lastIndexOf(separator));
                    
                    if (folderPath) {
                        this.currentFolderPath = folderPath;
                        this.elements.folderPathInput.value = folderPath;
                        await this.loadFolderContents();
                    } else {
                        Utils.showToast('无法获取文件夹路径', 'error');
                    }
                } else {
                    // Fallback for environments where file.path is not exposed
                    // We can't use server-side scan, but we can display selected files
                    // However, current compression logic relies on server-side path scanning.
                    Utils.showToast('无法获取文件的绝对路径，请确保在支持的环境运行', 'error');
                }
            };

            input.click();
        } catch (error) {
            console.error('选择文件夹失败:', error);
            Utils.showToast('选择文件夹失败', 'error');
        }
    }

    async loadFolderContents() {
        if (!this.currentFolderPath) {
            Utils.showToast('请先选择一个文件夹', '提示');
            return;
        }

        try {
            const response = await fetch('/api/folder/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: this.currentFolderPath,
                    target_size: parseInt(this.elements.targetSizeInput.value),
                    quality: parseInt(this.elements.qualityInput.value),
                    format: this.elements.formatSelect.value
                })
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            this.currentFiles = data.files;
            this.displayFileList(this.currentFiles);
        } catch (error) {
            console.error('文件夹内容加载错误:', error);
            this.elements.fileListDiv.innerHTML = `<p class="text-danger text-center py-4">加载失败: ${error.message}</p>`;
        }
    }

    displayFileList(files) {
        if (files.length === 0) {
            this.elements.fileListDiv.innerHTML = '<p class="text-muted text-center py-4">文件夹中没有找到图片文件</p>';
            this.selectedFiles = [];
            this.updateSelectedCount();
            return;
        }

        // Sort
        let sortedFiles = [...files];
        if (this.isSortedBySize) {
            sortedFiles.sort((a, b) => b.size_kb - a.size_kb);
        }

        // Filter
        let filteredFiles = sortedFiles;
        if (this.isFilterEnabled) {
            const targetSize = parseInt(this.elements.targetSizeInput.value) || 128;
            filteredFiles = sortedFiles.filter(file => file.size_kb > targetSize);
        }

        if (filteredFiles.length === 0 && this.isFilterEnabled) {
            this.elements.fileListDiv.innerHTML = '<div class="text-center py-4"><p class="text-muted">没有大于目标大小的文件</p></div>';
            this.selectedFiles = [];
            this.updateSelectedCount();
            return;
        }

        let html = '<div class="file-grid">';
        filteredFiles.forEach((file) => {
            const isChecked = this.selectedFiles.includes(file.path) ? 'checked' : '';
            const previewUrl = `/api/preview?file=${encodeURIComponent(file.path)}&t=${new Date().getTime()}`;
            html += `
                <div class="file-card ${isChecked ? 'selected' : ''}">
                    <div class="card-img-container">
                        <input type="checkbox" class="file-checkbox" data-file-path="${file.path}" ${isChecked}>
                        <img src="${previewUrl}" class="card-img-top img-preview" alt="${file.name}" onerror="this.onerror=null;this.src='data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\" viewBox=\"0 0 24 24\"><rect width=\"24\" height=\"24\" fill=\"#f0f0f0\"/><path d=\"M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8.5 11.5L7 11l-1.5 1.5L3 9l5.5 5.5L11 12l5 5-7.5-7.5z\" fill=\"#999\"/></svg>';">
                    </div>
                    <div class="card-body">
                        <h6 class="card-title" title="${file.name}">${file.name}</h6>
                        <p class="card-text"><small class="text-muted">${file.size_kb}KB</small></p>
                        <div class="file-actions">
                            <button class="btn btn-sm btn-outline-primary rename-btn" data-file-path="${file.path}">重命名</button>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        this.elements.fileListDiv.innerHTML = html;

        // Bind events for dynamic elements
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleFileSelection(e));
        });

        document.querySelectorAll('.rename-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const filePath = e.target.getAttribute('data-file-path');
                this.showRenameModal(filePath);
            });
        });

        // Sync selected files
        this.selectedFiles = filteredFiles.filter(file => this.selectedFiles.includes(file.path)).map(file => file.path);
        this.updateSelectedCount();
    }

    handleFileSelection(e) {
        const filePath = e.target.dataset.filePath;
        
        if (e.target.checked) {
            if (!this.selectedFiles.includes(filePath)) {
                this.selectedFiles.push(filePath);
            }
        } else {
            this.selectedFiles = this.selectedFiles.filter(path => path !== filePath);
        }
        
        const card = e.target.closest('.file-card');
        if (card) {
            card.classList.toggle('selected', e.target.checked);
        }
        
        this.updateSelectedCount();
    }

    updateSelectedCount() {
        this.elements.selectedCountSpan.textContent = `已选择: ${this.selectedFiles.length} 张`;
    }

    handleSelectAll() {
        if (this.currentFiles.length === 0) return;
        
        const allFilePaths = this.currentFiles.map(file => file.path);
        
        if (this.isFilterEnabled) {
            const targetSize = parseInt(this.elements.targetSizeInput.value) || 128;
            this.selectedFiles = this.currentFiles
                .filter(file => file.size_kb > targetSize)
                .map(file => file.path);
        } else {
            this.selectedFiles = allFilePaths;
        }
        
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            const filePath = checkbox.dataset.filePath;
            checkbox.checked = this.selectedFiles.includes(filePath);
            
            const card = checkbox.closest('.file-card');
            if (card) {
                card.classList.toggle('selected', this.selectedFiles.includes(filePath));
            }
        });
        
        this.updateSelectedCount();
    }

    handleDeselectAll() {
        this.selectedFiles = [];
        
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            const card = checkbox.closest('.file-card');
            if (card) card.classList.remove('selected');
        });
        
        this.updateSelectedCount();
    }

    handleInvertSelection() {
        if (this.currentFiles.length === 0) return;
        
        const allFilePaths = this.currentFiles.map(file => file.path);
        let targetFilePaths = allFilePaths;
        
        if (this.isFilterEnabled) {
            const targetSize = parseInt(this.elements.targetSizeInput.value) || 128;
            targetFilePaths = this.currentFiles
                .filter(file => file.size_kb > targetSize)
                .map(file => file.path);
        }
        
        this.selectedFiles = targetFilePaths.filter(path => !this.selectedFiles.includes(path));
        
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            const filePath = checkbox.dataset.filePath;
            const shouldCheck = this.selectedFiles.includes(filePath);
            checkbox.checked = shouldCheck;
            
            const card = checkbox.closest('.file-card');
            if (card) card.classList.toggle('selected', shouldCheck);
        });
        
        this.updateSelectedCount();
    }

    handleFilterToggle(e) {
        this.isFilterEnabled = e.target.checked;
        this.displayFileList(this.currentFiles);
    }

    handleSortBySize() {
        this.isSortedBySize = !this.isSortedBySize;
        this.elements.sortBySizeBtn.textContent = this.isSortedBySize ? '取消排序' : '按大小排序';
        this.displayFileList(this.currentFiles);
    }

    async handleCompress() {
        if (!this.currentFolderPath) {
            Utils.showToast('请先选择一个文件夹', '提示');
            return;
        }

        let filesToProcess = this.selectedFiles;

        if (filesToProcess.length === 0) {
            if (this.isFilterEnabled) {
                const targetSize = parseInt(this.elements.targetSizeInput.value) || 128;
                const allFiles = this.currentFiles.filter(file => file.size_kb > targetSize);

                if (allFiles.length > 0) {
                    if (confirm(`${allFiles.length}个文件大于目标大小，是否处理全文件？`)) {
                        filesToProcess = allFiles.map(file => file.path);
                    } else {
                        Utils.showToast('请至少选择一张图片', '提示');
                        return;
                    }
                } else {
                    Utils.showToast('没有大于目标大小的文件', '提示');
                    return;
                }
            } else {
                Utils.showToast('请至少选择一张图片', '提示');
                return;
            }
        }

        try {
            this.elements.progressContainer.style.display = 'block';
            this.elements.resultMessage.style.display = 'none';

            const response = await fetch('/api/compress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: this.currentFolderPath,
                    target_size: parseInt(this.elements.targetSizeInput.value),
                    quality: parseInt(this.elements.qualityInput.value),
                    format: this.elements.formatSelect.value,
                    selected_files: filesToProcess
                })
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            await this.pollTaskStatus(data.task_id);
        } catch (error) {
            console.error('压缩开始错误:', error);
            Utils.showToast('压缩开始失败: ' + error.message, '错误');
            this.elements.progressContainer.style.display = 'none';
        }
    }

    async pollTaskStatus(taskId) {
        let completed = false;
        while (!completed) {
            try {
                const response = await fetch(`/api/task/${taskId}`);
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

                const status = await response.json();
                this.elements.progressBar.style.width = status.progress + '%';
                this.elements.statusMessage.textContent = status.message;
                this.elements.progressDetails.textContent = `进度: ${Math.round(status.progress)}% (${status.processed_files}/${status.total_files} 文件)`;

                if (status.status === 'completed' || status.status === 'failed') {
                    completed = true;
                    this.elements.progressContainer.style.display = 'none';
                    this.elements.resultText.textContent = status.message;
                    this.elements.resultMessage.className = status.status === 'completed' ? 'alert alert-success' : 'alert alert-danger';
                    this.elements.resultMessage.style.display = 'block';
                }
            } catch (error) {
                console.error('获取任务状态错误:', error);
                this.elements.statusMessage.textContent = '状态获取失败: ' + error.message;
                completed = true;
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    showRenameModal(filePath) {
        const fileName = filePath.split('\\').pop().split('/').pop();
        this.elements.currentFileNameSpan.textContent = fileName;
        this.elements.currentFilePathInput.value = filePath;
        this.elements.newFileNameInput.value = fileName.split('.')[0];
        this.elements.renameModal.style.display = 'block';
    }

    hideRenameModal() {
        this.elements.renameModal.style.display = 'none';
    }

    async handleConfirmRename() {
        const filePath = this.elements.currentFilePathInput.value;
        const newFileName = this.elements.newFileNameInput.value.trim();
        
        if (!newFileName) {
            Utils.showToast('请输入新的文件名', '错误');
            return;
        }
        
        try {
            const response = await fetch('/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_path: filePath,
                    new_name: newFileName
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                Utils.showToast(data.message, '成功');
                this.hideRenameModal();
                await this.loadFolderContents();
            } else {
                Utils.showToast(`重命名失败: ${data.message || '未知错误'}`, '错误');
            }
        } catch (error) {
            console.error('重命名请求失败:', error);
            Utils.showToast(`重命名失败: ${error.message}`, '错误');
        }
    }

    handleCancel() {
        this.elements.folderPathInput.value = '';
        this.elements.targetSizeInput.value = '128';
        this.elements.qualityInput.value = '85';
        this.elements.formatSelect.value = '保持原格式';
        this.elements.fileListDiv.innerHTML = '<p class="text-muted text-center py-4">请选择一个文件夹以查看内容</p>';
        this.currentFolderPath = '';
        this.currentFiles = [];
        this.selectedFiles = [];
        this.updateSelectedCount();
        this.elements.progressContainer.style.display = 'none';
        this.elements.resultMessage.style.display = 'none';
    }

    async loadDefaultSettings() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const settings = await response.json();
                this.elements.targetSizeInput.value = settings.default_target_size;
                this.elements.qualityInput.value = settings.default_quality;
            }
        } catch (error) {
            console.error('加载默认设置错误:', error);
        }
        
        try {
            const response = await fetch('/api/default-path');
            if (response.ok) {
                const data = await response.json();
                if (!this.elements.folderPathInput.value) {
                    this.elements.folderPathInput.value = data.default_path;
                    this.currentFolderPath = data.default_path;
                }
            }
        } catch (error) {
            console.error('获取默认路径错误:', error);
            if (!this.elements.folderPathInput.value) {
                this.elements.folderPathInput.value = 'C:\\Users\\Administrator\\Downloads\\';
                this.currentFolderPath = 'C:\\Users\\Administrator\\Downloads\\';
            }
        }
    }
}
