export interface User {
  id: number;
  email: string;
}

export interface Project {
  id: number;
  name: string;
  app_type: string;
  description: string | null;
  latest_version_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AppVersion {
  id: number;
  project_id: number;
  version_no: number;
  status: "queued" | "running" | "completed" | "failed";
  prompt_snapshot: string;
  schema_json: string | null;
  code_json: string | null;
  created_at: string;
}
