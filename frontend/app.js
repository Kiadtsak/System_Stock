  // app.js
// ดึงข้อมูลจาก API แล้ววาดการ์ด + กราฟ (งบ 3 ชุด + อัตราส่วน EPS / Cost of Equity ฯลฯ)

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
  
      setStatus("ดึงข้อมูลสำเร็จ ", "success");
      renderAll(data);
    } catch (err) {
      console.error(err);
      setStatus("ดึงข้อมูลล้มเหลว: ไม่มีหุ้นชื่อนี้ : " + err.message, "error");
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
  ////   ================== load AI analysis ==================//
  async function loadAI() {
    const res = await fetch("/api/ai");
    const ai = await res.json();
  
    document.getElementById("aiDecision").innerText = ai.decision;
    document.getElementById("aiQuality").innerText = ai.quality_score;
    document.getElementById("aiValue").innerText = ai.value_score;
    document.getElementById("aiRisk").innerText = ai.risk_level;
  
    const ul = document.getElementById("aiReasons");
    ul.innerHTML = "";
    ai.reason.forEach(r => {
      const li = document.createElement("li");
      li.textContent = r;
      ul.appendChild(li);
    });
  }
  
  // ================= rander result ========================== // 
  
  function renderFromResultRows(data){
    const rows = Array.isArray(data.result) ? data.result : [];
    if (!rows.length){
      setStatus("มี result แต่เป็นค่าว่าง", "error");
      return;
    }

    // 1) โชว์ตาราง result.json ให้เห็นชัด ๆ (แทนงบดิบ)
    
    //renderResultTable(rows);
    plotCombined5(rows);     // Combined 5 Chart PE PBV ROE RoA Price EPS
    plotFCFCombo(rows);     // Free Cash Flow Combo Chart
    plotOCFCombo(rows);
    renderKpiCards(rows);
    loadAIAnalysis(rows);
    
    // 2) ส่ง ratios ให้แท็บอัตราส่วนใช้ได้
    const ratios = data.ratios || rowsToRatios(rows);
    renderRatioSection({ ratios });

    // 3) ทำกราฟหลัก 3-4 ช่อง จาก key ที่มีจริงใน result.json
    const years = rows.map(r => String(r.Year ?? r["Year"] ?? ""));

    const keys = pickNumericKeys(rows);
    if (!keys.length){
      setStatus("result.json ไม่มีตัวเลขให้ทำกราฟเลย (มีแต่ข้อความ?)", "error");
      return;
    }
  
    const s = (k) => rows.map(r => {
      const n = Number(r[k]);
      return Number.isFinite(n) ? n : null;
    });

    // เอา 4 ตัวแรกไปลงกราฟ (เอาตามที่มีจริง)
    const kROE = keys[0], kROA = keys[1] || keys[0], kEBITDA_MARGIN = keys[2] || keys[0], kNET_PROFIT_MATGIN = keys[3] || keys[0], 
          kGROSS_PROFIT_MARGIN = keys[4] || keys[0], kOperating_profit_margin = keys[5] || keys[0], kWACC = keys[6] || keys[0], 
          kCost_of_equity = keys[7] || keys[0],kUnlevered_free_cash_flow_UFCF = keys[8] || keys[0], kOperating_cash_flow_OCF= keys[9] || keys[0], 
          kFree_cash_flow_FCF= keys[10]|| keys[0], kCurrent_Ratio= keys[11]|| keys[0], kCash_ratio= keys[12]|| keys[0], kEPS= keys[13]|| keys[0], 
          kPE_RATIO= keys[14]|| keys[0], kOwners_Earnings= keys[15]|| keys[0], kPBV_Ratio= keys[16]|| keys[0],kROIC = keys[17] || keys[0], 
          kPRICE = keys[18] || keys[0];

    setupOrUpdateLine("ROE", years, s(kROE), kROE);
    setupOrUpdateLine("RoA", years, s(kROA), kROA);
    setupOrUpdateLine("ROIC", years, s(kROIC), kROIC);
    setupOrUpdateLine("PRICE", years, s(kPRICE), kPRICE);
    setupOrUpdateBar("EBITDA MARGIN", years, s(kEBITDA_MARGIN), kEBITDA_MARGIN);
    setupOrUpdateBar("Net Profit Margin", years, s(kNET_PROFIT_MATGIN), kNET_PROFIT_MATGIN);
    setupOrUpdateChart("GROSS_PROFIT_MARGIN", "line", years, s(kGROSS_PROFIT_MARGIN), kGROSS_PROFIT_MARGIN);
    setupOrUpdateLine("PE_Ratio", years, s(kPE_RATIO), kPE_RATIO,);
    setupOrUpdateLine("PBV_Ratio", "line", years, s(kPBV_Ratio), kPBV_Ratio);
    setupOrUpdateChart("GROSS_PROFIT_MARGIN", "line",  years, s(kGROSS_PROFIT_MARGIN), kGROSS_PROFIT_MARGIN);
    setupOrUpdateBar("Operating_profit_margin", years, s(kOperating_profit_margin), kOperating_profit_margin);
    setupOrUpdateBar("Owners_Earnings", years, s(kOwners_Earnings), kOwners_Earnings);
    setupOrUpdateLine("Current_Ratio", years, s(kCurrent_Ratio), kCurrent_Ratio);
    setupOrUpdateLine("Cash_ratio", years, s(kCash_ratio), kCash_ratio);
    setupOrUpdateBar("Unlevered_free_cash_flow_UFCF", years, s(kUnlevered_free_cash_flow_UFCF), kUnlevered_free_cash_flow_UFCF);
    setupOrUpdateBar("Operating_cash_flow_OCF", years, s(kOperating_cash_flow_OCF), kOperating_cash_flow_OCF);
    setupOrUpdateBar("Free_cash_flow_FCF", years, s(kFree_cash_flow_FCF), kFree_cash_flow_FCF); 
    setupOrUpdateBar("WACC", years, s(kWACC), kWACC);
    setupOrUpdateBar("Cost_of_equity", years, s(kCost_of_equity), kCost_of_equity);
    setupOrUpdateChart("EPS", "line", years, s(kEPS), kEPS);
    setupOrUpdateLine("PBV_Ratio", years, s(kPBV_Ratio), kPBV_Ratio);
   

  }

  // เพิ่มมา
  function plotCombined5(rows) {
    if (!rows?.length || !window.Chart) return;

    const sorted = [...rows].sort((a, b) => {
      const ya = String(a.Year ?? a["Year"] ?? "");
      const yb = String(b.Year ?? b["Year"] ?? "");
      const na = Number(ya), nb = Number(yb);
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
      return ya.localeCompare(yb);
    });

    const years = sorted.map((r) => String(r.Year ?? r["Year"] ?? ""));

    const normalizeKey = (k) => String(k).toLowerCase().replace(/[^a-z0-9]+/g, "");
    const toNum = (v) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };

    const findKey = (candidateKeys) => {
      const keys = Object.keys(sorted[0] || {});
      const normMap = new Map(keys.map((k) => [normalizeKey(k), k]));
      for (const c of candidateKeys) if (keys.includes(c)) return c;
      for (const c of candidateKeys) {
        const hit = normMap.get(normalizeKey(c));
        if (hit) return hit;
      }
      return null;
    };

    const series = (key) => sorted.map((r) => toNum(r[key]));

    // ==== ปรับ candidate ให้ตรงกับ key ใน result.json ของคุณได้ ====
    const kROE = findKey(["ROE", "roe", "Return on Equity", "return_on_equity"]);
    const kROA = findKey(["ROA", "RoA", "roa", "Return on Assets", "return_on_assets"]);
    const kPE = findKey(["PE_RATIO", "PE_Ratio", "pe", "pe_ratio", "P/E", "peratio"]);
    const kPBV = findKey(["PBV_Ratio", "pbv", "pbv_ratio", "P/BV", "price_to_book"]);
    const kROIC = findKey(["ROIC", "roic", "Return on Invested Capital", "return_on_invested_capital"]);
    const kPRICE = findKey(["Price", "price", "Close", "close", "Last", "last", "StockPrice", "stock_price"]);
    
    const datasets = [];
    const COLORS = {
      roe: "#2563EB",   // blue
      roa: "#7C3AED",   // violet
      pe: "#F59E0B",    // amber
      pbv: "#EF4444",   // red
      roic: "#D946EF",  // pink
      price: "#10B981", // green
     
    };

    if (kROE)
      datasets.push({
        label: "ROE (%)",
        data: series(kROE),
        yAxisID: "yPct",
        borderColor: COLORS.roe,
        borderWidth: 5,
        backgroundColor: COLORS.roe,
        tension: 0.25,
        pointRadius: 2,
      });

    if (kROA)
      datasets.push({
        label: "RoA (%)",
        data: series(kROA),
        yAxisID: "yPct",
        borderColor: COLORS.roa,
        borderWidth: 5,
        backgroundColor: COLORS.roa,
        tension: 0.25,
        pointRadius: 2,
      });

    if (kPE)
      datasets.push({
        label: "P/E",
        data: series(kPE),
        yAxisID: "yRight",
        borderColor: COLORS.pe,
        borderWidth: 5,
        backgroundColor: COLORS.pe,
        tension: 0.25,
        pointRadius: 2,
      });

    if (kPBV)
      datasets.push({
        label: "P/BV",
        data: series(kPBV),
        yAxisID: "yRight",
        borderColor: COLORS.pbv,
        borderWidth: 5,
        backgroundColor: COLORS.pbv,
        tension: 0.25,
        pointRadius: 2,
      });

    if (kROIC)
      datasets.push({
        label: "ROIC (%",
        data: series(kROIC),
        yAxisID: "yRight",
        borderColor: COLORS.roic,
        borderWidth: 5,
        backgroundColor: COLORS.roic,
        tension: 0.25,
        pointRadius: 2,
      });

    if (kPRICE)
      datasets.push({
        label: "Price",
        data: series(kPRICE),
        yAxisID: "yRight",
        borderColor: COLORS.price,
        borderWidth: 5,
        backgroundColor: COLORS.price,
        tension: 0.25,
        pointRadius: 2,
      });
    
    const canvas = document.getElementById("combinedChart");
    if (!canvas) return;

    // destroy กันซ้อน
    if (state?.charts?.combinedChart) state.charts.combinedChart.destroy();

    state.charts.combinedChart = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: years, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: { enabled: true },
        },
        scales: {
          yPct: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Percent (%)" },
          },
          yRight: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "PE / PBV / Price" },
          },
          x: { ticks: { autoSkip: true, maxTicksLimit: 12 } },
        },
        elements: {
          line: { borderWidth: 2 },
          point: { hoverRadius: 5 },
        },
      },
    });
  }
  
  //  
  function plotFCFCombo(rows) {
    if (!rows?.length || !window.Chart) return;
  
    const sorted = [...rows].sort((a, b) => {
      const ya = String(a.Year ?? a["Year"] ?? "");
      const yb = String(b.Year ?? b["Year"] ?? "");
      const na = Number(ya), nb = Number(yb);
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
      return ya.localeCompare(yb);
    });
  
    const years = sorted.map(r => String(r.Year ?? r["Year"] ?? ""));
  
    const normalize = (k) => String(k).toLowerCase().replace(/[^a-z0-9]+/g, "");
    const toNum = (v) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
  
    const findKey = (candidates) => {
      const keys = Object.keys(sorted[0] || {});
      const map = new Map(keys.map(k => [normalize(k), k]));
      for (const c of candidates) if (keys.includes(c)) return c;
      for (const c of candidates) {
        const hit = map.get(normalize(c));
        if (hit) return hit;
      }
      return null;
    };
  
    // ---- หา key ให้เจอใน result.json ----
    const kFCF = findKey([
      "Free_cash_flow_FCF",
      "Free Cash Flow (FCF)",
      "Free Cash Flow",
      "FCF",
      "free_cash_flow",
      "freecashflow"
    ]);
  
    if (!kFCF) {
      console.warn("ไม่เจอคีย์ FCF ใน result.json");
      return;
    }
  
    const fcf = sorted.map(r => toNum(r[kFCF]));
  
    // ---- Line: Growth % (YoY) ----
    const growthPct = fcf.map((v, i) => {
      if (i === 0) return null;
      const prev = fcf[i - 1];
      if (!Number.isFinite(v) || !Number.isFinite(prev) || prev === 0) return null;
      return ((v - prev) / Math.abs(prev)) * 100;
    });
  
    const canvas = document.getElementById("fcfComboChart");
    if (!canvas) return;
  
    // กันกราฟซ้อน
    if (state?.charts?.fcfComboChart) state.charts.fcfComboChart.destroy();
    
    //function cleanNegZero(x) {
    //  return (typeof x === "number" && Object.is(x, -0)) ? 0 : x;
    //}
    
    state.charts.fcfComboChart = new Chart(canvas.getContext("2d"), {
      data: {
        labels: years,
        datasets: [
          {
            type: "bar",
            label: "Free Cash Flow (FCF)",
            data: fcf,
            yAxisID: "yCash",
            borderRadius: 6
          },
          {
            type: "line",
            label: "FCF Growth (%)",
            data: growthPct, //.map(v => (v == null ? null : cleanNegZero(v))),
            yAxisID: "yPct",
            tension: 0.25,
            pointRadius: 3,
           /* 
            // สี “จุด” เปลี่ยนตามค่าบวก/ลบ
            pointBackgroundColor: (ctx) => {
              const v = ctx.raw;
              if (v == null) return "rgba(255, 255, 255, .35";
              return v < 0 ? "#EF4444" : "#10B981"; // แดง / ชมพู
            },
            pointBorderColor: (ctx) => {
              const v = ctx.raw;
              if (v == null) return "rgba(255, 255, 255, .35";
              return v < 0 ? "#EF4444" : "#10B981"; // แดง / เขียว
            },
            //สี “เส้น” เปลี่ยนตาม segment (ช่วงเส้น) ตามค่าบวก/ลบ
            segment: {
              borderColor: (ctx) => {
                const y0 = ctx.p0.parsed.y;
                const y1 = ctx.p1.parsed.y;
                // ถ้าช่วงเวลานี้มีค่าติดลบ ไห้เป็นแดง
                return (y0 < 0 || y1 < 0) ? "#EF4444" : "#10B981";
              }
            },
            borderColor: 3,
            */
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.raw;
                if (v == null) return `${ctx.dataset.label}: —`;
                if (ctx.dataset.yAxisID === "yPct") return `${ctx.dataset.label}: ${v.toFixed(2)}%`;
                // format เงิน
                const abs = Math.abs(v);
                if (abs >= 1e9) return `${ctx.dataset.label}: ${(v/1e9).toFixed(2)} B`;
                if (abs >= 1e6) return `${ctx.dataset.label}: ${(v/1e6).toFixed(2)} M`;
                return `${ctx.dataset.label}: ${Number(v).toLocaleString()}`;
              }
            }
          }
        },
        scales: {
          yCash: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Cash (FCF)" }
          },
          yPct: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Growth (%)" }
          },
          x: { ticks: { autoSkip: true, maxTicksLimit: 12 } }
        }
      }
    });
  }
  
  function plotOCFCombo(rows) {
    if (!rows?.length || !window.Chart) return;
  
    const sorted = [...rows].sort((a, b) => {
      const ya = String(a.Year ?? a["Year"] ?? "");
      const yb = String(b.Year ?? b["Year"] ?? "");
      const na = Number(ya), nb = Number(yb);
      if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
      return ya.localeCompare(yb);
    });
  
    const years = sorted.map(r => String(r.Year ?? r["Year"] ?? ""));
  
    const normalize = (k) => String(k).toLowerCase().replace(/[^a-z0-9]+/g, "");
    const toNum = (v) => {
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
  
    const findKey = (candidates) => {
      const keys = Object.keys(sorted[0] || {});
      const map = new Map(keys.map(k => [normalize(k), k]));
      for (const c of candidates) if (keys.includes(c)) return c;
      for (const c of candidates) {
        const hit = map.get(normalize(c));
        if (hit) return hit;
      }
      return null;
    };
  
    // ✅ หา key OCF ให้เจอใน result.json
    const kOCF = findKey([
      "Operating_cash_flow_OCF",
      "Operating Cash Flow (OCF)",
      "Operating Cash Flow",
      "OCF",
      "operating_cash_flow",
      "operatingcashflow"
    ]);
  
    if (!kOCF) {
      console.warn("ไม่เจอคีย์ OCF ใน result.json");
      return;
    }
  
    const ocf = sorted.map(r => toNum(r[kOCF]));
  
    // ✅ Growth % (YoY)
    const growthPct = ocf.map((v, i) => {
      if (i === 0) return null;
      const prev = ocf[i - 1];
      if (!Number.isFinite(v) || !Number.isFinite(prev) || prev === 0) return null;
      const g = ((v - prev) / Math.abs(prev)) * 100;
      return Object.is(g, -0) ? 0 : g; // กัน -0
    });
  
    const canvas = document.getElementById("ocfComboChart");
    if (!canvas) return;
  
    // กันกราฟซ้อน
    if (state?.charts?.ocfComboChart) state.charts.ocfComboChart.destroy();
  
    state.charts.ocfComboChart = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: years,
        datasets: [
          {
            type: "bar",
            label: "Operating Cash Flow (OCF)",
            data: ocf,
            yAxisID: "yCash",
            borderRadius: 6,
            barPercentage: 0.7,
            categoryPercentage: 0.7,
          },
          {
            type: "line",
            label: "OCF Growth (%)",
            data: growthPct,
            yAxisID: "yPct",
            tension: 0.25,
            pointRadius: 3,
            borderWidth: 3,
  
            // จุดแดงเมื่อค่าติดลบ
            pointBackgroundColor: (ctx) => {
              const v = ctx.raw;
              if (v == null) return "rgba(255,255,255,.35)";
              return v < 0 ? "#EF4444" : "#10B981";
            },
            pointBorderColor: (ctx) => {
              const v = ctx.raw;
              if (v == null) return "rgba(255,255,255,.35)";
              return v < 0 ? "#EF4444" : "#10B981";
            },
  
            // เส้นแดงเมื่อช่วงนั้นติดลบ
            segment: {
              borderColor: (ctx) => {
                const y0 = ctx.p0.parsed.y;
                const y1 = ctx.p1.parsed.y;
                return (y0 < 0 || y1 < 0) ? "#EF4444" : "#10B981";
              }
            }
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                let v = ctx.raw;
                if (v == null) return `${ctx.dataset.label}: —`;
                if (typeof v === "number" && Object.is(v, -0)) v = 0;
  
                if (ctx.dataset.yAxisID === "yPct") return `${ctx.dataset.label}: ${v.toFixed(2)}%`;
  
                const abs = Math.abs(v);
                if (abs >= 1e9) return `${ctx.dataset.label}: ${(v/1e9).toFixed(2)} B`;
                if (abs >= 1e6) return `${ctx.dataset.label}: ${(v/1e6).toFixed(2)} M`;
                return `${ctx.dataset.label}: ${Number(v).toLocaleString()}`;
              }
            }
          }
        },
        scales: {
          yCash: {
            type: "linear",
            position: "left",
            title: { display: true, text: "Cash (OCF)" },
            beginAtZero: false
          },
          yPct: {
            type: "linear",
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Growth (%)" },
            ticks: { callback: (v) => `${v}%` }
          },
          x: { ticks: { autoSkip: true, maxTicksLimit: 12 } }
        }
      }
    });
  }
      // ================== render KPI cards ================== (ROW)
  function renderKpiCards(rows){
  const el = document.getElementById("kpiCards");
  if (!el || !rows?.length) return;

  const sorted = [...rows].sort((a,b) => Number(a.Year ?? a["Year"]) - Number(b.Year ?? b["Year"]));
  const last = sorted[sorted.length - 1];
  const prev = sorted.length > 1 ? sorted[sorted.length - 2] : null;

  const toNum = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };

  const fmt = (key, v) => {
    const n = toNum(v);
    if (n == null) return "—";
    if (/margin|roe|roa|roic/i.test(key)) return n.toFixed(2) + "%";
    if (/wacc|cost of equity|cost_of_equity|coe/i.test(key)) return (n * 100).toFixed(2) + "%";
    return n.toLocaleString();
  };

  const KPIS = [
    { key: "EBITDA Margin", label: "EBITDA MARGIN" },
    { key: "Net Profit Margin", label: "NET PROFIT MARGIN" },
    { key: "Gross Profit MArgin", label: "GROSS PROFIT MARGIN" },
    { key: "Operating Profit Margin", label: "OPERATING PROFIT MARGIN" },
    { key: "WACC", label: "WACC" },
  ];

  const lowerIsBetter = new Set(["WACC"]);
  el.innerHTML = "";

  KPIS.forEach((kpi, idx) => {
    const cur = toNum(last?.[kpi.key]);
    const tar = toNum(prev?.[kpi.key]);
    const pct = (cur != null && tar != null && tar !== 0) ? (cur / tar) * 100 : null;

    const clamp = (x,a,b) => Math.max(a, Math.min(b, x));
    const fillPct = pct == null ? 0 : clamp(pct, 0, 150);

    let good = false;
    if (pct != null) {
      const invert = lowerIsBetter.has(kpi.key);
      good = invert ? (cur <= tar) : (cur >= tar);
    }

    const badgeText = pct == null ? "No Target" : `${pct.toFixed(2)}% of target`;

    const card = document.createElement("div");
    card.className = "kpi-card " + (pct == null ? "" : (good ? "kpi-good" : "kpi-bad"));
   
    card.innerHTML = `
      <div class="kpi-top">
        <div>
          <p class="kpi-title">Tab ${idx + 1}</p>
          <div class="kpi-name">${kpi.label}</div>
        </div>
        <div class="kpi-badge">${badgeText}</div>
      </div>

      <div class="kpi-metrics">
        <div class="kpi-metric">
          <div class="label">KPI VALUE (${last?.Year ?? last?.["Year"] ?? "-"})</div>
          <div class="value">${fmt(kpi.key, cur)}</div>
        </div>
        <div class="kpi-metric">
          <div class="label">TARGET (${prev?.Year ?? prev?.["Year"] ?? "-"})</div>
          <div class="value">${fmt(kpi.key, tar)}</div>
        </div>
      </div>

      <div class="kpi-progress">
        <div class="kpi-bar">
          <div class="kpi-fill" style="width:${fillPct}%"></div>
          <div class="kpi-marker" style="left:100%"></div>
        </div>
        <div class="kpi-scale">
          <span>0%</span><span>50%</span><span>100%</span><span>150%</span>
        </div>
      </div>
    `;

    el.appendChild(card);
  });
}
  // ================== แปลง rows เป็น ratios ==================
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
    if (!cards) return;
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
  
  async function loadAIAnalysis(rows) {
    try {
      if (!rows || !rows.length) throw new Error("rows ว่าง");
  
      // ถ้า frontend เปิดด้วย Live Server 5500 ให้ใช้ URL เต็ม (กัน CORS/คนละ origin)
      const url = "http://127.0.0.1:8000/api/ai-analysis"; // หรือใช้ "/api/ai-analysis" ถ้าเสิร์ฟหน้าเว็บจาก FastAPI
  
      // ใส่ข้อความโหลด
      const setLoading = (id) => {
        const el = document.getElementById(id);
        if (el) el.innerText = "กำลังวิเคราะห์...";
      };
      ["aiQuality","aiValuation","aiRisk","aiView"].forEach(setLoading);
  
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result: rows })
      });
  
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(`AI API ${res.status} ${t}`);
      }
  
      const data = await res.json();
      const a = data?.analysis;
  
      // รองรับ 2 แบบ:
      // 1) a เป็น object {quality, valuation, risk, view}
      // 2) a เป็น {text: "..."} (กรณี GPT ส่งเป็นข้อความเดียว)
      if (a && typeof a === "object" && ("quality" in a || "valuation" in a || "risk" in a || "view" in a)) {
        if (document.getElementById("aiQuality"))   document.getElementById("aiQuality").innerText   = a.quality ?? "—";
        if (document.getElementById("aiValuation")) document.getElementById("aiValuation").innerText = a.valuation ?? "—";
        if (document.getElementById("aiRisk"))      document.getElementById("aiRisk").innerText      = a.risk ?? "—";
        if (document.getElementById("aiView"))      document.getElementById("aiView").innerText      = a.view ?? "—";
        return;
      }
  
      if (a && typeof a === "object" && "text" in a) {
        // ถ้าได้ text เดียว เอาไปใส่ aiView และให้ช่องอื่นเป็น —
        if (document.getElementById("aiView")) document.getElementById("aiView").innerText = a.text ?? "—";
        if (document.getElementById("aiQuality"))   document.getElementById("aiQuality").innerText   = "—";
        if (document.getElementById("aiValuation")) document.getElementById("aiValuation").innerText = "—";
        if (document.getElementById("aiRisk"))      document.getElementById("aiRisk").innerText      = "—";
        return;
      }
  
      throw new Error("รูปแบบ response ไม่ถูกต้อง (analysis ไม่มีข้อมูลที่คาดไว้)");
  
    } catch (err) {
      console.error("AI ERROR:", err);
      if (document.getElementById("aiQuality"))   document.getElementById("aiQuality").innerText   = "❌ AI ใช้งานไม่ได้";
      if (document.getElementById("aiValuation")) document.getElementById("aiValuation").innerText = "❌ AI ใช้งานไม่ได้";
      if (document.getElementById("aiRisk"))      document.getElementById("aiRisk").innerText      = "❌ AI ใช้งานไม่ได้";
      if (document.getElementById("aiView"))      document.getElementById("aiView").innerText      = "❌ AI ใช้งานไม่ได้";
    }
  }
  
  /*
  async function loadAIAnalysis(rows) {
    const res = await fetch("/api/ai-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result: rows })
    });
  
    const data = await res.json();
    document.getElementById("aiView").innerText = data.analysis.text;
  }
  */
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
  
  function pickField(obj, keys) {
    if (!obj) return null;
    for (const k of keys) {
      if (obj[k] != null) return obj[k];
    }
    return null;
  }
  
  function firstObject(obj) {
    const v = obj && Object.values(obj)[0];
    return typeof v === "object" ? v : null;
  }

  // ================== ส่วนอัตราส่วน: EPS 5 ปี / Cost of Equity 5 ปี ฯลฯ ==================
  
  function renderRatioSection(data) {
    // สมมติ backend ส่ง ratios มาแบบนี้:
    // data.ratios = { EPS: {2021:..,2022:..}, Cost_of_Equity:{...}, ROE:{...}, ... }
    const ratios = data.ratios || data.metrics || null;
    if (!ratios) return;
  
    // init tabs แค่ครั้งแรก
    if (!state.ratioTabsInited) {
      initRatioTabs();
      state.ratioTabsInited = true;
    }
  
    // ค่า default ที่จะแสดง: EPS & CoE 5 ปี
    const defaultGroup = ratioGroups[0]; // EPS & CoE
    renderRatioPair(ratios, defaultGroup);
  }
  
  // กลุ่มหมวดหมู่ที่ต้องการ
  const ratioGroups = [
    {
      tab: "EPS & CoE",
      m1: { label: "EPS",            keys: ["eps", "earningspershare", "eps_diluted"] },
      m2: { label: "Cost of Equity", keys: ["costofequity", "coe", "cost_of_equity"] }
    },
    {
      tab: "Profitability",
      m1: { label: "ROE",  keys: ["roe", "returnonequity"] },
      m2: { label: "ROIC", keys: ["roic", "returnoninvestedcapital"] }
    },
    {
      tab: "Valuation",
      m1: { label: "P/E", keys: ["pe", "peratio", "priceearnings"] },
      m2: { label: "P/BV",keys: ["pbv", "pricebook", "price_to_book"] }
    },
    {
      tab: "Cashflow",
      m1: { label: "FCF Margin", keys: ["fcfmargin", "freecashflowmargin"] },
      m2: { label: "Owner Earnings", keys: ["ownerearnings", "owner_earnings"] }
    },
  ];
  
  function initRatioTabs() {
    const wrap = document.getElementById("ratioTabs");
    if (!wrap) return;
  
    wrap.innerHTML = "";
    ratioGroups.forEach((group, idx) => {
      const btn = document.createElement("button");
      btn.className = "tab" + (idx === 0 ? " active" : "");
      btn.textContent = group.tab;
      btn.addEventListener("click", () => onRatioTabClick(group, btn));
      wrap.appendChild(btn);
    });
  }
  
  function onRatioTabClick(group, btn) {
    const wrap = document.getElementById("ratioTabs");
    [...wrap.children].forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
  
    // ratios เก็บไว้ไม่ได้ เลยดึงจาก status ล่าสุดใน window ถ้าคุณอยากเก็บไว้
    // ที่ง่ายสุด: ให้ backend ส่ง ratios เสมอ และเราเก็บ data ล่าสุดไว้
    const lastData = window.__lastFinancialData;
    if (lastData && (lastData.ratios || lastData.metrics)) {
      const ratios = lastData.ratios || lastData.metrics;
      renderRatioPair(ratios, group);
    }
  }
  
  // เรียกจาก renderAll เพื่อเก็บ data ล่าสุดไว้ใช้เวลาเปลี่ยนแท็บ
  const _originalRenderAll = renderAll;
  renderAll = function (data) {
    window.__lastFinancialData = data;
    _originalRenderAll(data);
  };
  
  function renderRatioPair(ratios, group) {
    const epsSeries = findMetricSeries(ratios, group.m1.keys);
    const coeSeries = findMetricSeries(ratios, group.m2.keys);
  
    if (!epsSeries && !coeSeries) {
      console.warn("ไม่พบข้อมูลสำหรับกลุ่ม", group);
      return;
    }
  
    const { years, series1, series2 } = buildRatioSeries(epsSeries, coeSeries, 5); // ตัดเหลือ 5 ปี
  
    const t1 = document.getElementById("rTitle1");
    const t2 = document.getElementById("rTitle2");
    if (t1) t1.textContent = `${group.m1.label} (5Y)`;
    if (t2) t2.textContent = `${group.m2.label} (5Y)`;
  
    setupOrUpdateLine("rChart1", years, series1, group.m1.label);
    setupOrUpdateLine("rChart2", years, series2, group.m2.label);
  }
  
  // หา metric ตามชื่อ key (ไม่สนตัวพิมพ์เล็กใหญ่ / _ / ช่องว่าง)
  function normalizeKey(k) {
    return String(k).toLowerCase().replace(/[^a-z0-9]+/g, "");
  }
  
  function findMetricSeries(ratios, candidateKeys) {
    if (!ratios) return null;
    const candNorm = candidateKeys.map(normalizeKey);
    for (const [k, v] of Object.entries(ratios)) {
      if (candNorm.includes(normalizeKey(k))) {
        return v; // คาดว่าเป็น { "2021": value, "2022": value, ... }
      }
    }
    return null;
  }
  
  function buildRatioSeries(seriesObj1, seriesObj2, lastN = 5) {
    const yearSet = new Set();
  
    [seriesObj1, seriesObj2].forEach(s => {
      if (s && typeof s === "object") {
        Object.keys(s).forEach(y => yearSet.add(String(y)));
      }
    });
  
    const allYears = Array.from(yearSet).sort();
    const start = allYears.length > lastN ? allYears.length - lastN : 0;
    const years = allYears.slice(start);
  
    const makeArr = (obj) =>
      years.map(y => (obj && obj[y] != null ? obj[y] : null));
  
    return {
      years,
      series1: makeArr(seriesObj1),
      series2: makeArr(seriesObj2),
    };
  }
  
  // ================== helper สำหรับ Chart.js ==================
  
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
          datasets: [
            {
              label,
              data,
              fill: false,
              tension: 0.35
            }
          ]
        },
        options: {
          plugins: { legend: { display: true } },
          scales: {
            x: { grid: { color: "rgba(148,163,184,.14)" } },
            y: { grid: { color: "rgba(148,163,184,.08)" } }
          }
        }
      });
    } else {
      const chart = state.charts[canvasId];
      chart.data.labels = labels;
      chart.data.datasets[0].label = label;
      chart.data.datasets[0].data = data;
      chart.update();
    }
  }
 /*
  // ================== AI Analysis (Text Insight) ==================
  async function loadAIAnalysis(rows) {
    try {
      // ส่ง rows ไปให้ backend วิเคราะห์
      const res = await fetch("/api/ai-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          result: rows
        })
      });

      if (!res.ok) throw new Error("AI analysis failed");

      const data = await res.json();
      const a = data.analysis;

      // แสดงผลข้อความ
      document.getElementById("aiQuality").innerText   = a.quality;
      document.getElementById("aiValuation").innerText = a.valuation;
      document.getElementById("aiRisk").innerText      = a.risk;
      document.getElementById("aiView").innerText      = a.view;

    } catch (err) {
      console.error(err);
      document.getElementById("aiQuality").innerText =
        "ไม่สามารถโหลด AI Analysis ได้";
    }
  } */