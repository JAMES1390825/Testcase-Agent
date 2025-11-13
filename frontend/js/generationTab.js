import { buildRequestConfig } from "./configStore.js";

let oldPrdText = "";
let newPrdText = "";
let currentTestCases = ""; // may be CSV or Markdown table

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => resolve(event.target?.result ?? "");
        reader.onerror = () => reject(new Error("无法读取文件"));
        reader.readAsText(file);
    });
}

function setupFileInput(input, label, onContent) {
    if (!input || !label) {
        return;
    }

    input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (!file) {
            label.textContent = "点击或拖拽文件到此处";
            onContent("");
            return;
        }

        try {
            const content = await readFileAsText(file);
            label.textContent = file.name;
            onContent(String(content));
        } catch (error) {
            console.error(error);
            alert("文件读取失败，请重试。");
            input.value = "";
            label.textContent = "点击或拖拽文件到此处";
            onContent("");
        }
    });

    const dropzone = input.closest(".file-upload-wrapper");
    if (!dropzone) {
        return;
    }

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (event) => {
        const file = event.dataTransfer?.files?.[0];
        if (!file) {
            return;
        }
        input.files = event.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
    });
}

function renderMarkdown(target, markdown) {
    if (!target) {
        return;
    }

    if (!markdown.trim()) {
        target.innerHTML = '<p class="placeholder">暂无内容可显示。</p>';
        return;
    }

    target.innerHTML = marked.parse(markdown);
}

function isLikelyCsv(text) {
    if (!text) return false;
    const hasPipe = /\|/.test(text);
    const hasComma = /,/.test(text);
    const looksTabbed = /\t/.test(text);
    return hasComma && !hasPipe && /\n.+\n/.test(text) && !looksTabbed;
}

function csvToHtmlTable(csvText) {
    const rows = [];
    let i = 0;
    const s = csvText.replace(/\r\n?/g, "\n");
    while (i < s.length) {
        const row = [];
        let field = "";
        let inQuotes = false;
        for (; i <= s.length; i += 1) {
            const ch = s[i];
            if (inQuotes) {
                if (ch === '"') {
                    if (s[i + 1] === '"') { field += '"'; i += 1; } else { inQuotes = false; }
                } else if (ch === undefined) {
                    break;
                } else { field += ch; }
            } else if (ch === '"') {
                inQuotes = true;
            } else if (ch === ',') {
                row.push(field);
                field = "";
            } else if (ch === '\n' || ch === undefined) {
                row.push(field);
                rows.push(row);
                i += 1;
                break;
            } else {
                field += ch;
            }
        }
    }
    if (!rows.length) return "<p class=\"placeholder\">暂无内容可显示。</p>";
    const header = rows[0] || [];
    const body = rows.slice(1);
    const escape = (t) => String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    let html = '<table><thead><tr>' + header.map((h) => `<th>${escape(h)}</th>`).join("") + '</tr></thead><tbody>';
    for (const r of body) {
        html += '<tr>' + r.map((c) => `<td>${escape(c)}</td>`).join("") + '</tr>';
    }
    html += '</tbody></table>';
    return html;
}

function updateModeIndicator(indicator, { modeText, visionUsed }) {
    if (!indicator) {
        return;
    }

    indicator.classList.remove("hidden");
    indicator.innerHTML = "";

    const modeBadge = document.createElement("span");
    modeBadge.textContent = modeText;
    indicator.appendChild(modeBadge);

    const visionBadge = document.createElement("span");
    visionBadge.textContent = visionUsed ? "视觉模型已启用" : "文本模型已启用";
    indicator.appendChild(visionBadge);
}

function resetModeIndicator(indicator) {
    if (!indicator) {
        return;
    }

    indicator.classList.add("hidden");
    indicator.innerHTML = "";
}

function toggleLoading(loadingEl, submitButton, isLoading) {
    if (loadingEl) {
        loadingEl.classList.toggle("hidden", !isLoading);
    }

    if (submitButton) {
        submitButton.disabled = isLoading;
    }
}

function setupTimer(timerElId) {
    const el = document.getElementById(timerElId);
    let start = 0;
    let timerId = null;
    const show = (text) => {
        if (el) {
            el.textContent = text;
            el.classList.remove("hidden");
        }
    };
    return {
        start() {
            if (!el) return () => {};
            start = Date.now();
            show("已用时 0.0s");
            timerId = setInterval(() => {
                const s = (Date.now() - start) / 1000;
                show(`已用时 ${s.toFixed(1)}s`);
            }, 200);
            return () => {};
        },
        stop() {
            if (timerId) clearInterval(timerId);
            if (el) {
                const s = (Date.now() - start) / 1000;
                el.textContent = `总用时 ${s.toFixed(1)}s`;
            }
        },
        reset() {
            if (timerId) clearInterval(timerId);
            if (el) {
                el.textContent = "";
                el.classList.add("hidden");
            }
        },
    };
}

function exportTestCases(content) {
    let csv = "";
    if (isLikelyCsv(content)) {
        csv = content;
    } else {
        const container = document.createElement("div");
        container.innerHTML = marked.parse(content);
        const table = container.querySelector("table");
        if (!table) {
            alert("没有可导出的测试用例表格。");
            return;
        }
        const rows = table.querySelectorAll("tr");
        rows.forEach((row) => {
            const cols = row.querySelectorAll("th, td");
            const rowData = Array.from(cols).map((cell) => {
                const cellText = cell.innerText.replace(/"/g, '""');
                return `"${cellText}"`;
            });
            csv += `${rowData.join(",")}\r\n`;
        });
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "test_cases.csv";
    link.click();
    URL.revokeObjectURL(link.href);
}

export function initGenerationTab() {
    const form = document.getElementById("generateForm");
    if (!form) {
        return;
    }

    const oldPrdInput = document.getElementById("generateOldPrd");
    const newPrdInput = document.getElementById("generateNewPrd");
    const oldPrdLabel = document.getElementById("generateOldPrdLabel");
    const newPrdLabel = document.getElementById("generateNewPrdLabel");

    const submitButton = document.getElementById("generateSubmit");
    const exportButton = document.getElementById("generateExport");
    const loadingIndicator = document.getElementById("generateLoading");
    const outputContainer = document.getElementById("generateOutput");
    const modeIndicator = document.getElementById("generateModeIndicator");
    const timer = setupTimer("generateTimer");

    setupFileInput(oldPrdInput, oldPrdLabel, (text) => {
        oldPrdText = text;
    });
    setupFileInput(newPrdInput, newPrdLabel, (text) => {
        newPrdText = text;
    });

    exportButton?.addEventListener("click", () => {
        if (!currentTestCases.trim()) {
            alert("请先生成测试用例。");
            return;
        }
        exportTestCases(currentTestCases);
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (!newPrdText.trim()) {
            alert("请上传新版 PRD 文件。");
            return;
        }

    toggleLoading(loadingIndicator, submitButton, true);
    timer.start();
        exportButton?.classList.add("hidden");
        resetModeIndicator(modeIndicator);
        currentTestCases = "";
        outputContainer.innerHTML = '<p class="placeholder">AI 正在分析 PRD，请稍候...</p>';

        try {
            const payload = {
                config: buildRequestConfig(),
            };
            
            // Support KB selection via global IDs
            if (window._selectedOldPrdId) {
                payload.old_prd_id = window._selectedOldPrdId;
            } else {
                payload.old_prd = oldPrdText;
            }
            
            if (window._selectedNewPrdId) {
                payload.new_prd_id = window._selectedNewPrdId;
            } else {
                payload.new_prd = newPrdText;
            }

            const response = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const detail = await response.json().catch(() => ({ error: "未知错误" }));
                throw new Error(`请求失败 ${response.status}: ${detail.error}`);
            }

            const data = await response.json();
            currentTestCases = data.test_cases || "";
            if (isLikelyCsv(currentTestCases)) {
                outputContainer.innerHTML = csvToHtmlTable(currentTestCases);
            } else {
                renderMarkdown(outputContainer, currentTestCases);
            }
            exportButton?.classList.remove("hidden");

            const useVision = Boolean(data.meta?.use_vision);
            const isIncremental = Boolean(oldPrdText.trim());
            const modeLabel = isIncremental ? "增量模式" : "全量模式";
            updateModeIndicator(modeIndicator, {
                modeText: modeLabel,
                visionUsed: useVision,
            });

            if (data.meta) {
                const metaBox = document.createElement("div");
                metaBox.className = "meta-info";
                const { model_used: modelUsed, mode, use_vision: visionFlag } = data.meta;
                metaBox.innerHTML = `<strong>处理结果：</strong> 模式=${mode ?? modeLabel}，模型=${modelUsed ?? "未知"}，视觉=${visionFlag ? "启用" : "禁用"}`;
                outputContainer.appendChild(metaBox);
            }
        } catch (error) {
            console.error(error);
            outputContainer.innerHTML = `<p class="error">生成失败：${error.message}</p>`;
        } finally {
            toggleLoading(loadingIndicator, submitButton, false);
            timer.stop();
        }
    });
}
