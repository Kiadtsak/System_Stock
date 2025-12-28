
const state = {
    charts: {},   // เก็บ instance ของ Chart แต่ละ canvas
    ratioTabsInited: false,
  };
  
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("queryForm");
    if (form) form.addEventListener("submit", onSubmit);
  });
  
  // ================== ส่วน submit form / ดึง API ==================
  
  async function onSubmit(e) {
    e.preventDefault();
  
    const symbolInput = document.getElementById("symbolInput");
    const fileInput   = document.getElementById("fileInput");
  
    const symbol   = symbolInput.value.trim().toUpperCase();
    const filename = fileInput.value.trim();
  
    if (!symbol && !filename) {
      setStatus("กรุณากรอก symbol หรือ filename อย่างน้อย 1 ช่อง", "error");
      return;
    }
  
    setStatus("กำลังดึงข้อมูลจาก API ...", "loading");
  
    const params = new URLSearchParams();
    if (symbol) params.set("symbol", symbol);
    if (filename) params.set("filename", filename);
  
    try {
      // ถ้า backend ใช้ /api/ratios ให้เปลี่ยนตรงนี้
      //const res = await fetch(`/api/financials?${params.toString()}`);
      const res = await fetch(`/api/financials?${params.toString()}&ts=${Date.now()}`);
  
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
  
      const data = await res.json();
      console.log("API data:", data);
  
      setStatus("ดึงข้อมูลสำเร็จ ✅", "success");
      renderAll(data);
    } catch (err) {
      console.error(err);
      setStatus("ดึงข้อมูลล้มเหลว: " + err.message, "error");
    }
  }
  
  // ================== helper แสดง status ==================
  
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
  // ================= rander result ========================== // 
  
  function renderFromResultRows(data){
    const rows = Array.isArray(data.result) ? data.result : [];
    if (!rows.length){
      setStatus("มี result แต่เป็นค่าว่าง", "error");
      return;
    }
  
    // 1) โชว์ตาราง result.json ให้เห็นชัด ๆ (แทนงบดิบ)
    const cols = renderResultTable(rows);   /// แก้ไขตรงนี้ const cols = 
  
    // 2) ส่ง ratios ให้แท็บอัตราส่วนใช้ได้
    const ratios = data.ratios || rowsToRatios(rows);
    renderRatioSection({ ratios });
    
    // วาดกราฟกลุ่ม 16 ตัว (ถ้ามี)
    renderGrouped16Charts(rows, cols);

    // 3) ทำกราฟหลัก 3-4 ช่อง จาก key ที่มีจริงใน result.json
    const years = rows.map(r => String(r.Year ?? r["Year"] ?? ""));
  
    const keys = pickNumericKeys(rows);
    if (!keys.length){
      setStatus("result.json ไม่มีตัวเลขให้ทำกราฟเลย (มีแต่ข้อความ?)", "error");
      return;
    }
  
    const s = (k) => rows.map(r => { toNumber (r[k])     // ตรงนี้
    //const r = (k) => rows.map(r => toNumber(r[k])) // แก้ไขตรงนี้
      const n = Number(r[k]);
      return Number.isFinite(n) ? n : null;
    });
  
    // เอา 4 ตัวแรกไปลงกราฟ (เอาตามที่มีจริง)
    const k1 = keys[0], k2 = keys[1] || keys[0], k3 = keys[2] || keys[0], k4 = keys[3] || keys[0];
  
    setupOrUpdateLine("homeChart", years, s(k1), k1);s
    setupOrUpdateBar("fs1", years, s(k2), k2);
    setupOrUpdateBar("fs2", years, s(k3), k3);
    setupOrUpdateBar("fs3", years, s(k4), k4);
  }
  
  // 16 

  function renderGrouped16Charts(rows, cols){
    const wrap = document.getElementById("groupCharts");
    if (!wrap) return;
  
    // เคลียร์กราฟเก่า
    destroyChartsInContainer(wrap);
    wrap.innerHTML = "";
  
    const years = rows.map(r => String(r.Year ?? r["Year"] ?? ""));
  
    // เอา “16 ตัวที่โชว์จริง” (ตัด Year)
    const metricKeys = cols.filter(c => c !== "Year").slice(0, 16);
  
    // จัดกลุ่ม
    const groups = {};
    metricKeys.forEach(key => {
      const g = groupOfMetric(key);
      (groups[g] ||= []).push(key);
    });
  
    // วาดทีละกลุ่ม
    Object.entries(groups).forEach(([groupName, keys]) => {
      const section = document.createElement("section");
      section.className = "card";
      section.style.marginTop = "12px";
  
      const h = document.createElement("h3");
      h.textContent = `${groupName} (${keys.length})`;
      section.appendChild(h);
  
      const grid = document.createElement("div");
      grid.className = "grid cols-2";
      section.appendChild(grid);
  
      keys.forEach((key) => {
        const id = `g_${slugKey(key)}`;
  
        const card = document.createElement("div");
        card.className = "card";
  
        const title = document.createElement("div");
        title.style.fontWeight = "600";
        title.style.marginBottom = "6px";
        title.textContent = key;
        card.appendChild(title);
  
        const canvas = document.createElement("canvas");
        canvas.id = id;
        canvas.height = 120;
        card.appendChild(canvas);
  
        grid.appendChild(card);
  
        const series = rows.map(r => toNumber(r[key]));
  
        const isMoney = /(cash|flow|fcf|ufcf|ocf|earnings|revenue|income|capex|debt|assets|equity)/i.test(key);
        if (isMoney) setupOrUpdateBar(id, years, series, key);
        else setupOrUpdateLine(id, years, series, key);
      });
  
      wrap.appendChild(section);
    });
  }
  


  function rowsToRatios(rows){
    const out = {};
    rows.forEach(r => {
      const y = String(r["Year"]);
      Object.entries(r).forEach(([k,v]) => {
        if (k === "Year" || k === "Stock Symbol" || k === "Symbol" || k === "symbol") return;
        if (!out[k]) out[k] = {};
        out[k][y] = v;
      });
    });
    return out;
  }
  
  function pickNumericKeys(rows){
    const ignore = new Set(["Year","Stock Symbol","Symbol","symbol"]);
    const keys = Object.keys(rows[0] || {}).filter(k => !ignore.has(k));
  
    // เลือกเฉพาะคีย์ที่ “มีตัวเลขจริง” อย่างน้อย 1 ปี
    return keys.filter(k => rows.some(r => Number.isFinite(Number(r[k]))));
  }
  
  function renderResultTable(rows){
    const cards = document.getElementById("cards");
    if (!cards) return []; // แก้ใข []
    cards.innerHTML = "";
  
    const card = document.createElement("div");
    card.className = "card";
  
    const title = document.createElement("h3");
    title.textContent = "RESULT (จาก expotes/result.json)";
    card.appendChild(title);
  
    const ignore = new Set(["Stock Symbol","Symbol","symbol"]);
    const allKeys = Object.keys(rows[0] || {}).filter(k => !ignore.has(k));
  
    // เอา Year + 16 ตัวแรกพอ อ่านง่าย (ปรับได้)
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

    return cols; // แกใช้บรรทัดนี้
  }
  
  // ================== render หลัก ==================
  
  function renderAll(data) {
    const srcEl = document.getElementById("sourceInfo");
    if (srcEl) srcEl.textContent = data.source_file || "expotes/result.json";
  
    // ✅ ถ้า backend ส่ง result มา ให้ใช้ result เป็นตัวหลัก
    if (Array.isArray(data.result)) {
      renderFromResultRows(data);
      return;
    }
  
    // fallback (เผื่อไปเรียก raw endpoint)
    renderCards(data);
    renderFinancialCharts(data);
    renderRatioSection(data);
  }

  function buildKVCard(title, obj) {
    const card = document.createElement("div");
    card.className = "card";
  
    const h = document.createElement("h3");
    h.textContent = title;
    card.appendChild(h);
  
    const wrap = document.createElement("div");
    wrap.className = "kv";
  
    Object.entries(obj).forEach(([k, v]) => {
      const row = document.createElement("div");
      row.className = "kv-row";
      row.innerHTML = `
        <div class="k">${k}</div>
        <div class="v">${formatValue(v)}</div>
      `;
      wrap.appendChild(row);
    });
  
    card.appendChild(wrap);
    return card;
  }

  function buildStatementCard(title, stmtObj) {
    const card = document.createElement("div");
    card.className = "card";
  
    const h = document.createElement("h3");
    h.textContent = title;
    card.appendChild(h);
  
    const wrap = document.createElement("div");
    wrap.className = "kv";
  
    Object.entries(stmtObj).forEach(([lineItem, perYear]) => {
      const years =
        perYear && typeof perYear === "object"
          ? Object.keys(perYear).sort().join(", ")
          : "-";
  
      const row = document.createElement("div");
      row.className = "kv-row";
      row.innerHTML = `
        <div class="k">${lineItem}</div>
        <div class="v">ปี: ${years}</div>
      `;
      wrap.appendChild(row);
    });
  
    card.appendChild(wrap);
    return card;
  }
  // ================== helper format ค่า ================== กราฟ
  
  function formatValue(v) {
    if (v == null) return "—";
    if (typeof v === "number") {
      if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + " B";
      if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + " M";
      return v.toLocaleString();
    }
    if (typeof v === "object") {
      const years = Object.keys(v).slice(0, 5).join(", ");
      return `Object{${years}}`;
    }
    return String(v);
  }

  function toNumber(v){
    if (v == null) return null;
    if (typeof v === "number") return v;
  
    let s = String(v).trim();
    let mult = 1;
    const up = s.toUpperCase();
  
    if (up.endsWith("B")) { mult = 1e9; s = s.slice(0, -1).trim(); }
    else if (up.endsWith("M")) { mult = 1e6; s = s.slice(0, -1).trim(); }
    else if (up.endsWith("K")) { mult = 1e3; s = s.slice(0, -1).trim(); }
  
    const n = parseFloat(s.replace(/,/g, ""));
    return Number.isFinite(n) ? n * mult : null;
  }
  

  function slugKey(key) {
    return String(key.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""));
  }

  function groupOfMetric(key){
    const k = String(key).toLowerCase();
    if (/(roe|roa|roic|return)/i.test(k)) return "Profitability";
    if (/margin/i.test(k)) return "Margins";
    if (/(wacc|cost.*equity|beta|risk)/i.test(k)) return "Risk / Discount";
    if (/(cash|flow|fcf|ufcf|ocf|owner)/i.test(k)) return "Cash Flow";
    return "Other";
  }
  
  function destroyChartsInContainer(container){
    const canvases = container.querySelectorAll("canvas[id]");
    canvases.forEach(cv => {
      const id = cv.id;
      if (state.charts[id]) {
        state.charts[id].destroy();
        delete state.charts[id];
      }
    });
  }
  