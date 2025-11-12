document.addEventListener('DOMContentLoaded', () => {
    // Tab 切换
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // 切换按钮状态
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 切换内容
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(tabName + 'Tab').classList.add('active');
        });
    });
    
    // PRD生成测试用例 Tab 元素
    const oldPrdInput = document.getElementById('oldPrdInput');
    const newPrdInput = document.getElementById('newPrdInput');
    const oldPrdFileName = document.getElementById('oldPrdFileName');
    const newPrdFileName = document.getElementById('newPrdFileName');
    
    const generateBtn = document.getElementById('generateBtn');
    const exportBtn = document.getElementById('exportBtn');
    const loading = document.getElementById('loading');
    const genProgressBar = document.getElementById('genProgressBar');
    const genProgressText = document.getElementById('genProgressText');
    const genEtaText = document.getElementById('genEtaText');
    const testCaseOutput = document.getElementById('testCaseOutput');
    
    // 完善测试用例 Tab 元素
    const testCaseInput = document.getElementById('testCaseInput');
    const testCaseFileName = document.getElementById('testCaseFileName');
    const enhanceBtn = document.getElementById('enhanceBtn');
    const exportEnhancedBtn = document.getElementById('exportEnhancedBtn');
    const enhanceLoading = document.getElementById('enhanceLoading');
    const enhancedOutput = document.getElementById('enhancedOutput');
    
    // 全局配置面板（不再使用弹窗）
    
    // 通用模型参数输入框
    const apiKeyInput = document.getElementById('apiKey');
    const baseUrlInput = document.getElementById('baseUrl');
    const textModelInput = document.getElementById('textModel');
    const visionModelInput = document.getElementById('visionModel');
    
    const disableVisionCheckbox = document.getElementById('disableVision');
    const visionParamsDiv = document.getElementById('visionParams');
    const maxImagesPerBatchInput = document.getElementById('maxImagesPerBatch');
    const imageMaxSizeInput = document.getElementById('imageMaxSize');
    const imageQualityInput = document.getElementById('imageQuality');
    const maxSectionCharsInput = document.getElementById('maxSectionChars');
    const batchInferConcInput = document.getElementById('batchInferConc');
    const imageDlConcInput = document.getElementById('imageDlConc');
    
    let oldPrdText = '';
    let newPrdText = '';
    let testCaseText = '';
    let currentTestCases = ''; // 用于存储生成的测试用例
    let currentEnhancedCases = ''; // 用于存储完善后的测试用例
    
    // 切换多模态参数显示
    const toggleVisionParams = () => {
        if (disableVisionCheckbox.checked) {
            visionParamsDiv.classList.add('hidden');
        } else {
            visionParamsDiv.classList.remove('hidden');
        }
    };
    
    // 监听复选框变化
    disableVisionCheckbox.addEventListener('change', () => {
        toggleVisionParams();
        localStorage.setItem('disableVision', disableVisionCheckbox.checked);
    });
    
    // 从 localStorage 加载配置
    const loadConfig = () => {
        // 通用模型参数（允许为空）
        if (apiKeyInput) apiKeyInput.value = localStorage.getItem('apiKey') || '';
        if (baseUrlInput) baseUrlInput.value = localStorage.getItem('baseUrl') || '';
        if (textModelInput) textModelInput.value = localStorage.getItem('textModel') || '';
        if (visionModelInput) visionModelInput.value = localStorage.getItem('visionModel') || '';
        const savedDisableVision = localStorage.getItem('disableVision');
        disableVisionCheckbox.checked = savedDisableVision === null ? true : savedDisableVision === 'true';
        maxImagesPerBatchInput.value = localStorage.getItem('maxImagesPerBatch') || '10';
        imageMaxSizeInput.value = localStorage.getItem('imageMaxSize') || '1024';
        imageQualityInput.value = localStorage.getItem('imageQuality') || '85';
        maxSectionCharsInput.value = localStorage.getItem('maxSectionChars') || '60000';
        batchInferConcInput.value = localStorage.getItem('batchInferConc') || '2';
        imageDlConcInput.value = localStorage.getItem('imageDlConc') || '4';
        toggleVisionParams();
    };
    
    // 绑定输入框自动保存到 localStorage
    const bindAutoSave = (el, key) => {
        if (!el) return;
        el.addEventListener('change', () => {
            localStorage.setItem(key, (el.value || '').trim());
        });
        el.addEventListener('blur', () => {
            localStorage.setItem(key, (el.value || '').trim());
        });
    };
    bindAutoSave(apiKeyInput, 'apiKey');
    bindAutoSave(baseUrlInput, 'baseUrl');
    bindAutoSave(textModelInput, 'textModel');
    bindAutoSave(visionModelInput, 'visionModel');
    bindAutoSave(maxImagesPerBatchInput, 'maxImagesPerBatch');
    bindAutoSave(imageMaxSizeInput, 'imageMaxSize');
    bindAutoSave(imageQualityInput, 'imageQuality');
    bindAutoSave(maxSectionCharsInput, 'maxSectionChars');
    bindAutoSave(batchInferConcInput, 'batchInferConc');
    bindAutoSave(imageDlConcInput, 'imageDlConc');

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
            // 获取用户配置（通用 + 多模态）直接从输入框读取
            const userConfig = {
                api_key: (apiKeyInput.value || '').trim() || undefined,
                base_url: (baseUrlInput.value || '').trim() || undefined,
                text_model: (textModelInput.value || '').trim() || undefined,
                vision_model: (visionModelInput.value || '').trim() || undefined,
                disable_vision: disableVisionCheckbox.checked,
                max_images_per_batch: maxImagesPerBatchInput.value ? parseInt(maxImagesPerBatchInput.value) : undefined,
                image_max_size: imageMaxSizeInput.value ? parseInt(imageMaxSizeInput.value) : undefined,
                image_quality: imageQualityInput.value ? parseInt(imageQualityInput.value) : undefined,
                max_section_chars: maxSectionCharsInput.value ? parseInt(maxSectionCharsInput.value) : undefined,
                batch_inference_concurrency: batchInferConcInput.value ? parseInt(batchInferConcInput.value) : undefined,
                image_download_concurrency: imageDlConcInput.value ? parseInt(imageDlConcInput.value) : undefined,
            };
            
            // 使用异步任务接口，获取 job_id 并轮询进度
            const startResp = await fetch('/api/generate_async', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    old_prd: oldPrdText,
                    new_prd: newPrdText,
                    config: userConfig,
                }),
            });
            if (!startResp.ok) {
                const err = await startResp.json().catch(() => ({ error: '未知错误' }));
                throw new Error(`启动失败: ${err.error || startResp.status}`);
            }
            const startData = await startResp.json();
            if (startData.cached) {
                currentTestCases = startData.result;
                testCaseOutput.innerHTML = marked.parse(startData.result);
                exportBtn.classList.remove('hidden');
                loading.classList.add('hidden');
                generateBtn.disabled = false;
                generateBtn.style.backgroundColor = '#007bff';
                return;
            }
            const jobId = startData.job_id;
            let done = false;
            let lastTotal = 0;
            while (!done) {
                await new Promise(r => setTimeout(r, 1000));
                const st = await fetch(`/api/job_status/${jobId}`);
                if (!st.ok) throw new Error('查询任务失败');
                const js = await st.json();
                if (js.progress) {
                    const { current, total } = js.progress;
                    lastTotal = total || lastTotal;
                    if (total > 0) {
                        const pct = Math.round((current / total) * 100);
                        genProgressBar.style.width = `${pct}%`;
                        genProgressText.textContent = `批次进度 ${current}/${total}`;
                    } else {
                        genProgressBar.style.width = '10%';
                        genProgressText.textContent = '准备中…';
                    }
                }
                if (typeof js.eta_seconds === 'number') {
                    const eta = Math.max(0, js.eta_seconds);
                    const m = Math.floor(eta / 60);
                    const s = eta % 60;
                    genEtaText.textContent = `预计剩余 ${m}分${s}秒`;
                }
                if (js.status === 'done') {
                    currentTestCases = js.result;
                    testCaseOutput.innerHTML = marked.parse(js.result);
                    exportBtn.classList.remove('hidden');
                    if (js.meta) {
                        ensureModeBadge(!!oldPrdText.trim(), !!js.meta.use_vision);
                        const { model_used, use_vision, mode } = js.meta;
                        const infoBox = document.createElement('div');
                        infoBox.style.marginTop = '12px';
                        infoBox.style.fontSize = '0.8em';
                        infoBox.style.lineHeight = '1.4em';
                        infoBox.innerHTML = `<strong>处理结果：</strong> 模式=${mode}，模型=${model_used}，视觉=${use_vision ? '启用' : '禁用'}`;
                        testCaseOutput.appendChild(infoBox);
                    }
                    done = true;
                } else if (js.status === 'error') {
                    throw new Error(js.error || '任务失败');
                }
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

    // ========== 完善测试用例功能 ==========
    
    // 文件上传处理 - 支持多种格式
    testCaseInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            testCaseFileName.textContent = file.name;
            const fileExtension = file.name.split('.').pop().toLowerCase();
            
            if (fileExtension === 'csv') {
                // 处理 CSV 文件
                const reader = new FileReader();
                reader.onload = (event) => {
                    testCaseText = event.target.result;
                };
                reader.readAsText(file);
            } else if (fileExtension === 'xlsx' || fileExtension === 'xls') {
                // 处理 Excel 文件
                const reader = new FileReader();
                reader.onload = (event) => {
                    const data = new Uint8Array(event.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    
                    // 转换为 Markdown 表格格式
                    const csvData = XLSX.utils.sheet_to_csv(worksheet);
                    const rows = csvData.split('\n');
                    
                    if (rows.length > 0) {
                        let markdown = '| ' + rows[0].split(',').join(' | ') + ' |\n';
                        markdown += '| ' + rows[0].split(',').map(() => '---').join(' | ') + ' |\n';
                        
                        for (let i = 1; i < rows.length; i++) {
                            if (rows[i].trim()) {
                                markdown += '| ' + rows[i].split(',').join(' | ') + ' |\n';
                            }
                        }
                        
                        testCaseText = markdown;
                    }
                };
                reader.readAsArrayBuffer(file);
            } else {
                // 处理 Markdown/TXT 文件
                const reader = new FileReader();
                reader.onload = (event) => {
                    testCaseText = event.target.result;
                };
                reader.readAsText(file);
            }
        }
    });

    // 完善测试用例按钮
    enhanceBtn.addEventListener('click', async () => {
        if (!testCaseText.trim()) {
            alert('请上传测试用例文件！');
            return;
        }

        enhanceLoading.classList.remove('hidden');
        enhanceBtn.disabled = true;
        enhanceBtn.style.backgroundColor = '#6c757d';
        exportEnhancedBtn.classList.add('hidden');
        enhancedOutput.innerHTML = '<p class="placeholder">AI 正在分析并完善测试用例...</p>';

        try {
            // 获取用户配置（与生成流程一致）直接从输入框读取
            const userConfig = {
                api_key: (apiKeyInput.value || '').trim() || undefined,
                base_url: (baseUrlInput.value || '').trim() || undefined,
                text_model: (textModelInput.value || '').trim() || undefined,
                vision_model: (visionModelInput.value || '').trim() || undefined,
                disable_vision: disableVisionCheckbox.checked,
                max_images_per_batch: maxImagesPerBatchInput.value ? parseInt(maxImagesPerBatchInput.value) : undefined,
                image_max_size: imageMaxSizeInput.value ? parseInt(imageMaxSizeInput.value) : undefined,
                image_quality: imageQualityInput.value ? parseInt(imageQualityInput.value) : undefined,
                max_section_chars: maxSectionCharsInput.value ? parseInt(maxSectionCharsInput.value) : undefined,
                batch_inference_concurrency: batchInferConcInput.value ? parseInt(batchInferConcInput.value) : undefined,
                image_download_concurrency: imageDlConcInput.value ? parseInt(imageDlConcInput.value) : undefined,
            };
            
            const response = await fetch('/api/enhance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    test_cases: testCaseText,
                    config: userConfig
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: '未知错误' }));
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error}`);
            }

            const data = await response.json();
            currentEnhancedCases = data.enhanced_cases;
            enhancedOutput.innerHTML = marked.parse(data.enhanced_cases);
            exportEnhancedBtn.classList.remove('hidden');

        } catch (error) {
            console.error('Error enhancing test cases:', error);
            enhancedOutput.innerHTML = `<p class="error">完善失败: ${error.message}</p>`;
        } finally {
            enhanceLoading.classList.add('hidden');
            enhanceBtn.disabled = false;
            enhanceBtn.style.backgroundColor = '#007bff';
        }
    });

    // 导出完善后的测试用例
    exportEnhancedBtn.addEventListener('click', () => {
        const table = enhancedOutput.querySelector('table');
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
        link.setAttribute("download", "enhanced_test_cases.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
    // 初始化配置显示
    loadConfig();
});
