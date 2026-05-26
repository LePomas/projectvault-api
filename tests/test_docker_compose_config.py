from pathlib import Path


def test_compose_allows_blank_s3_endpoint_values_for_aws() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "S3_ENDPOINT_URL: ${S3_ENDPOINT_URL-http://minio:9000}" in compose
    assert (
        "S3_PUBLIC_ENDPOINT_URL: ${S3_PUBLIC_ENDPOINT_URL-http://localhost:9000}"
    ) in compose
    assert "S3_ENDPOINT_URL: ${S3_ENDPOINT_URL:-http://minio:9000}" not in compose
    assert (
        "S3_PUBLIC_ENDPOINT_URL: ${S3_PUBLIC_ENDPOINT_URL:-http://localhost:9000}"
    ) not in compose
