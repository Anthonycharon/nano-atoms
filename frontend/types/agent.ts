export type AgentName =
  | "product"
  | "design_director"
  | "architect"
  | "ui_builder"
  | "code"
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
    description: "视觉方向、页面节奏和首版质量约束",
  },
  architect: { label: "Architect Agent", description: "应用结构与页面区块设计" },
  ui_builder: { label: "UI Builder", description: "视觉主题与界面表现细化" },
  code: { label: "Code Agent", description: "交互逻辑与项目文件生成" },
  media: { label: "Media Agent", description: "配图与视觉资源生成" },
  qa: { label: "QA Agent", description: "一致性校验与自动修复检查" },
};
