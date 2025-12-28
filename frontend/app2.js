// app.js (lean version) — ใช้ result.json เป็นหลัก

const state = {
    charts: {},
  };
  
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("queryForm");
    if (form) form.addEventListener("submit", onSubmit);
  });
  
  // ================== submit / fetch ==================
  async function onSubmit(e) {
    e.preventDefault();
  
    const symbolInput = document.getElementById("symbolInput");
    const fileInput = document.getElementById("fileInput");
  
    const symbol = (symbolInput?.value || "").trim().toUpperCase();
    const filename = (fileInput?.value || "").trim();
  
    if (!symbol && !filename) {
      setStatus("กรุณากรอก symbol หรือ filename อย่างน้อย 1 ช่อง", "error");
      return;
    }
  
    setStatus("กำลังดึงข้อมูลจาก API ...", "loading");
  
    const params = new URLSearchParams();
    if (symbol) params.set("symbol", symbol);
    if (filename) params.set("filename", filename);
  
    try {
      const res = await fetch(`/api/financials?${params.toString()}&ts=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
  
      const data = await res.json();
      setStatus("ดึงข้อมูลสำเร็จ ✅", "success");
      renderAll(data);
    } catch (err) {
      console.error(err);
      setStatus("ดึงข้อมูลล้มเหลว: " + err.message, "error");
    }
  }
  
  // ================== status ==================
  function setStatus(msg, type = "info") {
    const box = document.getElementById("status");
    if (!box) return;
    box.innerHTML = "";
  
    const div = document.createElement("div");
    div.className = "toast";
    if (type === "error") div.classList.add("error");
    div.textContent = msg;
    box.appendChild(div);
  }
  
  // ================== render ==================
  function renderAll(data) {
    const srcEl = document.getElementById("sourceInfo");
    if (srcEl) srcEl.textContent = data.source_file || "expotes/result.json";
  
    if (!Array.isArray(data.result) || !data.result.length) {
      setStatus("API ไม่ส่ง data.result หรือ result ว่าง", "error");
      return;
    }
  
    renderFromResultRows(data.result, data.ratios);
  }
  
  function renderFromResultRows(rows, ratiosFromBackend) {
    renderResultTable(rows);
  
    const years = rows.map(r => String(r.Year ?? r["Year"] ?? ""));
  
    const keys = pickNumericKeys(rows);
    if (!keys.length) {
      setStatus("result.json ไม่มีคีย์ที่เป็นตัวเลขพอทำกราฟ", "error");
      return;
    }
  
    const series = (k) =>
      rows.map(r => {
        const n = Number(r[k]);
        return Number.isFinite(n) ? n : null;
      });
  
    // กราฟหลัก 4 ช่อง (เลือกจากคีย์ตัวเลขที่มีจริง)
    const k1 = keys[0];
    const k2 = keys[1] || keys[0];
    const k3 = keys[2] || keys[0];
    const k4 = keys[3] || keys[0];
  
    setupOrUpdateLine("homeChart", years, series(k1), k1);
    setupOrUpdateBar("fs1", years, series(k2), k2);
    setupOrUpdateBar("fs2", years, series(k3), k3);
    setupOrUpdateBar("fs3", years, series(k4), k4);
  
    // ratio 2 ช่อง (ถ้าไม่มีจาก backend ก็สร้างจาก rows)
    const ratios = ratiosFromBackend || rowsToRatios(rows);
    renderDefaultRatios(ratios); // EPS + Cost of Equity (ถ้ามี)
  }
  
  // ================== table ==================
  function renderResultTable(rows) {
    const cards = document.getElementById("cards");
    if (!cards) return;
    cards.innerHTML = ""; // กันตารางซ้อน
  
    const card = document.createElement("div");
    card.className = "card";
  
    const title = document.createElement("h3");
    title.textContent = "RESULT (จาก expotes/result.json)";
    card.appendChild(title);
  
    const ignore = new Set(["Stock Symbol", "Symbol", "symbol"]);
    const allKeys = Object.keys(rows[0] || {}).filter(k => !ignore.has(k));
  
    // เอา Year + 16 ตัวแรกพอ (ปรับได้)
    const cols = ["Year", ...allKeys.filter(k => k !== "Year").slice(0, 16)];
  
    const table = document.createElement("table");
    table.className = "table";
  
    const thead = document.createElement("thead");
    thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
    table.appendChild(thead);
  
    const tbody = document.createElement("tbody");
    rows.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = cols.map(c => `<td>${formatValue(r[c])}</td>`).join("");
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  
    card.appendChild(table);
    cards.appendChild(card);
  }
  
  // ================== ratios (default only) ==================
  function renderDefaultRatios(ratios) {
    // หา EPS และ Cost of Equity แบบยืดหยุ่น
    const eps = findMetricSeries(ratios, ["EPS", "eps", "earningspershare", "eps_diluted"]);
    const coe = findMetricSeries(ratios, ["Cost of Equity", "cost_of_equity", "costofequity", "coe"]);
  
    if (!eps && !coe) return;
  
    const { years, series1, series2 } = buildRatioSeries(eps, coe, 5);
  
    const t1 = document.getElementById("rTitle1");
    const t2 = document.getElementById("rTitle2");
    if (t1) t1.textContent = "EPS (5Y)";
    if (t2) t2.textContent = "Cost of Equity (5Y)";
  
    setupOrUpdateLine("rChart1", years, series1, "EPS");
    setupOrUpdateLine("rChart2", years, series2, "Cost of Equity");
  }
  
  function rowsToRatios(rows) {
    const out = {};
    rows.forEach(r => {
      const y = String(r["Year"]);
      Object.entries(r).forEach(([k, v]) => {
        if (k === "Year" || k === "Stock Symbol" || k === "Symbol" || k === "symbol") return;
        if (!out[k]) out[k] = {};
        out[k][y] = v;
      });
    });
    return out;
  }
  
  function normalizeKey(k) {
    return String(k).toLowerCase().replace(/[^a-z0-9]+/g, "");
  }
  
  function findMetricSeries(ratios, candidateKeys) {
    if (!ratios) return null;
    const candNorm = candidateKeys.map(normalizeKey);
    for (const [k, v] of Object.entries(ratios)) {
      if (candNorm.includes(normalizeKey(k))) return v; // {year: value}
    }
    return null;
  }
  
  function buildRatioSeries(seriesObj1, seriesObj2, lastN = 5) {
    const yearSet = new Set();
    [seriesObj1, seriesObj2].forEach(s => {
      if (s && typeof s === "object") Object.keys(s).forEach(y => yearSet.add(String(y)));
    });
  
    const allYears = Array.from(yearSet).sort();
    const start = allYears.length > lastN ? allYears.length - lastN : 0;
    const years = allYears.slice(start);
  
    const makeArr = (obj) => years.map(y => (obj && obj[y] != null ? Number(obj[y]) : null));
  
    return {
      years,
      series1: makeArr(seriesObj1),
      series2: makeArr(seriesObj2),
    };
  }
  
  // ================== utilities ==================
  function pickNumericKeys(rows) {
    const ignore = new Set(["Year", "Stock Symbol", "Symbol", "symbol"]);
    const keys = Object.keys(rows[0] || {}).filter(k => !ignore.has(k));
    return keys.filter(k => rows.some(r => Number.isFinite(Number(r[k]))));
  }
  
  function formatValue(v) {
    if (v == null) return "—";
    const n = Number(v);
    if (Number.isFinite(n)) {
      if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + " B";
      if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + " M";
      return n.toLocaleString();
    }
    return String(v);
  }
  
  // ================== Chart.js helpers ==================
  function setupOrUpdateLine(canvasId, labels, data, label) {
    setupOrUpdateChart(canvasId, "line", labels, data, label);
  }
  
  function setupOrUpdateBar(canvasId, labels, data, label) {
    setupOrUpdateChart(canvasId, "bar", labels, data, label);
  }
  
  function setupOrUpdateChart(canvasId, type, labels, data, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
  
    if (!state.charts[canvasId]) {
      const ctx = canvas.getContext("2d");
      state.charts[canvasId] = new Chart(ctx, {
        type,
        data: {
          labels,
          datasets: [{ label, data, fill: false, tension: 0.35 }],
        },
        options: {
          plugins: { legend: { display: true } },
          scales: {
            x: { grid: { color: "rgba(148,163,184,.14)" } },
            y: { grid: { color: "rgba(148,163,184,.08)" } },
          },
        },
      });
    } else {
      const chart = state.charts[canvasId];
      chart.data.labels = labels;
      chart.data.datasets[0].label = label;
      chart.data.datasets[0].data = data;
      chart.update();
    }
  }
  