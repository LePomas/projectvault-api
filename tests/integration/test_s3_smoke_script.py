import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "s3-smoke-test.sh"
STALE_RESPONSE_FILE = Path("/tmp/projectvault-smoke-response.json")


FAKE_CURL = r"""#!/usr/bin/env python3
import os
import sys

MODE = os.environ.get("FAKE_CURL_MODE", "success")


def arg_after(args, name):
    try:
        return args[args.index(name) + 1]
    except ValueError:
        return None


def find_url(args):
    for arg in args:
        if arg.startswith("http://") or arg.startswith("https://"):
            return arg
    return ""


def write_response(path, body):
    if path:
        with open(path, "w", encoding="utf-8") as response:
            response.write(body)


args = sys.argv[1:]
output_file = arg_after(args, "-o")
url = find_url(args)

if MODE == "connection_failure":
    print(
        "curl: (7) Failed to connect to 127.0.0.1 port 9 after 0 ms: "
        "Could not connect to server",
        file=sys.stderr,
    )
    sys.exit(7)

if "/auth/register" in url:
    write_response(
        output_file,
        '{"id":1,"login":"s3smoke-test","email":"s3smoke-test@example.com"}',
    )
    print("201", end="")
elif "/auth/login" in url:
    write_response(output_file, '{"access_token":"test-token"}')
    print("200", end="")
elif url.endswith("/projects"):
    write_response(output_file, '{"id":1,"name":"S3 Smoke Test"}')
    print("201", end="")
elif "/projects/1/documents/presign-upload" in url:
    if MODE == "presign_error":
        write_response(output_file, "Internal Server Error")
        print("500", end="")
    else:
        write_response(
            output_file,
            '{"document_id":1,'
            '"storage_key":"projects/1/smoke.pdf",'
            '"upload_url":"https://projectvault-documents.s3.amazonaws.com/upload",'
            '"headers":{"Content-Type":"application/pdf"},'
            '"expires_in":900}',
        )
        print("201", end="")
elif url == "https://projectvault-documents.s3.amazonaws.com/upload":
    write_response(output_file, "")
    print("200", end="")
elif "/projects/1/documents/complete-upload" in url:
    write_response(output_file, '{"id":1,"status":"uploaded","size_bytes":20}')
    print("200", end="")
elif "/documents/1/download-url" in url:
    write_response(
        output_file,
        '{"download_url":"https://projectvault-documents.s3.amazonaws.com/download",'
        '"expires_in":900}',
    )
    print("200", end="")
elif url == "https://projectvault-documents.s3.amazonaws.com/download":
    print("%PDF-1.7 smoke test", end="")
else:
    write_response(output_file, "Not Found")
    print("404", end="")
"""


def run_smoke_script(tmp_path: Path, *, mode: str = "success"):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(FAKE_CURL)
    fake_curl.chmod(0o755)

    env = os.environ.copy()
    env["BASE"] = "http://testserver"
    env["FAKE_CURL_MODE"] = mode
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    return subprocess.run(
        [str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def test_s3_smoke_script_passes_against_presigned_flow(tmp_path: Path) -> None:
    result = run_smoke_script(tmp_path)

    assert result.returncode == 0
    assert "S3 smoke test passed." in result.stdout
    assert "https://projectvault-documents.s3.amazonaws.com/upload" in result.stdout


def test_s3_smoke_script_reports_non_json_api_errors_without_jq_parse_error(
    tmp_path: Path,
) -> None:
    result = run_smoke_script(tmp_path, mode="presign_error")

    assert result.returncode == 1
    assert (
        "API request failed: POST /projects/1/documents/presign-upload "
        "returned HTTP 500"
    ) in result.stderr
    assert "Internal Server Error" in result.stderr
    assert "jq: parse error" not in result.stderr


def test_s3_smoke_script_does_not_print_stale_response_after_connection_failure(
    tmp_path: Path,
) -> None:
    STALE_RESPONSE_FILE.write_text('{"download_url":"http://localhost:9000/stale"}')

    result = run_smoke_script(tmp_path, mode="connection_failure")

    assert result.returncode == 1
    assert "could not connect" in result.stderr
    assert "download_url" not in result.stderr
