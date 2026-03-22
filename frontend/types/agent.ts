export type AgentName = "product" | "architect" | "ui_builder" | "code" | "media" | "qa";
export type AgentStatus = "pending" | "running" | "done" | "error";

export interface AgentState {
  name: AgentName;
  label: string;
  status: AgentStatus;
  summary?: string;
}

export interface AgentStatusMessage {
  type: "agent_status";
  agent: AgentName;
  status: "running" | "done" | "error";
  summary?: string;
  timestamp: string;
}

export interface GenerationStatusMessage {
  type: "generation_status";
  status: "queued" | "running" | "completed" | "failed";
  version_id?: number;
  error?: string;
}

export type WsMessage = AgentStatusMessage | GenerationStatusMessage;

export const AGENT_META: Record<AgentName, { label: string; description: string }> = {
  product: { label: "Product Agent", description: "需求理解与规格整理" },
  architect: { label: "Architect Agent", description: "应用结构设计" },
  ui_builder: { label: "UI Builder", description: "界面布局与视觉方案" },
  code: { label: "Code Agent", description: "前端逻辑与文件产物生成" },
  media: { label: "Media Agent", description: "配图与视觉资源生成" },
  qa: { label: "QA Agent", description: "一致性校验与问题检查" },
};
