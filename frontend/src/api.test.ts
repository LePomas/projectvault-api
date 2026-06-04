import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./api";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      "content-type": "application/json",
      ...Object.fromEntries(new Headers(init.headers).entries()),
    },
  });
}

describe("api client", () => {
  it("serializes JSON requests with bearer auth", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: 1,
        name: "Demo",
        description: null,
        owner_id: 2,
        total_size_bytes: 0,
        documents_count: 0,
        created_at: "2026-06-04T00:00:00Z",
        updated_at: "2026-06-04T00:00:00Z",
      }),
    );

    await api.createProject("token-123", {
      name: "Demo",
      description: "Demo project",
    });

    const [url, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Headers;
    expect(url).toBe("https://api.lepomas.xyz/project");
    expect(init?.method).toBe("POST");
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(init?.body).toBe(
      JSON.stringify({ name: "Demo", description: "Demo project" }),
    );
  });

  it("uploads FormData without forcing a JSON content type", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        id: 7,
        project_id: 3,
        uploaded_by_id: 2,
        filename: "brief.pdf",
        content_type: "application/pdf",
        size_bytes: 12,
        storage_key: "documents/brief.pdf",
        status: "uploaded",
        created_at: "2026-06-04T00:00:00Z",
        updated_at: "2026-06-04T00:00:00Z",
      }),
    );

    await api.uploadDocument(
      "token-123",
      3,
      new File(["pdf"], "brief.pdf", { type: "application/pdf" }),
    );

    const [url, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Headers;
    expect(url).toBe("https://api.lepomas.xyz/project/3/documents");
    expect(init?.method).toBe("POST");
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(headers.has("Content-Type")).toBe(false);
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it("maps ProjectVault error responses to ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          error: {
            code: "PROJECT_NOT_FOUND",
            message: "Project was not found.",
            details: { project_id: 404 },
          },
        },
        { status: 404 },
      ),
    );

    await expect(api.getProject("token-123", 404)).rejects.toMatchObject({
      status: 404,
      code: "PROJECT_NOT_FOUND",
      message: "Project was not found.",
      details: { project_id: 404 },
    });
  });

  it("maps FastAPI validation responses to ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: [{ msg: "Input should be a valid integer" }],
        },
        { status: 422 },
      ),
    );

    await expect(api.getProject("token-123", Number.NaN)).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Input should be a valid integer",
    });
  });

  it("maps non-JSON failures to a generic ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("Gateway timeout", {
        status: 504,
        headers: { "content-type": "text/plain" },
      }),
    );

    await expect(api.listProjects("token-123")).rejects.toEqual(
      new ApiError(504, "HTTP_ERROR", "Request failed.", "Gateway timeout"),
    );
  });

  it("calls the current singular business routes", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({})));

    await api.grantParticipant("token-123", 9, "demo user");
    await api.downloadUrl("token-123", 11);
    await api.renameDocument("token-123", 12, "updated.pdf");
    await api.deleteDocument("token-123", 13);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "https://api.lepomas.xyz/project/9/invite?user=demo%20user",
      "https://api.lepomas.xyz/document/11/download-url",
      "https://api.lepomas.xyz/document/12",
      "https://api.lepomas.xyz/document/13",
    ]);
    expect(fetchMock.mock.calls.map(([, init]) => init?.method ?? "GET")).toEqual([
      "POST",
      "GET",
      "PUT",
      "DELETE",
    ]);
  });
});
