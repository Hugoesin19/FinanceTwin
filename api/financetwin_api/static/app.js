/**
 * P14 Decision Studio — shell único, wizards, resultado hero.
 * Regla: ningún número financiero se calcula aquí; solo se muestra lo que
 * devuelve la API (CalculationRun / motor).
 */
(function () {
  const LS_COMPANY = "ft_company_id";
  const LS_NAME = "ft_company_name";
  const LS_PACK = "ft_pack_id";

  const STEPS = ["home", "twin", "decision", "liquidity", "report", "followup"];
  const STEP_SECTIONS = {
    home: "sec-home",
    twin: "sec-company",
    decision: "sec-pack",
    liquidity: "sec-pack",
    report: "sec-report",
    followup: "sec-twin-loop",
  };

  /** Campos que van al bloque colapsado «avanzados» (el resto = esenciales). */
  const ADVANCED_KEYS = {
    new_site: ["collection_days", "discount_rate_annual", "employer_cost_per_person", "headcount"],
    financing: ["linked_capex", "use_of_funds"],
    asset_purchase: ["leasing_monthly", "leasing_term_months", "discount_rate_annual"],
    hiring: ["discount_rate_annual", "gross_margin_pct"],
    generic_investment: ["debt_amount", "equity_amount", "discount_rate_annual", "gross_margin_pct"],
    liquidity_plan: ["one_off_outflows"],
  };

  /** Campos canónicos por pack (DECISION_PACKS / inputs_schema). Defaults = camino feliz. */
  const PACK_FORMS = {
    new_site: {
      title: "Nuevo establecimiento",
      hint: "Simula abrir un local: CAPEX, ventas, alquiler y financiación.",
      fields: [
        { key: "site_name", label: "Nombre del local", type: "text", value: "Tienda Alicante" },
        { key: "open_year_month", label: "Apertura (YYYY-MM)", type: "text", value: "2027-01" },
        { key: "capex_total", label: "Inversión inicial (CAPEX)", type: "money", value: "350000" },
        { key: "sales_run_rate", label: "Ventas en régimen (€/mes)", type: "money", value: "40000" },
        { key: "gross_margin_pct", label: "Margen bruto (0–1)", type: "rate", value: "0.40" },
        { key: "rent_monthly", label: "Alquiler mensual", type: "money", value: "4500" },
        { key: "other_opex_monthly", label: "Otros costes fijos / mes", type: "money", value: "1500" },
        { key: "headcount", label: "Plantilla", type: "count", value: "2" },
        { key: "employer_cost_per_person", label: "Coste empresa / persona", type: "money", value: "2800" },
        { key: "debt_amount", label: "Deuda", type: "money", value: "200000" },
        { key: "equity_amount", label: "Capital propio", type: "money", value: "150000" },
        { key: "loan_term_months", label: "Plazo préstamo (meses)", type: "count", value: "60" },
        { key: "loan_annual_rate", label: "TIN préstamo (0–1)", type: "rate", value: "0.055" },
        { key: "horizon_months", label: "Horizonte (meses)", type: "count", value: "24" },
        { key: "discount_rate_annual", label: "Tasa descuento (0–1)", type: "rate", value: "0.08" },
        { key: "collection_days", label: "Días de cobro", type: "count", value: "0" },
      ],
    },
    financing: {
      title: "Financiación",
      hint: "Simula pedir un préstamo y su efecto en caja.",
      fields: [
        { key: "loan_name", label: "Nombre del préstamo", type: "text", value: "Puente" },
        { key: "principal", label: "Principal", type: "money", value: "50000" },
        { key: "disbursement_year_month", label: "Mes de disposición", type: "text", value: "2027-01" },
        { key: "annual_rate", label: "TIN anual (0–1)", type: "rate", value: "0.06" },
        { key: "term_months", label: "Plazo (meses)", type: "count", value: "24" },
        {
          key: "use_of_funds",
          label: "Uso de fondos",
          type: "enum",
          value: "cash_buffer",
          options: ["cash_buffer", "capex", "refinance_placeholder", "general"],
        },
        { key: "linked_capex", label: "CAPEX ligado", type: "money", value: "" },
        { key: "horizon_months", label: "Horizonte", type: "count", value: "24" },
      ],
    },
    asset_purchase: {
      title: "Compra de activo",
      hint: "Comprar maquinaria/vehículo: contado, préstamo o leasing.",
      fields: [
        { key: "asset_name", label: "Activo", type: "text", value: "Furgoneta" },
        { key: "acquisition_cost", label: "Coste de adquisición", type: "money", value: "25000" },
        { key: "acquisition_year_month", label: "Mes de adquisición", type: "text", value: "2027-01" },
        { key: "useful_life_months", label: "Vida útil (meses)", type: "count", value: "60" },
        {
          key: "funding_mode",
          label: "Cómo se paga",
          type: "enum",
          value: "cash",
          options: ["cash", "loan", "leasing_as_cost"],
        },
        { key: "opex_savings_monthly", label: "Ahorro opex / mes", type: "money", value: "400" },
        { key: "leasing_monthly", label: "Cuota leasing", type: "money", value: "" },
        { key: "leasing_term_months", label: "Plazo leasing", type: "count", value: "" },
        { key: "horizon_months", label: "Horizonte", type: "count", value: "24" },
        { key: "discount_rate_annual", label: "Tasa descuento (0–1)", type: "rate", value: "0.08" },
      ],
    },
    hiring: {
      title: "Contratación",
      hint: "Contratar personal y estimar el uplift de ventas.",
      fields: [
        { key: "role_name", label: "Rol", type: "text", value: "Comercial" },
        { key: "headcount", label: "Personas", type: "count", value: "2" },
        { key: "employer_cost_per_person", label: "Coste empresa / persona", type: "money", value: "3000" },
        { key: "start_year_month", label: "Inicio", type: "text", value: "2027-01" },
        { key: "expected_monthly_revenue_uplift", label: "Uplift ventas / mes", type: "money", value: "8000" },
        { key: "gross_margin_pct", label: "Margen (0–1)", type: "rate", value: "0.4" },
        { key: "horizon_months", label: "Horizonte", type: "count", value: "12" },
        { key: "discount_rate_annual", label: "Tasa descuento (0–1)", type: "rate", value: "0.08" },
      ],
    },
    generic_investment: {
      title: "Inversión genérica",
      hint: "CAPEX + beneficio esperado (ahorro o ingresos).",
      fields: [
        { key: "name", label: "Nombre", type: "text", value: "Software" },
        {
          key: "capex_schedule",
          label: "Calendario CAPEX (JSON)",
          type: "json",
          value: '[{"year_month":"2027-01","amount":"20000"}]',
        },
        { key: "horizon_months", label: "Horizonte", type: "count", value: "24" },
        {
          key: "benefit_cadence",
          label: "Cadencia del beneficio",
          type: "enum",
          value: "monthly",
          options: ["monthly", "annual"],
        },
        { key: "benefit_amount", label: "Importe del beneficio", type: "money", value: "1500" },
        {
          key: "benefit_type",
          label: "Tipo de beneficio",
          type: "enum",
          value: "revenue",
          options: ["opex_reduction", "revenue"],
        },
        { key: "gross_margin_pct", label: "Margen (0–1)", type: "rate", value: "0.8" },
        { key: "debt_amount", label: "Deuda", type: "money", value: "0" },
        { key: "equity_amount", label: "Capital propio", type: "money", value: "20000" },
        { key: "discount_rate_annual", label: "Tasa descuento (0–1)", type: "rate", value: "0.08" },
      ],
    },
    liquidity_plan: {
      title: "Plan de liquidez",
      hint: "Estrés de caja: ajuste de ventas, opex extra y salidas puntuales.",
      fields: [
        { key: "horizon_months", label: "Horizonte", type: "count", value: "12" },
        { key: "anchor_year_month", label: "Ancla (YYYY-MM)", type: "text", value: "2027-01" },
        { key: "sales_adjustment_pct", label: "Ajuste ventas (p.ej. -0.10)", type: "rate", value: "-0.10" },
        { key: "extra_monthly_opex", label: "Opex extra / mes", type: "money", value: "1000" },
        {
          key: "one_off_outflows",
          label: "Salidas puntuales (JSON)",
          type: "json",
          value: '[{"year_month":"2027-03","amount":"5000","label":"tax"}]',
        },
      ],
    },
  };

  const CANONICAL_PACKS = Object.keys(PACK_FORMS);

  /**
   * Checklist P3: campos pintados en UI ⊆ respuesta API / CalculationResult.
   * No añadir aquí aliases inventados.
   */
  const REPORT_FIELDS = {
    investment_metrics: [
      "npv",
      "irr_annual",
      "payback_simple",
      "payback_discounted",
      "warnings",
    ],
    financing_need: [
      "min_cash",
      "min_cash_month",
      "max_shortfall_vs_policy",
      "first_shortfall_month",
      "months_below_policy",
    ],
    policy_checks: ["policy_id", "status", "value", "threshold", "message"],
    cash_flow: [
      "t",
      "opening_cash",
      "closing_cash",
      "operating_cash_flow",
      "capex_paid",
      "loan_drawdowns",
      "net_cash_flow",
    ],
    meta: [
      "pack_id",
      "calculation_run_id",
      "scenario_id",
      "model_version_id",
      "engine_version",
      "variant",
      "inputs_hash",
      "result_hash",
      "warnings",
    ],
  };

  const COMPARE_ROWS = [
    { label: "Valor creado (VAN)", path: ["investment_metrics", "npv"] },
    { label: "Rentabilidad (TIR)", path: ["investment_metrics", "irr_annual"] },
    { label: "Payback simple", path: ["investment_metrics", "payback_simple"] },
    { label: "Payback descontado", path: ["investment_metrics", "payback_discounted"] },
    { label: "Caja más baja", path: ["financing_need", "min_cash"] },
    { label: "Hueco vs política", path: ["financing_need", "max_shortfall_vs_policy"] },
    { label: "Mes de caja más baja", path: ["financing_need", "min_cash_month"] },
    { label: "Meses bajo política", path: ["financing_need", "months_below_policy"] },
    { label: "Id del cálculo", path: ["calculation_run_id"] },
    { label: "Huella del resultado", path: ["result_hash"] },
  ];

  const METRIC_LABELS = {
    npv: "Valor creado (VAN)",
    irr_annual: "Rentabilidad anual (TIR)",
    payback_simple: "Payback simple",
    payback_discounted: "Payback descontado",
    min_cash: "Caja más baja del periodo",
    min_cash_month: "Mes de la caja más baja",
    max_shortfall_vs_policy: "Hueco frente a tu política",
    first_shortfall_month: "Primer mes en hueco",
    months_below_policy: "Meses bajo la política",
  };

  const VARIANT_LABELS = {
    base: "Base",
    conservative: "Conservador",
    adverse: "Adverso",
  };

  const ENUM_LABELS = {
    cash_buffer: "Colchón de caja",
    capex: "CAPEX",
    refinance_placeholder: "Refinanciar",
    general: "General",
    cash: "Contado",
    loan: "Préstamo",
    leasing_as_cost: "Leasing",
    monthly: "Mensual",
    annual: "Anual",
    opex_reduction: "Ahorro de opex",
    revenue: "Ingresos",
  };

  const VARIABLE_LABELS = {
    sales_monthly: "Ventas mensuales",
    min_cash: "Caja más baja",
    npv: "VAN",
    irr_annual: "TIR anual",
  };

  const MONEY_METRIC_KEYS = new Set([
    "npv",
    "min_cash",
    "max_shortfall_vs_policy",
  ]);
  const RATE_METRIC_KEYS = new Set(["irr_annual"]);
  const COUNT_METRIC_KEYS = new Set([
    "payback_simple",
    "payback_discounted",
    "months_below_policy",
  ]);
  const MONTH_METRIC_KEYS = new Set(["min_cash_month", "first_shortfall_month"]);
  const KEY_METRICS = new Set(["npv", "min_cash", "max_shortfall_vs_policy"]);

  const VARIANTS = ["base", "conservative", "adverse"];

  const state = {
    companyId: null,
    modelVersionId: null,
    lastRun: null,
    lastCompare: null,
    selectedDecisionId: null,
    lastCalib: null,
    busy: false,
    step: "home",
    hasReport: false,
    companyName: "",
    draftRevenues: [],
    draftCosts: [],
    liquidityMode: false,
    wizStep: 1,
    fromDemo: false,
    successTimer: null,
  };

  const $ = (id) => document.getElementById(id);

  function formatApiDetail(detail) {
    if (detail == null) return "";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .slice(0, 5)
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
            const msg = item.msg || item.message || item.detail || JSON.stringify(item);
            return loc ? `${loc}: ${msg}` : String(msg);
          }
          return String(item);
        })
        .join("\n");
    }
    if (typeof detail === "object") {
      if (detail.issues && Array.isArray(detail.issues)) {
        return detail.issues
          .slice(0, 5)
          .map((i) => (typeof i === "string" ? i : i.message || JSON.stringify(i)))
          .join("\n");
      }
      if (detail.message) return String(detail.message);
      try {
        return JSON.stringify(detail);
      } catch {
        return String(detail);
      }
    }
    return String(detail);
  }

  function humanizeError(err) {
    const raw = err && err.message != null ? err.message : String(err || "Error");
    let parsed = raw;
    try {
      const asJson = JSON.parse(raw);
      parsed = formatApiDetail(asJson);
    } catch {
      parsed = raw;
    }
    const text = String(parsed || raw).trim();
    if (!text) return "Algo falló. Revisa los datos e inténtalo de nuevo.";
    if (/no current snapshot|has no current snapshot/i.test(text)) {
      return "Falta el twin de la empresa. Guarda los datos antes de calcular.";
    }
    if (/company not found/i.test(text)) {
      return "No encuentro esa empresa. Pulsa «Cargar demo» o crea una empresa nueva.";
    }
    if (/unknown pack|no analysis_plan|empty analysis_plan/i.test(text)) {
      return "Esta sensibilidad solo está disponible para «Nuevo establecimiento».";
    }
    if (/Crea una empresa|Selecciona|Rellena|Calcula un escenario/i.test(text)) {
      return text;
    }
    const lines = text.split("\n").filter(Boolean).slice(0, 3);
    return lines.join("\n");
  }

  function showError(msg) {
    const el = $("error");
    el.hidden = !msg;
    el.textContent = msg || "";
    if (msg && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function showCaught(err) {
    hideStatus();
    showError(humanizeError(err));
  }

  function showStatus(kind, text) {
    const bar = $("status-bar");
    const span = $("status-text");
    if (!bar || !span) return;
    if (state.successTimer) {
      clearTimeout(state.successTimer);
      state.successTimer = null;
    }
    bar.hidden = false;
    bar.classList.add("visible");
    bar.classList.toggle("loading", kind === "loading");
    bar.classList.toggle("success", kind === "success");
    const spinner = bar.querySelector(".spinner");
    if (spinner) spinner.style.display = kind === "loading" ? "" : "none";
    span.textContent = text || "";
    if (kind === "success") {
      state.successTimer = setTimeout(() => hideStatus(), 3000);
    }
  }

  function hideStatus() {
    const bar = $("status-bar");
    if (!bar) return;
    bar.hidden = true;
    bar.classList.remove("visible", "loading", "success");
  }

  function showSuccess(text, nextHintId, nextText) {
    showStatus("success", text);
    if (nextHintId && $(nextHintId)) {
      $(nextHintId).hidden = false;
      $(nextHintId).textContent = nextText || "";
    }
  }

  function updateTwinSummary() {
    const el = $("twin_summary");
    if (!el) return;
    if (!state.companyId) {
      el.hidden = true;
      return;
    }
    const name = $("company_name").value || state.companyName || "Empresa";
    const cash = $("opening_cash").value || "—";
    const minCash = $("min_cash").value || "—";
    el.hidden = false;
    el.textContent =
      `${name}: caja inicial ${cash} € · política de caja mínima ${minCash} €` +
      (state.modelVersionId ? ` · twin guardado` : "");
  }

  function setFollowStep(n) {
    for (let i = 1; i <= 3; i++) {
      const el = $(`follow-step-${i}`);
      if (el) el.classList.toggle("active-follow", i === n);
    }
  }

  function goToStep(step) {
    if (!STEPS.includes(step)) return;

    const needsCompany = ["decision", "liquidity", "followup", "report"].includes(step);
    if (needsCompany && !state.companyId && step !== "report") {
      showError("Primero crea una empresa o carga la demo.");
      step = "home";
    }

    if (step === "liquidity") {
      state.liquidityMode = true;
      $("pack_id").value = "liquidity_plan";
      localStorage.setItem(LS_PACK, "liquidity_plan");
      renderPackCards(true);
      renderPackForm("liquidity_plan");
      if ($("pack_workspace_title")) $("pack_workspace_title").textContent = "Liquidez";
      if ($("pack_hint")) {
        $("pack_hint").textContent = "¿Aguanto N meses? El motor responde con caja mínima y huecos.";
      }
      state.wizStep = 2;
    } else if (step === "decision") {
      state.liquidityMode = false;
      if ($("pack_id").value === "liquidity_plan") {
        $("pack_id").value = "new_site";
        localStorage.setItem(LS_PACK, "new_site");
      }
      renderPackCards(false);
      renderPackForm($("pack_id").value);
      if ($("pack_workspace_title")) $("pack_workspace_title").textContent = "Decidir";
      if ($("pack_hint")) {
        $("pack_hint").textContent = "Elige la decisión, revisa hipótesis y calcula.";
      }
      state.wizStep = 1;
    }

    if (step === "report" && !state.hasReport && !state.lastRun) {
      showError("Primero calcula un escenario en Decidir o Liquidez.");
      step = state.liquidityMode ? "liquidity" : "decision";
      if (!state.companyId) step = "home";
    }

    state.step = step;

    const showPack = step === "decision" || step === "liquidity";
    for (const s of ["home", "twin", "decision", "report", "followup"]) {
      const sec = $(STEP_SECTIONS[s]);
      if (!sec) continue;
      if (s === "decision") {
        sec.hidden = !showPack;
      } else if (s === "report") {
        sec.hidden = !(state.hasReport && step === "report");
      } else {
        sec.hidden = s !== step;
      }
    }
    if (step === "report" && state.hasReport) {
      $("sec-report").hidden = false;
    }

    document.querySelectorAll("#app-nav .side-link").forEach((btn) => {
      const g = btn.getAttribute("data-goto");
      const active =
        g === step ||
        (g === "liquidity" && step === "liquidity") ||
        (g === "decision" && step === "decision");
      btn.classList.toggle("active", Boolean(active));
    });

    if (showPack) {
      setWizardStep(state.wizStep);
      updateLiquidityWizardChrome();
    }
    updateNavReport();
    updateContextBar();
    updateHomeGates();
    updateCreateButtonLabels();
    if (step === "home") refreshHome();
    if (step === "twin") refreshTwinQuality().catch(() => {});
    if (step === "followup") updateFollowupEmpty();
    const target = showPack ? $("sec-pack") : $(STEP_SECTIONS[step]);
    if (target && typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function updateLiquidityWizardChrome() {
    const liq = state.liquidityMode || $("pack_id").value === "liquidity_plan";
    const step1 = $("wiz-step-1");
    const pane1 = $("wiz-pane-1");
    const back2 = $("wiz-back-2");
    if (step1) step1.hidden = liq;
    if (pane1 && liq) pane1.hidden = true;
    if (back2) back2.hidden = liq;
    if (liq) {
      if ($("wiz-step-2")) $("wiz-step-2").textContent = "1 · Hipótesis";
      if ($("wiz-step-3")) $("wiz-step-3").textContent = "2 · Calcular";
    } else {
      if ($("wiz-step-2")) $("wiz-step-2").textContent = "2 · Hipótesis";
      if ($("wiz-step-3")) $("wiz-step-3").textContent = "3 · Calcular";
    }
  }

  function updateNavReport() {
    const btn = $("nav-report");
    if (!btn) return;
    const ready = Boolean(state.hasReport && state.lastRun);
    btn.disabled = !ready;
  }

  function updateHomeGates() {
    const ready = Boolean(state.companyId);
    const onboard = $("home-onboard");
    const card = $("home-company-card");
    if (onboard) onboard.hidden = ready;
    if (card) card.hidden = !ready;
    for (const id of ["home-btn-decide", "home-btn-liquidity", "home-btn-followup"]) {
      const el = $(id);
      if (!el) continue;
      el.classList.toggle("job-disabled", !ready);
      el.setAttribute("aria-disabled", ready ? "false" : "true");
    }
  }

  function updateCreateButtonLabels() {
    const create = $("btn-create");
    if (!create) return;
    if (state.companyId) {
      create.textContent = "Crear otra empresa";
      create.classList.remove("primary");
      create.classList.add("secondary");
    } else {
      create.textContent = "Crear empresa";
      create.classList.add("primary");
      create.classList.remove("secondary");
    }
  }

  function updateFollowupEmpty() {
    const empty = $("followup-empty");
    const body = $("followup-body");
    const noRun = !state.lastRun;
    if (empty) empty.hidden = !noRun;
    if (body) body.hidden = noRun;
  }

  function setWizardStep(n) {
    state.wizStep = n;
    const liq = state.liquidityMode || $("pack_id").value === "liquidity_plan";
    for (let i = 1; i <= 3; i++) {
      const pane = $(`wiz-pane-${i}`);
      if (pane) {
        if (liq && i === 1) pane.hidden = true;
        else pane.hidden = i !== n;
      }
      const btn = $(`wiz-step-${i}`);
      if (btn) {
        btn.classList.toggle("active", i === n);
        btn.classList.toggle("done", i < n);
      }
    }
    updateLiquidityWizardChrome();
  }

  function updateContextBar() {
    const el = $("context_status");
    if (!el) return;
    if (!state.companyId) {
      el.textContent = "Sin empresa — carga demo o crea una";
      return;
    }
    const name = $("company_name").value || state.companyName || "Empresa";
    const cash = $("opening_cash").value || "—";
    el.textContent = `${name} · caja ${fmtMoney(cash)}`;
  }

  function updateStepper() {
    /* P14/P15: sin stepper duplicado */
  }

  function setBusy(busy) {
    state.busy = busy;
    const demoBtn = $("btn-demo");
    if (demoBtn) demoBtn.disabled = busy;
    $("btn-create").disabled = busy;
    $("btn-save-twin").disabled = busy || !state.companyId;
    $("btn-run").disabled = busy || !state.companyId;
    $("btn-compare").disabled = busy || !state.companyId;
    const compareReport = $("btn-compare-report");
    if (compareReport) compareReport.disabled = busy || !state.companyId || !state.lastRun;
    $("pack_id").disabled = busy;
    $("variant").disabled = busy;
    $("btn-register-decision").disabled = busy || !state.companyId || !state.lastRun;
    $("btn-refresh-decisions").disabled = busy || !state.companyId;
    $("btn-record-actuals").disabled = busy || !state.companyId || !state.selectedDecisionId;
    $("btn-mark-executed").disabled = busy || !state.companyId || !state.selectedDecisionId;
    $("btn-load-bias").disabled = busy || !state.companyId;
    $("btn-calib-preview").disabled = busy || !state.companyId;
    $("btn-import-csv").disabled = busy || !state.companyId;
    $("btn-sensitivity").disabled =
      busy || !state.companyId || !state.lastRun || $("pack_id").value !== "new_site";
    const dl = $("btn-download-report");
    if (dl) dl.disabled = busy || !state.companyId || !state.lastRun;
    if (busy) $("btn-apply-calib").disabled = true;
  }

  function setCompanyUi() {
    const ready = Boolean(state.companyId);
    if (!state.busy) {
      $("btn-save-twin").disabled = !ready;
      $("btn-run").disabled = !ready;
      $("btn-compare").disabled = !ready;
      const compareReport = $("btn-compare-report");
      if (compareReport) compareReport.disabled = !ready || !state.lastRun;
      $("btn-register-decision").disabled = !ready || !state.lastRun;
      $("btn-refresh-decisions").disabled = !ready;
      $("btn-record-actuals").disabled = !ready || !state.selectedDecisionId;
      $("btn-mark-executed").disabled = !ready || !state.selectedDecisionId;
      $("btn-load-bias").disabled = !ready;
      $("btn-calib-preview").disabled = !ready;
      $("btn-import-csv").disabled = !ready;
      $("btn-sensitivity").disabled =
        !ready || !state.lastRun || $("pack_id").value !== "new_site";
      const dl = $("btn-download-report");
      if (dl) dl.disabled = !ready || !state.lastRun;
    }
    $("company_meta").textContent = ready
      ? `Empresa lista`
      : "Sin empresa aún. Pulsa «Cargar demo» o «Crear empresa».";
    updateTwinSummary();
    updateContextBar();
    updateHomeGates();
    updateCreateButtonLabels();
    updateNavReport();
  }

  function clearReport() {
    state.lastRun = null;
    state.lastCompare = null;
    state.lastCalib = null;
    state.hasReport = false;
    $("sec-report").hidden = true;
    $("run_meta").textContent = "";
    $("compare").querySelector("tbody").innerHTML = "";
    $("compare_hint").textContent =
      "Pulsa «Comparar 3 escenarios» para ver base, conservador y adverso juntos.";
    $("btn-apply-calib").hidden = true;
    $("calib_out").textContent = "";
    $("sensitivity_out").textContent = "";
    $("sensitivity_out").hidden = true;
    const tables = $("sensitivity_tables");
    if (tables) tables.innerHTML = "";
    const sj = $("sensitivity_json_wrap");
    if (sj) sj.hidden = true;
    const sh = $("sensitivity_hint");
    if (sh) {
      sh.textContent =
        "Pulsa «¿Qué tendría que pasar?» para ver cambios directos, umbrales e estrés (solo nuevo establecimiento).";
    }
    $("metrics").innerHTML = "";
    $("policy-summary").textContent = "";
    if ($("report_title")) $("report_title").textContent = "Informe";
    if ($("report_meta")) $("report_meta").textContent = "";
    if ($("report_reading")) $("report_reading").textContent = "";
    if ($("hero_value")) $("hero_value").textContent = "—";
    if ($("hero_label")) $("hero_label").textContent = "Métrica";
    const banner = $("demo_banner");
    if (banner) banner.hidden = true;
    state.fromDemo = false;
    setCompanyUi();
  }

  function getPath(obj, path) {
    let cur = obj;
    for (const key of path) {
      if (cur == null || typeof cur !== "object") return undefined;
      cur = cur[key];
    }
    return cur;
  }

  function fmt(value) {
    return value === null || value === undefined || value === "" ? "—" : String(value);
  }

  /** Display-only formatting of API decimal strings (es-ES). No engine recalculation. */
  function parseDecimalString(value) {
    if (value === null || value === undefined || value === "") return null;
    const s = String(value).trim().replace(",", ".");
    if (!s || s === "—") return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }

  function fmtMoney(value) {
    const n = parseDecimalString(value);
    if (n === null) return fmt(value);
    try {
      return (
        n.toLocaleString("es-ES", {
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        }) + " €"
      );
    } catch {
      return fmt(value) + " €";
    }
  }

  function fmtRate(value) {
    const n = parseDecimalString(value);
    if (n === null) return fmt(value);
    try {
      return (n * 100).toLocaleString("es-ES", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 2,
      }) + " %";
    } catch {
      return fmt(value);
    }
  }

  function fmtCount(value) {
    const n = parseDecimalString(value);
    if (n === null) return fmt(value);
    try {
      return n.toLocaleString("es-ES", {
        maximumFractionDigits: 1,
      });
    } catch {
      return fmt(value);
    }
  }

  function fmtMonth(value) {
    return fmt(value);
  }

  function fmtMetric(key, value) {
    if (MONEY_METRIC_KEYS.has(key)) return fmtMoney(value);
    if (RATE_METRIC_KEYS.has(key)) return fmtRate(value);
    if (COUNT_METRIC_KEYS.has(key)) return fmtCount(value);
    if (MONTH_METRIC_KEYS.has(key)) return fmtMonth(value);
    return fmt(value);
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let body = null;
    const text = await res.text();
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }
    if (!res.ok) {
      const detail =
        typeof body === "object" && body && body.detail != null
          ? formatApiDetail(body.detail)
          : text || res.statusText;
      throw new Error(detail);
    }
    return body;
  }

  function twinSnapshot() {
    const revenues =
      state.draftRevenues.length > 0
        ? state.draftRevenues
        : [
            {
              id: "R0",
              name: "base",
              revenue_type: "recurring",
              start_year_month: "2027-01",
              base_monthly_revenue: "30000",
              gross_margin_pct: "0.4",
              collection_days: 0,
            },
          ];
    const costs =
      state.draftCosts.length > 0
        ? state.draftCosts
        : [
            {
              id: "C0",
              name: "opex",
              nature: "fixed",
              start_year_month: "2027-01",
              amount_monthly: "5000",
              payment_days: 0,
            },
          ];
    return {
      schema_version: "1.0",
      company: {
        currency: $("company_currency").value || "EUR",
        opening_cash: $("opening_cash").value,
        default_purchase_payment_days: 0,
      },
      fiscal: {
        vat_rate: $("vat_rate").value,
        vat_settlement: "monthly",
        vat_payment_lag_months: 0,
        corp_tax_rate: $("corp_tax_rate").value,
        corp_tax_payment_mode: "none",
      },
      policies: { min_cash: $("min_cash").value },
      revenue_streams: revenues,
      cost_items: costs,
    };
  }

  function renderStreamTables() {
    const revBody = $("rev-table") && $("rev-table").querySelector("tbody");
    const costBody = $("cost-table") && $("cost-table").querySelector("tbody");
    if (revBody) {
      revBody.innerHTML = "";
      state.draftRevenues.forEach((r, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = "";
        for (let i = 0; i < 5; i++) tr.appendChild(document.createElement("td"));
        const c = tr.children;
        c[0].textContent = r.id || "";
        c[1].textContent = r.name || "";
        c[2].textContent = r.base_monthly_revenue || "";
        c[3].textContent = r.gross_margin_pct || "";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "secondary";
        btn.textContent = "Quitar";
        btn.addEventListener("click", () => {
          state.draftRevenues.splice(idx, 1);
          renderStreamTables();
        });
        c[4].appendChild(btn);
        revBody.appendChild(tr);
      });
    }
    if (costBody) {
      costBody.innerHTML = "";
      state.draftCosts.forEach((r, idx) => {
        const tr = document.createElement("tr");
        for (let i = 0; i < 4; i++) tr.appendChild(document.createElement("td"));
        const c = tr.children;
        c[0].textContent = r.id || "";
        c[1].textContent = r.name || "";
        c[2].textContent = r.amount_monthly || "";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "secondary";
        btn.textContent = "Quitar";
        btn.addEventListener("click", () => {
          state.draftCosts.splice(idx, 1);
          renderStreamTables();
        });
        c[3].appendChild(btn);
        costBody.appendChild(tr);
      });
    }
  }

  function hydrateTwin(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return;
    const company = snapshot.company || {};
    const fiscal = snapshot.fiscal || {};
    const policies = snapshot.policies || {};
    if (company.currency != null) $("company_currency").value = String(company.currency);
    if (company.opening_cash != null) $("opening_cash").value = String(company.opening_cash);
    if (fiscal.vat_rate != null) $("vat_rate").value = String(fiscal.vat_rate);
    if (fiscal.corp_tax_rate != null) $("corp_tax_rate").value = String(fiscal.corp_tax_rate);
    if (policies.min_cash != null) $("min_cash").value = String(policies.min_cash);
    state.draftRevenues = Array.isArray(snapshot.revenue_streams)
      ? snapshot.revenue_streams.map((x) => ({ ...x }))
      : [];
    state.draftCosts = Array.isArray(snapshot.cost_items)
      ? snapshot.cost_items.map((x) => ({ ...x }))
      : [];
    renderStreamTables();
    updateTwinSummary();
  }

  function renderQuality(quality) {
    const list = $("twin_quality_list");
    const meta = $("twin_quality_meta");
    const badges = $("twin_quality_badges");
    if (badges) badges.innerHTML = "";
    if (!list) return;
    list.innerHTML = "";
    if (!quality) {
      list.innerHTML = "<li>Sin twin todavía.</li>";
      if (badges) {
        const b = document.createElement("span");
        b.className = "badge warn";
        b.textContent = "Sin twin";
        badges.appendChild(b);
      }
      return;
    }
    let okN = 0;
    let badN = 0;
    for (const c of quality.checks || []) {
      const li = document.createElement("li");
      li.className = c.ok ? "q-ok" : "q-bad";
      li.textContent = `${c.ok ? "OK" : "Falta"} — ${c.label}${c.detail ? ` (${c.detail})` : ""}`;
      list.appendChild(li);
      if (c.ok) okN += 1;
      else badN += 1;
    }
    if (badges) {
      const bOk = document.createElement("span");
      bOk.className = "badge";
      bOk.textContent = `${okN} OK`;
      badges.appendChild(bOk);
      if (badN) {
        const bBad = document.createElement("span");
        bBad.className = "badge warn";
        bBad.textContent = `${badN} pendiente${badN > 1 ? "s" : ""}`;
        badges.appendChild(bBad);
      }
      const ready = quality.ready_for_packs || {};
      const bLiq = document.createElement("span");
      bLiq.className = ready.liquidity_plan ? "badge" : "badge warn";
      bLiq.textContent = ready.liquidity_plan ? "Liquidez lista" : "Liquidez: faltan datos";
      badges.appendChild(bLiq);
    }
    if (meta) {
      const issues = (quality.summary && quality.summary.issues) || [];
      meta.textContent = issues.length
        ? `Pendiente: ${issues.join("; ")}`
        : "Twin completo para los checks básicos.";
    }
    const hq = $("home_quality");
    if (hq) {
      hq.hidden = false;
      hq.className = "home-quality badge-row";
      hq.innerHTML = "";
      const ready = quality.ready_for_packs || {};
      const b = document.createElement("span");
      b.className = ready.liquidity_plan ? "badge" : "badge warn";
      b.textContent = ready.liquidity_plan
        ? "Calidad: OK para liquidez y decisiones"
        : "Calidad: completa ingresos/costes para liquidez";
      hq.appendChild(b);
    }
  }

  async function refreshTwinQuality() {
    if (!state.companyId) {
      renderQuality(null);
      return;
    }
    const data = await api(`/companies/${state.companyId}/twin-quality`);
    renderQuality(data.quality);
  }

  async function refreshCompanySelect() {
    const sel = $("company_select");
    if (!sel) return;
    const data = await api("/companies");
    const cur = state.companyId || "";
    sel.innerHTML = '<option value="">— Seleccionar —</option>';
    for (const c of data.companies || []) {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    }
    if (cur) sel.value = cur;
  }

  async function refreshHome() {
    const sum = $("home_company_summary");
    const last = $("home_last_run");
    updateHomeGates();
    if (!state.companyId) {
      if (sum) sum.textContent = "";
      if (last) last.textContent = "";
      return;
    }
    if (sum) {
      sum.textContent = `${$("company_name").value || state.companyName}: caja ${fmtMoney(
        $("opening_cash").value
      )} · mínima ${fmtMoney($("min_cash").value)}`;
    }
    if (last) {
      last.textContent = state.lastRun
        ? `Último cálculo: ${packTitle(state.lastRun.pack_id)} · ${
            VARIANT_LABELS[state.lastRun.variant] || state.lastRun.variant
          }`
        : "Todavía no hay cálculo en esta sesión.";
    }
    try {
      await refreshTwinQuality();
    } catch {
      /* ignore */
    }
  }

  async function downloadExecutiveReport() {
    showError("");
    if (!state.companyId || !state.lastRun) {
      throw new Error("Calcula un escenario antes de descargar el informe");
    }
    showStatus("loading", "Preparando informe…");
    const res = await fetch(`/companies/${state.companyId}/reports/executive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run: state.lastRun,
        compare: state.lastCompare || null,
        company_name: $("company_name").value || state.companyName || "Empresa",
      }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "informe_finance_twin.html";
    a.click();
    URL.revokeObjectURL(url);
    showSuccess("Informe descargado (HTML).", null, null);
  }

  function syncForecastActualTable() {
    const tbody = $("forecast-actual-table") && $("forecast-actual-table").querySelector("tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    const host = $("actual_items");
    if (!host) return;
    const forecasts = host.querySelectorAll('input[data-role="forecast"]');
    for (const fEl of forecasts) {
      const key = fEl.dataset.key;
      const aEl = $(`actual_a_${key}`);
      const tr = document.createElement("tr");
      for (let i = 0; i < 3; i++) tr.appendChild(document.createElement("td"));
      tr.children[0].textContent = key;
      tr.children[1].textContent = fEl.value || "—";
      tr.children[2].textContent = (aEl && aEl.value) || "—";
      tbody.appendChild(tr);
    }
  }

  function fieldInputId(key) {
    return `pack_field_${key}`;
  }

  function updatePackHint(packId) {
    const def = PACK_FORMS[packId];
    const hint = $("pack_hint");
    if (hint && def) {
      hint.textContent = def.hint || def.title;
    }
  }

  function renderPackCards(liquidityOnly) {
    const host = $("pack_cards");
    if (!host) return;
    host.innerHTML = "";
    const current = $("pack_id").value;
    const ids = liquidityOnly
      ? ["liquidity_plan"]
      : CANONICAL_PACKS.filter((id) => id !== "liquidity_plan");
    for (const id of ids) {
      const def = PACK_FORMS[id];
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pack-card" + (id === current ? " selected" : "");
      btn.dataset.pack = id;
      const strong = document.createElement("strong");
      strong.textContent = def.title;
      const span = document.createElement("span");
      span.textContent = def.hint;
      btn.appendChild(strong);
      btn.appendChild(span);
      btn.addEventListener("click", () => {
        $("pack_id").value = id;
        localStorage.setItem(LS_PACK, id);
        clearReport();
        showError("");
        renderPackForm(id);
        renderPackCards(liquidityOnly);
        setCompanyUi();
      });
      host.appendChild(btn);
    }
  }

  function appendFieldControl(host, f) {
    const label = document.createElement("label");
    label.textContent = f.label + " ";
    let control;
    if (f.type === "enum") {
      control = document.createElement("select");
      for (const opt of f.options || []) {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = ENUM_LABELS[opt] || opt;
        if (opt === f.value) o.selected = true;
        control.appendChild(o);
      }
    } else {
      control = document.createElement("input");
      control.type = f.type === "count" ? "number" : "text";
      if (f.value != null && f.value !== "") control.value = String(f.value);
      if (f.type === "json") control.className = "json-field";
    }
    control.id = fieldInputId(f.key);
    control.dataset.key = f.key;
    control.dataset.type = f.type;
    label.appendChild(control);
    host.appendChild(label);
  }

  function renderPackForm(packId) {
    const def = PACK_FORMS[packId];
    if (!def) throw new Error(`pack desconocido: ${packId}`);
    if ($("pack_legend")) $("pack_legend").textContent = `Hipótesis — ${def.title}`;
    updatePackHint(packId);
    const host = $("pack_fields");
    const advHost = $("pack_fields_advanced");
    const advWrap = $("pack_advanced");
    host.innerHTML = "";
    if (advHost) advHost.innerHTML = "";
    const advanced = new Set(ADVANCED_KEYS[packId] || []);
    let hasAdv = false;
    for (const f of def.fields) {
      if (advanced.has(f.key) && advHost) {
        appendFieldControl(advHost, f);
        hasAdv = true;
      } else {
        appendFieldControl(host, f);
      }
    }
    if (advWrap) advWrap.hidden = !hasAdv;
  }

  function collectPackInputs(packId) {
    const def = PACK_FORMS[packId];
    const out = {};
    for (const f of def.fields) {
      const el = $(fieldInputId(f.key));
      if (!el) continue;
      const raw = el.value;
      if (raw === "" || raw == null) continue;
      if (f.type === "count") {
        const n = Number(raw);
        if (Number.isNaN(n)) throw new Error(`${f.label || f.key} debe ser un número`);
        out[f.key] = n;
      } else if (f.type === "json") {
        try {
          out[f.key] = JSON.parse(raw);
        } catch {
          throw new Error(`${f.label || f.key}: JSON inválido`);
        }
      } else {
        out[f.key] = raw;
      }
    }
    return out;
  }

  function metricCard(key, value) {
    const div = document.createElement("div");
    div.className = "metric" + (KEY_METRICS.has(key) ? " metric-key" : "");
    const k = document.createElement("div");
    k.className = "k";
    k.textContent = METRIC_LABELS[key] || key;
    const v = document.createElement("div");
    v.className = "v";
    v.textContent = fmtMetric(key, value);
    div.appendChild(k);
    div.appendChild(v);
    return div;
  }

  function policyCounts(run) {
    let pass = 0;
    let fail = 0;
    let skip = 0;
    let other = 0;
    for (const p of run.policy_checks || []) {
      if (p.status === "pass") pass += 1;
      else if (p.status === "fail") fail += 1;
      else if (p.status === "skip") skip += 1;
      else other += 1;
    }
    return { pass, fail, skip, other };
  }

  function renderCompare(byVariant) {
    const tbody = $("compare").querySelector("tbody");
    tbody.innerHTML = "";
    if (!byVariant) {
      $("compare_hint").textContent =
        "Pulsa «Comparar 3 escenarios» para ver base, conservador y adverso juntos.";
      return;
    }
    $("compare_hint").textContent =
      "Mismos indicadores en los tres escenarios (cada columna es un cálculo del motor).";
    for (const row of COMPARE_ROWS) {
      const tr = document.createElement("tr");
      for (let i = 0; i < 4; i++) tr.appendChild(document.createElement("td"));
      const cells = tr.children;
      cells[0].textContent = row.label;
      cells[1].textContent = fmtMetricPath(row.path, getPath(byVariant.base, row.path));
      cells[2].textContent = fmtMetricPath(row.path, getPath(byVariant.conservative, row.path));
      cells[3].textContent = fmtMetricPath(row.path, getPath(byVariant.adverse, row.path));
      tbody.appendChild(tr);
    }
  }

  function fmtMetricPath(path, value) {
    const key = path && path.length ? path[path.length - 1] : "";
    return fmtMetric(key, value);
  }

  function packTitle(packId) {
    return (PACK_FORMS[packId] && PACK_FORMS[packId].title) || packId;
  }

  function validatePackInputs(packId) {
    const def = PACK_FORMS[packId];
    if (!def) throw new Error("Tipo de decisión no reconocido");
    const problems = [];
    for (const f of def.fields) {
      const el = $(fieldInputId(f.key));
      if (!el) continue;
      const raw = el.value;
      if (raw === "" || raw == null) {
        if (f.type === "json" || f.type === "money" || f.type === "rate" || f.type === "count" || f.type === "text") {
          // optional empties for linked_capex etc. — only require if default was non-empty
          if (f.value != null && f.value !== "") {
            problems.push(`Falta: ${f.label}`);
          }
        }
        continue;
      }
      if (f.type === "count" && Number.isNaN(Number(raw))) {
        problems.push(`${f.label} debe ser un número`);
      }
      if (f.type === "money" || f.type === "rate") {
        if (Number.isNaN(Number(raw))) problems.push(`${f.label} no parece un número válido`);
      }
      if (f.type === "json") {
        try {
          JSON.parse(raw);
        } catch {
          problems.push(`${f.label}: el JSON no es válido`);
        }
      }
    }
    if (problems.length) {
      throw new Error(problems.slice(0, 3).join("\n"));
    }
  }

  function fillSensitivityTable(title, headers, rows) {
    const host = $("sensitivity_tables");
    if (!host) return;
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const h = document.createElement("h4");
    h.textContent = title;
    wrap.appendChild(h);
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    for (const htxt of headers) {
      const th = document.createElement("th");
      th.textContent = htxt;
      hr.appendChild(th);
    }
    thead.appendChild(hr);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    for (const cells of rows) {
      const tr = document.createElement("tr");
      for (const c of cells) {
        const td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    wrap.appendChild(table);
    host.appendChild(wrap);
  }

  /** Solo pinta campos presentes en la respuesta del motor. */
  function renderReport(run, compareByVariant) {
    state.lastRun = run;
    state.hasReport = true;
    if (compareByVariant !== undefined) {
      state.lastCompare = compareByVariant;
    }
    const sec = $("sec-report");
    sec.hidden = false;

    const packId = run.pack_id || $("pack_id").value;
    const variantLabel = VARIANT_LABELS[run.variant] || run.variant;
    if ($("report_title")) {
      $("report_title").textContent = `${packTitle(packId)} · escenario ${variantLabel}`;
    }
    if ($("report_meta")) {
      const cname = $("company_name").value || state.companyName || "Empresa";
      $("report_meta").textContent = `${cname} · cálculo ${run.calculation_run_id || "—"}`;
    }

    const im = run.investment_metrics || {};
    const fn = run.financing_need || {};

    const isLiquidity = packId === "liquidity_plan";
    const heroKey = isLiquidity ? "min_cash" : "npv";
    const heroVal = isLiquidity ? fn.min_cash : im.npv;
    if ($("hero_label")) {
      $("hero_label").textContent = isLiquidity
        ? "Caja más baja del periodo"
        : "Valor creado (VAN)";
      $("hero_label").title = isLiquidity
        ? "Mínimo de caja proyectado por el motor en el horizonte"
        : "Valor actual neto según el motor (no se calcula en la UI)";
    }
    if ($("hero_value")) $("hero_value").textContent = fmtMetric(heroKey, heroVal);

    const metrics = $("metrics");
    metrics.innerHTML = "";
    metrics.hidden = false;
    metrics.appendChild(metricCard("npv", im.npv));
    metrics.appendChild(metricCard("irr_annual", im.irr_annual));
    metrics.appendChild(metricCard("payback_simple", im.payback_simple));
    metrics.appendChild(metricCard("payback_discounted", im.payback_discounted));
    metrics.appendChild(metricCard("min_cash", fn.min_cash));
    metrics.appendChild(metricCard("min_cash_month", fn.min_cash_month));
    metrics.appendChild(metricCard("max_shortfall_vs_policy", fn.max_shortfall_vs_policy));
    metrics.appendChild(metricCard("first_shortfall_month", fn.first_shortfall_month));
    metrics.appendChild(metricCard("months_below_policy", fn.months_below_policy));

    const counts = policyCounts(run);
    const policyOk = counts.fail === 0;
    const policyEl = $("policy-summary");
    if (policyEl) {
      policyEl.classList.toggle("ok", policyOk);
      policyEl.classList.toggle("fail", !policyOk);
      policyEl.textContent = policyOk
        ? `Políticas: OK (${counts.pass} comprobaciones)`
        : `Atención: ${counts.fail} política(s) no se cumplen`;
    }
    if ($("report_reading")) {
      if (isLiquidity) {
        $("report_reading").textContent = policyOk
          ? `¿Aguanto? La caja más baja proyectada es ${fmtMoney(fn.min_cash)}` +
            (fn.min_cash_month ? ` (mes ${fmt(fn.min_cash_month)})` : "") +
            `. Políticas en orden.`
          : `Hay tensión de caja: ${counts.fail} política(s) en fallo. Caja más baja ${fmtMoney(fn.min_cash)}.`;
      } else {
        $("report_reading").textContent = policyOk
          ? `VAN ${fmtMoney(im.npv)} · caja más baja ${fmtMoney(fn.min_cash)} · políticas pasan.`
          : `VAN ${fmtMoney(im.npv)}, pero hay políticas en fallo. Revisa detalle o otro escenario.`;
      }
    }

    const banner = $("demo_banner");
    if (banner) {
      banner.hidden = !state.fromDemo;
    }

    const sensBlock = $("sensitivity-block");
    if (sensBlock) sensBlock.hidden = packId !== "new_site";
    const sensBtn = $("btn-sensitivity");
    if (sensBtn && packId !== "new_site") sensBtn.disabled = true;

    const compareBlock = $("detail-compare");
    if (compareBlock) {
      compareBlock.open = Boolean(state.lastCompare);
    }

    renderCompare(state.lastCompare);

    const tbody = $("policies").querySelector("tbody");
    tbody.innerHTML = "";
    for (const p of run.policy_checks || []) {
      const tr = document.createElement("tr");
      const status = p.status || "";
      for (let i = 0; i < 5; i++) tr.appendChild(document.createElement("td"));
      const cells = tr.children;
      cells[0].textContent = p.policy_id ?? "";
      cells[1].textContent = status;
      cells[1].className = `status-${status}`;
      cells[2].textContent = fmtMoney(p.value);
      cells[3].textContent = fmtMoney(p.threshold);
      cells[4].textContent = p.message ?? "";
      tbody.appendChild(tr);
    }

    const cashBody = $("cash").querySelector("tbody");
    cashBody.innerHTML = "";
    const rows = (run.results && run.results.cash_flow) || [];
    for (const row of rows) {
      const tr = document.createElement("tr");
      for (let i = 0; i < 7; i++) tr.appendChild(document.createElement("td"));
      const c = tr.children;
      c[0].textContent = String(row.t);
      c[1].textContent = fmtMoney(row.opening_cash);
      c[2].textContent = fmtMoney(row.closing_cash);
      c[3].textContent = fmtMoney(row.operating_cash_flow);
      c[4].textContent = fmtMoney(row.capex_paid);
      c[5].textContent = fmtMoney(row.loan_drawdowns);
      c[6].textContent = fmtMoney(row.net_cash_flow);
      cashBody.appendChild(tr);
    }

    $("trace").textContent = [
      `pack_id: ${packId}`,
      `calculation_run_id: ${run.calculation_run_id}`,
      `scenario_id: ${run.scenario_id}`,
      `model_version_id: ${run.model_version_id}`,
      `engine_version: ${run.engine_version}`,
      `variant: ${run.variant}`,
      `inputs_hash: ${run.inputs_hash}`,
      `result_hash: ${run.result_hash}`,
    ].join("\n");

    const warnParts = [];
    if (run.warnings && run.warnings.length) {
      warnParts.push(...run.warnings);
    }
    if (im.warnings && im.warnings.length) {
      warnParts.push(...im.warnings.map((w) => `metrics:${w}`));
    }
    $("warnings").textContent = warnParts.length
      ? "Avisos del motor:\n" + warnParts.join("\n")
      : "";

    $("run_meta").textContent = `Escenario ${variantLabel} listo`;
    setCompanyUi();
    updateNavReport();
    goToStep("report");
  }

  async function restoreSession() {
    const savedId = localStorage.getItem(LS_COMPANY);
    const savedName = localStorage.getItem(LS_NAME);
    const savedPack = localStorage.getItem(LS_PACK);
    if (savedName) $("company_name").value = savedName;
    if (savedPack && PACK_FORMS[savedPack]) {
      $("pack_id").value = savedPack;
    }
    renderPackForm($("pack_id").value);
    renderPackCards($("pack_id").value === "liquidity_plan");
    if (!savedId) {
      state.companyId = null;
      setCompanyUi();
      goToStep("home");
      return;
    }
    try {
      const cur = await api(`/companies/${savedId}/snapshot`);
      state.companyId = savedId;
      state.modelVersionId = cur.model_version_id;
      hydrateTwin(cur.snapshot);
      if (cur.quality) renderQuality(cur.quality);
      setCompanyUi();
      await refreshDecisions();
      goToStep("home");
    } catch {
      localStorage.removeItem(LS_COMPANY);
      state.companyId = null;
      state.modelVersionId = null;
      setCompanyUi();
      goToStep("home");
    }
  }

  async function createCompanyAndTwin() {
    showError("");
    hideStatus();
    clearReport();
    setBusy(true);
    showStatus("loading", "Guardando tu empresa…");
    try {
      const company = await api("/companies", {
        method: "POST",
        body: JSON.stringify({
          name: $("company_name").value,
          country: $("company_country").value,
          currency: $("company_currency").value,
        }),
      });
      state.companyId = company.id;
      state.companyName = company.name;
      localStorage.setItem(LS_COMPANY, company.id);
      localStorage.setItem(LS_NAME, company.name);
      const put = await api(`/companies/${state.companyId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ snapshot: twinSnapshot(), label: "ui-v1" }),
      });
      state.modelVersionId = put.model_version_id;
      hydrateTwin(twinSnapshot());
      await refreshCompanySelect();
      setCompanyUi();
      showSuccess(
        "Empresa y twin guardados.",
        "twin_next",
        "Siguiente: elige la decisión que quieres simular."
      );
      goToStep("decision");
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function loadDemo() {
    showError("");
    hideStatus();
    $("demo_meta").textContent = "";
    clearReport();
    state.fromDemo = true;
    $("company_name").value = "Demo Tienda SL";
    $("company_country").value = "ES";
    $("opening_cash").value = "120000";
    $("min_cash").value = "10000";
    $("vat_rate").value = "0";
    $("corp_tax_rate").value = "0";
    $("pack_id").value = "new_site";
    localStorage.setItem(LS_PACK, "new_site");
    renderPackForm("new_site");
    $("variant").value = "base";
    $("dec_title").value = "Apertura tienda demo";
    setBusy(true);
    showStatus("loading", "Preparando la demo…");
    try {
      const company = await api("/companies", {
        method: "POST",
        body: JSON.stringify({
          name: $("company_name").value,
          country: $("company_country").value,
          currency: $("company_currency").value,
        }),
      });
      state.companyId = company.id;
      state.companyName = company.name;
      localStorage.setItem(LS_COMPANY, company.id);
      localStorage.setItem(LS_NAME, company.name);
      const snap = twinSnapshot();
      const put = await api(`/companies/${state.companyId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ snapshot: snap, label: "demo-p8" }),
      });
      state.modelVersionId = put.model_version_id;
      hydrateTwin(snap);
      await refreshCompanySelect();
      showStatus("loading", "Calculando el escenario de la tienda…");
      const run = await postPackRun("new_site", collectPackInputs("new_site"), "base");
      state.fromDemo = true;
      renderReport(run, null);
      $("demo_meta").textContent = "Demo lista.";
      const banner = $("demo_banner");
      if (banner) {
        banner.hidden = false;
        if ($("demo_banner_text")) {
          $("demo_banner_text").textContent =
            "Aperturaste una tienda de ejemplo. Siguiente: registrar la decisión o ajustar hipótesis.";
        }
      }
      showSuccess("Demo lista: ya estás viendo el resultado.", null, null);
      setCompanyUi();
    } catch (e) {
      state.fromDemo = false;
      $("demo_meta").textContent = "";
      throw e;
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function saveTwin() {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    setBusy(true);
    showStatus("loading", "Actualizando el twin…");
    try {
      const put = await api(`/companies/${state.companyId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ snapshot: twinSnapshot(), label: "ui-edit" }),
      });
      state.modelVersionId = put.model_version_id;
      setCompanyUi();
      showSuccess("Twin actualizado.", "twin_next", "Puedes continuar a la decisión.");
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function importTwinCsv() {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const input = $("import_file");
    const file = input.files && input.files[0];
    if (!file) throw new Error("Selecciona un archivo CSV");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const label = $("import_label").value;
      if (label) form.append("label", label);
      const res = await fetch(`/companies/${state.companyId}/imports/twin-csv`, {
        method: "POST",
        body: form,
      });
      const text = await res.text();
      let body = null;
      if (text) {
        try {
          body = JSON.parse(text);
        } catch {
          body = text;
        }
      }
      if (!res.ok) {
        const detail =
          typeof body === "object" && body && body.detail != null
            ? formatApiDetail(body.detail)
            : text || res.statusText;
        $("import_out").textContent = detail;
        throw new Error(detail);
      }
      state.modelVersionId = body.model_version_id;
      hydrateTwin(body.snapshot);
      clearReport();
      $("import_meta").textContent =
        `Importación OK · versión twin=${body.model_version_id}` +
        (body.source_filename ? ` · archivo=${body.source_filename}` : "");
      $("import_out").textContent = JSON.stringify(
        {
          model_version_id: body.model_version_id,
          company: body.snapshot && body.snapshot.company,
          policies: body.snapshot && body.snapshot.policies,
          revenue_streams: (body.snapshot && body.snapshot.revenue_streams) || [],
          cost_items: (body.snapshot && body.snapshot.cost_items) || [],
        },
        null,
        2
      );
      setCompanyUi();
      goToStep("decision");
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function postPackRun(packId, inputs, variant) {
    return api(`/companies/${state.companyId}/packs/${packId}/run`, {
      method: "POST",
      body: JSON.stringify({ inputs, variant }),
    });
  }

  async function runPack() {
    showError("");
    hideStatus();
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const packId = $("pack_id").value;
    if (!PACK_FORMS[packId]) throw new Error(`pack no soportado: ${packId}`);
    validatePackInputs(packId);
    setBusy(true);
    showStatus("loading", "Calculando tu escenario…");
    try {
      const run = await postPackRun(packId, collectPackInputs(packId), $("variant").value);
      renderReport(run, null);
      showSuccess(
        "Cálculo listo.",
        "decision_next",
        "Siguiente: compara los 3 escenarios o registra la decisión."
      );
    } catch (e) {
      clearReport();
      throw e;
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  /** Tres llamadas API independientes; JS solo muestra, no agrega cifras. */
  async function compareVariants() {
    showError("");
    hideStatus();
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const packId = $("pack_id").value;
    if (!PACK_FORMS[packId]) throw new Error(`pack no soportado: ${packId}`);
    validatePackInputs(packId);
    const inputs = collectPackInputs(packId);
    setBusy(true);
    showStatus("loading", "Comparando los 3 escenarios…");
    try {
      const byVariant = {};
      for (const variant of VARIANTS) {
        byVariant[variant] = await postPackRun(packId, inputs, variant);
      }
      const detailVariant = $("variant").value;
      const detail = byVariant[detailVariant] || byVariant.base;
      renderReport(detail, byVariant);
      showSuccess("Comparación lista. Mira la tabla de escenarios.", null, null);
    } catch (e) {
      clearReport();
      throw e;
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  function list(xs) {
    return Array.isArray(xs) ? xs.slice() : [];
  }

  function renderActualFields(keys) {
    const host = $("actual_items");
    host.innerHTML = "";
    const packInputs = (() => {
      try {
        return collectPackInputs($("pack_id").value);
      } catch {
        return {};
      }
    })();
    // Defaults de forecast solo copian inputs del formulario (no calculados).
    const forecastHints = {
      sales_monthly: packInputs.sales_run_rate,
      gross_margin_pct: packInputs.gross_margin_pct,
      capex_total: packInputs.capex_total,
      rent_monthly: packInputs.rent_monthly,
      headcount: packInputs.headcount != null ? String(packInputs.headcount) : "",
      min_cash: $("min_cash").value,
    };
    for (const key of keys) {
      const wrap = document.createElement("div");
      wrap.className = "actual-key";
      const nice = VARIABLE_LABELS[key] || key;
      const labF = document.createElement("label");
      labF.textContent = `${nice} previsto `;
      const inF = document.createElement("input");
      inF.id = `actual_f_${key}`;
      inF.dataset.key = key;
      inF.dataset.role = "forecast";
      if (forecastHints[key] != null && forecastHints[key] !== "") {
        inF.value = String(forecastHints[key]);
      }
      labF.appendChild(inF);
      const labA = document.createElement("label");
      labA.textContent = `${nice} real `;
      const inA = document.createElement("input");
      inA.id = `actual_a_${key}`;
      inA.dataset.key = key;
      inA.dataset.role = "actual";
      labA.appendChild(inA);
      wrap.appendChild(labF);
      wrap.appendChild(labA);
      host.appendChild(wrap);
    }
    syncForecastActualTable();
  }

  function collectActualItems() {
    const items = [];
    const host = $("actual_items");
    const forecasts = host.querySelectorAll('input[data-role="forecast"]');
    for (const fEl of forecasts) {
      const key = fEl.dataset.key;
      const aEl = $(`actual_a_${key}`);
      const forecast = fEl.value;
      const actual = aEl ? aEl.value : "";
      if (!forecast || !actual) continue;
      items.push({
        variable_key: key,
        forecast_value: forecast,
        actual_value: actual,
        source: "manual",
      });
    }
    return items;
  }

  async function registerDecision() {
    showError("");
    hideStatus();
    if (!state.companyId) throw new Error("Crea una empresa primero");
    if (!state.lastRun) throw new Error("Calcula un escenario antes de registrar");
    setBusy(true);
    showStatus("loading", "Registrando la decisión…");
    try {
      const body = {
        title: $("dec_title").value,
        decision_pack_id: state.lastRun.pack_id || $("pack_id").value,
        decision_date: $("dec_date").value,
        calculation_run_id: state.lastRun.calculation_run_id,
        status: $("dec_status").value,
        rationale: $("dec_rationale").value,
        owner_user_id: "local",
      };
      const dec = await api(`/companies/${state.companyId}/decisions`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      state.selectedDecisionId = dec.id;
      $("decision_meta").textContent =
        `Decisión #${dec.number} guardada · ${dec.status}`;
      await refreshDecisions();
      $("actual_decision_id").value = dec.id;
      const keys = list(state.lastRun.actual_keys);
      renderActualFields(keys.length ? keys : ["sales_monthly", "min_cash"]);
      const actuals = $("actuals-block");
      if (actuals) actuals.open = true;
      setFollowStep(2);
      showSuccess(
        "Decisión registrada.",
        "follow_next",
        "Siguiente: anota lo que ocurrió de verdad."
      );
      goToStep("followup");
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function refreshDecisions() {
    if (!state.companyId) return;
    const data = await api(`/companies/${state.companyId}/decisions`);
    const tbody = $("decisions-table").querySelector("tbody");
    tbody.innerHTML = "";
    const select = $("actual_decision_id");
    const prev = state.selectedDecisionId || select.value;
    select.innerHTML = "";
    const rows = data.decisions || [];
    const empty = $("decisions_empty");
    if (empty) empty.hidden = rows.length > 0;
    for (const d of rows) {
      const tr = document.createElement("tr");
      if (d.id === state.selectedDecisionId) tr.className = "selected-row";
      for (let i = 0; i < 7; i++) tr.appendChild(document.createElement("td"));
      const c = tr.children;
      c[0].textContent = String(d.number);
      c[1].textContent = d.title || "";
      c[2].textContent = d.decision_pack_id || "";
      c[3].textContent = d.status || "";
      c[4].textContent = d.decision_date || "";
      c[5].textContent = String(d.actual_results_count ?? "");
      c[6].textContent = d.id;
      tr.style.cursor = "pointer";
      tr.addEventListener("click", () => {
        selectDecision(d.id, d.decision_pack_id, d.status).catch(showCaught);
      });
      tbody.appendChild(tr);

      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = `#${d.number} ${d.title} (${d.status})`;
      select.appendChild(opt);
    }
    if (prev) select.value = prev;
  }

  async function selectDecision(decisionId, packId, status) {
    state.selectedDecisionId = decisionId;
    $("actual_decision_id").value = decisionId;
    $("decision_meta").textContent =
      `Decisión seleccionada` +
      (packId ? ` · ${packTitle(packId)}` : "") +
      (status ? ` · ${status}` : "");
    const detail = await api(`/decisions/${decisionId}`);
    const keys =
      (state.lastRun &&
        state.lastRun.pack_id === detail.decision_pack_id &&
        state.lastRun.actual_keys) ||
      (detail.actual_results || []).map((a) => a.variable_key);
    const uniq = [...new Set(keys.length ? keys : ["sales_monthly", "min_cash"])];
    renderActualFields(uniq);
    const empty = $("actuals_empty");
    if (empty) empty.hidden = true;
    setFollowStep(2);
    await refreshDecisions();
    setCompanyUi();
  }

  async function markExecuted() {
    showError("");
    if (!state.selectedDecisionId) throw new Error("Selecciona una decisión");
    setBusy(true);
    try {
      const dec = await api(`/decisions/${state.selectedDecisionId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "executed" }),
      });
      $("decision_meta").textContent = `Decisión marcada como ${dec.status}`;
      await refreshDecisions();
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function recordActuals() {
    showError("");
    const decisionId = $("actual_decision_id").value || state.selectedDecisionId;
    if (!decisionId) throw new Error("Selecciona una decisión");
    const items = collectActualItems();
    if (!items.length) throw new Error("Rellena al menos un par previsto/real");
    setBusy(true);
    try {
      const out = await api(`/decisions/${decisionId}/actuals`, {
        method: "POST",
        body: JSON.stringify({
          period_year_month: $("actual_period").value,
          items,
          source: "manual",
        }),
      });
      $("actuals_out").textContent = JSON.stringify(
        {
          recorded: out.recorded,
          warnings: out.warnings,
          status: out.decision && out.decision.status,
        },
        null,
        2
      );
      state.selectedDecisionId = decisionId;
      await refreshDecisions();
      await loadBiasProfiles({ manageBusy: false });
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function loadBiasProfiles(opts) {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const packId = $("pack_id").value;
    const manageBusy = !opts || opts.manageBusy !== false;
    if (manageBusy) setBusy(true);
    try {
      const data = await api(
        `/companies/${state.companyId}/packs/${packId}/bias-profiles`
      );
      const tbody = $("bias-table").querySelector("tbody");
      tbody.innerHTML = "";
      const profiles = data.profiles || [];
      for (const p of profiles) {
        const tr = document.createElement("tr");
        for (let i = 0; i < 5; i++) tr.appendChild(document.createElement("td"));
        const c = tr.children;
        c[0].textContent = VARIABLE_LABELS[p.variable_key] || p.variable_key || "";
        c[1].textContent = String(p.n_observations ?? "");
        c[2].textContent = fmt(p.median_bias);
        c[3].textContent = p.direction ?? "";
        c[4].textContent = p.confidence ?? "";
        tbody.appendChild(tr);
      }
      const ready = profiles.some((p) => Number(p.n_observations) >= 3);
      $("bias_meta").textContent = ready
        ? `${profiles.length} perfiles · hay datos suficientes para ofrecer calibración`
        : `${profiles.length} perfiles · hacen falta al menos 3 datos reales por variable`;
    } finally {
      if (manageBusy) {
        setBusy(false);
        setCompanyUi();
      }
    }
  }

  async function previewCalibration() {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const packId = $("pack_id").value;
    const inputs = collectPackInputs(packId);
    setBusy(true);
    try {
      const out = await api(
        `/companies/${state.companyId}/packs/${packId}/calibration/preview`,
        { method: "POST", body: JSON.stringify({ inputs }) }
      );
      state.lastCalib = out.offered ? out.calibrated_inputs : null;
      $("calib_out").textContent = JSON.stringify(out, null, 2);
      const applyBtn = $("btn-apply-calib");
      if (out.offered === true && out.calibrated_inputs) {
        applyBtn.hidden = false;
        applyBtn.disabled = false;
      } else {
        applyBtn.hidden = true;
        applyBtn.disabled = true;
        state.lastCalib = null;
      }
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  function applyCalibratedInputs() {
    showError("");
    if (!state.lastCalib) throw new Error("No hay inputs calibrados (la API no ofreció calibración)");
    const packId = $("pack_id").value;
    for (const [key, value] of Object.entries(state.lastCalib)) {
      const el = $(fieldInputId(key));
      if (el) el.value = String(value);
    }
    $("run_meta").textContent =
      `Inputs calibrados aplicados (${packId}); vuelve a calcular para ver el impacto del motor`;
    goToStep("decision");
  }

  async function runSensitivity() {
    showError("");
    hideStatus();
    if (!state.companyId) throw new Error("Crea una empresa primero");
    const packId = $("pack_id").value;
    validatePackInputs(packId);
    const inputs = collectPackInputs(packId);
    setBusy(true);
    showStatus("loading", "Calculando sensibilidad…");
    try {
      const out = await api(
        `/companies/${state.companyId}/packs/${packId}/sensitivity`,
        {
          method: "POST",
          body: JSON.stringify({
            inputs,
            variant: $("variant").value,
            include: ["direct", "inverse", "stress"],
          }),
        }
      );
      const host = $("sensitivity_tables");
      if (host) host.innerHTML = "";
      if ($("sensitivity_hint")) {
        $("sensitivity_hint").textContent =
          "Resultados del motor: cambios directos, umbrales («qué tendría que pasar») y estrés.";
      }
      if (out.direct) {
        const rows = [];
        if (out.direct.base) {
          rows.push([
            "Base",
            "—",
            "—",
            fmt(out.direct.base.npv),
            fmt(out.direct.base.min_cash),
          ]);
        }
        for (const r of out.direct.rows || []) {
          if (r.skipped) {
            rows.push([r.variable || "—", "omitida", r.reason || "—", "—", "—"]);
          } else {
            rows.push([
              r.variable || "—",
              fmt(r.delta_pct),
              fmt(r.trial_value),
              fmt(r.metrics && r.metrics.npv),
              fmt(r.metrics && r.metrics.min_cash),
            ]);
          }
        }
        fillSensitivityTable(
          "Cambios directos (±%)",
          ["Variable", "Cambio", "Valor usado", "VAN", "Caja más baja"],
          rows
        );
      }
      if (out.inverse) {
        const rows = [];
        for (const r of out.inverse.rows || []) {
          if (r.found) {
            rows.push([
              r.metric || "—",
              fmt(r.threshold),
              r.variable || "—",
              fmt(r.value),
              fmt(r.metric_at_value),
            ]);
          } else {
            rows.push([
              r.metric || "—",
              fmt(r.threshold),
              r.variable || "—",
              "no encontrado",
              r.reason || "—",
            ]);
          }
        }
        fillSensitivityTable(
          "¿Qué tendría que pasar?",
          ["Objetivo", "Umbral", "Variable", "Valor hallado", "Métrica resultante"],
          rows
        );
      }
      if (out.stress) {
        const rows = [];
        for (const r of out.stress.rows || []) {
          if (r.skipped) {
            rows.push([r.stress || "—", "omitido", r.reason || "—", "—"]);
          } else {
            rows.push([
              r.stress || "—",
              fmt(r.metrics && r.metrics.npv),
              fmt(r.metrics && r.metrics.min_cash),
              "ok",
            ]);
          }
        }
        fillSensitivityTable(
          "Pruebas de estrés",
          ["Escenario", "VAN", "Caja más baja", "Estado"],
          rows
        );
      }
      $("sensitivity_out").hidden = true;
      const wrap = $("sensitivity_json_wrap");
      const sj = $("sensitivity_json");
      if (wrap && sj) {
        wrap.hidden = false;
        sj.textContent = JSON.stringify(out, null, 2);
      }
      showSuccess("Sensibilidad lista.", null, null);
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  function printReport() {
    if (!state.hasReport) {
      showError("Calcula un escenario antes de imprimir.");
      return;
    }
    goToStep("report");
    window.print();
  }

  document.querySelectorAll("[data-goto]").forEach((el) => {
    el.addEventListener("click", () => {
      showError("");
      const dest = el.getAttribute("data-goto");
      if (
        el.classList.contains("job-disabled") &&
        ["decision", "liquidity", "followup"].includes(dest)
      ) {
        showError("Primero crea una empresa o carga la demo.");
        return;
      }
      goToStep(dest);
    });
  });

  $("pack_id").addEventListener("change", () => {
    const packId = $("pack_id").value;
    localStorage.setItem(LS_PACK, packId);
    clearReport();
    showError("");
    renderPackForm(packId);
    renderPackCards(packId === "liquidity_plan" || state.liquidityMode);
    setCompanyUi();
  });

  $("variant").addEventListener("change", () => {
    if (!state.lastCompare) return;
    const detail =
      state.lastCompare[$("variant").value] || state.lastCompare.base;
    if (detail) renderReport(detail, state.lastCompare);
  });

  function wireWizard() {
    if ($("wiz-next-1")) {
      $("wiz-next-1").addEventListener("click", () => {
        if (!$("pack_id").value) {
          showError("Elige un tipo de decisión.");
          return;
        }
        showError("");
        setWizardStep(2);
      });
    }
    if ($("wiz-next-2")) {
      $("wiz-next-2").addEventListener("click", () => {
        try {
          validatePackInputs($("pack_id").value);
          showError("");
          setWizardStep(3);
        } catch (e) {
          showCaught(e);
        }
      });
    }
    if ($("wiz-back-2")) {
      $("wiz-back-2").addEventListener("click", () => {
        if (state.liquidityMode) return;
        setWizardStep(1);
      });
    }
    if ($("wiz-back-3")) {
      $("wiz-back-3").addEventListener("click", () => setWizardStep(2));
    }
    document.querySelectorAll(".wiz-step").forEach((btn) => {
      btn.addEventListener("click", () => {
        const n = Number(btn.getAttribute("data-wiz"));
        if (state.liquidityMode && n === 1) return;
        if (n >= 1 && n <= 3) setWizardStep(n);
      });
    });
  }
  wireWizard();

  $("btn-demo").addEventListener("click", () => {
    loadDemo().catch(showCaught);
  });
  $("btn-create").addEventListener("click", () => {
    createCompanyAndTwin().catch(showCaught);
  });
  if ($("btn-create-top")) {
    $("btn-create-top").addEventListener("click", () => {
      showError("");
      goToStep("twin");
    });
  }
  if ($("btn-create-home")) {
    $("btn-create-home").addEventListener("click", () => {
      showError("");
      goToStep("twin");
    });
  }
  $("btn-save-twin").addEventListener("click", () => {
    saveTwin().catch(showCaught);
  });
  $("btn-import-csv").addEventListener("click", () => {
    importTwinCsv().catch(showCaught);
  });
  $("btn-run").addEventListener("click", () => {
    runPack().catch(showCaught);
  });
  $("btn-compare").addEventListener("click", () => {
    compareVariants().catch(showCaught);
  });
  if ($("btn-compare-report")) {
    $("btn-compare-report").addEventListener("click", () => {
      compareVariants().catch(showCaught);
    });
  }
  $("btn-sensitivity").addEventListener("click", () => {
    runSensitivity().catch(showCaught);
  });
  if ($("btn-print")) {
    $("btn-print").addEventListener("click", () => {
      try {
        printReport();
      } catch (e) {
        showCaught(e);
      }
    });
  }
  if ($("btn-download-report")) {
    $("btn-download-report").addEventListener("click", () => {
      downloadExecutiveReport().catch(showCaught);
    });
  }
  if ($("btn-add-rev")) {
    $("btn-add-rev").addEventListener("click", () => {
      const n = state.draftRevenues.length + 1;
      state.draftRevenues.push({
        id: `R${n}`,
        name: `ingreso ${n}`,
        revenue_type: "recurring",
        start_year_month: "2027-01",
        base_monthly_revenue: "10000",
        gross_margin_pct: "0.4",
        collection_days: 0,
      });
      renderStreamTables();
    });
  }
  if ($("btn-add-cost")) {
    $("btn-add-cost").addEventListener("click", () => {
      const n = state.draftCosts.length + 1;
      state.draftCosts.push({
        id: `C${n}`,
        name: `coste ${n}`,
        nature: "fixed",
        start_year_month: "2027-01",
        amount_monthly: "2000",
        payment_days: 0,
      });
      renderStreamTables();
    });
  }
  if ($("home-btn-liquidity")) {
    $("home-btn-liquidity").addEventListener("click", () => {
      if (!state.companyId) {
        showError("Primero crea una empresa o carga la demo.");
        return;
      }
      goToStep("liquidity");
    });
  }
  if ($("btn-demo-home")) {
    $("btn-demo-home").addEventListener("click", () => loadDemo().catch(showCaught));
  }
  if ($("company_select")) {
    $("company_select").addEventListener("change", () => {
      const id = $("company_select").value;
      if (!id) {
        state.companyId = null;
        state.modelVersionId = null;
        localStorage.removeItem(LS_COMPANY);
        clearReport();
        setCompanyUi();
        goToStep("home");
        return;
      }
      localStorage.setItem(LS_COMPANY, id);
      state.companyId = id;
      restoreSession().catch(showCaught);
    });
  }
  $("btn-register-decision").addEventListener("click", () => {
    registerDecision().catch(showCaught);
  });
  $("btn-refresh-decisions").addEventListener("click", () => {
    refreshDecisions().catch(showCaught);
  });
  $("btn-mark-executed").addEventListener("click", () => {
    markExecuted().catch(showCaught);
  });
  $("btn-record-actuals").addEventListener("click", () => {
    recordActuals()
      .then(() => {
        setFollowStep(3);
        showSuccess("Valores reales guardados. Puedes mirar los sesgos.", null, null);
      })
      .catch(showCaught);
  });
  $("btn-load-bias").addEventListener("click", () => {
    loadBiasProfiles().catch(showCaught);
  });
  $("btn-calib-preview").addEventListener("click", () => {
    previewCalibration().catch(showCaught);
  });
  $("btn-apply-calib").addEventListener("click", () => {
    try {
      applyCalibratedInputs();
    } catch (e) {
      showCaught(e);
    }
  });
  $("actual_decision_id").addEventListener("change", () => {
    const id = $("actual_decision_id").value;
    if (!id) return;
    selectDecision(id).catch(showCaught);
  });

  window.__FT_PACKS__ = CANONICAL_PACKS;
  window.__FT_REPORT_FIELDS__ = REPORT_FIELDS;

  setCompanyUi();
  renderStreamTables();
  renderPackCards(false);
  goToStep("home");
  refreshCompanySelect().catch(() => {});
  restoreSession()
    .then(() => refreshCompanySelect())
    .catch(() => {
      state.companyId = null;
      renderPackForm($("pack_id").value || "new_site");
      setCompanyUi();
      goToStep("home");
    });
})();
