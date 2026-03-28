export type AgentName =
  | "product"
  | "design_director"
  | "page_codegen"
  | "media"
  | "qa";

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
  product: { label: "Product Agent", description: "需求理解与产品规格整理" },
  design_director: {
    label: "Design Director",
    description: "视觉方向、界面节奏和首版质量约束",
  },
  page_codegen: { label: "应用生成引擎", description: "应用界面代码与预览生成" },
  media: { label: "Media Agent", description: "配图与视觉资源生成" },
  qa: { label: "QA Agent", description: "结果验收、一致性校验与质量守护" },
};
