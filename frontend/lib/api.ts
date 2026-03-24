import axios from "axios";
import type { AppVersion, Project, ProjectAsset, User } from "@/types/project";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("nano_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  register: (email: string, password: string) =>
    api.post<{ access_token: string }>("/api/auth/register", { email, password }),

  login: (email: string, password: string) =>
    api.post<{ access_token: string }>("/api/auth/login", { email, password }),

  me: () => api.get<User>("/api/auth/me"),
};

export const projectsApi = {
  list: () => api.get<Project[]>("/api/projects"),

  create: (data: { name: string; app_type?: string; description?: string }) =>
    api.post<Project>("/api/projects", data),

  get: (id: number) => api.get<Project>(`/api/projects/${id}`),

  update: (id: number, data: { name?: string; description?: string }) =>
    api.patch<Project>(`/api/projects/${id}`, data),

  versions: (id: number) => api.get<AppVersion[]>(`/api/projects/${id}/versions`),

  assets: (id: number) => api.get<ProjectAsset[]>(`/api/projects/${id}/assets`),

  uploadAssets: (id: number, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return api.post<ProjectAsset[]>(`/api/projects/${id}/assets`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  deleteAsset: (projectId: number, assetId: number) =>
    api.delete(`/api/projects/${projectId}/assets/${assetId}`),

  generate: (id: number, prompt: string, mode: string = "standard") =>
    api.post(`/api/projects/${id}/generate`, { prompt, mode }),

  iterate: (id: number, prompt: string, scope?: string) =>
    api.post(`/api/projects/${id}/iterate`, { prompt, scope }),

  publish: (id: number, version_id?: number) =>
    api.post<{ slug: string; url: string }>(`/api/projects/${id}/publish`, {
      version_id,
    }),
};

export const versionApi = {
  get: (id: number) => api.get(`/api/versions/${id}`),
};

export const publicApi = {
  get: (slug: string) => api.get(`/api/published/${slug}`),
};
