/* Renders demo/data.js (window.RECON_DEMO), produced by `python -m invoice_recon demo`. No network access. */
(function () {
  "use strict";
  var data = window.RECON_DEMO;
  var STATUS_TONE = {
    MATCHED: "good", AMOUNT_MISMATCH: "bad", CURRENCY_MISMATCH: "bad", AMBIGUOUS: "warn",
    ONLY_IN_INVOICES: "warn", ONLY_IN_LEDGER: "warn", DUPLICATE: "", INVALID_RECORD: "bad"
  };
  var DECISION_TONE = { MATCHED: "good", AMOUNT_MISMATCH: "bad", CURRENCY_MISMATCH: "bad", NOT_DECIDED_MULTIPLE_CANDIDATES: "warn" };

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") { node.textContent = attrs[key]; } else { node.setAttribute(key, attrs[key]); }
    });
    (children || []).forEach(function (child) { if (child) { node.appendChild(child); } });
    return node;
  }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function pct(rate) { return (Number(rate) * 100).toFixed(1) + "%"; }
  function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } return node; }
  function table(target, headers, rows) {
    clear(target);
    var head = el("tr", {}, headers.map(function (h) { return el("th", { text: h[0], class: h[1] || "" }); }));
    target.appendChild(el("thead", {}, [head]));
    target.appendChild(el("tbody", {}, rows.map(function (cells) {
      return el("tr", {}, cells.map(function (c, i) {
        return c instanceof Node ? el("td", { class: headers[i][1] || "" }, [c]) : el("td", { text: c === null || c === undefined ? "" : String(c), class: headers[i][1] || "" });
      }));
    })));
  }

  if (!data) {
    document.getElementById("source-note").textContent =
      "demo/data.js is missing. Run `python -m invoice_recon run --generate` and `python -m invoice_recon demo`.";
    return;
  }

  document.getElementById("source-note").textContent = data.source;
  var badges = document.getElementById("badges");
  badges.appendChild(el("span", { class: "badge " + (data.all_checks_passed ? "good" : "bad"),
    text: data.all_checks_passed ? "All validation checks passed" : "Validation checks FAILED" }));
  Object.keys(data.versions).sort().forEach(function (name) {
    badges.appendChild(el("span", { class: "badge", text: name + " " + data.versions[name] }));
  });
  badges.appendChild(el("span", { class: "badge", text: "Fabric execution: not tested" }));

  function renderBatch(batch) {
    var m = batch.metrics;
    var kpis = clear(document.getElementById("kpis"));
    [
      ["Invoice records", fmt(m.invoice_records), "period " + batch.reconciliation_period],
      ["Ledger records", fmt(m.ledger_records), "ERP export lines"],
      ["Matched pairs", fmt(m.matched_pairs), pct(m.reconciliation_rate) + " of invoice records"],
      ["Single-source", fmt(Number(m.only_in_invoices) + Number(m.only_in_ledger)),
        fmt(m.only_in_invoices) + " invoices · " + fmt(m.only_in_ledger) + " ledger"],
      ["Amount / currency mismatches", fmt(Number(m.amount_mismatch_pairs) + Number(m.currency_mismatch_pairs)),
        fmt(m.amount_mismatch_pairs) + " amount · " + fmt(m.currency_mismatch_pairs) + " currency (pairs)"],
      ["Duplicates · ambiguous", fmt(m.duplicate_records) + " · " + fmt(m.ambiguous_records), "records"],
      ["Records with DQ errors", fmt(m.records_with_dq_errors), fmt(m.records_with_dq_warnings) + " with warnings"],
      ["Requires review", fmt(m.records_requiring_review), "eligible match rate " + pct(m.eligible_reconciliation_rate)]
    ].forEach(function (k) {
      kpis.appendChild(el("div", { class: "kpi" }, [
        el("span", { class: "label", text: k[0] }), el("span", { class: "value", text: k[1] }), el("span", { class: "sub", text: k[2] })
      ]));
    });

    var L = batch.layers, layers = clear(document.getElementById("layers"));
    function layer(title, pairs) {
      var dl = el("dl");
      pairs.forEach(function (p) { dl.appendChild(el("dt", { text: p[0] })); dl.appendChild(el("dd", { text: p[1] })); });
      layers.appendChild(el("div", { class: "layer" }, [el("h3", { text: title }), dl]));
    }
    layer("Landing (Files/landing)", [
      ["E_INVOICES records (CSV)", fmt(L.landing_records.E_INVOICES)],
      ["ERP_LEDGER records (JSONL)", fmt(L.landing_records.ERP_LEDGER)]
    ]);
    layer("Bronze (raw strings + lineage)", [
      ["bronze_invoices rows", fmt(L.bronze.E_INVOICES.rows)], ["  unparseable rows kept", fmt(L.bronze.E_INVOICES.parse_errors)],
      ["bronze_ledger rows", fmt(L.bronze.ERP_LEDGER.rows)], ["  unparseable rows kept", fmt(L.bronze.ERP_LEDGER.parse_errors)]
    ]);
    function silver(source) {
      var s = L.silver[source] || {};
      return fmt(s.VALID || 0) + " / " + fmt(s.INVALID || 0) + " / " + fmt(s.DUPLICATE || 0);
    }
    layer("Silver (valid / invalid / duplicate)", [
      ["invoices", silver("E_INVOICES")], ["ledger", silver("ERP_LEDGER")], ["quarantined with a reason", fmt(L.quarantined)]
    ]);
    var gold = function (side) { var g = L.gold[side] || {}; return Object.keys(g).reduce(function (a, k) { return a + g[k]; }, 0); };
    layer("Gold (one status per record)", [
      ["invoice records with a status", fmt(gold("INVOICE"))], ["ledger records with a status", fmt(gold("LEDGER"))],
      ["exceptions for review", fmt(batch.exceptions.total)], ["candidate suggestions", fmt(m.candidate_suggestions)]
    ]);

    var maxCount = 1;
    batch.status_table.forEach(function (r) { maxCount = Math.max(maxCount, r.invoices, r.ledger); });
    function bar(value, cls) {
      var width = value > 0 ? Math.max(0.5, 100 * value / maxCount) : 0;
      return el("div", { class: "bar " + cls, style: "width:" + width.toFixed(1) + "%" + (value > 0 ? "" : ";min-width:0"),
        title: fmt(value), "aria-hidden": "true" });
    }
    table(document.getElementById("status-table"),
      [["Status"], ["Invoices", "num"], [""], ["Ledger", "num"], [""]],
      batch.status_table.map(function (r) {
        var name = el("span", { class: "status-name" }, [el("span", { class: "dot " + (STATUS_TONE[r.status] || "") }), el("code", { text: r.status })]);
        return [name, fmt(r.invoices), bar(r.invoices, ""), fmt(r.ledger), bar(r.ledger, "ledger")];
      }));
    Array.prototype.forEach.call(document.querySelectorAll("#status-table td:nth-child(3), #status-table td:nth-child(5)"),
      function (td) { td.className = "bar-cell"; });

    var evidence = clear(document.getElementById("evidence"));
    batch.evidence_examples.forEach(function (ex) {
      var first = ex.rows[0];
      var items = ex.rows.map(function (r) {
        return el("li", { text: "invoice line " + r.invoice_line + " ↔ ledger line " + r.ledger_line + ": " + r.explanation });
      });
      if (ex.ledger_posting_date) {
        var p = ex.ledger_posting_date;
        items.push(el("li", { text: "posting date '" + p.posting_date_text + "' could be " + (p.posting_date_candidates || []).join(" or ") + "; left unresolved for review" }));
      }
      if (first.flags && first.flags.length) { items.push(el("li", { text: "flags: " + first.flags.join(", ") })); }
      evidence.appendChild(el("div", { class: "card" }, [
        el("h3", { text: ex.title }),
        el("span", { class: "decision " + (DECISION_TONE[first.decision] || ""), text: first.decision + " · " + first.reason_code }),
        el("ul", {}, items)
      ]));
    });

    var fired = batch.dq_rules.filter(function (r) { return r.failed_records > 0; });
    table(document.getElementById("dq-table"),
      [["Source"], ["Rule"], ["Severity"], ["Failed", "num"], ["Rate", "num"]],
      fired.map(function (r) { return [r._source_system, el("code", { text: r.rule_id }), r.severity, fmt(r.failed_records), pct(r.failure_rate)]; }));
    document.getElementById("dq-note").textContent = (batch.dq_rules.length - fired.length) +
      " other catalog rules ran on this batch and found no failures. ERROR rules quarantine the record; WARNING rules flag it.";

    table(document.getElementById("suggestions"),
      [["Invoice line", "num"], ["Ledger line", "num"], ["Criterion"], ["Score", "num"], ["Names"], ["References"], ["Auto-approved"]],
      batch.suggestions.map(function (s) {
        return [s.invoice_line, s.ledger_line, el("code", { text: s.criterion }), s.score,
          s.invoice_supplier_name + " / " + s.ledger_supplier_name, s.invoice_reference + " / " + s.ledger_reference,
          s.auto_approved ? "yes" : "never"];
      }));

    var pills = clear(document.getElementById("exception-pills"));
    pills.appendChild(el("span", { class: "pill", text: fmt(batch.exceptions.total) + " records to review" }));
    ["HIGH", "MEDIUM", "LOW"].forEach(function (p) {
      if (batch.exceptions.by_priority[p]) { pills.appendChild(el("span", { class: "pill", text: p + ": " + fmt(batch.exceptions.by_priority[p]) })); }
    });
    table(document.getElementById("exceptions"),
      [["Priority"], ["Side"], ["Line", "num"], ["Status"], ["Reason"], ["Recommended action"]],
      batch.exceptions.sample.map(function (e) {
        return [e.priority, e.side, e.line_number, el("code", { text: e.status }), el("code", { text: e.reason_code || "" }), e.recommended_action];
      }));

    var checks = clear(document.getElementById("checks"));
    batch.validation.checks.forEach(function (c) {
      checks.appendChild(el("li", {}, [
        el("span", { class: "result " + (c.passed ? "pass" : "fail"), text: c.passed ? "PASS" : "FAIL" }),
        el("code", { text: c.check_id }), el("span", { class: "detail", text: " · " + c.detail })
      ]));
    });
  }

  var tabs = document.getElementById("batch-tabs");
  data.batches.forEach(function (batch, index) {
    var button = el("button", { type: "button", role: "tab", "aria-selected": index === 0 ? "true" : "false",
      text: batch.batch_id + " (" + batch.reconciliation_period + ")" });
    button.addEventListener("click", function () {
      Array.prototype.forEach.call(tabs.children, function (b) { b.setAttribute("aria-selected", "false"); });
      button.setAttribute("aria-selected", "true");
      renderBatch(batch);
    });
    tabs.appendChild(button);
  });
  renderBatch(data.batches[0]);
})();
