window.RECON_DEMO = {
 "all_checks_passed": true,
 "batches": [
  {
   "batch_id": "batch-2026-03",
   "dq_rules": [
    {
     "_source_system": "ERP_LEDGER",
     "description": "Amount is not positive or exceeds the configured maximum.",
     "failed_records": 17,
     "failure_rate": "0.0034",
     "rule_id": "AMOUNT_OUT_OF_RANGE",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Repeated record ID with different content; no copy is trusted.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "DUPLICATE_CONFLICT",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Repeated record ID with identical normalized content; the earliest line survives.",
     "failed_records": 53,
     "failure_rate": "0.0105",
     "rule_id": "DUPLICATE_EXACT",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Amount is not a decimal number (max 4 decimals, optional thousands separators).",
     "failed_records": 23,
     "failure_rate": "0.0046",
     "rule_id": "INVALID_AMOUNT",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Currency is not in the configured ISO 4217 allow-list.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "INVALID_CURRENCY",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Date does not match an accepted format or is not a calendar date.",
     "failed_records": 16,
     "failure_rate": "0.0032",
     "rule_id": "INVALID_DATE",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period is not YYYY-MM / YYYYMM with month 01-12.",
     "failed_records": 12,
     "failure_rate": "0.0024",
     "rule_id": "INVALID_PERIOD",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Row could not be parsed against the source contract (field count, JSON shape or field names).",
     "failed_records": 10,
     "failure_rate": "0.0020",
     "rule_id": "MALFORMED_ROW",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Supplier identifier does not match SUP-#### after normalization.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MALFORMED_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "A required amount is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_AMOUNT",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Currency is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_CURRENCY",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Date is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_DATE",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_PERIOD",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Invoice reference is empty after removing whitespace and separators.",
     "failed_records": 20,
     "failure_rate": "0.0040",
     "rule_id": "MISSING_REFERENCE",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Supplier identifier is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Ledger transaction ID is empty.",
     "failed_records": 19,
     "failure_rate": "0.0038",
     "rule_id": "MISSING_TRANSACTION_ID",
     "severity": "ERROR",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Posting date reads as two different valid dates (D/M vs M/D); not resolved.",
     "failed_records": 150,
     "failure_rate": "0.0298",
     "rule_id": "AMBIGUOUS_DATE",
     "severity": "WARNING",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Payment status is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_PAYMENT_STATUS",
     "severity": "WARNING",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period differs from the batch reconciliation period.",
     "failed_records": 82,
     "failure_rate": "0.0163",
     "rule_id": "OUT_OF_PERIOD",
     "severity": "WARNING",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Posting date month differs from the accounting period.",
     "failed_records": 27,
     "failure_rate": "0.0054",
     "rule_id": "PERIOD_INCONSISTENT",
     "severity": "WARNING",
     "total_records": 5041
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Payment status is not in the configured list.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "UNKNOWN_PAYMENT_STATUS",
     "severity": "WARNING",
     "total_records": 5041
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Amount is not positive or exceeds the configured maximum.",
     "failed_records": 16,
     "failure_rate": "0.0031",
     "rule_id": "AMOUNT_OUT_OF_RANGE",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Repeated record ID with different content; no copy is trusted.",
     "failed_records": 48,
     "failure_rate": "0.0094",
     "rule_id": "DUPLICATE_CONFLICT",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Repeated record ID with identical normalized content; the earliest line survives.",
     "failed_records": 54,
     "failure_rate": "0.0106",
     "rule_id": "DUPLICATE_EXACT",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Amount is not a decimal number (max 4 decimals, optional thousands separators).",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "INVALID_AMOUNT",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Currency is not in the configured ISO 4217 allow-list.",
     "failed_records": 17,
     "failure_rate": "0.0033",
     "rule_id": "INVALID_CURRENCY",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Date does not match an accepted format or is not a calendar date.",
     "failed_records": 20,
     "failure_rate": "0.0039",
     "rule_id": "INVALID_DATE",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Row could not be parsed against the source contract (field count, JSON shape or field names).",
     "failed_records": 12,
     "failure_rate": "0.0024",
     "rule_id": "MALFORMED_ROW",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Supplier identifier does not match SUP-#### after normalization.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MALFORMED_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "A required amount is empty.",
     "failed_records": 16,
     "failure_rate": "0.0031",
     "rule_id": "MISSING_AMOUNT",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Currency is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_CURRENCY",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Date is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_DATE",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice ID is empty.",
     "failed_records": 17,
     "failure_rate": "0.0033",
     "rule_id": "MISSING_INVOICE_ID",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice reference is empty after removing whitespace and separators.",
     "failed_records": 18,
     "failure_rate": "0.0035",
     "rule_id": "MISSING_REFERENCE",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Supplier identifier is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "subtotal + tax_amount differs from total_amount by more than the currency tolerance.",
     "failed_records": 23,
     "failure_rate": "0.0045",
     "rule_id": "TOTAL_INCONSISTENT",
     "severity": "ERROR",
     "total_records": 5101
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice date falls outside the batch reconciliation period.",
     "failed_records": 55,
     "failure_rate": "0.0108",
     "rule_id": "OUT_OF_PERIOD",
     "severity": "WARNING",
     "total_records": 5101
    }
   ],
   "evidence_examples": [
    {
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0032 on both sides; reference 'SAO-021941' vs 'SAO-021941' normalize to SAO021941; currency USD on both sides; |7398.0400 - 7398.0400| = 0.0000 vs tolerance 0.0100",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-03776",
       "invoice_line": 2,
       "invoice_reference": "SAO-021941",
       "invoice_total": "7398.0400",
       "ledger_amount": "7398.0400",
       "ledger_currency": "USD",
       "ledger_line": 2732,
       "ledger_reference": "SAO-021941",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "SAO021941",
       "supplier_id": "SUP-0032",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-003748"
      }
     ],
     "title": "Exact match"
    },
    {
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0040 on both sides; reference 'UMC-036532' vs 'UMC 036532' normalize to UMC036532; currency EUR on both sides; |9921.6500 - 9921.6500| = 0.0000 vs tolerance 0.0100",
       "flags": [
        "REFERENCE_FORMAT_VARIANT"
       ],
       "invoice_currency": "EUR",
       "invoice_id": "EI-202603-03875",
       "invoice_line": 17,
       "invoice_reference": "UMC-036532",
       "invoice_total": "9921.6500",
       "ledger_amount": "9921.6500",
       "ledger_currency": "EUR",
       "ledger_line": 4271,
       "ledger_reference": "UMC 036532",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "UMC036532",
       "supplier_id": "SUP-0040",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-003844"
      }
     ],
     "title": "Reference written differently"
    },
    {
     "rows": [
      {
       "amount_difference": "0.0100",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0006 on both sides; reference 'NIL-033969' vs 'NIL-033969' normalize to NIL033969; currency USD on both sides; |16926.3200 - 16926.3300| = 0.0100 vs tolerance 0.0100",
       "flags": [
        "ROUNDING_DIFFERENCE"
       ],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-00219",
       "invoice_line": 18,
       "invoice_reference": "NIL-033969",
       "invoice_total": "16926.3200",
       "ledger_amount": "16926.3300",
       "ledger_currency": "USD",
       "ledger_line": 3073,
       "ledger_reference": "NIL-033969",
       "reason_code": "WITHIN_TOLERANCE",
       "reference_key": "NIL033969",
       "supplier_id": "SUP-0006",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-000212"
      }
     ],
     "title": "Rounding within tolerance"
    },
    {
     "ledger_posting_date": {
      "posting_date_basis": "AMBIGUOUS_D/M_OR_M/D",
      "posting_date_candidates": [
       "2026-03-05",
       "2026-05-03"
      ],
      "posting_date_text": "05/03/2026"
     },
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0037 on both sides; reference 'DEP-025023' vs 'DEP-025023' normalize to DEP025023; currency USD on both sides; |25021.6800 - 25021.6800| = 0.0000 vs tolerance 0.0100",
       "flags": [
        "AMBIGUOUS_DATE"
       ],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-00298",
       "invoice_line": 95,
       "invoice_reference": "DEP-025023",
       "invoice_total": "25021.6800",
       "ledger_amount": "25021.6800",
       "ledger_currency": "USD",
       "ledger_line": 418,
       "ledger_reference": "DEP-025023",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "DEP025023",
       "supplier_id": "SUP-0037",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-000292"
      }
     ],
     "title": "Matched, posting date ambiguous"
    },
    {
     "rows": [
      {
       "amount_difference": "823.8400",
       "decision": "AMOUNT_MISMATCH",
       "explanation": "supplier_id SUP-0006 on both sides; reference 'NIL-034194' vs 'NIL-034194' normalize to NIL034194; currency USD on both sides; |16476.7900 - 17300.6300| = 823.8400 vs tolerance 0.0100",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-02767",
       "invoice_line": 84,
       "invoice_reference": "NIL-034194",
       "invoice_total": "16476.7900",
       "ledger_amount": "17300.6300",
       "ledger_currency": "USD",
       "ledger_line": 4360,
       "ledger_reference": "NIL-034194",
       "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
       "reference_key": "NIL034194",
       "supplier_id": "SUP-0006",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-002748"
      }
     ],
     "title": "Amount mismatch"
    },
    {
     "rows": [
      {
       "amount_difference": null,
       "decision": "CURRENCY_MISMATCH",
       "explanation": "supplier_id SUP-0027 on both sides; reference 'LMP-001675' vs 'LMP-001675' normalize to LMP001675; currency USD vs EUR: amounts not compared (no conversion rule)",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-00199",
       "invoice_line": 57,
       "invoice_reference": "LMP-001675",
       "invoice_total": "10263.3300",
       "ledger_amount": "10263.3300",
       "ledger_currency": "EUR",
       "ledger_line": 3623,
       "ledger_reference": "LMP-001675",
       "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
       "reference_key": "LMP001675",
       "supplier_id": "SUP-0027",
       "tolerance": null,
       "transaction_id": "GL-202603-000193"
      }
     ],
     "title": "Currency mismatch"
    },
    {
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "NOT_DECIDED_MULTIPLE_CANDIDATES",
       "explanation": "supplier_id SUP-0013 on both sides; reference 'FEF-006412' vs 'FEF-006412' normalize to FEF006412; currency USD on both sides; |3195.8000 - 3195.8000| = 0.0000 vs tolerance 0.0100; 1 invoice(s) and 2 ledger record(s) share this key: not decided",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-03047",
       "invoice_line": 53,
       "invoice_reference": "FEF-006412",
       "invoice_total": "3195.8000",
       "ledger_amount": "3195.8000",
       "ledger_currency": "USD",
       "ledger_line": 1012,
       "ledger_reference": "FEF-006412",
       "reason_code": "MULTIPLE_LEDGER_ENTRIES_FOR_KEY",
       "reference_key": "FEF006412",
       "supplier_id": "SUP-0013",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-003031"
      },
      {
       "amount_difference": "0.0000",
       "decision": "NOT_DECIDED_MULTIPLE_CANDIDATES",
       "explanation": "supplier_id SUP-0013 on both sides; reference 'FEF-006412' vs 'FEF-006412' normalize to FEF006412; currency USD on both sides; |3195.8000 - 3195.8000| = 0.0000 vs tolerance 0.0100; 1 invoice(s) and 2 ledger record(s) share this key: not decided",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202603-03047",
       "invoice_line": 53,
       "invoice_reference": "FEF-006412",
       "invoice_total": "3195.8000",
       "ledger_amount": "3195.8000",
       "ledger_currency": "USD",
       "ledger_line": 3813,
       "ledger_reference": "FEF-006412",
       "reason_code": "MULTIPLE_LEDGER_ENTRIES_FOR_KEY",
       "reference_key": "FEF006412",
       "supplier_id": "SUP-0013",
       "tolerance": "0.0100",
       "transaction_id": "GL-202603-003032"
      }
     ],
     "title": "Several candidates, not decided"
    }
   ],
   "exceptions": {
    "by_priority": {
     "HIGH": 663,
     "LOW": 464,
     "MEDIUM": 1031
    },
    "by_status": {
     "AMBIGUOUS": 213,
     "AMOUNT_MISMATCH": 278,
     "CURRENCY_MISMATCH": 124,
     "DUPLICATE": 155,
     "INVALID_RECORD": 256,
     "MATCHED": 464,
     "ONLY_IN_INVOICES": 341,
     "ONLY_IN_LEDGER": 327
    },
    "sample": [
     {
      "flags": [],
      "line_number": 20,
      "priority": "HIGH",
      "reason_code": "DUPLICATE_CONFLICT",
      "recommended_action": "Same record ID with different content; ask the source owner which version is valid.",
      "record_id": "EI-202603-01516",
      "side": "INVOICE",
      "status": "DUPLICATE",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 53,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_LEDGER_ENTRIES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202603-03047",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 57,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202603-00199",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 62,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202603-02718",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 84,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202603-02767",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 91,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202603-02213",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 101,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202603-04110",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 109,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202603-00957",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 137,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202603-03965",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 176,
      "priority": "HIGH",
      "reason_code": "DUPLICATE_CONFLICT",
      "recommended_action": "Same record ID with different content; ask the source owner which version is valid.",
      "record_id": "EI-202603-00059",
      "side": "INVOICE",
      "status": "DUPLICATE",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 179,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202603-00997",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 203,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202603-00899",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     }
    ],
    "total": 2158
   },
   "generator": {
    "base_invoices": 5000,
    "batch_index": 0,
    "name": "invoice_recon.generator",
    "seed": 4242,
    "version": "1"
   },
   "layers": {
    "bronze": {
     "ERP_LEDGER": {
      "parse_errors": 10,
      "rows": 5041
     },
     "E_INVOICES": {
      "parse_errors": 12,
      "rows": 5101
     }
    },
    "gold": {
     "INVOICE": {
      "AMBIGUOUS": 94,
      "AMOUNT_MISMATCH": 139,
      "CURRENCY_MISMATCH": 62,
      "DUPLICATE": 102,
      "INVALID_RECORD": 139,
      "MATCHED": 4224,
      "ONLY_IN_INVOICES": 341
     },
     "LEDGER": {
      "AMBIGUOUS": 119,
      "AMOUNT_MISMATCH": 139,
      "CURRENCY_MISMATCH": 62,
      "DUPLICATE": 53,
      "INVALID_RECORD": 117,
      "MATCHED": 4224,
      "ONLY_IN_LEDGER": 327
     }
    },
    "ingestion_errors": {
     "ERP_LEDGER": {
      "MALFORMED_ROW": 4,
      "SCHEMA_DRIFT": 6
     },
     "E_INVOICES": {
      "MALFORMED_ROW": 12
     }
    },
    "landing_records": {
     "ERP_LEDGER": 5041,
     "E_INVOICES": 5101
    },
    "quarantined": 411,
    "silver": {
     "ERP_LEDGER": {
      "DUPLICATE": 53,
      "INVALID": 117,
      "VALID": 4871
     },
     "E_INVOICES": {
      "DUPLICATE": 102,
      "INVALID": 139,
      "VALID": 4860
     }
    }
   },
   "matched_amounts_by_currency": [
    {
     "amount": "5400284.3000",
     "currency": "CAD",
     "records": 379
    },
    {
     "amount": "7607893.1600",
     "currency": "EUR",
     "records": 578
    },
    {
     "amount": "135310574.0000",
     "currency": "JPY",
     "records": 87
    },
    {
     "amount": "14455463.6000",
     "currency": "MXN",
     "records": 1043
    },
    {
     "amount": "29315819.5900",
     "currency": "USD",
     "records": 2137
    }
   ],
   "metrics": {
    "ambiguous_records": 213,
    "amount_mismatch_pairs": 139,
    "candidate_suggestions": 51,
    "currency_mismatch_pairs": 62,
    "duplicate_records": 155,
    "eligible_reconciliation_rate": "0.8691",
    "invalid_records": 256,
    "invoice_records": 5101,
    "ledger_records": 5041,
    "matched_pairs": 4224,
    "only_in_invoices": 341,
    "only_in_ledger": 327,
    "reconciliation_period": "2026-03",
    "reconciliation_rate": "0.8281",
    "records_requiring_review": 2158,
    "records_with_dq_errors": 256,
    "records_with_dq_warnings": 287,
    "rules_version": "2026.1"
   },
   "quarantine_sample": [
    {
     "_line_number": 77,
     "_raw_line": "{\"transaction_id\": \"GL-202603-000741\", \"invoice_reference\": \"ROF-030816\", \"supplier_id\": \"SUP-0030\", \"supplier_name\": \"Rosmerin Fixtures Co\", \"posting_date\": \"2026-03-12\", \"currency\": \"JPY\", \"recorded_amount\": \"250000000\", \"payment_status\": \"PARTIALLY_PAID\", \"accounting_period\": \"2026-03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "AMOUNT_OUT_OF_RANGE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202603-000741",
     "record_status": "INVALID",
     "status_reason": "AMOUNT_OUT_OF_RANGE"
    },
    {
     "_line_number": 114,
     "_raw_line": "{\"transaction_id\": \"GL-202603-004400\", \"invoice_reference\": \"VXP-007893\", \"supplier_id\": \"SUP-0044\", \"supplier_name\": \"Vexmoor Polymer Co\", \"posting_date\": \"31/02/2026\", \"currency\": \"USD\", \"recorded_amount\": \"27590.05\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_DATE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202603-004400",
     "record_status": "INVALID",
     "status_reason": "INVALID_DATE"
    },
    {
     "_line_number": 118,
     "_raw_line": "{\"transaction_id\": \"GL-202603-004257\", \"invoice_reference\": \"MRP-001555\", \"supplier_id\": \"SUP-0045\", \"supplier_name\": \"Marrowind Polymer Ltd\", \"posting_date\": \"20/03/2026\", \"currency\": \"MXN\", \"recorded_amount\": \"250000000.00\", \"payment_status\": \"PAID\", \"accounting_period\": \"2026-03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "AMOUNT_OUT_OF_RANGE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202603-004257",
     "record_status": "INVALID",
     "status_reason": "AMOUNT_OUT_OF_RANGE"
    },
    {
     "_line_number": 138,
     "_raw_line": "{\"transaction_id\": \"GL-202603-001648\", \"invoice_reference\": \"KEP-006537\", \"supplier_id\": \"SUP-0017\", \"supplier_name\": \"Kestwick Polymers Ltd\", \"posting_date\": \"2026-03-25\", \"currency\": \"USD\", \"recorded_amount\": \"717.74\", \"payment_status\": \"PAID\", \"accounting_period\": \"2026/03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_PERIOD"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202603-001648",
     "record_status": "INVALID",
     "status_reason": "INVALID_PERIOD"
    },
    {
     "_line_number": 245,
     "_raw_line": "{\"transaction_id\": \"GL-202603-002242\", \"invoice_reference\": \"UMT-031874\", \"supplier_id\": \"SUP-0019\", \"supplier_name\": \"Umbervale Tooling Ltd\", \"posting_date\": \"17-Mar-2026\", \"currency\": \"MXN\", \"recorded_amount\": \"5579.25\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-00\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_PERIOD"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202603-002242",
     "record_status": "INVALID",
     "status_reason": "INVALID_PERIOD"
    },
    {
     "_line_number": 278,
     "_raw_line": "{\"transaction_id\": \"\", \"invoice_reference\": \"UMT-031894\", \"supplier_id\": \"SUP-0019\", \"supplier_name\": \"Umbervale Tooling Ltd\", \"posting_date\": \"2026-03-31\", \"currency\": \"MXN\", \"recorded_amount\": \"8161.06\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MISSING_TRANSACTION_ID"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": null,
     "record_status": "INVALID",
     "status_reason": "MISSING_TRANSACTION_ID"
    },
    {
     "_line_number": 282,
     "_raw_line": "{\"transaction_id\": \"GL-202603-001392\", \"invoice_reference\": \"GRT-005004\", \"supplier_id\": \"SUP-0036\", \"supplier_name\": \"Gristmere Tooling Inc\", \"posting_date\": \"2026-03-",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MALFORMED_ROW"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": null,
     "record_status": "INVALID",
     "status_reason": "MALFORMED_ROW"
    },
    {
     "_line_number": 324,
     "_raw_line": "{\"transaction_id\": \"\", \"invoice_reference\": \"KEF-033953\", \"supplier_id\": \"SUP-0010\", \"supplier_name\": \"Kestwick Fixtures Inc\", \"posting_date\": \"2026-03-08\", \"currency\": \"USD\", \"recorded_amount\": \"12578.21\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-03\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MISSING_TRANSACTION_ID"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": null,
     "record_status": "INVALID",
     "status_reason": "MISSING_TRANSACTION_ID"
    }
   ],
   "reconciliation_period": "2026-03",
   "rules_version": "2026.1",
   "status_table": [
    {
     "invoices": 4224,
     "ledger": 4224,
     "status": "MATCHED"
    },
    {
     "invoices": 139,
     "ledger": 139,
     "status": "AMOUNT_MISMATCH"
    },
    {
     "invoices": 62,
     "ledger": 62,
     "status": "CURRENCY_MISMATCH"
    },
    {
     "invoices": 341,
     "ledger": 0,
     "status": "ONLY_IN_INVOICES"
    },
    {
     "invoices": 0,
     "ledger": 327,
     "status": "ONLY_IN_LEDGER"
    },
    {
     "invoices": 94,
     "ledger": 119,
     "status": "AMBIGUOUS"
    },
    {
     "invoices": 102,
     "ledger": 53,
     "status": "DUPLICATE"
    },
    {
     "invoices": 139,
     "ledger": 117,
     "status": "INVALID_RECORD"
    }
   ],
   "suggestions": [
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.778; supplier SUP-0031 'Marrowind Electrical Ltd' vs SUP-0031 'Marrowind Electrical Ltd' (name similarity 1.000); reference 'MAE-009911' vs 'MAE-9911' (similarity 0.778); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-04671",
     "invoice_line": 162,
     "invoice_reference": "MAE-009911",
     "invoice_supplier_id": "SUP-0031",
     "invoice_supplier_name": "Marrowind Electrical Ltd",
     "ledger_line": 4707,
     "ledger_reference": "MAE-9911",
     "ledger_supplier_id": "SUP-0031",
     "ledger_supplier_name": "Marrowind Electrical Ltd",
     "name_similarity": "1.000",
     "reference_similarity": "0.778",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.778",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-004643"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.941; supplier SUP-0006 'Nimbrel Logistics Co' vs SUP-0046 'Nimbrel Logistic Ltd' (name similarity 0.941); reference 'NIL-034220' vs 'NIL-034220' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-03012",
     "invoice_line": 190,
     "invoice_reference": "NIL-034220",
     "invoice_supplier_id": "SUP-0006",
     "invoice_supplier_name": "Nimbrel Logistics Co",
     "ledger_line": 539,
     "ledger_reference": "NIL-034220",
     "ledger_supplier_id": "SUP-0046",
     "ledger_supplier_name": "Nimbrel Logistic Ltd",
     "name_similarity": "0.941",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.941",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-002996"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.941; supplier SUP-0001 'Amberlyn Castings Ltd' vs SUP-0041 'Amberlyn Casting Co' (name similarity 0.941); reference 'AMC-038287' vs 'AMC-038287' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-04868",
     "invoice_line": 201,
     "invoice_reference": "AMC-038287",
     "invoice_supplier_id": "SUP-0001",
     "invoice_supplier_name": "Amberlyn Castings Ltd",
     "ledger_line": 1751,
     "ledger_reference": "AMC-038287",
     "ledger_supplier_id": "SUP-0041",
     "ledger_supplier_name": "Amberlyn Casting Co",
     "name_similarity": "0.941",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.941",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-004836"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.889; supplier SUP-0030 'Rosmerin Fixtures Co' vs SUP-0030 'Rosmerin Fixtures Co' (name similarity 1.000); reference 'ROF-031068' vs 'ROF-31068' (similarity 0.889); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-03232",
     "invoice_line": 378,
     "invoice_reference": "ROF-031068",
     "invoice_supplier_id": "SUP-0030",
     "invoice_supplier_name": "Rosmerin Fixtures Co",
     "ledger_line": 1728,
     "ledger_reference": "ROF-31068",
     "ledger_supplier_id": "SUP-0030",
     "ledger_supplier_name": "Rosmerin Fixtures Co",
     "name_similarity": "1.000",
     "reference_similarity": "0.889",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.889",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-003210"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.944; supplier SUP-0002 'Ostravale Fixtures, Co' vs SUP-0042 'Ostravale Fixture Inc' (name similarity 0.944); reference 'OSF-027337' vs 'OSF-027337' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-03083",
     "invoice_line": 414,
     "invoice_reference": "OSF-027337",
     "invoice_supplier_id": "SUP-0002",
     "invoice_supplier_name": "Ostravale Fixtures, Co",
     "ledger_line": 2845,
     "ledger_reference": "OSF-027337",
     "ledger_supplier_id": "SUP-0042",
     "ledger_supplier_name": "Ostravale Fixture Inc",
     "name_similarity": "0.944",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.944",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-003067"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.944; supplier SUP-0002 'Ostravale Fixtures, Co' vs SUP-0042 'Ostravale Fixture Inc' (name similarity 0.944); reference 'OSF-027204' vs 'OSF-027204' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-00905",
     "invoice_line": 573,
     "invoice_reference": "OSF-027204",
     "invoice_supplier_id": "SUP-0002",
     "invoice_supplier_name": "Ostravale Fixtures, Co",
     "ledger_line": 4900,
     "ledger_reference": "OSF-027204",
     "ledger_supplier_id": "SUP-0042",
     "ledger_supplier_name": "Ostravale Fixture Inc",
     "name_similarity": "0.944",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.944",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-000901"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.941; supplier SUP-0001 'Amberlyn Castings Ltd' vs SUP-0041 'Amberlyn Casting Co' (name similarity 0.941); reference 'AMC-037998' vs 'AMC-037998' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-01492",
     "invoice_line": 600,
     "invoice_reference": "AMC-037998",
     "invoice_supplier_id": "SUP-0001",
     "invoice_supplier_name": "Amberlyn Castings Ltd",
     "ledger_line": 4549,
     "ledger_reference": "AMC-037998",
     "ledger_supplier_id": "SUP-0041",
     "ledger_supplier_name": "Amberlyn Casting Co",
     "name_similarity": "0.941",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.941",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-001474"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.889; supplier SUP-0038 'Corvantis Office Supplies LLC' vs SUP-0038 'Corvantis Office Supplies LLC' (name similarity 1.000); reference 'COO-030261' vs 'COO-30261' (similarity 0.889); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202603-04198",
     "invoice_line": 829,
     "invoice_reference": "COO-030261",
     "invoice_supplier_id": "SUP-0038",
     "invoice_supplier_name": "Corvantis Office Supplies LLC",
     "ledger_line": 942,
     "ledger_reference": "COO-30261",
     "ledger_supplier_id": "SUP-0038",
     "ledger_supplier_name": "Corvantis Office Supplies LLC",
     "name_similarity": "1.000",
     "reference_similarity": "0.889",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.889",
     "suggestion_rank": 1,
     "transaction_id": "GL-202603-004170"
    }
   ],
   "synthetic": true,
   "validation": {
    "batch_id": "batch-2026-03",
    "checks": [
     {
      "check_id": "LANDING_TO_BRONZE[E_INVOICES]",
      "detail": "5101 non-blank landing records, 5101 bronze rows",
      "passed": true
     },
     {
      "check_id": "BRONZE_TO_SILVER[E_INVOICES]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_TO_GOLD[INVOICE]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_STATUS_PARTITION[E_INVOICES]",
      "detail": "statuses {'DUPLICATE': 102, 'INVALID': 139, 'VALID': 4860}",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_COMPLETE[E_INVOICES]",
      "detail": "241 quarantined, 241 non-VALID silver rows",
      "passed": true
     },
     {
      "check_id": "LANDING_TO_BRONZE[ERP_LEDGER]",
      "detail": "5041 non-blank landing records, 5041 bronze rows",
      "passed": true
     },
     {
      "check_id": "BRONZE_TO_SILVER[ERP_LEDGER]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_TO_GOLD[LEDGER]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_STATUS_PARTITION[ERP_LEDGER]",
      "detail": "statuses {'DUPLICATE': 53, 'INVALID': 117, 'VALID': 4871}",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_COMPLETE[ERP_LEDGER]",
      "detail": "170 quarantined, 170 non-VALID silver rows",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_HAS_REASON",
      "detail": "0 quarantined rows without a reason",
      "passed": true
     },
     {
      "check_id": "GOLD_ONE_ROW_PER_RECORD",
      "detail": "0 records with more than one status",
      "passed": true
     },
     {
      "check_id": "STATUS_IN_CATALOG",
      "detail": "0 rows with an unknown status",
      "passed": true
     },
     {
      "check_id": "NO_NULL_KEY_MATCH",
      "detail": "0 MATCHED rows with a NULL key or record ID",
      "passed": true
     },
     {
      "check_id": "ONE_TO_ONE_MATCHES",
      "detail": "matched invoices, matched ledger rows, evidence rows, distinct invoice lines, distinct ledger lines = 4224, 4224, 4224, 4224, 4224",
      "passed": true
     },
     {
      "check_id": "COUNTERPARTS_SYMMETRIC",
      "detail": "0 decided pairs whose two sides disagree",
      "passed": true
     },
     {
      "check_id": "MATCHED_SAME_CURRENCY",
      "detail": "0 MATCHED pairs with different currencies",
      "passed": true
     },
     {
      "check_id": "MATCHED_WITHIN_TOLERANCE",
      "detail": "0 MATCHED pairs outside tolerance",
      "passed": true
     },
     {
      "check_id": "NO_CROSS_CURRENCY_COMPARISON",
      "detail": "0 currency mismatches with a computed amount difference",
      "passed": true
     },
     {
      "check_id": "ONLY_VALID_RECORDS_DECIDED",
      "detail": "0 non-VALID records that reached a matching status",
      "passed": true
     },
     {
      "check_id": "SUGGESTIONS_NEVER_APPROVED",
      "detail": "0 suggestions auto-approved or attached to a record that is not ONLY_IN_*",
      "passed": true
     },
     {
      "check_id": "EXCEPTIONS_MATCH_REVIEW_FLAG",
      "detail": "2158 exceptions, 2158 records requiring review",
      "passed": true
     },
     {
      "check_id": "METRICS_CONSISTENT",
      "detail": "recomputed (5101, 5041, 4224, 2158, 51), stored (5101, 5041, 4224, 2158, 51)",
      "passed": true
     },
     {
      "check_id": "SYNTHETIC_GROUND_TRUTH",
      "detail": "10142/10142 records match their designed outcome",
      "passed": true
     },
     {
      "check_id": "SYNTHETIC_SUGGESTIONS",
      "detail": "51/51 designed suggestions produced",
      "passed": true
     }
    ],
    "passed": true
   },
   "versions": {
    "delta-spark": "4.2.0",
    "fabric-invoice-reconciliation": "0.1.0",
    "pyspark": "4.1.1"
   }
  },
  {
   "batch_id": "batch-2026-04",
   "dq_rules": [
    {
     "_source_system": "ERP_LEDGER",
     "description": "Amount is not positive or exceeds the configured maximum.",
     "failed_records": 14,
     "failure_rate": "0.0028",
     "rule_id": "AMOUNT_OUT_OF_RANGE",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Repeated record ID with different content; no copy is trusted.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "DUPLICATE_CONFLICT",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Repeated record ID with identical normalized content; the earliest line survives.",
     "failed_records": 55,
     "failure_rate": "0.0109",
     "rule_id": "DUPLICATE_EXACT",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Amount is not a decimal number (max 4 decimals, optional thousands separators).",
     "failed_records": 18,
     "failure_rate": "0.0036",
     "rule_id": "INVALID_AMOUNT",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Currency is not in the configured ISO 4217 allow-list.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "INVALID_CURRENCY",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Date does not match an accepted format or is not a calendar date.",
     "failed_records": 22,
     "failure_rate": "0.0043",
     "rule_id": "INVALID_DATE",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period is not YYYY-MM / YYYYMM with month 01-12.",
     "failed_records": 18,
     "failure_rate": "0.0036",
     "rule_id": "INVALID_PERIOD",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Row could not be parsed against the source contract (field count, JSON shape or field names).",
     "failed_records": 8,
     "failure_rate": "0.0016",
     "rule_id": "MALFORMED_ROW",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Supplier identifier does not match SUP-#### after normalization.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MALFORMED_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "A required amount is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_AMOUNT",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Currency is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_CURRENCY",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Date is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_DATE",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_PERIOD",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Invoice reference is empty after removing whitespace and separators.",
     "failed_records": 21,
     "failure_rate": "0.0041",
     "rule_id": "MISSING_REFERENCE",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Supplier identifier is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Ledger transaction ID is empty.",
     "failed_records": 18,
     "failure_rate": "0.0036",
     "rule_id": "MISSING_TRANSACTION_ID",
     "severity": "ERROR",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Posting date reads as two different valid dates (D/M vs M/D); not resolved.",
     "failed_records": 129,
     "failure_rate": "0.0255",
     "rule_id": "AMBIGUOUS_DATE",
     "severity": "WARNING",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Payment status is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_PAYMENT_STATUS",
     "severity": "WARNING",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Accounting period differs from the batch reconciliation period.",
     "failed_records": 64,
     "failure_rate": "0.0126",
     "rule_id": "OUT_OF_PERIOD",
     "severity": "WARNING",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Posting date month differs from the accounting period.",
     "failed_records": 24,
     "failure_rate": "0.0047",
     "rule_id": "PERIOD_INCONSISTENT",
     "severity": "WARNING",
     "total_records": 5067
    },
    {
     "_source_system": "ERP_LEDGER",
     "description": "Payment status is not in the configured list.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "UNKNOWN_PAYMENT_STATUS",
     "severity": "WARNING",
     "total_records": 5067
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Amount is not positive or exceeds the configured maximum.",
     "failed_records": 14,
     "failure_rate": "0.0027",
     "rule_id": "AMOUNT_OUT_OF_RANGE",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Repeated record ID with different content; no copy is trusted.",
     "failed_records": 40,
     "failure_rate": "0.0079",
     "rule_id": "DUPLICATE_CONFLICT",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Repeated record ID with identical normalized content; the earliest line survives.",
     "failed_records": 47,
     "failure_rate": "0.0092",
     "rule_id": "DUPLICATE_EXACT",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Amount is not a decimal number (max 4 decimals, optional thousands separators).",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "INVALID_AMOUNT",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Currency is not in the configured ISO 4217 allow-list.",
     "failed_records": 18,
     "failure_rate": "0.0035",
     "rule_id": "INVALID_CURRENCY",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Date does not match an accepted format or is not a calendar date.",
     "failed_records": 17,
     "failure_rate": "0.0033",
     "rule_id": "INVALID_DATE",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Row could not be parsed against the source contract (field count, JSON shape or field names).",
     "failed_records": 9,
     "failure_rate": "0.0018",
     "rule_id": "MALFORMED_ROW",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Supplier identifier does not match SUP-#### after normalization.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MALFORMED_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "A required amount is empty.",
     "failed_records": 22,
     "failure_rate": "0.0043",
     "rule_id": "MISSING_AMOUNT",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Currency is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_CURRENCY",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Date is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_DATE",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice ID is empty.",
     "failed_records": 21,
     "failure_rate": "0.0041",
     "rule_id": "MISSING_INVOICE_ID",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice reference is empty after removing whitespace and separators.",
     "failed_records": 23,
     "failure_rate": "0.0045",
     "rule_id": "MISSING_REFERENCE",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Supplier identifier is empty.",
     "failed_records": 0,
     "failure_rate": "0.0000",
     "rule_id": "MISSING_SUPPLIER_ID",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "subtotal + tax_amount differs from total_amount by more than the currency tolerance.",
     "failed_records": 23,
     "failure_rate": "0.0045",
     "rule_id": "TOTAL_INCONSISTENT",
     "severity": "ERROR",
     "total_records": 5095
    },
    {
     "_source_system": "E_INVOICES",
     "description": "Invoice date falls outside the batch reconciliation period.",
     "failed_records": 40,
     "failure_rate": "0.0079",
     "rule_id": "OUT_OF_PERIOD",
     "severity": "WARNING",
     "total_records": 5095
    }
   ],
   "evidence_examples": [
    {
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0029 on both sides; reference 'DEF-018641' vs 'DEF-018641' normalize to DEF018641; currency USD on both sides; |19769.3800 - 19769.3800| = 0.0000 vs tolerance 0.0100",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202604-01764",
       "invoice_line": 2,
       "invoice_reference": "DEF-018641",
       "invoice_total": "19769.3800",
       "ledger_amount": "19769.3800",
       "ledger_currency": "USD",
       "ledger_line": 1477,
       "ledger_reference": "DEF-018641",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "DEF018641",
       "supplier_id": "SUP-0029",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-001774"
      }
     ],
     "title": "Exact match"
    },
    {
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0034 on both sides; reference 'SAC-012583' vs 'SAC012583' normalize to SAC012583; currency EUR on both sides; |3519.4100 - 3519.4100| = 0.0000 vs tolerance 0.0100",
       "flags": [
        "REFERENCE_FORMAT_VARIANT"
       ],
       "invoice_currency": "EUR",
       "invoice_id": "EI-202604-02376",
       "invoice_line": 18,
       "invoice_reference": "SAC-012583",
       "invoice_total": "3519.4100",
       "ledger_amount": "3519.4100",
       "ledger_currency": "EUR",
       "ledger_line": 1335,
       "ledger_reference": "SAC012583",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "SAC012583",
       "supplier_id": "SUP-0034",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-002381"
      }
     ],
     "title": "Reference written differently"
    },
    {
     "rows": [
      {
       "amount_difference": "0.0100",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0040 on both sides; reference 'UMC-037038' vs 'UMC-037038' normalize to UMC037038; currency EUR on both sides; |10403.8500 - 10403.8400| = 0.0100 vs tolerance 0.0100",
       "flags": [
        "ROUNDING_DIFFERENCE"
       ],
       "invoice_currency": "EUR",
       "invoice_id": "EI-202604-04394",
       "invoice_line": 6,
       "invoice_reference": "UMC-037038",
       "invoice_total": "10403.8500",
       "ledger_amount": "10403.8400",
       "ledger_currency": "EUR",
       "ledger_line": 2085,
       "ledger_reference": "UMC-037038",
       "reason_code": "WITHIN_TOLERANCE",
       "reference_key": "UMC037038",
       "supplier_id": "SUP-0040",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-004378"
      }
     ],
     "title": "Rounding within tolerance"
    },
    {
     "ledger_posting_date": {
      "posting_date_basis": "AMBIGUOUS_D/M_OR_M/D",
      "posting_date_candidates": [
       "2026-04-09",
       "2026-09-04"
      ],
      "posting_date_text": "09/04/2026"
     },
     "rows": [
      {
       "amount_difference": "0.0000",
       "decision": "MATCHED",
       "explanation": "supplier_id SUP-0002 on both sides; reference 'OSF-027915' vs 'OSF-027915' normalize to OSF027915; currency MXN on both sides; |864.6700 - 864.6700| = 0.0000 vs tolerance 0.0100",
       "flags": [
        "AMBIGUOUS_DATE"
       ],
       "invoice_currency": "MXN",
       "invoice_id": "EI-202604-04619",
       "invoice_line": 33,
       "invoice_reference": "OSF-027915",
       "invoice_total": "864.6700",
       "ledger_amount": "864.6700",
       "ledger_currency": "MXN",
       "ledger_line": 3861,
       "ledger_reference": "OSF-027915",
       "reason_code": "EXACT_AMOUNT",
       "reference_key": "OSF027915",
       "supplier_id": "SUP-0002",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-004604"
      }
     ],
     "title": "Matched, posting date ambiguous"
    },
    {
     "rows": [
      {
       "amount_difference": "306.2100",
       "decision": "AMOUNT_MISMATCH",
       "explanation": "supplier_id SUP-0002 on both sides; reference 'OSF-027802' vs 'OSF-027802' normalize to OSF027802; currency MXN on both sides; |3062.1000 - 2755.8900| = 306.2100 vs tolerance 0.0100",
       "flags": [],
       "invoice_currency": "MXN",
       "invoice_id": "EI-202604-03618",
       "invoice_line": 19,
       "invoice_reference": "OSF-027802",
       "invoice_total": "3062.1000",
       "ledger_amount": "2755.8900",
       "ledger_currency": "MXN",
       "ledger_line": 1410,
       "ledger_reference": "OSF-027802",
       "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
       "reference_key": "OSF027802",
       "supplier_id": "SUP-0002",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-003604"
      }
     ],
     "title": "Amount mismatch"
    },
    {
     "rows": [
      {
       "amount_difference": null,
       "decision": "CURRENCY_MISMATCH",
       "explanation": "supplier_id SUP-0043 on both sides; reference 'CRC-036668' vs 'CRC-036668' normalize to CRC036668; currency USD vs CAD: amounts not compared (no conversion rule)",
       "flags": [],
       "invoice_currency": "USD",
       "invoice_id": "EI-202604-02390",
       "invoice_line": 15,
       "invoice_reference": "CRC-036668",
       "invoice_total": "12984.9700",
       "ledger_amount": "12984.9700",
       "ledger_currency": "CAD",
       "ledger_line": 4808,
       "ledger_reference": "CRC-036668",
       "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
       "reference_key": "CRC036668",
       "supplier_id": "SUP-0043",
       "tolerance": null,
       "transaction_id": "GL-202604-002395"
      }
     ],
     "title": "Currency mismatch"
    },
    {
     "rows": [
      {
       "amount_difference": "4715.7200",
       "decision": "NOT_DECIDED_MULTIPLE_CANDIDATES",
       "explanation": "supplier_id SUP-0012 on both sides; reference 'SAT-021651' vs 'SAT-021651' normalize to SAT021651; currency CAD on both sides; |13564.1500 - 18279.8700| = 4715.7200 vs tolerance 0.0100; 2 invoice(s) and 1 ledger record(s) share this key: not decided",
       "flags": [],
       "invoice_currency": "CAD",
       "invoice_id": "EI-202604-03177",
       "invoice_line": 3,
       "invoice_reference": "SAT-021651",
       "invoice_total": "13564.1500",
       "ledger_amount": "18279.8700",
       "ledger_currency": "CAD",
       "ledger_line": 1240,
       "ledger_reference": "SAT-021651",
       "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
       "reference_key": "SAT021651",
       "supplier_id": "SUP-0012",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-003171"
      },
      {
       "amount_difference": "0.0000",
       "decision": "NOT_DECIDED_MULTIPLE_CANDIDATES",
       "explanation": "supplier_id SUP-0012 on both sides; reference 'SAT-021651' vs 'SAT-021651' normalize to SAT021651; currency CAD on both sides; |18279.8700 - 18279.8700| = 0.0000 vs tolerance 0.0100; 2 invoice(s) and 1 ledger record(s) share this key: not decided",
       "flags": [],
       "invoice_currency": "CAD",
       "invoice_id": "EI-202604-03176",
       "invoice_line": 724,
       "invoice_reference": "SAT-021651",
       "invoice_total": "18279.8700",
       "ledger_amount": "18279.8700",
       "ledger_currency": "CAD",
       "ledger_line": 1240,
       "ledger_reference": "SAT-021651",
       "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
       "reference_key": "SAT021651",
       "supplier_id": "SUP-0012",
       "tolerance": "0.0100",
       "transaction_id": "GL-202604-003171"
      }
     ],
     "title": "Several candidates, not decided"
    }
   ],
   "exceptions": {
    "by_priority": {
     "HIGH": 736,
     "LOW": 386,
     "MEDIUM": 1054
    },
    "by_status": {
     "AMBIGUOUS": 228,
     "AMOUNT_MISMATCH": 318,
     "CURRENCY_MISMATCH": 150,
     "DUPLICATE": 142,
     "INVALID_RECORD": 266,
     "MATCHED": 386,
     "ONLY_IN_INVOICES": 337,
     "ONLY_IN_LEDGER": 349
    },
    "sample": [
     {
      "flags": [],
      "line_number": 3,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202604-03177",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 15,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202604-02390",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 19,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202604-03618",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 25,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_LEDGER_ENTRIES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202604-03018",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 37,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202604-01165",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 39,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_LEDGER_ENTRIES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202604-05013",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 40,
      "priority": "HIGH",
      "reason_code": "MULTIPLE_INVOICES_FOR_KEY",
      "recommended_action": "Several records share supplier and reference (possible double posting); decide which belong together.",
      "record_id": "EI-202604-00329",
      "side": "INVOICE",
      "status": "AMBIGUOUS",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 44,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202604-03980",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 82,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202604-02132",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 106,
      "priority": "HIGH",
      "reason_code": "DUPLICATE_CONFLICT",
      "recommended_action": "Same record ID with different content; ask the source owner which version is valid.",
      "record_id": "EI-202604-02714",
      "side": "INVOICE",
      "status": "DUPLICATE",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 108,
      "priority": "HIGH",
      "reason_code": "CURRENCY_DIFFERS_NO_CONVERSION",
      "recommended_action": "Confirm the document currency; amounts in different currencies are never compared.",
      "record_id": "EI-202604-00197",
      "side": "INVOICE",
      "status": "CURRENCY_MISMATCH",
      "suggestion_count": 0
     },
     {
      "flags": [],
      "line_number": 113,
      "priority": "HIGH",
      "reason_code": "DIFFERENCE_ABOVE_TOLERANCE",
      "recommended_action": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
      "record_id": "EI-202604-02186",
      "side": "INVOICE",
      "status": "AMOUNT_MISMATCH",
      "suggestion_count": 0
     }
    ],
    "total": 2176
   },
   "generator": {
    "base_invoices": 5000,
    "batch_index": 1,
    "name": "invoice_recon.generator",
    "seed": 4242,
    "version": "1"
   },
   "layers": {
    "bronze": {
     "ERP_LEDGER": {
      "parse_errors": 8,
      "rows": 5067
     },
     "E_INVOICES": {
      "parse_errors": 9,
      "rows": 5095
     }
    },
    "gold": {
     "INVOICE": {
      "AMBIGUOUS": 104,
      "AMOUNT_MISMATCH": 159,
      "CURRENCY_MISMATCH": 75,
      "DUPLICATE": 87,
      "INVALID_RECORD": 147,
      "MATCHED": 4186,
      "ONLY_IN_INVOICES": 337
     },
     "LEDGER": {
      "AMBIGUOUS": 124,
      "AMOUNT_MISMATCH": 159,
      "CURRENCY_MISMATCH": 75,
      "DUPLICATE": 55,
      "INVALID_RECORD": 119,
      "MATCHED": 4186,
      "ONLY_IN_LEDGER": 349
     }
    },
    "ingestion_errors": {
     "ERP_LEDGER": {
      "MALFORMED_ROW": 6,
      "SCHEMA_DRIFT": 2
     },
     "E_INVOICES": {
      "MALFORMED_ROW": 9
     }
    },
    "landing_records": {
     "ERP_LEDGER": 5067,
     "E_INVOICES": 5095
    },
    "quarantined": 408,
    "silver": {
     "ERP_LEDGER": {
      "DUPLICATE": 55,
      "INVALID": 119,
      "VALID": 4893
     },
     "E_INVOICES": {
      "DUPLICATE": 87,
      "INVALID": 147,
      "VALID": 4861
     }
    }
   },
   "matched_amounts_by_currency": [
    {
     "amount": "4717450.0200",
     "currency": "CAD",
     "records": 358
    },
    {
     "amount": "7627319.4000",
     "currency": "EUR",
     "records": 560
    },
    {
     "amount": "119205148.0000",
     "currency": "JPY",
     "records": 99
    },
    {
     "amount": "12778569.8400",
     "currency": "MXN",
     "records": 959
    },
    {
     "amount": "30384069.5900",
     "currency": "USD",
     "records": 2210
    }
   ],
   "metrics": {
    "ambiguous_records": 228,
    "amount_mismatch_pairs": 159,
    "candidate_suggestions": 50,
    "currency_mismatch_pairs": 75,
    "duplicate_records": 142,
    "eligible_reconciliation_rate": "0.8611",
    "invalid_records": 266,
    "invoice_records": 5095,
    "ledger_records": 5067,
    "matched_pairs": 4186,
    "only_in_invoices": 337,
    "only_in_ledger": 349,
    "reconciliation_period": "2026-04",
    "reconciliation_rate": "0.8216",
    "records_requiring_review": 2176,
    "records_with_dq_errors": 266,
    "records_with_dq_warnings": 233,
    "rules_version": "2026.1"
   },
   "quarantine_sample": [
    {
     "_line_number": 42,
     "_raw_line": "{\"transaction_id\": \"GL-202604-004302\", \"invoice_reference\": \"QUO-008283\", \"supplier_id\": \"SUP-0039\", \"supplier_name\": \"Quillbrook Office Supplies Co\", \"posting_date\": \"2026-02-30\", \"currency\": \"USD\", \"recorded_amount\": \"8904.33\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_DATE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202604-004302",
     "record_status": "INVALID",
     "status_reason": "INVALID_DATE"
    },
    {
     "_line_number": 71,
     "_raw_line": "{\"transaction_id\": \"GL-202604-002924\", \"invoice_reference\": \"DEF-018729\", \"supplier_id\": \"SUP-0029\", \"supplier_name\": \"Delmora Fixtures Inc\", \"posting_date\": \"2026-04-03\", \"currency\": \"USD\", \"recorded_amount\": \"12550.51\", \"payment_status\": \"PARTIALLY_PAID\", \"accounting_period\": \"2026-00\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_PERIOD"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202604-002924",
     "record_status": "INVALID",
     "status_reason": "INVALID_PERIOD"
    },
    {
     "_line_number": 144,
     "_raw_line": "{\"transaction_id\": \"GL-202604-003119\", \"invoice_reference\": null, \"supplier_id\": \"SUP-0009\", \"supplier_name\": \"Wrenfold Fixtures Inc\", \"posting_date\": \"2026-04-30\", \"currency\": \"EUR\", \"recorded_amount\": 13638.79, \"payment_status\": \"OPEN\", \"accounting_period\": \"202604\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MISSING_REFERENCE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202604-003119",
     "record_status": "INVALID",
     "status_reason": "MISSING_REFERENCE"
    },
    {
     "_line_number": 146,
     "_raw_line": "{\"transaction_id\": \"\", \"invoice_reference\": \"UMT-032307\", \"supplier_id\": \"SUP-0019\", \"supplier_name\": \"Umbervale Tooling Ltd\", \"posting_date\": \"2026-04-08\", \"currency\": \"MXN\", \"recorded_amount\": \"17272.31\", \"payment_status\": \"OPEN\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MISSING_TRANSACTION_ID"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": null,
     "record_status": "INVALID",
     "status_reason": "MISSING_TRANSACTION_ID"
    },
    {
     "_line_number": 147,
     "_raw_line": "{\"transaction_id\": \"GL-202604-001764\", \"invoice_reference\": null, \"supplier_id\": \"SUP-0002\", \"supplier_name\": \"Ostravale Fixtures, Co\", \"posting_date\": \"2026-04-13\", \"currency\": \"MXN\", \"recorded_amount\": \"14,561.58\", \"payment_status\": \"PARTIALLY_PAID\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MISSING_REFERENCE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202604-001764",
     "record_status": "INVALID",
     "status_reason": "MISSING_REFERENCE"
    },
    {
     "_line_number": 224,
     "_raw_line": "{\"transaction_id\": \"GL-202604-001202\", \"invoice_reference\": \"ISE-012112\", \"supplier_id\": \"SUP-0015\", \"supplier_name\": \"Istrella Electrical LLC\", \"posting_date\": \"31/02/2026\", \"currency\": \"CAD\", \"recorded_amount\": 6246.59, \"payment_status\": \"PARTIALLY_PAID\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "INVALID_DATE"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": "GL-202604-001202",
     "record_status": "INVALID",
     "status_reason": "INVALID_DATE"
    },
    {
     "_line_number": 235,
     "_raw_line": "{\"transaction_id\": \"GL-202604-002438\", \"invoice_reference\": \"DEP-025697\", \"supplier_id\": \"SUP-0037\", \"supplier_name\": \"Delmora Polymers Ltd\", \"posting_date\": \"2026-04-13\", \"currency\": \"USD\", \"recorded_amount\": \"2668.44\", \"payment_status\": \"PAID\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [],
     "dq_warnings": [],
     "duplicate_of_line": 29,
     "record_id": "GL-202604-002438",
     "record_status": "DUPLICATE",
     "status_reason": "DUPLICATE_EXACT"
    },
    {
     "_line_number": 338,
     "_raw_line": "{\"transaction_id\": \"GL-202604-002423\", \"invoice_reference\": \"DEF-018675\", \"supplier_id\": \"SUP-0029\", \"supplier_name\": \"Delmora Fixtures Inc\", \"posting_date\": \"19/04/2026\", \"currency\": \"USD\", \"amount\": \"20987.23\", \"payment_status\": \"PARTIALLY_PAID\", \"accounting_period\": \"2026-04\"}",
     "_source_system": "ERP_LEDGER",
     "dq_errors": [
      "MALFORMED_ROW"
     ],
     "dq_warnings": [],
     "duplicate_of_line": null,
     "record_id": null,
     "record_status": "INVALID",
     "status_reason": "MALFORMED_ROW"
    }
   ],
   "reconciliation_period": "2026-04",
   "rules_version": "2026.1",
   "status_table": [
    {
     "invoices": 4186,
     "ledger": 4186,
     "status": "MATCHED"
    },
    {
     "invoices": 159,
     "ledger": 159,
     "status": "AMOUNT_MISMATCH"
    },
    {
     "invoices": 75,
     "ledger": 75,
     "status": "CURRENCY_MISMATCH"
    },
    {
     "invoices": 337,
     "ledger": 0,
     "status": "ONLY_IN_INVOICES"
    },
    {
     "invoices": 0,
     "ledger": 349,
     "status": "ONLY_IN_LEDGER"
    },
    {
     "invoices": 104,
     "ledger": 124,
     "status": "AMBIGUOUS"
    },
    {
     "invoices": 87,
     "ledger": 55,
     "status": "DUPLICATE"
    },
    {
     "invoices": 147,
     "ledger": 119,
     "status": "INVALID_RECORD"
    }
   ],
   "suggestions": [
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.889; supplier SUP-0001 'Amberlyn Castings Ltd' vs SUP-0001 'Amberlyn Castings Ltd' (name similarity 1.000); reference 'AMC-038710' vs 'AMC-38710' (similarity 0.889); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-04161",
     "invoice_line": 41,
     "invoice_reference": "AMC-038710",
     "invoice_supplier_id": "SUP-0001",
     "invoice_supplier_name": "Amberlyn Castings Ltd",
     "ledger_line": 424,
     "ledger_reference": "AMC-38710",
     "ledger_supplier_id": "SUP-0001",
     "ledger_supplier_name": "Amberlyn Castings Ltd",
     "name_similarity": "1.000",
     "reference_similarity": "0.889",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.889",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-004144"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.944; supplier SUP-0003 'Corvantis Coatings Inc' vs SUP-0043 'Corvantis Coating Co' (name similarity 0.944); reference 'COC-039372' vs 'COC-039372' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-01113",
     "invoice_line": 191,
     "invoice_reference": "COC-039372",
     "invoice_supplier_id": "SUP-0003",
     "invoice_supplier_name": "Corvantis Coatings Inc",
     "ledger_line": 4165,
     "ledger_reference": "COC-039372",
     "ledger_supplier_id": "SUP-0043",
     "ledger_supplier_name": "Corvantis Coating Co",
     "name_similarity": "0.944",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.944",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-001113"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.944; supplier SUP-0002 'Ostravale Fixtures, Co' vs SUP-0042 'Ostravale Fixture Inc' (name similarity 0.944); reference 'OSF-027795' vs 'OSF-027795' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-03581",
     "invoice_line": 235,
     "invoice_reference": "OSF-027795",
     "invoice_supplier_id": "SUP-0002",
     "invoice_supplier_name": "Ostravale Fixtures, Co",
     "ledger_line": 2036,
     "ledger_reference": "OSF-027795",
     "ledger_supplier_id": "SUP-0042",
     "ledger_supplier_name": "Ostravale Fixture Inc",
     "name_similarity": "0.944",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.944",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-003569"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.889; supplier SUP-0015 'Istrella Electrical LLC' vs SUP-0015 'Istrella Electrical LLC' (name similarity 1.000); reference 'ISE-012413' vs 'ISE-12413' (similarity 0.889); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-04280",
     "invoice_line": 264,
     "invoice_reference": "ISE-012413",
     "invoice_supplier_id": "SUP-0015",
     "invoice_supplier_name": "Istrella Electrical LLC",
     "ledger_line": 3637,
     "ledger_reference": "ISE-12413",
     "ledger_supplier_id": "SUP-0015",
     "ledger_supplier_name": "Istrella Electrical LLC",
     "name_similarity": "1.000",
     "reference_similarity": "0.889",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.889",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-004262"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.944; supplier SUP-0005 'Marrowind Polymers Co' vs SUP-0045 'Marrowind Polymer Ltd' (name similarity 0.944); reference 'MAP-018576' vs 'MAP-018576' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-01380",
     "invoice_line": 282,
     "invoice_reference": "MAP-018576",
     "invoice_supplier_id": "SUP-0005",
     "invoice_supplier_name": "Marrowind Polymers Co",
     "ledger_line": 1064,
     "ledger_reference": "MAP-018576",
     "ledger_supplier_id": "SUP-0045",
     "ledger_supplier_name": "Marrowind Polymer Ltd",
     "name_similarity": "0.944",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.944",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-001383"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.778; supplier SUP-0013 'Fenlowe Fixtures Ltd' vs SUP-0013 'Fenlowe Fixtures Ltd' (name similarity 1.000); reference 'FEF-007128' vs 'FEF-7128' (similarity 0.778); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-04712",
     "invoice_line": 478,
     "invoice_reference": "FEF-007128",
     "invoice_supplier_id": "SUP-0013",
     "invoice_supplier_name": "Fenlowe Fixtures Ltd",
     "ledger_line": 4741,
     "ledger_reference": "FEF-7128",
     "ledger_supplier_id": "SUP-0013",
     "ledger_supplier_name": "Fenlowe Fixtures Ltd",
     "name_similarity": "1.000",
     "reference_similarity": "0.778",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.778",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-004698"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE",
     "currency_equal": true,
     "explanation": "criterion SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE, score 0.889; supplier SUP-0038 'Corvantis Office Supplies LLC' vs SUP-0038 'Corvantis Office Supplies LLC' (name similarity 1.000); reference 'COO-030589' vs 'COO-30589' (similarity 0.889); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-03113",
     "invoice_line": 502,
     "invoice_reference": "COO-030589",
     "invoice_supplier_id": "SUP-0038",
     "invoice_supplier_name": "Corvantis Office Supplies LLC",
     "ledger_line": 1592,
     "ledger_reference": "COO-30589",
     "ledger_supplier_id": "SUP-0038",
     "ledger_supplier_name": "Corvantis Office Supplies LLC",
     "name_similarity": "1.000",
     "reference_similarity": "0.889",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.889",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-003105"
    },
    {
     "amount_difference": "0.0000",
     "auto_approved": false,
     "criterion": "SAME_REFERENCE_DIFFERENT_SUPPLIER",
     "currency_equal": true,
     "explanation": "criterion SAME_REFERENCE_DIFFERENT_SUPPLIER, score 0.938; supplier SUP-0004 'Vexmoor Polymers Co' vs SUP-0044 'Vexmoor Polymer Co' (name similarity 0.938); reference 'VEP-004315' vs 'VEP-004315' (similarity 1.000); suggestion only: deterministic identifiers disagree, a person must decide",
     "invoice_id": "EI-202604-01102",
     "invoice_line": 588,
     "invoice_reference": "VEP-004315",
     "invoice_supplier_id": "SUP-0004",
     "invoice_supplier_name": "Vexmoor Polymers Co",
     "ledger_line": 4016,
     "ledger_reference": "VEP-004315",
     "ledger_supplier_id": "SUP-0044",
     "ledger_supplier_name": "Vexmoor Polymer Co",
     "name_similarity": "0.938",
     "reference_similarity": "1.000",
     "review_action": "HUMAN_REVIEW_REQUIRED",
     "score": "0.938",
     "suggestion_rank": 1,
     "transaction_id": "GL-202604-001103"
    }
   ],
   "synthetic": true,
   "validation": {
    "batch_id": "batch-2026-04",
    "checks": [
     {
      "check_id": "LANDING_TO_BRONZE[E_INVOICES]",
      "detail": "5095 non-blank landing records, 5095 bronze rows",
      "passed": true
     },
     {
      "check_id": "BRONZE_TO_SILVER[E_INVOICES]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_TO_GOLD[INVOICE]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_STATUS_PARTITION[E_INVOICES]",
      "detail": "statuses {'DUPLICATE': 87, 'INVALID': 147, 'VALID': 4861}",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_COMPLETE[E_INVOICES]",
      "detail": "234 quarantined, 234 non-VALID silver rows",
      "passed": true
     },
     {
      "check_id": "LANDING_TO_BRONZE[ERP_LEDGER]",
      "detail": "5067 non-blank landing records, 5067 bronze rows",
      "passed": true
     },
     {
      "check_id": "BRONZE_TO_SILVER[ERP_LEDGER]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_TO_GOLD[LEDGER]",
      "detail": "0 lost, 0 added",
      "passed": true
     },
     {
      "check_id": "SILVER_STATUS_PARTITION[ERP_LEDGER]",
      "detail": "statuses {'DUPLICATE': 55, 'INVALID': 119, 'VALID': 4893}",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_COMPLETE[ERP_LEDGER]",
      "detail": "174 quarantined, 174 non-VALID silver rows",
      "passed": true
     },
     {
      "check_id": "QUARANTINE_HAS_REASON",
      "detail": "0 quarantined rows without a reason",
      "passed": true
     },
     {
      "check_id": "GOLD_ONE_ROW_PER_RECORD",
      "detail": "0 records with more than one status",
      "passed": true
     },
     {
      "check_id": "STATUS_IN_CATALOG",
      "detail": "0 rows with an unknown status",
      "passed": true
     },
     {
      "check_id": "NO_NULL_KEY_MATCH",
      "detail": "0 MATCHED rows with a NULL key or record ID",
      "passed": true
     },
     {
      "check_id": "ONE_TO_ONE_MATCHES",
      "detail": "matched invoices, matched ledger rows, evidence rows, distinct invoice lines, distinct ledger lines = 4186, 4186, 4186, 4186, 4186",
      "passed": true
     },
     {
      "check_id": "COUNTERPARTS_SYMMETRIC",
      "detail": "0 decided pairs whose two sides disagree",
      "passed": true
     },
     {
      "check_id": "MATCHED_SAME_CURRENCY",
      "detail": "0 MATCHED pairs with different currencies",
      "passed": true
     },
     {
      "check_id": "MATCHED_WITHIN_TOLERANCE",
      "detail": "0 MATCHED pairs outside tolerance",
      "passed": true
     },
     {
      "check_id": "NO_CROSS_CURRENCY_COMPARISON",
      "detail": "0 currency mismatches with a computed amount difference",
      "passed": true
     },
     {
      "check_id": "ONLY_VALID_RECORDS_DECIDED",
      "detail": "0 non-VALID records that reached a matching status",
      "passed": true
     },
     {
      "check_id": "SUGGESTIONS_NEVER_APPROVED",
      "detail": "0 suggestions auto-approved or attached to a record that is not ONLY_IN_*",
      "passed": true
     },
     {
      "check_id": "EXCEPTIONS_MATCH_REVIEW_FLAG",
      "detail": "2176 exceptions, 2176 records requiring review",
      "passed": true
     },
     {
      "check_id": "METRICS_CONSISTENT",
      "detail": "recomputed (5095, 5067, 4186, 2176, 50), stored (5095, 5067, 4186, 2176, 50)",
      "passed": true
     },
     {
      "check_id": "SYNTHETIC_GROUND_TRUTH",
      "detail": "10162/10162 records match their designed outcome",
      "passed": true
     },
     {
      "check_id": "SYNTHETIC_SUGGESTIONS",
      "detail": "50/50 designed suggestions produced",
      "passed": true
     }
    ],
    "passed": true
   },
   "versions": {
    "delta-spark": "4.2.0",
    "fabric-invoice-reconciliation": "0.1.0",
    "pyspark": "4.1.1"
   }
  }
 ],
 "project": "fabric-invoice-reconciliation",
 "source": "Local PySpark + Delta Lake run of this repository on synthetic data (fictional companies).",
 "synthetic": true,
 "totals": {
  "ambiguous_records": 441,
  "amount_mismatch_pairs": 298,
  "candidate_suggestions": 101,
  "currency_mismatch_pairs": 137,
  "duplicate_records": 297,
  "invalid_records": 522,
  "invoice_records": 10196,
  "ledger_records": 10108,
  "matched_pairs": 8410,
  "only_in_invoices": 678,
  "only_in_ledger": 676,
  "records_requiring_review": 4334,
  "records_with_dq_errors": 522,
  "records_with_dq_warnings": 520
 },
 "versions": {
  "delta-spark": "4.2.0",
  "fabric-invoice-reconciliation": "0.1.0",
  "pyspark": "4.1.1"
 }
};
