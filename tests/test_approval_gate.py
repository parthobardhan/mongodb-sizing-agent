from pathlib import Path

from agent.session import read_approval_status

EXAMPLE_MODEL = (
    Path(__file__).resolve().parent.parent / "cases/_example/outputs/data-model.md"
)


def test_example_data_model_is_approved():
    assert read_approval_status(EXAMPLE_MODEL) == "approved"
