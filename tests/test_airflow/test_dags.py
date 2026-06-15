"""Tests for the Airflow DAG definitions.

The DAG modules import ``airflow`` at module top, so importing them requires the
optional ``[airflow]`` extra. The structural tests below parse the source with
``ast`` (no airflow needed) so they always run in CI; the import-based test is
skipped unless airflow is installed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DAGS_DIR = Path(__file__).resolve().parents[2] / "startupintel" / "airflow" / "dags"

EXPECTED_DAG_IDS = {
    "run_runway_bot.py": "runway_bot_daily",
    "run_obituary_bot.py": "obituary_bot_weekly",
    "run_term_bot.py": "term_bot_daily",
    "run_pivot_bot.py": "pivot_bot_weekly",
    "run_pmf_bot.py": "pmf_bot_daily",
    "run_accelerator_bot.py": "accelerator_bot_weekly",
    "run_investor_bot.py": "investor_bot_daily",
    "run_acqui_bot.py": "acqui_bot_weekly",
    "weekly_digest.py": "weekly_digest",
}


def test_all_expected_dag_files_present():
    present = {p.name for p in DAGS_DIR.glob("*.py") if p.name != "__init__.py"}
    assert present == set(EXPECTED_DAG_IDS)


@pytest.mark.parametrize("filename,dag_id", sorted(EXPECTED_DAG_IDS.items()))
def test_dag_source_is_valid_and_declares_expected_id(filename, dag_id):
    source = (DAGS_DIR / filename).read_text()
    tree = ast.parse(source)  # must be syntactically valid

    # The first positional arg of the DAG(...) call is the dag_id.
    dag_ids = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "DAG"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert dag_ids == [dag_id]
    assert "PythonOperator" in source
    assert "schedule_interval" in source


def test_dags_import_with_airflow_installed():
    pytest.importorskip("airflow")

    import importlib

    for filename, dag_id in EXPECTED_DAG_IDS.items():
        module_name = f"startupintel.airflow.dags.{filename[:-3]}"
        module = importlib.import_module(module_name)
        assert module.dag.dag_id == dag_id
