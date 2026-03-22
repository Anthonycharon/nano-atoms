"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";

function renderContent(text: string): ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((part, index) =>
    index % 2 === 1 ? <strong key={index}>{part}</strong> : part
  );
}

function getAgentBadgeClass(status: "pending" | "running" | "done" | "error") {
  if (status === "done") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "running") return "border-indigo-200 bg-indigo-50 text-indigo-700";
  if (status === "error") return "border-rose-200 bg-rose-50 text-rose-700";
  return "border-slate-200 bg-white text-slate-500";
}

interface Props {
  onSend: (prompt: string) => void;
  disabled?: boolean;
}

export default function ChatPanel({ onSend, disabled }: Props) {
  const messages = useWorkspaceStore((state) => state.messages);
  const agents = useWorkspaceStore((state) => state.agents);
  const generationStatus = useWorkspaceStore((state) => state.generationStatus);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, generationStatus, agents]);

  const completedCount = agents.filter((agent) => agent.status === "done").length;
  const runningCount = agents.filter((agent) => agent.status === "running").length;
  const failedCount = agents.filter((agent) => agent.status === "error").length;
  const progress =
    generationStatus === "completed"
      ? 100
      : generationStatus === "failed"
        ? Math.max(20, Math.round(((completedCount + failedCount) / agents.length) * 100))
        : Math.max(
            8,
            Math.round(((completedCount + runningCount * 0.45) / agents.length) * 100)
          );

  const activeAgent =
    agents.find((agent) => agent.status === "running") ??
    (generationStatus === "running"
      ? agents.find((agent) => agent.status === "pending")
      : undefined);

  const send = () => {
    const value = inputRef.current?.value.trim();
    if (!value || disabled) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="flex h-full flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="text-sm font-semibold text-slate-800">需求对话</div>
        <div className="mt-1 text-xs text-slate-500">
          继续描述修改点，平台会基于当前版本继续迭代。
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-slate-50/60 px-4 py-4">
        <div className="space-y-4">
          {generationStatus === "running" && (
            <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-sky-50 p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-800">正在生成应用</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {activeAgent
                      ? `${activeAgent.label} 正在处理当前步骤`
                      : "已进入生成队列，正在准备执行。"}
                  </div>
                </div>
                <div className="text-sm font-semibold text-indigo-600">{progress}%</div>
              </div>

              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-sky-500 to-cyan-400 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="mt-4 grid grid-cols-1 gap-2">
                {agents.map((agent) => (
                  <div
                    key={agent.name}
                    className={`rounded-xl border px-3 py-2 text-xs transition-colors ${getAgentBadgeClass(agent.status)}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium">{agent.label}</span>
                      <span>
                        {agent.status === "done"
                          ? "已完成"
                          : agent.status === "running"
                            ? "执行中"
                            : agent.status === "error"
                              ? "异常"
                              : "等待中"}
                      </span>
                    </div>
                    {agent.summary && (
                      <div className="mt-1 leading-relaxed opacity-80">{agent.summary}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {messages.length === 0 && (
            <div className="py-12 text-center text-sm text-slate-500">
              <div className="mb-3 text-3xl">...</div>
              输入需求，开始生成
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                  message.role === "user"
                    ? "rounded-br-sm bg-indigo-600 text-white"
                    : "rounded-bl-sm border border-slate-200 bg-white text-slate-700"
                }`}
              >
                {renderContent(message.content)}
              </div>
            </div>
          ))}

          {generationStatus === "running" && (
            <div className="flex justify-start">
              <div className="max-w-[88%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm">
                <div className="flex items-center gap-3">
                  <span>平台正在处理中</span>
                  <span className="flex items-center gap-1">
                    {[0, 1, 2].map((index) => (
                      <span
                        key={index}
                        className="h-2 w-2 rounded-full bg-indigo-400 animate-bounce"
                        style={{ animationDelay: `${index * 0.15}s` }}
                      />
                    ))}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  {activeAgent?.summary ||
                    (activeAgent
                      ? `${activeAgent.label} 正在生成中，请稍候。`
                      : "正在等待后台返回结果。")}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white p-4">
        <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 transition-colors focus-within:border-indigo-400">
          <textarea
            ref={inputRef}
            rows={1}
            disabled={disabled}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            className="max-h-32 flex-1 resize-none bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400 disabled:opacity-50"
            placeholder={disabled ? "生成中，请稍候..." : "输入你的修改需求...（Enter 发送）"}
          />
          <button
            onClick={send}
            disabled={disabled}
            className="pb-0.5 text-sm text-indigo-600 transition-colors hover:text-indigo-700 disabled:opacity-30"
          >
            发送
          </button>
        </div>
        <p className="mt-2 text-center text-xs text-slate-400">
          Enter 发送 · Shift+Enter 换行
        </p>
      </div>
    </div>
  );
}
