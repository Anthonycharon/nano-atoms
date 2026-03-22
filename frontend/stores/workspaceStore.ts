import { create } from "zustand";
import type { AgentName, AgentState, AgentStatus } from "@/types/agent";
import type { AppVersion } from "@/types/project";
import { AGENT_META } from "@/types/agent";

const INITIAL_AGENTS: AgentState[] = (
  ["product", "architect", "ui_builder", "code", "media", "qa"] as AgentName[]
).map((name) => ({
  name,
  label: AGENT_META[name].label,
  status: "pending",
}));

interface WorkspaceState {
  projectId: number | null;
  currentVersionId: number | null;
  versions: AppVersion[];
  agents: AgentState[];
  generationStatus: "idle" | "running" | "completed" | "failed";
  messages: { role: "user" | "assistant"; content: string; id: string }[];
  previewDevice: "desktop" | "mobile";
  setProject: (projectId: number) => void;
  setVersions: (versions: AppVersion[]) => void;
  setCurrentVersion: (versionId: number) => void;
  updateAgentStatus: (agent: AgentName, status: AgentStatus, summary?: string) => void;
  resetAgents: () => void;
  setGenerationStatus: (status: WorkspaceState["generationStatus"]) => void;
  addMessage: (role: "user" | "assistant", content: string) => void;
  setPreviewDevice: (device: "desktop" | "mobile") => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  projectId: null,
  currentVersionId: null,
  versions: [],
  agents: INITIAL_AGENTS,
  generationStatus: "idle",
  messages: [],
  previewDevice: "desktop",

  setProject: (projectId) =>
    set((state) => {
      if (state.projectId === projectId) return {};
      return {
        projectId,
        currentVersionId: null,
        versions: [],
        agents: INITIAL_AGENTS,
        generationStatus: "idle",
        messages: [],
      };
    }),

  setVersions: (versions) => set({ versions }),

  setCurrentVersion: (versionId) => set({ currentVersionId: versionId }),

  updateAgentStatus: (agent, status, summary) =>
    set((state) => ({
      agents: state.agents.map((item) =>
        item.name === agent ? { ...item, status, summary } : item
      ),
    })),

  resetAgents: () => set({ agents: INITIAL_AGENTS, generationStatus: "idle" }),

  setGenerationStatus: (generationStatus) => set({ generationStatus }),

  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { role, content, id: `${Date.now()}-${Math.random()}` },
      ],
    })),

  setPreviewDevice: (previewDevice) => set({ previewDevice }),
}));
