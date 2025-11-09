document.addEventListener('DOMContentLoaded', () => {
    const oldPrdInput = document.getElementById('oldPrdInput');
    const newPrdInput = document.getElementById('newPrdInput');
    const oldPrdFileName = document.getElementById('oldPrdFileName');
    const newPrdFileName = document.getElementById('newPrdFileName');
    
    const generateBtn = document.getElementById('generateBtn');
    const exportBtn = document.getElementById('exportBtn');
    const loading = document.getElementById('loading');
    const testCaseOutput = document.getElementById('testCaseOutput');
    
    let oldPrdText = '';
    let newPrdText = '';
    let currentTestCases = ''; // 用于存储生成的测试用例

    // Generic file handler
    const handleFileSelect = (input, fileNameSpan, textVariableSetter) => {
        const file = input.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                textVariableSetter(e.target.result);
                fileNameSpan.textContent = file.name;
            };
            reader.readAsText(file);
        } else {
            textVariableSetter('');
            fileNameSpan.textContent = '点击或拖拽文件到此处';
        }
    };

    oldPrdInput.addEventListener('change', () => handleFileSelect(oldPrdInput, oldPrdFileName, (text) => oldPrdText = text));
    newPrdInput.addEventListener('change', () => handleFileSelect(newPrdInput, newPrdFileName, (text) => newPrdText = text));

    // Generic drag-and-drop handler
    const setupDragAndDrop = (wrapper, input) => {
        wrapper.addEventListener('dragover', (event) => {
            event.preventDefault();
            wrapper.classList.add('dragover');
        });
        wrapper.addEventListener('dragleave', () => {
            wrapper.classList.remove('dragover');
        });
        wrapper.addEventListener('drop', (event) => {
            event.preventDefault();
            wrapper.classList.remove('dragover');
            const file = event.dataTransfer.files[0];
            if (file) {
                input.files = event.dataTransfer.files;
                const changeEvent = new Event('change');
                input.dispatchEvent(changeEvent);
            }
        });
    };

    setupDragAndDrop(oldPrdInput.parentElement, oldPrdInput);
    setupDragAndDrop(newPrdInput.parentElement, newPrdInput);

    // Handle generation
    // Inject mode badge container above output when generating
    // Updated: second param now indicates whether vision (image understanding) actually used (from backend meta)
    const ensureModeBadge = (isIncremental, visionUsed) => {
        let indicator = document.querySelector('.mode-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'mode-indicator';
            testCaseOutput.parentElement.insertBefore(indicator, testCaseOutput);
        }
        const mode = isIncremental ? '增量模式' : '全量模式';
        const vision = visionUsed;
        indicator.innerHTML = '';
        const spanMode = document.createElement('span');
        spanMode.textContent = mode;
        indicator.appendChild(spanMode);
        const spanModel = document.createElement('span');
        spanModel.textContent = vision ? '视觉模型已启用' : '文本模型已启用';
        indicator.appendChild(spanModel);
    };

    generateBtn.addEventListener('click', async () => {
        if (!newPrdText.trim()) {
            alert('请至少上传新版PRD文件！');
            return;
        }

        loading.classList.remove('hidden');
        generateBtn.disabled = true;
        exportBtn.classList.add('hidden');
        generateBtn.style.backgroundColor = '#6c757d';
        const modeHint = oldPrdText.trim() ? '正在分析版本差异并生成增量用例...' : '正在生成全量用例...';
        // Initial badge assumes text-only until backend confirms vision usage
        ensureModeBadge(!!oldPrdText.trim(), false);
        testCaseOutput.innerHTML = `<p class="placeholder">${modeHint}</p>`;

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    old_prd: oldPrdText,
                    new_prd: newPrdText
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: '未知错误' }));
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error}`);
            }

            const data = await response.json();
            currentTestCases = data.test_cases; // 存储测试用例
            testCaseOutput.innerHTML = marked.parse(data.test_cases);
            exportBtn.classList.remove('hidden');
            // Update badge based on actual backend meta.use_vision
            if (data.meta) {
                ensureModeBadge(!!oldPrdText.trim(), !!data.meta.use_vision);
            }

            // 显示元信息（精简版：仅显示模型与模式）
            if (data.meta) {
                const { model_used, use_vision, mode } = data.meta;
                const infoBox = document.createElement('div');
                infoBox.style.marginTop = '12px';
                infoBox.style.fontSize = '0.8em';
                infoBox.style.lineHeight = '1.4em';
                let html = `<strong>处理结果：</strong> 模式=${mode}，模型=${model_used}，视觉=${use_vision ? '启用' : '禁用'}`;
                infoBox.innerHTML = html;
                testCaseOutput.appendChild(infoBox);
            }

        } catch (error) {
            console.error('Error generating test cases:', error);
            testCaseOutput.innerHTML = `<p class="error">生成失败: ${error.message}</p>`;
        } finally {
            loading.classList.add('hidden');
            generateBtn.disabled = false;
            generateBtn.style.backgroundColor = '#007bff';
        }
    });


    // Handle CSV export
    exportBtn.addEventListener('click', () => {
        const table = testCaseOutput.querySelector('table');
        if (!table) {
            alert('没有可导出的测试用例表格。');
            return;
        }
        
        let csvContent = "data:text/csv;charset=utf-8,";
        const rows = table.querySelectorAll('tr');
        
        rows.forEach(row => {
            const rowData = [];
            const cols = row.querySelectorAll('th, td');
            cols.forEach(col => {
                let data = col.innerText.replace(/"/g, '""');
                rowData.push(`"${data}"`);
            });
            csvContent += rowData.join(',') + "\r\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "test_cases.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});
