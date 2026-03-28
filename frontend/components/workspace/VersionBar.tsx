"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import AtomBrandMark from "@/components/ui/AtomBrandMark";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import { projectsApi } from "@/lib/api";
import { useThemeStore } from "@/stores/themeStore";
import type { AppVersion } from "@/types/project";

interface Props {
  projectId: number;
  projectName: string;
  versions: AppVersion[];
  currentVersionId: number | null;
  onVersionChange: (versionId: number) => void;
}

function getVersionLabel(status: AppVersion["status"]) {
  if (status === "completed") return "完成";
  if (status === "failed") return "失败";
  if (status === "running") return "生成中";
  return "排队中";
}

function getVersionBadgeClass(status: AppVersion["status"], isCyber: boolean) {
  if (status === "completed") {
    return isCyber ? "bg-emerald-400/10 text-emerald-300" : "bg-emerald-50 text-emerald-600";
  }
  if (status === "failed") {
    return isCyber ? "bg-rose-400/10 text-rose-300" : "bg-rose-50 text-rose-600";
  }
  return isCyber ? "bg-cyan-400/10 text-cyan-300" : "bg-indigo-50 text-indigo-600";
}

export default function VersionBar({
  projectId,
  projectName,
  versions,
  currentVersionId,
  onVersionChange,
}: Props) {
  const queryClient = useQueryClient();
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [publishing, setPublishing] = useState(false);
  const [publishedSlug, setPublishedSlug] = useState<string | null>(null);
  const isCyber = theme === "cyber";

  const publishMutation = useMutation({
    mutationFn: () => projectsApi.publish(projectId, currentVersionId ?? undefined),
    onSuccess: (response) => {
      setPublishedSlug(response.data.slug);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onSettled: () => setPublishing(false),
  });

  const currentVersion = versions.find((version) => version.id === currentVersionId);

  return (
    <div
      className={`flex items-center justify-between border-b px-5 py-4 ${
        isCyber
          ? "border-cyan-400/12 bg-slate-950/65 text-slate-100"
          : "border-slate-200 bg-white text-slate-900"
      }`}
    >
      <div className="flex items-center gap-4">
        <Link href="/" className="group flex items-center gap-3">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-xl border shadow-sm transition-transform group-hover:-translate-y-0.5 ${
              isCyber
                ? "border-cyan-400/18 bg-slate-950/72 shadow-[0_0_24px_rgba(34,211,238,0.16)]"
                : "border-slate-200 bg-white"
            }`}
          >
            <AtomBrandMark className="h-7 w-7" />
          </div>
          <div className="flex flex-col">
            <span className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
              Nano Atoms
            </span>
            <span className={`text-xs ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
              返回首页
            </span>
          </div>
        </Link>

        <span className={isCyber ? "text-slate-600" : "text-slate-300"}>|</span>

        <Link
          href="/dashboard"
          className={`text-sm transition-colors ${
            isCyber ? "text-slate-400 hover:text-white" : "text-slate-500 hover:text-slate-900"
          }`}
        >
          项目列表
        </Link>

        <span className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
          {projectName}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {versions.length > 0 && (
          <select
            value={currentVersionId ?? ""}
            onChange={(event) => onVersionChange(Number(event.target.value))}
            className={`rounded-lg border px-3 py-1.5 text-sm outline-none ${
              isCyber
                ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 focus:border-cyan-300/50"
                : "border-slate-300 bg-white text-slate-700 focus:border-indigo-500"
            }`}
          >
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                v{version.version_no} · {getVersionLabel(version.status)}
              </option>
            ))}
          </select>
        )}

        {currentVersion && (
          <span
            className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs ${getVersionBadgeClass(
              currentVersion.status,
              isCyber
            )}`}
          >
            {(currentVersion.status === "running" || currentVersion.status === "queued") && (
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
            )}
            {currentVersion.status === "completed"
              ? "已生成"
              : currentVersion.status === "failed"
                ? "生成失败"
                : currentVersion.status === "running"
                  ? "生成中"
                  : "排队中"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <ThemeToggleButton theme={theme} onToggle={toggleTheme} />

        {publishedSlug && (
          <a
            href={`/p/${publishedSlug}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`text-xs hover:underline ${
              isCyber ? "text-cyan-300" : "text-indigo-600"
            }`}
          >
            查看发布页
          </a>
        )}

        <button
          onClick={() => {
            setPublishing(true);
            publishMutation.mutate();
          }}
          disabled={publishing || !currentVersionId || currentVersion?.status !== "completed"}
          className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40 ${
            isCyber
              ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.18)] hover:bg-cyan-300"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
        >
          {publishing ? "发布中..." : "发布"}
        </button>
      </div>
    </div>
  );
}
