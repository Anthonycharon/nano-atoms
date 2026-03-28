import axios from "axios";
import type {
  AppVersion,
  ConversationMessage,
  Project,
  ProjectAsset,
  User,
  VersionDetail,
} from "@/types/project";

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
  captcha: () =>
    api.get<{ captcha_token: string; svg_data_url: string }>("/api/auth/captcha"),

  sendRegisterCode: (email: string) =>
    api.post<{
      verification_token: string;
      expires_in_seconds: number;
      resend_after_seconds: number;
    }>("/api/auth/register/send-code", { email }),

  register: (email: string, password: string, verification_token: string, verification_code: string) =>
    api.post<{ access_token: string }>("/api/auth/register", {
      email,
      password,
      verification_token,
      verification_code,
    }),

  login: (email: string, password: string, captcha_token: string, captcha_answer: string) =>
    api.post<{ access_token: string }>("/api/auth/login", {
      email,
      password,
      captcha_token,
      captcha_answer,
    }),

  me: () => api.get<User>("/api/auth/me"),
};

export const projectsApi = {
  list: () => api.get<Project[]>("/api/projects"),

  create: (data: { name: string; app_type?: string; description?: string }) =>
    api.post<Project>("/api/projects", data),

  get: (id: number) => api.get<Project>(`/api/projects/${id}`),

  update: (id: number, data: { name?: string; description?: string }) =>
    api.patch<Project>(`/api/projects/${id}`, data),

  delete: (id: number) => api.delete(`/api/projects/${id}`),

  versions: (id: number) => api.get<AppVersion[]>(`/api/projects/${id}/versions`),

  messages: (id: number) => api.get<ConversationMessage[]>(`/api/projects/${id}/messages`),

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
  get: (id: number) => api.get<VersionDetail>(`/api/versions/${id}`),
};

export const publicApi = {
  get: (slug: string) => api.get(`/api/published/${slug}`),
};
