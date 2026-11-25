"""The Fabric notebook is valid nbformat and its code cells run against local Spark.

This proves the notebook's logic and API usage locally. It does not prove execution in
Microsoft Fabric: the %pip cell is skipped and the lakehouse is a local directory.
"""

from pathlib import Path

import nbformat
import pytest

import invoice_recon

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "fabric_invoice_reconciliation.ipynb"


def _notebook():
    return nbformat.read(NOTEBOOK, as_version=4)


def test_notebook_is_valid_and_marks_fabric_as_not_tested():
    nb = _notebook()
    nbformat.validate(nb)
    text = "\n".join(cell.source for cell in nb.cells)
    assert "execution inside Microsoft Fabric has NOT been tested" in text and "lh_invoice_recon" in text
    assert any("parameters" in cell.metadata.get("tags", []) for cell in nb.cells)
    assert all(not cell.get("outputs") for cell in nb.cells if cell.cell_type == "code"), "committed without outputs"
    assert f"fabric_invoice_reconciliation-{invoice_recon.__version__}-py3-none-any.whl" in text


@pytest.mark.spark
def test_notebook_code_cells_run_locally(spark, tmp_path, capsys):
    nb = _notebook()
    namespace = {"spark": spark}
    overrides = (f'LAKEHOUSE_FILES_DIR = r"{tmp_path}"\nLAKEHOUSE_SPARK_ROOT = "{tmp_path.as_posix()}"\n'
                 "BATCHES = 1\nINVOICES_PER_BATCH = 100\n")
    executed = 0
    for cell in nb.cells:
        if cell.cell_type != "code" or cell.source.lstrip().startswith("%"):
            continue
        exec(compile(cell.source, f"<notebook cell {executed}>", "exec"), namespace)  # noqa: S102 - our own notebook
        if "parameters" in cell.metadata.get("tags", []):
            exec(overrides, namespace)  # noqa: S102
        executed += 1
    out = capsys.readouterr().out
    assert namespace["batch_ids"] == ["batch-2026-03"]
    assert "batch-2026-03 PASSED" in out and "FAIL" not in out
    assert "# Reconciliation report: batch-2026-03" in out
    assert executed >= 9
