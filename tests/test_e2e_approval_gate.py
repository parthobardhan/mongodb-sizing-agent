import pytest

from agent.tools_runner import run_tools_pipeline

pytestmark = pytest.mark.integration


def test_run_tools_pipeline_raises_when_not_approved(temp_case_dir, mongo_uri, docker_stack):
    data_model = temp_case_dir / "outputs" / "data-model.md"
    text = data_model.read_text(encoding="utf-8")
    data_model.write_text(
        text.replace("approved", "pending").replace("Approved", "Pending"),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="approved"):
        run_tools_pipeline(temp_case_dir, uri=mongo_uri, no_cleanup=True)
