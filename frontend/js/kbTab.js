import { buildRequestConfig } from "./configStore.js";

function setupTimer(elId) {
  const el = document.getElementById(elId);
  let start = 0;
  let tid = null;
  const show = (t) => {
    if (!el) return;
    el.textContent = t;
    el.classList.remove("hidden");
  };
  return {
    start() {
      if (!el) return () => {};
      start = Date.now();
      show("已用时 0.0s");
      tid = setInterval(() => {
        const s = (Date.now() - start) / 1000;
        show(`已用时 ${s.toFixed(1)}s`);
      }, 200);
    },
    stop() {
      if (tid) clearInterval(tid);
      if (el) {
        const s = (Date.now() - start) / 1000;
        el.textContent = `总用时 ${s.toFixed(1)}s`;
      }
    },
  };
}

async function refreshDocs() {
  const list = document.getElementById("kbDocsList");
  if (!list) return;
  try {
    const resp = await fetch("/api/kb/docs");
    const data = await resp.json();
    const docs = data.docs || [];
    if (!docs.length) {
      list.innerHTML = '<p class="placeholder">尚无文档，请先入库。</p>';
      return;
    }
    list.innerHTML = "";
    docs.forEach((d) => {
      const card = document.createElement("div");
      card.className = "kb-doc-card";
      card.innerHTML = `
        <div class="kb-doc-title">${d.name || d.doc_id}</div>
        <div class="kb-doc-meta">章节：${d.sections}；图片：${d.total_images}</div>
        <div class="kb-doc-actions">
          <button data-id="${d.doc_id}" class="kb-gen-btn">基于此文档生成用例</button>
        </div>
      `;
      list.appendChild(card);
    });

    list.querySelectorAll(".kb-gen-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const docId = btn.getAttribute("data-id");
        const output = document.getElementById("kbGenerateOutput");
        if (!output) return;
        output.innerHTML = '<p class="placeholder">AI 正在基于知识库生成用例...</p>';
        try {
          const resp = await fetch("/api/kb/generate_from_kb", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ doc_id: docId, config: buildRequestConfig() }),
          });
          if (!resp.ok) {
            const detail = await resp.json().catch(() => ({ error: "未知错误" }));
            throw new Error(`请求失败 ${resp.status}: ${detail.error}`);
          }
          const data = await resp.json();
          const text = data.test_cases || "";
          if (/[,\n]/.test(text) && !/\|/.test(text)) {
            // likely CSV
            const table = csvToHtmlTable(text);
            output.innerHTML = table;
          } else {
            output.innerHTML = marked.parse(text);
          }
        } catch (err) {
          output.innerHTML = `<p class="error">生成失败：${err.message}</p>`;
        }
      });
    });
  } catch (err) {
    list.innerHTML = `<p class="error">加载失败：${err.message}</p>`;
  }
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
        } else if (ch === undefined) { break; } else { field += ch; }
      } else if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        row.push(field); field = "";
      } else if (ch === '\n' || ch === undefined) {
        row.push(field); rows.push(row); i += 1; break;
      } else { field += ch; }
    }
  }
  if (!rows.length) return '<p class="placeholder">暂无内容可显示。</p>';
  const header = rows[0] || [];
  const body = rows.slice(1);
  const escape = (t) => String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  let html = '<table><thead><tr>' + header.map((h) => `<th>${escape(h)}</th>`).join("") + '</tr></thead><tbody>';
  for (const r of body) html += '<tr>' + r.map((c) => `<td>${escape(c)}</td>`).join("") + '</tr>';
  html += '</tbody></table>';
  return html;
}

export function initKbTab() {
  const ingestBtn = document.getElementById("kbIngestBtn");
  const nameInput = document.getElementById("kbDocName");
  const contentInput = document.getElementById("kbContent");
  const loading = document.getElementById("kbIngestLoading");
  const timer = setupTimer("kbIngestTimer");

  if (ingestBtn) {
    ingestBtn.addEventListener("click", async () => {
      const name = (nameInput?.value || "").trim();
      const content = (contentInput?.value || "").trim();
      if (!content) {
        alert("请粘贴 PRD 文本");
        return;
      }
      loading?.classList.remove("hidden");
      timer.start();
      try {
        const resp = await fetch("/api/kb/ingest_async", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, prd_content: content }),
        });
        if (!resp.ok) {
          const detail = await resp.json().catch(() => ({ error: "未知错误" }));
          throw new Error(`启动失败 ${resp.status}: ${detail.error}`);
        }
        const { job_id } = await resp.json();
        let done = false;
        while (!done) {
          await new Promise((r) => setTimeout(r, 1000));
          const st = await fetch(`/api/job_status/${job_id}`);
          if (!st.ok) throw new Error("查询任务失败");
          const js = await st.json();
          if (js.status === "done") {
            done = true;
          } else if (js.status === "error") {
            throw new Error(js.error || "任务失败");
          }
        }
        await refreshDocs();
      } catch (err) {
        alert(`入库失败：${err.message}`);
      } finally {
        loading?.classList.add("hidden");
        timer.stop();
      }
    });
  }

  refreshDocs();
}
