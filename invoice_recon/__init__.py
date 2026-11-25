"""Invoice reconciliation on PySpark + Delta Lake, laid out like a Microsoft Fabric Lakehouse.

Bronze ingests two synthetic sources as raw strings, Silver normalizes and quality-checks
them, Gold reconciles them with deterministic rules and records the evidence for every
decision. All data is synthetic; see README.md for what is implemented and what is not.
"""

__version__ = "0.1.0"
