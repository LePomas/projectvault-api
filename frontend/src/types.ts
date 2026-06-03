export type User = {
  id: number;
  login: string;
  email: string;
  created_at: string;
  updated_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type Project = {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  total_size_bytes: number;
  documents_count: number;
  created_at: string;
  updated_at: string;
};

export type ProjectSummary = Project & {
  documents: string[];
};

export type ProjectMember = {
  id: number;
  project_id: number;
  user_id: number;
  login: string;
  role: string;
  created_at: string;
};

export type DocumentItem = {
  id: number;
  project_id: number;
  uploaded_by_id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  storage_key: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type DownloadUrl = {
  download_url: string;
  expires_in: number;
};
