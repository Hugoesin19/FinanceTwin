/**
 * F6 Decision Studio — UI mínima.
 * Regla: ningún número financiero se calcula aquí; solo se muestra lo que
 * devuelve la API (CalculationRun / motor).
 */
(function () {
  const LS_COMPANY = "ft_company_id";
  const LS_NAME = "ft_company_name";

  const state = {
    companyId: null,
    modelVersionId: null,
    lastRun: null,
    busy: false,
  };

  const $ = (id) => document.getElementById(id);

  function showError(msg) {
    const el = $("error");
    el.hidden = !msg;
    el.textContent = msg || "";
  }

  function setBusy(busy) {
    state.busy = busy;
    $("btn-create").disabled = busy;
    $("btn-save-twin").disabled = busy || !state.companyId;
    $("btn-run").disabled = busy || !state.companyId;
  }

  function setCompanyUi() {
    const ready = Boolean(state.companyId);
    if (!state.busy) {
      $("btn-save-twin").disabled = !ready;
      $("btn-run").disabled = !ready;
    }
    $("company_meta").textContent = ready
      ? `company_id=${state.companyId}` +
        (state.modelVersionId ? ` · model_version_id=${state.modelVersionId}` : "")
      : "Sin empresa aún. Pulsa «Crear empresa + guardar twin».";
  }

  function clearReport() {
    state.lastRun = null;
    $("sec-report").hidden = true;
    $("run_meta").textContent = "";
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
        typeof body === "object" && body && body.detail
          ? typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail, null, 2)
          : text || res.statusText;
      throw new Error(detail);
    }
    return body;
  }

  function twinSnapshot() {
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
    };
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
  }

  function packInputs() {
    const headcount = Number($("headcount").value);
    const loanTerm = Number($("loan_term_months").value);
    const horizon = Number($("horizon_months").value);
    if (Number.isNaN(headcount) || Number.isNaN(loanTerm) || Number.isNaN(horizon)) {
      throw new Error("headcount, loan_term_months y horizon_months deben ser números");
    }
    return {
      site_name: $("site_name").value,
      open_year_month: $("open_year_month").value,
      capex_total: $("capex_total").value,
      sales_run_rate: $("sales_run_rate").value,
      gross_margin_pct: $("gross_margin_pct").value,
      rent_monthly: $("rent_monthly").value,
      other_opex_monthly: $("other_opex_monthly").value,
      headcount,
      employer_cost_per_person: $("employer_cost_per_person").value,
      debt_amount: $("debt_amount").value,
      equity_amount: $("equity_amount").value,
      loan_term_months: loanTerm,
      loan_annual_rate: $("loan_annual_rate").value,
      horizon_months: horizon,
      discount_rate_annual: $("discount_rate_annual").value,
      collection_days: 0,
    };
  }

  function metricCard(label, value) {
    const div = document.createElement("div");
    div.className = "metric";
    const k = document.createElement("div");
    k.className = "k";
    k.textContent = label;
    const v = document.createElement("div");
    v.className = "v";
    v.textContent = value === null || value === undefined ? "—" : String(value);
    div.appendChild(k);
    div.appendChild(v);
    return div;
  }

  /** Solo pinta campos presentes en la respuesta del motor. */
  function renderReport(run) {
    state.lastRun = run;
    const sec = $("sec-report");
    sec.hidden = false;

    const metrics = $("metrics");
    metrics.innerHTML = "";
    const im = run.investment_metrics || {};
    const fn = run.financing_need || {};
    metrics.appendChild(metricCard("VAN (npv)", im.npv));
    metrics.appendChild(metricCard("TIR anual (irr_annual)", im.irr_annual));
    metrics.appendChild(metricCard("Payback simple", im.payback_simple));
    metrics.appendChild(metricCard("Payback descontado", im.payback_discounted));
    metrics.appendChild(metricCard("Caja mínima (min_cash)", fn.min_cash));
    metrics.appendChild(metricCard("Mes caja mínima", fn.min_cash_month));
    metrics.appendChild(
      metricCard("Max shortfall vs política", fn.max_shortfall_vs_policy)
    );
    metrics.appendChild(metricCard("Primer mes shortfall", fn.first_shortfall_month));
    metrics.appendChild(metricCard("Meses bajo política", fn.months_below_policy));

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
      cells[2].textContent =
        p.value === null || p.value === undefined ? "—" : String(p.value);
      cells[3].textContent =
        p.threshold === null || p.threshold === undefined
          ? "—"
          : String(p.threshold);
      cells[4].textContent = p.message ?? "";
      tbody.appendChild(tr);
    }

    const cashBody = $("cash").querySelector("tbody");
    cashBody.innerHTML = "";
    const rows = (run.results && run.results.cash_flow) || [];
    for (const row of rows) {
      const tr = document.createElement("tr");
      for (let i = 0; i < 6; i++) tr.appendChild(document.createElement("td"));
      const c = tr.children;
      c[0].textContent = String(row.t);
      c[1].textContent = row.opening_cash ?? "";
      c[2].textContent = row.closing_cash ?? "";
      c[3].textContent = row.capex_paid ?? "";
      c[4].textContent = row.loan_drawdowns ?? "";
      c[5].textContent = row.net_cash_flow ?? "";
      cashBody.appendChild(tr);
    }

    $("trace").textContent = [
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
      ? "Warnings:\n" + warnParts.join("\n")
      : "";

    $("run_meta").textContent = `run=${run.calculation_run_id}`;
  }

  async function restoreSession() {
    const savedId = localStorage.getItem(LS_COMPANY);
    const savedName = localStorage.getItem(LS_NAME);
    if (savedName) $("company_name").value = savedName;
    if (!savedId) {
      state.companyId = null;
      setCompanyUi();
      return;
    }
    try {
      const cur = await api(`/companies/${savedId}/snapshot`);
      state.companyId = savedId;
      state.modelVersionId = cur.model_version_id;
      hydrateTwin(cur.snapshot);
      setCompanyUi();
    } catch {
      localStorage.removeItem(LS_COMPANY);
      state.companyId = null;
      state.modelVersionId = null;
      setCompanyUi();
    }
  }

  async function createCompanyAndTwin() {
    showError("");
    clearReport();
    setBusy(true);
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
      localStorage.setItem(LS_COMPANY, company.id);
      localStorage.setItem(LS_NAME, company.name);
      const put = await api(`/companies/${state.companyId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ snapshot: twinSnapshot(), label: "ui-v1" }),
      });
      state.modelVersionId = put.model_version_id;
      setCompanyUi();
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function saveTwin() {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    setBusy(true);
    try {
      const put = await api(`/companies/${state.companyId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ snapshot: twinSnapshot(), label: "ui-edit" }),
      });
      state.modelVersionId = put.model_version_id;
      setCompanyUi();
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  async function runPack() {
    showError("");
    if (!state.companyId) throw new Error("Crea una empresa primero");
    setBusy(true);
    try {
      const run = await api(`/companies/${state.companyId}/packs/new_site/run`, {
        method: "POST",
        body: JSON.stringify({
          inputs: packInputs(),
          variant: $("variant").value,
        }),
      });
      renderReport(run);
    } catch (e) {
      clearReport();
      throw e;
    } finally {
      setBusy(false);
      setCompanyUi();
    }
  }

  $("btn-create").addEventListener("click", () => {
    createCompanyAndTwin().catch((e) => showError(String(e.message || e)));
  });
  $("btn-save-twin").addEventListener("click", () => {
    saveTwin().catch((e) => showError(String(e.message || e)));
  });
  $("btn-run").addEventListener("click", () => {
    runPack().catch((e) => showError(String(e.message || e)));
  });

  setCompanyUi();
  restoreSession().catch(() => {
    state.companyId = null;
    setCompanyUi();
  });
})();
