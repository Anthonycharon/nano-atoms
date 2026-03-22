"use client";

import { useState } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import AppRenderer from "@/components/renderer/AppRenderer";
import CodePanel from "@/components/workspace/CodePanel";
import { extractCodeBundle } from "@/lib/codeArtifacts";
import type { AppSchema } from "@/types/schema";

interface Props {
  schemaJson: string | null;
  codeJson: string | null;
  status: string;
}

function parseSchema(raw: string | null): AppSchema | null {
  if (!raw) return null;

  try {
    return JSON.parse(raw) as AppSchema;
  } catch {
    return null;
  }
}

export default function PreviewPanel({ schemaJson, codeJson, status }: Props) {
  const { previewDevice, setPreviewDevice } = useWorkspaceStore();
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");

  const schema = parseSchema(schemaJson);
  const codeBundle = extractCodeBundle(codeJson);

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-700">
            {activeTab === "preview" ? "实时预览" : "项目文件"}
          </span>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
            <button
              onClick={() => setActiveTab("preview")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                activeTab === "preview"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              预览
            </button>
            <button
              onClick={() => setActiveTab("code")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                activeTab === "code"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              文件
            </button>
          </div>
        </div>

        {activeTab === "preview" && (
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
            <button
              onClick={() => setPreviewDevice("desktop")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                previewDevice === "desktop"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              桌面
            </button>
            <button
              onClick={() => setPreviewDevice("mobile")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                previewDevice === "mobile"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              移动
            </button>
          </div>
        )}
      </div>

      {activeTab === "code" ? (
        <CodePanel schemaJson={schemaJson} codeJson={codeJson} status={status} />
      ) : (
        <div className="flex flex-1 items-start justify-center overflow-hidden bg-slate-100 p-5">
          {status === "queued" || status === "running" ? (
            <div className="flex h-full flex-col items-center justify-center text-slate-500">
              <div className="mb-4 h-12 w-12 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin" />
              <p className="text-sm font-medium text-slate-700">生成中，请稍候...</p>
              <p className="mt-2 text-xs text-slate-500">右侧预览会在产物可用后自动刷新</p>
            </div>
          ) : status === "failed" ? (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
              <div className="mb-3 text-4xl">!</div>
              <p className="text-sm font-medium text-slate-700">本次生成失败</p>
              <p className="mt-2 max-w-sm text-xs leading-6 text-slate-500">
                请查看左侧对话里的错误提示，调整需求后重新生成。
              </p>
            </div>
          ) : !schema ? (
            <div className="flex h-full flex-col items-center justify-center text-slate-500">
              <div className="mb-3 text-4xl">[]</div>
              <p className="text-sm">生成完成后，预览会显示在这里</p>
            </div>
          ) : (
            <div
              className="overflow-auto rounded-2xl border border-slate-200 bg-white shadow-[0_20px_50px_rgba(15,23,42,0.12)] transition-all duration-300"
              style={{
                width: previewDevice === "mobile" ? "375px" : "100%",
                maxWidth: previewDevice === "mobile" ? "375px" : "none",
                height: previewDevice === "mobile" ? "667px" : "100%",
                maxHeight: "100%",
              }}
            >
              <AppRenderer schema={schema} codeBundle={codeBundle} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
