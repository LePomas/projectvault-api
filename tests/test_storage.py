from app.services.storage import S3DocumentStorage


class FakeS3Client:
    def __init__(self, endpoint_url: str | None) -> None:
        self.endpoint_url = endpoint_url

    def generate_presigned_url(
        self,
        operation: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        return (
            f"{self.endpoint_url}/{Params['Bucket']}/{Params['Key']}"
            f"?operation={operation}&expires={ExpiresIn}"
        )


def test_s3_presigned_urls_are_signed_with_public_endpoint(
    monkeypatch,
) -> None:
    created_endpoints: list[str | None] = []

    def fake_create_client(
        *,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str,
    ) -> FakeS3Client:
        created_endpoints.append(endpoint_url)
        return FakeS3Client(endpoint_url)

    monkeypatch.setattr(
        S3DocumentStorage,
        "_create_client",
        staticmethod(fake_create_client),
    )

    storage = S3DocumentStorage(
        bucket="projectvault-documents",
        endpoint_url="http://minio:9000",
        public_endpoint_url="http://localhost:9000",
        access_key="projectvault",
        secret_key="projectvault-secret",
        region="us-east-1",
        expires_in=900,
    )

    presigned = storage.presign_download("projects/7/example.pdf")

    assert created_endpoints == ["http://minio:9000", "http://localhost:9000"]
    assert presigned.url == (
        "http://localhost:9000/projectvault-documents/projects/7/example.pdf"
        "?operation=get_object&expires=900"
    )
