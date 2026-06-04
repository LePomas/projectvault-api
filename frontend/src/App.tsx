import { FormEvent, useEffect, useMemo, useState } from "react";
import { API_BASE_URL, ApiError, api } from "./api";
import type { DocumentItem, Project, ProjectMember, ProjectSummary, User } from "./types";

const TOKEN_KEY = "projectvault.access_token";

type Notice = {
  kind: "info" | "error";
  message: string;
};

type AuthMode = "login" | "register";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);

  const isOwner = Boolean(
    currentUser && selectedProject && selectedProject.owner_id === currentUser.id,
  );

  const selectedSummary = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    void loadSession(token);
  }, [token]);

  async function loadSession(activeToken: string) {
    setLoading(true);
    try {
      const user = await api.me(activeToken);
      setCurrentUser(user);
      await loadProjects(activeToken);
    } catch (error) {
      handleError(error);
      clearSession();
    } finally {
      setLoading(false);
    }
  }

  async function loadProjects(activeToken = token) {
    if (!activeToken) {
      return;
    }

    const loadedProjects = await api.listProjects(activeToken);
    setProjects(loadedProjects);
    if (
      selectedProjectId !== null &&
      !loadedProjects.some((project) => project.id === selectedProjectId)
    ) {
      setSelectedProjectId(null);
      setSelectedProject(null);
      setMembers([]);
      setDocuments([]);
    }
  }

  async function loadProjectDetail(projectId: number, activeToken = token) {
    if (!activeToken) {
      return;
    }

    setLoading(true);
    try {
      const [project, projectMembers, projectDocuments] = await Promise.all([
        api.getProject(activeToken, projectId),
        api.listMembers(activeToken, projectId),
        api.listDocuments(activeToken, projectId),
      ]);
      setSelectedProjectId(projectId);
      setSelectedProject(project);
      setMembers(projectMembers);
      setDocuments(projectDocuments);
      setNotice(null);
    } catch (error) {
      handleError(error);
    } finally {
      setLoading(false);
    }
  }

  function saveToken(nextToken: string) {
    localStorage.setItem(TOKEN_KEY, nextToken);
    setToken(nextToken);
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setCurrentUser(null);
    setProjects([]);
    setSelectedProjectId(null);
    setSelectedProject(null);
    setMembers([]);
    setDocuments([]);
  }

  function handleError(error: unknown) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        clearSession();
      }
      setNotice({
        kind: "error",
        message: `${error.code}: ${error.message}`,
      });
      return;
    }

    setNotice({
      kind: "error",
      message: error instanceof Error ? error.message : "Something went wrong.",
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ProjectVault</p>
          <h1>ProjectVault demo console</h1>
        </div>
        <div className="api-status">
          <span>API</span>
          <strong>{API_BASE_URL}</strong>
        </div>
      </header>

      {notice ? (
        <div className={`notice notice-${notice.kind}`}>{notice.message}</div>
      ) : null}

      {!currentUser || !token ? (
        <AuthPanel
          loading={loading}
          onError={handleError}
          onToken={saveToken}
          onNotice={setNotice}
        />
      ) : (
        <section className="workspace">
          <aside className="sidebar">
            <CurrentUser user={currentUser} onLogout={clearSession} />
            <ProjectCreator
              token={token}
              onError={handleError}
              onCreated={async (project) => {
                setNotice({
                  kind: "info",
                  message: `Created project ${project.name}.`,
                });
                await loadProjects();
                await loadProjectDetail(project.id);
              }}
            />
            <ProjectList
              projects={projects}
              selectedProjectId={selectedProjectId}
              onSelect={loadProjectDetail}
            />
          </aside>

          <section className="content">
            {selectedProject ? (
              <ProjectDetail
                project={selectedProject}
                summary={selectedSummary}
                members={members}
                documents={documents}
                token={token}
                isOwner={isOwner}
                onError={handleError}
                onNotice={setNotice}
                onRefresh={async () => {
                  await loadProjects();
                  await loadProjectDetail(selectedProject.id);
                }}
              />
            ) : (
              <div className="empty-state">
                <h2>Select or create a project</h2>
                <p>
                  Use this console to validate auth, project access, members, and
                  document flows against the review API.
                </p>
              </div>
            )}
          </section>
        </section>
      )}
    </main>
  );
}

function AuthPanel({
  loading,
  onError,
  onToken,
  onNotice,
}: {
  loading: boolean;
  onError: (error: unknown) => void;
  onToken: (token: string) => void;
  onNotice: (notice: Notice | null) => void;
}) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [login, setLogin] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register({
          login,
          email,
          password,
          repeat_password: repeatPassword,
        });
        onNotice({
          kind: "info",
          message: "Registration complete. Logging in now.",
        });
      }

      const auth = await api.login({ login, password });
      onToken(auth.access_token);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-grid">
      <form className="panel auth-panel" onSubmit={submit}>
        <div className="segmented" role="tablist" aria-label="Authentication mode">
          <button
            type="button"
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <label>
          Login
          <input
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            autoComplete="username"
            required
          />
        </label>

        {mode === "register" ? (
          <label>
            Email
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="email"
              required
            />
          </label>
        ) : null}

        <label>
          Password
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            required
          />
        </label>

        {mode === "register" ? (
          <label>
            Repeat password
            <input
              value={repeatPassword}
              onChange={(event) => setRepeatPassword(event.target.value)}
              type="password"
              autoComplete="new-password"
              required
            />
          </label>
        ) : null}

        <button className="primary-action" disabled={busy || loading}>
          {busy ? "Working..." : mode === "register" ? "Register and login" : "Login"}
        </button>
      </form>

      <div className="panel review-panel">
        <h2>Live test path</h2>
        <dl>
          <div>
            <dt>Auth</dt>
            <dd>JWT stored locally and sent as Bearer auth.</dd>
          </div>
          <div>
            <dt>Projects</dt>
            <dd>Create, list, and inspect project details.</dd>
          </div>
          <div>
            <dt>Members</dt>
            <dd>Owners grant participant access by login.</dd>
          </div>
          <div>
            <dt>Documents</dt>
            <dd>Upload PDF/DOCX and download via presigned URLs.</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

function CurrentUser({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <section className="panel current-user">
      <div>
        <p className="eyebrow">Signed in</p>
        <h2>{user.login}</h2>
        <p>{user.email}</p>
      </div>
      <button type="button" className="secondary-action" onClick={onLogout}>
        Logout
      </button>
    </section>
  );
}

function ProjectCreator({
  token,
  onCreated,
  onError,
}: {
  token: string;
  onCreated: (project: Project) => void;
  onError: (error: unknown) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const project = await api.createProject(token, {
        name,
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      onCreated(project);
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel stack" onSubmit={submit}>
      <h2>New project</h2>
      <label>
        Name
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </label>
      <label>
        Description
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
        />
      </label>
      <button className="primary-action" disabled={busy}>
        {busy ? "Creating..." : "Create project"}
      </button>
    </form>
  );
}

function ProjectList({
  projects,
  selectedProjectId,
  onSelect,
}: {
  projects: ProjectSummary[];
  selectedProjectId: number | null;
  onSelect: (projectId: number) => void;
}) {
  return (
    <section className="panel project-list">
      <h2>Projects</h2>
      {projects.length === 0 ? (
        <p className="muted">No accessible projects yet.</p>
      ) : (
        <div className="list">
          {projects.map((project) => (
            <button
              type="button"
              key={project.id}
              className={`list-item ${project.id === selectedProjectId ? "selected" : ""}`}
              onClick={() => onSelect(project.id)}
            >
              <span>{project.name}</span>
              <small>
                {project.documents_count} docs · {formatBytes(project.total_size_bytes)}
              </small>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function ProjectDetail({
  project,
  summary,
  members,
  documents,
  token,
  isOwner,
  onError,
  onNotice,
  onRefresh,
}: {
  project: Project;
  summary: ProjectSummary | null;
  members: ProjectMember[];
  documents: DocumentItem[];
  token: string;
  isOwner: boolean;
  onError: (error: unknown) => void;
  onNotice: (notice: Notice | null) => void;
  onRefresh: () => Promise<void>;
}) {
  return (
    <div className="detail-stack">
      <section className="project-header">
        <div>
          <p className="eyebrow">Project #{project.id}</p>
          <h2>{project.name}</h2>
          <p>{project.description || "No description set."}</p>
        </div>
        <div className="metric-row">
          <Metric label="Role" value={isOwner ? "owner" : "participant"} />
          <Metric label="Documents" value={String(project.documents_count)} />
          <Metric label="Storage" value={formatBytes(project.total_size_bytes)} />
        </div>
      </section>

      {summary && summary.documents.length > 0 ? (
        <section className="panel">
          <h3>Project list summary</h3>
          <div className="tag-row">
            {summary.documents.map((filename) => (
              <span className="tag" key={filename}>
                {filename}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <div className="two-column">
        <MemberPanel
          projectId={project.id}
          members={members}
          token={token}
          isOwner={isOwner}
          onError={onError}
          onNotice={onNotice}
          onRefresh={onRefresh}
        />
        <DocumentPanel
          projectId={project.id}
          documents={documents}
          token={token}
          isOwner={isOwner}
          onError={onError}
          onNotice={onNotice}
          onRefresh={onRefresh}
        />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MemberPanel({
  projectId,
  members,
  token,
  isOwner,
  onError,
  onNotice,
  onRefresh,
}: {
  projectId: number;
  members: ProjectMember[];
  token: string;
  isOwner: boolean;
  onError: (error: unknown) => void;
  onNotice: (notice: Notice | null) => void;
  onRefresh: () => Promise<void>;
}) {
  const [login, setLogin] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.grantParticipant(token, projectId, login);
      setLogin("");
      onNotice({ kind: "info", message: `Granted access to ${login}.` });
      await onRefresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel stack">
      <h3>Members</h3>
      <div className="table-list">
        {members.map((member) => (
          <div className="table-row" key={member.id}>
            <span>{member.login}</span>
            <strong>{member.role}</strong>
          </div>
        ))}
      </div>

      {isOwner ? (
        <form className="inline-form" onSubmit={submit}>
          <label>
            Add participant by login
            <input
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              required
            />
          </label>
          <button className="secondary-action" disabled={busy}>
            {busy ? "Adding..." : "Grant access"}
          </button>
        </form>
      ) : (
        <p className="muted">Only owners can grant access.</p>
      )}
    </section>
  );
}

function DocumentPanel({
  projectId,
  documents,
  token,
  isOwner,
  onError,
  onNotice,
  onRefresh,
}: {
  projectId: number;
  documents: DocumentItem[];
  token: string;
  isOwner: boolean;
  onError: (error: unknown) => void;
  onNotice: (notice: Notice | null) => void;
  onRefresh: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [filename, setFilename] = useState("");

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      return;
    }

    setBusy(true);
    try {
      await api.uploadDocument(token, projectId, file);
      setFile(null);
      onNotice({ kind: "info", message: `Uploaded ${file.name}.` });
      await onRefresh();
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  async function download(documentId: number) {
    try {
      const download = await api.downloadUrl(token, documentId);
      window.open(download.download_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      onError(error);
    }
  }

  async function rename(documentId: number) {
    if (!filename.trim()) {
      return;
    }

    try {
      await api.renameDocument(token, documentId, filename.trim());
      setRenamingId(null);
      setFilename("");
      onNotice({ kind: "info", message: "Document renamed." });
      await onRefresh();
    } catch (error) {
      onError(error);
    }
  }

  async function remove(documentId: number) {
    try {
      await api.deleteDocument(token, documentId);
      onNotice({ kind: "info", message: "Document deleted." });
      await onRefresh();
    } catch (error) {
      onError(error);
    }
  }

  return (
    <section className="panel stack">
      <h3>Documents</h3>
      <form className="inline-form" onSubmit={upload}>
        <label>
          Upload PDF or DOCX
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button className="secondary-action" disabled={!file || busy}>
          {busy ? "Uploading..." : "Upload"}
        </button>
      </form>

      {documents.length === 0 ? (
        <p className="muted">No uploaded documents yet.</p>
      ) : (
        <div className="document-list">
          {documents.map((document) => (
            <article className="document-item" key={document.id}>
              <div>
                <h4>{document.filename}</h4>
                <p>
                  {document.status} · {formatBytes(document.size_bytes)} ·{" "}
                  {document.content_type}
                </p>
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="secondary-action compact"
                  onClick={() => download(document.id)}
                >
                  Download
                </button>
                <button
                  type="button"
                  className="secondary-action compact"
                  onClick={() => {
                    setRenamingId(document.id);
                    setFilename(document.filename);
                  }}
                >
                  Rename
                </button>
                {isOwner ? (
                  <button
                    type="button"
                    className="danger-action compact"
                    onClick={() => remove(document.id)}
                  >
                    Delete
                  </button>
                ) : null}
              </div>
              {renamingId === document.id ? (
                <div className="rename-row">
                  <input
                    value={filename}
                    onChange={(event) => setFilename(event.target.value)}
                  />
                  <button
                    type="button"
                    className="secondary-action compact"
                    onClick={() => rename(document.id)}
                  >
                    Save
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatBytes(value: number) {
  if (value === 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export default App;
