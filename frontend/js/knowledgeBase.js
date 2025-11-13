/**
 * Knowledge Base Management Module
 * Handles file upload, listing, search, and selection for test case generation
 */

export class KnowledgeBaseManager {
    constructor() {
        this.uploadedDocs = [];
        this.init();
    }

    init() {
        // Upload functionality
        const uploadBtn = document.getElementById('kbUploadBtn');
        const uploadFile = document.getElementById('kbUploadFile');
        const uploadFileLabel = document.getElementById('kbUploadFileLabel');
        const uploadLoading = document.getElementById('kbUploadLoading');

        if (uploadFile) {
            uploadFile.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    uploadFileLabel.textContent = file.name;
                }
            });
        }

        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => this.handleUpload(uploadFile, uploadLoading));
        }

        // Search functionality
        const searchBtn = document.getElementById('kbSearchBtn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.handleSearch());
        }

        // KB select buttons in generation/enhance forms
        this.initKbSelectButtons();

        // Load docs list
        this.loadDocsList();
    }

    async handleUpload(fileInput, loadingEl) {
        const file = fileInput.files[0];
        if (!file) {
            alert('请先选择文件');
            return;
        }

        const ext = file.name.split('.').pop().toLowerCase();
        if (!['md', 'csv', 'txt'].includes(ext)) {
            alert('只支持 .md / .csv / .txt 格式');
            return;
        }

        loadingEl.classList.remove('hidden');

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Upload to PRD endpoint (since KB can contain PRDs or test cases)
            const response = await fetch('/api/uploads/prds', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || '上传失败');
            }

            const result = await response.json();
            alert(`✅ 文档已上传并向量化：${result.name}`);
            
            // Reset form and reload list
            fileInput.value = '';
            document.getElementById('kbUploadFileLabel').textContent = '点击或拖拽文件到此处';
            this.loadDocsList();
        } catch (error) {
            console.error('Upload error:', error);
            alert(`上传失败：${error.message}`);
        } finally {
            loadingEl.classList.add('hidden');
        }
    }

    async loadDocsList() {
        const listEl = document.getElementById('kbDocsList');
        if (!listEl) return;

        try {
            // Load both PRDs and test cases
            const [prdsRes, testCasesRes] = await Promise.all([
                fetch('/api/uploads/prds'),
                fetch('/api/uploads/testcases')
            ]);

            const prds = await prdsRes.json();
            const testCases = await testCasesRes.json();

            this.uploadedDocs = [
                ...(prds.items || []).map(item => ({ ...item, type: 'prd' })),
                ...(testCases.items || []).map(item => ({ ...item, type: 'testcase' }))
            ];

            if (this.uploadedDocs.length === 0) {
                listEl.innerHTML = '<p class="placeholder">尚无文档，请先上传。</p>';
                return;
            }

            // Render list
            listEl.innerHTML = this.uploadedDocs.map(doc => `
                <div class="kb-doc-item" data-id="${doc.id}" data-type="${doc.type}">
                    <div class="kb-doc-info">
                        <span class="kb-doc-name">${doc.name}</span>
                        <span class="kb-doc-meta">${new Date(doc.created_at * 1000).toLocaleString()}</span>
                        <span class="kb-doc-type">${doc.type === 'prd' ? 'PRD' : '测试用例'}</span>
                    </div>
                    <button class="kb-doc-preview-btn" data-id="${doc.id}" data-type="${doc.type}">预览</button>
                </div>
            `).join('');

            // Add preview listeners
            listEl.querySelectorAll('.kb-doc-preview-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.previewDoc(btn.dataset.id, btn.dataset.type);
                });
            });
        } catch (error) {
            console.error('Load docs error:', error);
            listEl.innerHTML = '<p class="placeholder error">加载失败，请刷新重试。</p>';
        }
    }

    async previewDoc(id, type) {
        try {
            const endpoint = type === 'prd' ? `/api/uploads/prds/${id}` : `/api/uploads/testcases/${id}`;
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error('获取文档失败');
            
            const doc = await response.json();
            
            // Show in a modal or alert (simplified)
            const preview = doc.content.substring(0, 500);
            alert(`文档预览：${doc.name}\n\n${preview}${doc.content.length > 500 ? '...' : ''}`);
        } catch (error) {
            alert(`预览失败：${error.message}`);
        }
    }

    async handleSearch() {
        const queryInput = document.getElementById('kbSearchQuery');
        const searchBtn = document.getElementById('kbSearchBtn');
        const loadingEl = document.getElementById('kbSearchLoading');
        const resultsEl = document.getElementById('kbSearchResults');

        const query = queryInput.value.trim();
        if (!query) {
            alert('请输入查询文本');
            return;
        }

        loadingEl.classList.remove('hidden');
        searchBtn.disabled = true;

        try {
            const response = await fetch('/api/kb/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: 5 })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || '检索失败');
            }

            const data = await response.json();
            const results = data.results || [];

            if (results.length === 0) {
                resultsEl.innerHTML = '<p class="placeholder">未找到相关内容</p>';
            } else {
                resultsEl.innerHTML = results.map((r, i) => `
                    <div class="kb-search-result-item">
                        <div class="result-header">
                            <span class="result-rank">#${i + 1}</span>
                            <span class="result-score">相似度: ${(r.similarity * 100).toFixed(1)}%</span>
                        </div>
                        <div class="result-title">${r.title || '无标题'}</div>
                        <div class="result-text">${r.text.substring(0, 200)}...</div>
                        <div class="result-doc">来源: ${r.doc_name || r.doc_id}</div>
                    </div>
                `).join('');
            }

            resultsEl.classList.remove('hidden');
        } catch (error) {
            console.error('Search error:', error);
            alert(`检索失败：${error.message}`);
        } finally {
            loadingEl.classList.add('hidden');
            searchBtn.disabled = false;
        }
    }

    initKbSelectButtons() {
        document.querySelectorAll('.kb-select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const target = btn.dataset.target;
                this.showKbSelectionModal(target);
            });
        });
    }

    showKbSelectionModal(target) {
        // Filter docs by target type
        let filteredDocs = [];
        if (target === 'testcases') {
            filteredDocs = this.uploadedDocs.filter(d => d.type === 'testcase');
        } else {
            filteredDocs = this.uploadedDocs.filter(d => d.type === 'prd');
        }

        if (filteredDocs.length === 0) {
            alert('知识库中暂无相关文档，请先上传');
            return;
        }

        // Simple modal using prompt (in production, use a proper modal)
        const options = filteredDocs.map((d, i) => `${i + 1}. ${d.name}`).join('\n');
        const choice = prompt(`选择文档（输入序号）：\n\n${options}`);
        
        if (choice) {
            const index = parseInt(choice) - 1;
            if (index >= 0 && index < filteredDocs.length) {
                const selectedDoc = filteredDocs[index];
                this.applyKbSelection(target, selectedDoc);
            } else {
                alert('无效的选择');
            }
        }
    }

    async applyKbSelection(target, doc) {
        try {
            // Fetch full document content
            const endpoint = doc.type === 'prd' ? `/api/uploads/prds/${doc.id}` : `/api/uploads/testcases/${doc.id}`;
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error('获取文档失败');
            
            const fullDoc = await response.json();

            // Apply to corresponding input
            if (target === 'old') {
                // Old PRD in generate tab
                const label = document.getElementById('generateOldPrdLabel');
                if (label) label.textContent = `已选择：${doc.name}`;
                // Store in a data attribute or global state
                window._selectedOldPrdId = doc.id;
            } else if (target === 'new') {
                // New PRD in generate tab
                const label = document.getElementById('generateNewPrdLabel');
                if (label) label.textContent = `已选择：${doc.name}`;
                window._selectedNewPrdId = doc.id;
            } else if (target === 'testcases') {
                // Test cases in enhance tab
                const label = document.getElementById('enhanceFileLabel');
                if (label) label.textContent = `已选择：${doc.name}`;
                window._selectedTestCasesId = doc.id;
            }

            alert(`✅ 已选择文档：${doc.name}`);
        } catch (error) {
            alert(`选择失败：${error.message}`);
        }
    }
}

// Export singleton instance
export const kbManager = new KnowledgeBaseManager();
