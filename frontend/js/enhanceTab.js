import { buildRequestConfig } from "./configStore.js";

let uploadedContent = "";
let enhancedContent = ""; // may be CSV text or Markdown table

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => resolve(event.target?.result ?? "");
        reader.onerror = () => reject(new Error("无法读取文件"));
        reader.readAsText(file);
    });
}

function handleSpreadsheet(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = new Uint8Array(event.target?.result ?? new ArrayBuffer(0));
                const workbook = XLSX.read(data, { type: "array" });
                const sheetName = workbook.SheetNames[0];
                if (!sheetName) {
                    reject(new Error("Excel 文件中没有可用工作表"));
                    return;
                }
                const worksheet = workbook.Sheets[sheetName];
                const csvData = XLSX.utils.sheet_to_csv(worksheet);
                const rows = csvData.split("\n").filter((row) => row.trim());
                if (!rows.length) {
                    resolve("");
                    return;
                }
                let markdown = `| ${rows[0].split(",").join(" | ")} |\n`;
                markdown += `| ${rows[0].split(",").map(() => "---").join(" | ")} |\n`;
                for (let i = 1; i < rows.length; i += 1) {
                    markdown += `| ${rows[i].split(",").join(" | ")} |\n`;
                }
                resolve(markdown);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = () => reject(new Error("无法读取文件"));
        reader.readAsArrayBuffer(file);
    });
}

async function readTestCaseFile(file) {
    const extension = file.name.split(".").pop()?.toLowerCase();

    if (extension === "csv") {
        return readFileAsText(file);
    }

    if (extension === "xlsx" || extension === "xls") {
        return handleSpreadsheet(file);
    }

    return readFileAsText(file);
}

function setupFileInput(input, label) {
    if (!input || !label) {
        return;
    }

    input.addEventListener("change", async () => {
        const file = input.files?.[0];
        if (!file) {
            label.textContent = "点击或拖拽文件到此处";
            uploadedContent = "";
            return;
        }

        try {
            const content = await readTestCaseFile(file);
            uploadedContent = content;
            label.textContent = file.name;
        } catch (error) {
            console.error(error);
            alert("文件读取失败，请重试。");
            input.value = "";
            label.textContent = "点击或拖拽文件到此处";
            uploadedContent = "";
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
    // Consider CSV if contains commas, no markdown table pipes, and multiple lines
    return hasComma && !hasPipe && /\n.+\n/.test(text) && !looksTabbed;
}

function csvToHtmlTable(csvText) {
    // Minimal CSV parser supporting quoted fields with commas and quotes
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
                i += 1; // move past newline
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

function exportEnhanced(content) {
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
                const text = cell.innerText.replace(/"/g, '""');
                return `"${text}"`;
            });
            csv += `${rowData.join(",")}\r\n`;
        });
    }

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "enhanced_test_cases.csv";
    link.click();
    URL.revokeObjectURL(link.href);
}

export function initEnhanceTab() {
    const form = document.getElementById("enhanceForm");
    if (!form) {
        return;
    }

    const fileInput = document.getElementById("enhanceFile");
    const fileLabel = document.getElementById("enhanceFileLabel");
    const submitButton = document.getElementById("enhanceSubmit");
    const exportButton = document.getElementById("enhanceExport");
    const loadingIndicator = document.getElementById("enhanceLoading");
    const outputContainer = document.getElementById("enhanceOutput");
    const timer = setupTimer("enhanceTimer");

    setupFileInput(fileInput, fileLabel);

    exportButton?.addEventListener("click", () => {
        if (!enhancedContent.trim()) {
            alert("请先完善测试用例。");
            return;
        }
        exportEnhanced(enhancedContent);
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (!uploadedContent.trim()) {
            alert("请上传测试用例文件。");
            return;
        }

    toggleLoading(loadingIndicator, submitButton, true);
    timer.start();
        exportButton?.classList.add("hidden");
        enhancedMarkdown = "";
        outputContainer.innerHTML = '<p class="placeholder">AI 正在完善测试用例，请稍候...</p>';

        try {
            const payload = {
                config: buildRequestConfig(),
            };
            
            // Support KB selection via global ID
            if (window._selectedTestCasesId) {
                payload.test_cases_id = window._selectedTestCasesId;
            } else {
                payload.test_cases = uploadedContent;
            }

            // Use async job to avoid long blocking requests
            const startResp = await fetch("/api/enhance_async", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!startResp.ok) {
                const detail = await startResp.json().catch(() => ({ error: "未知错误" }));
                throw new Error(`启动失败 ${startResp.status}: ${detail.error}`);
            }
            const startData = await startResp.json();

            if (startData.cached) {
                enhancedContent = startData.result || "";
                if (isLikelyCsv(enhancedContent)) {
                    outputContainer.innerHTML = csvToHtmlTable(enhancedContent);
                } else {
                    renderMarkdown(outputContainer, enhancedContent);
                }
                exportButton?.classList.remove("hidden");
            } else {
                const jobId = startData.job_id;
                let done = false;
                while (!done) {
                    await new Promise((r) => setTimeout(r, 1000));
                    const st = await fetch(`/api/job_status/${jobId}`);
                    if (!st.ok) throw new Error("查询任务失败");
                    const js = await st.json();
                    if (js.status === "done") {
                        enhancedContent = js.result || "";
                        if (isLikelyCsv(enhancedContent)) {
                            outputContainer.innerHTML = csvToHtmlTable(enhancedContent);
                        } else {
                            renderMarkdown(outputContainer, enhancedContent);
                        }
                        exportButton?.classList.remove("hidden");
                        done = true;
                    } else if (js.status === "error") {
                        throw new Error(js.error || "任务失败");
                    } else {
                        // keep timer running; optionally show ETA if available
                        const el = document.getElementById("enhanceTimer");
                        if (el && typeof js.eta_seconds === "number") {
                            const eta = Math.max(0, js.eta_seconds);
                            el.textContent = `${el.textContent}（预计剩余 ${Math.floor(eta / 60)}分${eta % 60}秒）`;
                        }
                    }
                }
            }
        } catch (error) {
            console.error(error);
            outputContainer.innerHTML = `<p class="error">完善失败：${error.message}</p>`;
        } finally {
            toggleLoading(loadingIndicator, submitButton, false);
            timer.stop();
        }
    });
}
