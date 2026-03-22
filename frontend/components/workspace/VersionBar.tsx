"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
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

function getVersionBadgeClass(status: AppVersion["status"]) {
  if (status === "completed") return "bg-emerald-50 text-emerald-600";
  if (status === "failed") return "bg-rose-50 text-rose-600";
  return "bg-indigo-50 text-indigo-600";
}

export default function VersionBar({
  projectId,
  projectName,
  versions,
  currentVersionId,
  onVersionChange,
}: Props) {
  const queryClient = useQueryClient();
  const [publishing, setPublishing] = useState(false);
  const [publishedSlug, setPublishedSlug] = useState<string | null>(null);

  const publishMutation = useMutation({
    mutationFn: () => projectsApi.publish(projectId, currentVersionId ?? undefined),
    onSuccess: (res) => {
      setPublishedSlug(res.data.slug);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onSettled: () => setPublishing(false),
  });

  const currentVersion = versions.find((version) => version.id === currentVersionId);

  return (
    <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
      <div className="flex items-center gap-4">
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-sm transition-transform group-hover:-translate-y-0.5">
            N
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-slate-900">Nano Atoms</span>
            <span className="text-xs text-slate-400 group-hover:text-slate-500">
              返回首页
            </span>
          </div>
        </Link>

        <span className="text-slate-300">|</span>

        <Link
          href="/dashboard"
          className="text-sm text-slate-500 transition-colors hover:text-slate-900"
        >
          项目列表
        </Link>

        <span className="text-sm font-semibold text-slate-900">{projectName}</span>
      </div>

      <div className="flex items-center gap-2">
        {versions.length > 0 && (
          <select
            value={currentVersionId ?? ""}
            onChange={(e) => onVersionChange(Number(e.target.value))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 outline-none focus:border-indigo-500"
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
            className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs ${getVersionBadgeClass(currentVersion.status)}`}
          >
            {(currentVersion.status === "running" || currentVersion.status === "queued") && (
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
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
        {publishedSlug && (
          <a
            href={`/p/${publishedSlug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-indigo-600 hover:underline"
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
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {publishing ? "发布中..." : "发布"}
        </button>
      </div>
    </div>
  );
}
