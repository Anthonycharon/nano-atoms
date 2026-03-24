"use client";

import { useState } from "react";
import AppRenderer from "@/components/renderer/AppRenderer";
import CodePanel from "@/components/workspace/CodePanel";
import { extractCodeBundle } from "@/lib/codeArtifacts";
import { useThemeStore } from "@/stores/themeStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import type { AppSchema, QualityReport } from "@/types/schema";

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

function getCheckBadgeClass(status: "passed" | "warning" | "fixed", isCyber: boolean) {
  if (status === "passed") {
    return isCyber ? "bg-emerald-400/10 text-emerald-300" : "bg-emerald-50 text-emerald-700";
  }
  if (status === "fixed") {
    return isCyber ? "bg-cyan-400/10 text-cyan-200" : "bg-indigo-50 text-indigo-700";
  }
  return isCyber ? "bg-amber-400/10 text-amber-300" : "bg-amber-50 text-amber-700";
}

function QualityPanel({ report, isCyber }: { report: QualityReport; isCyber: boolean }) {
  return (
    <div
      className={`border-b px-5 py-4 ${
        isCyber
          ? "border-cyan-400/12 bg-[linear-gradient(90deg,rgba(2,6,23,0.96),rgba(8,47,73,0.82),rgba(2,6,23,0.96))]"
          : "border-slate-200 bg-gradient-to-r from-white via-slate-50 to-indigo-50"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
            Quality Guardian
          </div>
          <div className={`mt-1 text-xs leading-6 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            {report.summary}
          </div>
        </div>
        <div
          className={`rounded-2xl border px-4 py-3 shadow-sm ${
            isCyber
              ? "border-cyan-400/15 bg-slate-950/85"
              : "border-indigo-100 bg-white"
          }`}
        >
          <div className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
            Quality Score
          </div>
          <div className={`mt-1 text-2xl font-black ${isCyber ? "text-cyan-200" : "text-slate-900"}`}>
            {report.score}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {report.checks.map((check) => (
          <span
            key={check.id}
            className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${getCheckBadgeClass(
              check.status,
              isCyber
            )}`}
            title={check.detail}
          >
            {check.label}
          </span>
        ))}
      </div>

      {(report.applied_repairs?.length ?? 0) > 0 && (
        <div className="mt-4">
          <div className={`text-xs font-medium ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            自动修复与收尾
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {report.applied_repairs?.slice(0, 3).map((item) => (
              <span
                key={item}
                className={`rounded-full border px-3 py-1 text-xs ${
                  isCyber
                    ? "border-cyan-400/12 bg-slate-950/90 text-slate-300"
                    : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {(report.recommended_prompts?.length ?? 0) > 0 && (
        <div className="mt-4">
          <div className={`text-xs font-medium ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            建议下一步迭代
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {report.recommended_prompts?.slice(0, 3).map((item) => (
              <span
                key={item}
                className={`rounded-full border px-3 py-1 text-xs ${
                  isCyber
                    ? "border-cyan-400/15 bg-cyan-400/10 text-cyan-200"
                    : "border-indigo-100 bg-indigo-50 text-indigo-700"
                }`}
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PreviewPanel({ schemaJson, codeJson, status }: Props) {
  const theme = useThemeStore((state) => state.theme);
  const { previewDevice, setPreviewDevice } = useWorkspaceStore();
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");
  const schema = parseSchema(schemaJson);
  const codeBundle = extractCodeBundle(codeJson);
  const qualityReport = schema?.quality_report ?? null;
  const isCyber = theme === "cyber";

  return (
    <div className={`flex h-full flex-col ${isCyber ? "bg-slate-950/70" : "bg-white"}`}>
      <div
        className={`flex items-center justify-between border-b px-5 py-4 ${
          isCyber ? "border-cyan-400/12 bg-slate-950/80" : "border-slate-200 bg-white"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className={`text-sm font-semibold ${isCyber ? "text-slate-200" : "text-slate-700"}`}>
            {activeTab === "preview" ? "实时预览" : "项目文件"}
          </span>
          <div
            className={`overflow-hidden rounded-lg border ${
              isCyber ? "border-cyan-400/12 bg-slate-900" : "border-slate-200 bg-slate-100"
            }`}
          >
            <button
              onClick={() => setActiveTab("preview")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                activeTab === "preview"
                  ? isCyber
                    ? "bg-cyan-400/10 text-cyan-200 shadow-sm"
                    : "bg-white text-slate-900 shadow-sm"
                  : isCyber
                    ? "text-slate-400 hover:text-white"
                    : "text-slate-500 hover:text-slate-800"
              }`}
            >
              预览
            </button>
            <button
              onClick={() => setActiveTab("code")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                activeTab === "code"
                  ? isCyber
                    ? "bg-cyan-400/10 text-cyan-200 shadow-sm"
                    : "bg-white text-slate-900 shadow-sm"
                  : isCyber
                    ? "text-slate-400 hover:text-white"
                    : "text-slate-500 hover:text-slate-800"
              }`}
            >
              文件
            </button>
          </div>
        </div>

        {activeTab === "preview" && (
          <div
            className={`overflow-hidden rounded-lg border ${
              isCyber ? "border-cyan-400/12 bg-slate-900" : "border-slate-200 bg-slate-100"
            }`}
          >
            <button
              onClick={() => setPreviewDevice("desktop")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                previewDevice === "desktop"
                  ? isCyber
                    ? "bg-cyan-400/10 text-cyan-200 shadow-sm"
                    : "bg-white text-slate-900 shadow-sm"
                  : isCyber
                    ? "text-slate-400 hover:text-white"
                    : "text-slate-500 hover:text-slate-800"
              }`}
            >
              桌面
            </button>
            <button
              onClick={() => setPreviewDevice("mobile")}
              className={`px-3 py-1.5 text-xs transition-colors ${
                previewDevice === "mobile"
                  ? isCyber
                    ? "bg-cyan-400/10 text-cyan-200 shadow-sm"
                    : "bg-white text-slate-900 shadow-sm"
                  : isCyber
                    ? "text-slate-400 hover:text-white"
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
        <div className="flex min-h-0 flex-1 flex-col">
          {qualityReport && <QualityPanel report={qualityReport} isCyber={isCyber} />}

          <div
            className={`flex flex-1 items-start justify-center overflow-hidden p-5 ${
              isCyber ? "bg-slate-950/55" : "bg-slate-100"
            }`}
          >
            {status === "queued" || status === "running" ? (
              <div className={`flex h-full flex-col items-center justify-center ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                <div
                  className={`mb-4 h-12 w-12 animate-spin rounded-full border-2 ${
                    isCyber ? "border-cyan-400/15 border-t-cyan-300" : "border-indigo-200 border-t-indigo-500"
                  }`}
                />
                <p className={`text-sm font-medium ${isCyber ? "text-slate-200" : "text-slate-700"}`}>
                  生成中，请稍候...
                </p>
                <p className={`mt-2 text-xs ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
                  右侧预览会在产物可用后自动刷新
                </p>
              </div>
            ) : status === "failed" ? (
              <div className={`flex h-full flex-col items-center justify-center text-center ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                <div className="mb-3 text-4xl">!</div>
                <p className={`text-sm font-medium ${isCyber ? "text-slate-200" : "text-slate-700"}`}>
                  本次生成失败
                </p>
                <p className={`mt-2 max-w-sm text-xs leading-6 ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
                  请查看左侧对话里的错误提示，调整需求后重新生成。
                </p>
              </div>
            ) : !schema ? (
              <div className={`flex h-full flex-col items-center justify-center ${isCyber ? "text-slate-500" : "text-slate-500"}`}>
                <div className="mb-3 text-4xl">[]</div>
                <p className="text-sm">生成完成后，预览会显示在这里</p>
              </div>
            ) : (
              <div
                className={`overflow-auto rounded-2xl border shadow-[0_20px_50px_rgba(15,23,42,0.12)] transition-all duration-300 ${
                  isCyber
                    ? "border-cyan-400/12 bg-white"
                    : "border-slate-200 bg-white"
                }`}
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
        </div>
      )}
    </div>
  );
}
