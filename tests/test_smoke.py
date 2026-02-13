"""Smoke tests for excel-model-eval."""
import os
def test_sample_models_exist():
    assert os.path.isdir(os.path.join(os.path.dirname(__file__), "..", "sample_models"))
def test_eval_rubrics_exist():
    assert os.path.isdir(os.path.join(os.path.dirname(__file__), "..", "eval", "llm_rubrics"))
