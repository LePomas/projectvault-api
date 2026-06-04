import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { ApiError, api } from "./api";
import type {
  DocumentItem,
  Project,
  ProjectMember,
  ProjectSummary,
  TokenResponse,
  User,
} from "./types";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual,
    api: {
      register: vi.fn(),
      login: vi.fn(),
      me: vi.fn(),
      createProject: vi.fn(),
      listProjects: vi.fn(),
      getProject: vi.fn(),
      listMembers: vi.fn(),
      grantParticipant: vi.fn(),
      listDocuments: vi.fn(),
      uploadDocument: vi.fn(),
      downloadUrl: vi.fn(),
      renameDocument: vi.fn(),
      deleteDocument: vi.fn(),
    },
  };
});

const mockedApi = vi.mocked(api);
const TOKEN_KEY = "projectvault.access_token";

const user: User = {
  id: 1,
  login: "demo-owner",
  email: "demo-owner@example.com",
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

const tokenResponse: TokenResponse = {
  access_token: "jwt-token",
  token_type: "bearer",
  expires_in: 900,
};

const project: Project = {
  id: 10,
  name: "Demo project",
  description: "Controlled demo",
  owner_id: user.id,
  total_size_bytes: 2048,
  documents_count: 1,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

const projectSummary: ProjectSummary = {
  ...project,
  documents: ["brief.pdf"],
};

const members: ProjectMember[] = [
  {
    id: 1,
    project_id: project.id,
    user_id: user.id,
    login: user.login,
    role: "owner",
    created_at: "2026-06-04T00:00:00Z",
  },
];

const documentItem: DocumentItem = {
  id: 50,
  project_id: project.id,
  uploaded_by_id: user.id,
  filename: "brief.pdf",
  content_type: "application/pdf",
  size_bytes: 2048,
  storage_key: "documents/brief.pdf",
  status: "uploaded",
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  vi.spyOn(window, "open").mockImplementation(() => null);

  mockedApi.register.mockResolvedValue(user);
  mockedApi.login.mockResolvedValue(tokenResponse);
  mockedApi.me.mockResolvedValue(user);
  mockedApi.listProjects.mockResolvedValue([projectSummary]);
  mockedApi.createProject.mockResolvedValue(project);
  mockedApi.getProject.mockResolvedValue(project);
  mockedApi.listMembers.mockResolvedValue(members);
  mockedApi.grantParticipant.mockResolvedValue({
    id: 2,
    project_id: project.id,
    user_id: 2,
    login: "demo-participant",
    role: "participant",
    created_at: "2026-06-04T00:00:00Z",
  });
  mockedApi.listDocuments.mockResolvedValue([documentItem]);
  mockedApi.uploadDocument.mockResolvedValue(documentItem);
  mockedApi.downloadUrl.mockResolvedValue({
    download_url: "https://signed.example.com/brief.pdf",
    expires_in: 900,
  });
});

describe("App", () => {
  it("registers, logs in, stores the JWT, and loads the session", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("button", { name: "Register" }));
    await userEvent.type(screen.getByLabelText("Login"), user.login);
    await userEvent.type(screen.getByLabelText("Email"), user.email);
    await userEvent.type(screen.getByLabelText("Password"), "super-secret-123");
    await userEvent.type(
      screen.getByLabelText("Repeat password"),
      "super-secret-123",
    );
    await userEvent.click(screen.getByRole("button", { name: "Register and login" }));

    await waitFor(() => expect(localStorage.getItem(TOKEN_KEY)).toBe("jwt-token"));
    expect(mockedApi.register).toHaveBeenCalledWith({
      login: user.login,
      email: user.email,
      password: "super-secret-123",
      repeat_password: "super-secret-123",
    });
    expect(mockedApi.login).toHaveBeenCalledWith({
      login: user.login,
      password: "super-secret-123",
    });
    await screen.findByText(user.email);
    expect(mockedApi.me).toHaveBeenCalledWith("jwt-token");
    expect(mockedApi.listProjects).toHaveBeenCalledWith("jwt-token");
  });

  it("restores a stored JWT and clears it after a 401", async () => {
    localStorage.setItem(TOKEN_KEY, "expired-token");
    mockedApi.me.mockRejectedValueOnce(
      new ApiError(401, "UNAUTHORIZED", "Token expired."),
    );

    render(<App />);

    await screen.findByText("UNAUTHORIZED: Token expired.");
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("creates a project, loads details, and renders members and documents", async () => {
    localStorage.setItem(TOKEN_KEY, "jwt-token");
    render(<App />);

    await screen.findByText(user.email);
    await userEvent.type(screen.getByLabelText("Name"), project.name);
    await userEvent.type(screen.getByLabelText("Description"), "Controlled demo");
    await userEvent.click(screen.getByRole("button", { name: "Create project" }));

    await screen.findByRole("heading", { name: project.name });
    expect(mockedApi.createProject).toHaveBeenCalledWith("jwt-token", {
      name: project.name,
      description: "Controlled demo",
    });
    expect(mockedApi.getProject).toHaveBeenCalledWith("jwt-token", project.id);
    expect(mockedApi.listMembers).toHaveBeenCalledWith("jwt-token", project.id);
    expect(mockedApi.listDocuments).toHaveBeenCalledWith("jwt-token", project.id);
    expect(screen.getAllByText("owner").length).toBeGreaterThan(0);
    expect(screen.getAllByText("brief.pdf").length).toBeGreaterThan(0);
  });

  it("grants participants, uploads documents, and opens download URLs", async () => {
    localStorage.setItem(TOKEN_KEY, "jwt-token");
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: /Demo project/ }));
    await userEvent.type(
      screen.getByLabelText("Add participant by login"),
      "demo-participant",
    );
    await userEvent.click(screen.getByRole("button", { name: "Grant access" }));

    await waitFor(() =>
      expect(mockedApi.grantParticipant).toHaveBeenCalledWith(
        "jwt-token",
        project.id,
        "demo-participant",
      ),
    );

    const upload = new File(["%PDF-1.4"], "brief.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Upload PDF or DOCX"), upload);
    await userEvent.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() =>
      expect(mockedApi.uploadDocument).toHaveBeenCalledWith(
        "jwt-token",
        project.id,
        upload,
      ),
    );

    await userEvent.click(screen.getByRole("button", { name: "Download" }));
    await waitFor(() =>
      expect(window.open).toHaveBeenCalledWith(
        "https://signed.example.com/brief.pdf",
        "_blank",
        "noopener,noreferrer",
      ),
    );
  });

  it("surfaces API failures as notices", async () => {
    localStorage.setItem(TOKEN_KEY, "jwt-token");
    mockedApi.listProjects.mockRejectedValueOnce(
      new ApiError(500, "API_ERROR", "Unexpected failure."),
    );

    render(<App />);

    await screen.findByText("API_ERROR: Unexpected failure.");
  });
});
