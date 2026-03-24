"use client";

import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import type { ProjectAsset } from "@/types/project";
import { useThemeStore } from "@/stores/themeStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";

function renderContent(text: string): ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((part, index) =>
    index % 2 === 1 ? <strong key={index}>{part}</strong> : part
  );
}

function getAgentBadgeClass(
  status: "pending" | "running" | "done" | "error",
  isCyber: boolean
) {
  if (status === "done") {
    return isCyber ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-300" : "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "running") {
    return isCyber ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-200" : "border-indigo-200 bg-indigo-50 text-indigo-700";
  }
  if (status === "error") {
    return isCyber ? "border-rose-400/20 bg-rose-400/10 text-rose-300" : "border-rose-200 bg-rose-50 text-rose-700";
  }
  return isCyber ? "border-slate-700 bg-slate-900/80 text-slate-400" : "border-slate-200 bg-white text-slate-500";
}

const SCOPE_OPTIONS = [
  { value: "full", label: "整体迭代" },
  { value: "hero", label: "首页 Hero" },
  { value: "landing", label: "首页区块" },
  { value: "auth", label: "认证流程" },
  { value: "data", label: "数据页面" },
  { value: "style", label: "视觉风格" },
];

interface Props {
  onSend: (prompt: string, options?: { scope?: string }) => void;
  disabled?: boolean;
  canScopeIterate?: boolean;
  assets?: ProjectAsset[];
  uploadingAssets?: boolean;
  onUploadAssets?: (files: File[]) => void;
  onDeleteAsset?: (asset: ProjectAsset) => void;
}

export default function ChatPanel({
  onSend,
  disabled,
  canScopeIterate = false,
  assets = [],
  uploadingAssets = false,
  onUploadAssets,
  onDeleteAsset,
}: Props) {
  const theme = useThemeStore((state) => state.theme);
  const messages = useWorkspaceStore((state) => state.messages);
  const agents = useWorkspaceStore((state) => state.agents);
  const generationStatus = useWorkspaceStore((state) => state.generationStatus);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const [scope, setScope] = useState("full");
  const isCyber = theme === "cyber";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, generationStatus, agents]);

  useEffect(() => {
    if (!canScopeIterate) {
      setScope("full");
    }
  }, [canScopeIterate]);

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
    onSend(value, { scope });
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length && onUploadAssets) {
      onUploadAssets(files);
    }
    event.target.value = "";
  };

  return (
    <div
      className={`flex h-full flex-col border-r ${
        isCyber
          ? "border-cyan-400/12 bg-slate-950/78 text-slate-100"
          : "border-slate-200 bg-white text-slate-900"
      }`}
    >
      <div className={`border-b px-5 py-4 ${isCyber ? "border-cyan-400/12" : "border-slate-200"}`}>
        <div className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-800"}`}>
          需求对话
        </div>
        <div className={`mt-1 text-xs ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
          继续描述修改点，平台会基于当前版本继续迭代；也可以限制修改范围，做局部重生成。
        </div>
      </div>

      <div
        className={`border-b px-4 py-3 ${
          isCyber ? "border-cyan-400/12 bg-slate-950/60" : "border-slate-200 bg-slate-50"
        }`}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className={`text-xs font-semibold uppercase tracking-[0.12em] ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
              项目素材
            </div>
            <div className={`mt-1 text-xs ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
              支持上传图片、PDF、CSV 等资料，后续生成会纳入上下文。
            </div>
          </div>
          <input
            ref={uploadRef}
            type="file"
            multiple
            accept="image/*,.pdf,.csv,.txt,.json,.doc,.docx,.xls,.xlsx"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={() => uploadRef.current?.click()}
            disabled={uploadingAssets || disabled}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 ${
              isCyber
                ? "border-cyan-400/15 bg-slate-900 text-slate-200 hover:border-cyan-300/40 hover:text-white"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900"
            }`}
          >
            {uploadingAssets ? "上传中..." : "上传素材"}
          </button>
        </div>

        {assets.length > 0 && (
          <div className="mt-3 space-y-2">
            {assets.slice(0, 6).map((asset) => (
              <div
                key={asset.id}
                className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${
                  isCyber
                    ? "border-cyan-400/12 bg-slate-900/85"
                    : "border-slate-200 bg-white"
                }`}
              >
                {asset.kind === "image" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={asset.public_url}
                    alt={asset.original_name}
                    className={`h-10 w-10 rounded-lg object-cover ${
                      isCyber ? "border border-cyan-400/15" : "border border-slate-200"
                    }`}
                  />
                ) : (
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-lg text-[11px] font-semibold uppercase ${
                      isCyber
                        ? "border border-cyan-400/15 bg-slate-950 text-slate-400"
                        : "border border-slate-200 bg-slate-50 text-slate-500"
                    }`}
                  >
                    {asset.kind}
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <div className={`truncate text-sm font-medium ${isCyber ? "text-slate-100" : "text-slate-700"}`}>
                    {asset.original_name}
                  </div>
                  <div className={`mt-0.5 text-xs ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
                    {asset.kind} · {(asset.file_size / 1024).toFixed(0)} KB
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onDeleteAsset?.(asset)}
                  className={`text-xs transition-colors ${
                    isCyber ? "text-slate-500 hover:text-rose-300" : "text-slate-400 hover:text-rose-600"
                  }`}
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={`flex-1 overflow-y-auto px-4 py-4 ${isCyber ? "bg-slate-950/55" : "bg-slate-50/60"}`}>
        <div className="space-y-4">
          {generationStatus === "running" && (
            <div
              className={`rounded-2xl border p-4 shadow-sm ${
                isCyber
                  ? "border-cyan-400/15 bg-[linear-gradient(135deg,rgba(8,47,73,0.65),rgba(2,6,23,0.92))]"
                  : "border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-sky-50"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-800"}`}>
                    正在生成应用
                  </div>
                  <div className={`mt-1 text-xs ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                    {activeAgent
                      ? `${activeAgent.label} 正在处理当前步骤`
                      : "已进入生成队列，正在准备执行。"}
                  </div>
                </div>
                <div className={`text-sm font-semibold ${isCyber ? "text-cyan-300" : "text-indigo-600"}`}>
                  {progress}%
                </div>
              </div>

              <div className={`mt-3 h-2 overflow-hidden rounded-full ${isCyber ? "bg-slate-900" : "bg-slate-200"}`}>
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isCyber
                      ? "bg-gradient-to-r from-cyan-400 via-sky-400 to-teal-300"
                      : "bg-gradient-to-r from-indigo-500 via-sky-500 to-cyan-400"
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="mt-4 grid grid-cols-1 gap-2">
                {agents.map((agent) => (
                  <div
                    key={agent.name}
                    className={`rounded-xl border px-3 py-2 text-xs transition-colors ${getAgentBadgeClass(
                      agent.status,
                      isCyber
                    )}`}
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
            <div className={`py-12 text-center text-sm ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
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
                    ? isCyber
                      ? "rounded-br-sm bg-cyan-400 text-slate-950"
                      : "rounded-br-sm bg-indigo-600 text-white"
                    : isCyber
                      ? "rounded-bl-sm border border-cyan-400/12 bg-slate-900/90 text-slate-200"
                      : "rounded-bl-sm border border-slate-200 bg-white text-slate-700"
                }`}
              >
                {renderContent(message.content)}
              </div>
            </div>
          ))}

          {generationStatus === "running" && (
            <div className="flex justify-start">
              <div
                className={`max-w-[88%] rounded-2xl rounded-bl-sm border px-4 py-3 text-sm shadow-sm ${
                  isCyber
                    ? "border-cyan-400/12 bg-slate-900/90 text-slate-200"
                    : "border-slate-200 bg-white text-slate-700"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span>平台正在处理中</span>
                  <span className="flex items-center gap-1">
                    {[0, 1, 2].map((index) => (
                      <span
                        key={index}
                        className={`h-2 w-2 animate-bounce rounded-full ${
                          isCyber ? "bg-cyan-300" : "bg-indigo-400"
                        }`}
                        style={{ animationDelay: `${index * 0.15}s` }}
                      />
                    ))}
                  </span>
                </div>
                <div className={`mt-2 text-xs ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
                  {activeAgent?.summary ||
                    (activeAgent
                      ? `${activeAgent.label} 正在生成中，请稍候。`
                      : "正在等待后端返回结果。")}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className={`border-t p-4 ${isCyber ? "border-cyan-400/12 bg-slate-950/82" : "border-slate-200 bg-white"}`}>
        {canScopeIterate && (
          <div className="mb-3">
            <div className={`mb-2 text-xs font-medium ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
              局部重生成范围
            </div>
            <div className="flex flex-wrap gap-2">
              {SCOPE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setScope(option.value)}
                  disabled={disabled}
                  className={`rounded-full border px-3 py-1.5 text-xs transition-colors disabled:opacity-40 ${
                    scope === option.value
                      ? isCyber
                        ? "border-cyan-300/40 bg-cyan-400/10 text-cyan-200"
                        : "border-indigo-200 bg-indigo-50 text-indigo-700"
                      : isCyber
                        ? "border-cyan-400/12 bg-slate-900 text-slate-400 hover:border-cyan-300/25 hover:text-white"
                        : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div
          className={`flex items-end gap-2 rounded-2xl border px-4 py-3 transition-colors ${
            isCyber
              ? "border-cyan-400/12 bg-slate-900/80 focus-within:border-cyan-300/40"
              : "border-slate-200 bg-slate-50 focus-within:border-indigo-400"
          }`}
        >
          <textarea
            ref={inputRef}
            rows={1}
            disabled={disabled}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            className={`max-h-32 flex-1 resize-none bg-transparent text-sm outline-none disabled:opacity-50 ${
              isCyber ? "text-slate-100 placeholder:text-slate-500" : "text-slate-800 placeholder:text-slate-400"
            }`}
            placeholder={disabled ? "生成中，请稍候..." : "输入你的修改需求...（Enter 发送）"}
          />
          <button
            onClick={send}
            disabled={disabled}
            className={`pb-0.5 text-sm transition-colors disabled:opacity-30 ${
              isCyber ? "text-cyan-300 hover:text-cyan-200" : "text-indigo-600 hover:text-indigo-700"
            }`}
          >
            发送
          </button>
        </div>
        <p className={`mt-2 text-center text-xs ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
          Enter 发送，Shift+Enter 换行
        </p>
      </div>
    </div>
  );
}
