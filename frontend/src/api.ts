import type {
  DocumentItem,
  DownloadUrl,
  Project,
  ProjectMember,
  ProjectSummary,
  TokenResponse,
  User,
} from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_PROJECTVAULT_API_BASE_URL ?? "https://api.lepomas.xyz";

type RequestOptions = {
  method?: string;
  token?: string | null;
  body?: unknown;
};

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  path: string,
  { method = "GET", token, body }: RequestOptions = {},
): Promise<T> {
  const headers = new Headers();
  if (body !== undefined && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw toApiError(response.status, data);
  }

  return data as T;
}

function toApiError(status: number, data: unknown): ApiError {
  if (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof data.error === "object" &&
    data.error !== null
  ) {
    const error = data.error as {
      code?: unknown;
      message?: unknown;
      details?: unknown;
    };
    return new ApiError(
      status,
      String(error.code ?? "API_ERROR"),
      String(error.message ?? "Request failed."),
      error.details,
    );
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "detail" in data &&
    Array.isArray(data.detail)
  ) {
    const firstError = data.detail[0] as { msg?: unknown } | undefined;
    return new ApiError(
      status,
      "VALIDATION_ERROR",
      String(firstError?.msg ?? "Request validation failed."),
      data.detail,
    );
  }

  return new ApiError(status, "HTTP_ERROR", "Request failed.", data);
}

export const api = {
  register(payload: {
    login: string;
    email: string;
    password: string;
    repeat_password: string;
  }) {
    return request<User>("/auth/register", {
      method: "POST",
      body: payload,
    });
  },
  login(payload: { login: string; password: string }) {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: payload,
    });
  },
  me(token: string) {
    return request<User>("/auth/me", { token });
  },
  createProject(token: string, payload: { name: string; description?: string }) {
    return request<Project>("/project", {
      method: "POST",
      token,
      body: payload,
    });
  },
  listProjects(token: string) {
    return request<ProjectSummary[]>("/projects", { token });
  },
  getProject(token: string, projectId: number) {
    return request<Project>(`/project/${projectId}/info`, { token });
  },
  listMembers(token: string, projectId: number) {
    return request<ProjectMember[]>(`/project/${projectId}/members`, { token });
  },
  grantParticipant(token: string, projectId: number, login: string) {
    const user = encodeURIComponent(login);
    return request<ProjectMember>(`/project/${projectId}/invite?user=${user}`, {
      method: "POST",
      token,
    });
  },
  listDocuments(token: string, projectId: number) {
    return request<DocumentItem[]>(`/project/${projectId}/documents`, { token });
  },
  uploadDocument(token: string, projectId: number, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request<DocumentItem>(`/project/${projectId}/documents`, {
      method: "POST",
      token,
      body: formData,
    });
  },
  downloadUrl(token: string, documentId: number) {
    return request<DownloadUrl>(`/document/${documentId}/download-url`, {
      token,
    });
  },
  renameDocument(token: string, documentId: number, filename: string) {
    return request<DocumentItem>(`/document/${documentId}`, {
      method: "PUT",
      token,
      body: { filename },
    });
  },
  deleteDocument(token: string, documentId: number) {
    return request<void>(`/document/${documentId}`, {
      method: "DELETE",
      token,
    });
  },
};
