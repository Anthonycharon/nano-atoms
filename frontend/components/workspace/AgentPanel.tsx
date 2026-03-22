"use client";

import { useWorkspaceStore } from "@/stores/workspaceStore";
import { AGENT_META } from "@/types/agent";
import type { AgentStatus } from "@/types/agent";

const STATUS_CONFIG: Record<AgentStatus, { label: string; color: string; dot: string }> = {
  pending:  { label: "等待中", color: "text-slate-500", dot: "bg-slate-600" },
  running:  { label: "执行中", color: "text-indigo-400", dot: "bg-indigo-400 animate-pulse" },
  done:     { label: "完成",   color: "text-green-400",  dot: "bg-green-400" },
  error:    { label: "失败",   color: "text-red-400",    dot: "bg-red-400" },
};

export default function AgentPanel() {
  const { agents, generationStatus } = useWorkspaceStore();

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800">
      {/* 标题 */}
      <div className="px-4 py-4 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Agent 执行状态</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            generationStatus === "running" ? "bg-indigo-500/20 text-indigo-400" :
            generationStatus === "completed" ? "bg-green-500/20 text-green-400" :
            generationStatus === "failed" ? "bg-red-500/20 text-red-400" :
            "bg-slate-800 text-slate-500"
          }`}>
            {generationStatus === "running" ? "生成中" :
             generationStatus === "completed" ? "生成完成" :
             generationStatus === "failed" ? "生成失败" : "空闲"}
          </span>
        </div>
      </div>

      {/* Agent 卡片列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {agents.map((agent, idx) => {
          const cfg = STATUS_CONFIG[agent.status];
          const meta = AGENT_META[agent.name];
          return (
            <div key={agent.name}
              className={`bg-slate-900 border rounded-xl p-4 transition-all ${
                agent.status === "running" ? "border-indigo-500/50 shadow-lg shadow-indigo-500/5" :
                agent.status === "done" ? "border-green-500/20" :
                agent.status === "error" ? "border-red-500/20" :
                "border-slate-800"
              }`}>
              {/* 卡片头 */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-600 font-mono w-5">0{idx + 1}</span>
                  <span className="text-sm font-medium">{meta.label}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                  <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
                </div>
              </div>

              {/* 描述 */}
              <p className="text-xs text-slate-600 mb-2 pl-7">{meta.description}</p>

              {/* 摘要 */}
              {agent.summary && (
                <div className="pl-7">
                  <p className={`text-xs ${agent.status === "error" ? "text-red-400" : "text-slate-400"} bg-slate-800/50 rounded-lg px-3 py-2 leading-relaxed`}>
                    {agent.summary}
                  </p>
                </div>
              )}

              {/* 运行动画 */}
              {agent.status === "running" && (
                <div className="pl-7 mt-2">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
