import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_SKIP_REASON = (
    "E2E tests require PROJECTVAULT_RUN_E2E=1 and an already-running "
    "S3-backed Docker Compose stack."
)

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("PROJECTVAULT_RUN_E2E") != "1",
        reason=E2E_SKIP_REASON,
    ),
]


def run_smoke_script(script_name: str) -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / script_name)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, (
        f"{script_name} exited with {result.returncode}\n\n"
        f"stdout:\n{result.stdout}\n\n"
        f"stderr:\n{result.stderr}"
    )


def test_s3_presigned_upload_smoke_script() -> None:
    run_smoke_script("s3-smoke-test.sh")


def test_s3_event_upload_smoke_script() -> None:
    run_smoke_script("s3-event-smoke-test.sh")
