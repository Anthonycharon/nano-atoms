"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import ChatPanel from "@/components/workspace/ChatPanel";
import PreviewPanel from "@/components/workspace/PreviewPanel";
import VersionBar from "@/components/workspace/VersionBar";
import { useWebSocket } from "@/hooks/useWebSocket";
import { projectsApi, versionApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import type { ProjectAsset } from "@/types/project";

interface Props {
  params: Promise<{ projectId: string }>;
}

const SCOPE_LABELS: Record<string, string> = {
  full: "整体",
  hero: "首页 Hero",
  landing: "首页与营销区块",
  auth: "认证流程",
  data: "数据页面",
  style: "视觉风格",
};

export default function WorkspacePage({ params }: Props) {
  const { projectId: projectIdStr } = use(params);
  const projectId = Number(projectIdStr);
  const router = useRouter();
  const theme = useThemeStore((state) => state.theme);
  const isCyber = theme === "cyber";

  const { isAuthenticated, hasHydrated } = useAuthStore();
  const {
    setProject,
    setVersions,
    setCurrentVersion,
    currentVersionId,
    messages,
    addMessage,
    resetAgents,
    setGenerationStatus,
    generationStatus,
  } = useWorkspaceStore();

  const [mounted, setMounted] = useState(false);
  const [versionData, setVersionData] = useState<{
    projectId: number;
    schema_json: string | null;
    code_json: string | null;
    status: string;
  } | null>(null);
  const [uploadingAssets, setUploadingAssets] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !hasHydrated) return;
    if (!isAuthenticated) router.push("/login");
  }, [mounted, hasHydrated, isAuthenticated, router]);

  useEffect(() => {
    setProject(projectId);
  }, [projectId, setProject]);

  useEffect(() => {
    setVersionData(null);
  }, [projectId]);

  useWebSocket(projectId);

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId).then((response) => response.data),
    enabled: hasHydrated && isAuthenticated && !!projectId,
  });

  const { data: versions = [], refetch: refetchVersions } = useQuery({
    queryKey: ["versions", projectId],
    queryFn: () => projectsApi.versions(projectId).then((response) => response.data),
    enabled: hasHydrated && isAuthenticated && !!projectId,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasRunning = data?.some(
        (version) => version.status === "running" || version.status === "queued"
      );
      return hasRunning ? 3000 : false;
    },
  });

  const { data: assets = [], refetch: refetchAssets } = useQuery({
    queryKey: ["project-assets", projectId],
    queryFn: () => projectsApi.assets(projectId).then((response) => response.data),
    enabled: hasHydrated && isAuthenticated && !!projectId,
  });

  useEffect(() => {
    if (versions.length === 0) {
      setVersionData(null);
      return;
    }

    setVersions(versions);
    if (!currentVersionId) {
      setCurrentVersion(project?.latest_version_id ?? versions[0].id);
    }
  }, [versions, project, currentVersionId, setVersions, setCurrentVersion]);

  useEffect(() => {
    if (!currentVersionId) {
      setVersionData(null);
      return;
    }

    const currentVersion = versions.find((version) => version.id === currentVersionId);
    if (!currentVersion) {
      setVersionData(null);
      return;
    }

    setVersionData((prev) => ({
      projectId,
      schema_json: currentVersion.schema_json ?? prev?.schema_json ?? null,
      code_json: currentVersion.code_json ?? prev?.code_json ?? null,
      status: currentVersion.status,
    }));
  }, [versions, currentVersionId, projectId]);

  useEffect(() => {
    if (!currentVersionId) return;
    versionApi
      .get(currentVersionId)
      .then((response) => {
        setVersionData({
          projectId,
          schema_json: response.data.schema_json,
          code_json: response.data.code_json,
          status: response.data.status,
        });
      })
      .catch(() => {});
  }, [currentVersionId, projectId]);

  useEffect(() => {
    if (!currentVersionId) return;

    const currentVersion = versions.find((version) => version.id === currentVersionId);
    if (!currentVersion) return;

    if (currentVersion.status === "queued" || currentVersion.status === "running") {
      if (generationStatus !== "running") {
        setGenerationStatus("running");
      }

      if (messages.length === 0) {
        resetAgents();
        if (currentVersion.prompt_snapshot?.trim()) {
          addMessage("user", currentVersion.prompt_snapshot.trim());
        }
        addMessage(
          "assistant",
          "已进入自动生成流程，正在依次执行 Product、Design Director、Architect、UI、Code、Media、QA 七个步骤。"
        );
      }
      return;
    }

    if (currentVersion.status === "completed" && generationStatus === "running") {
      setGenerationStatus("completed");
      return;
    }

    if (currentVersion.status === "failed" && generationStatus === "running") {
      setGenerationStatus("failed");
    }
  }, [
    currentVersionId,
    versions,
    messages.length,
    addMessage,
    generationStatus,
    resetAgents,
    setGenerationStatus,
  ]);

  useEffect(() => {
    if (generationStatus === "completed" || generationStatus === "failed") {
      refetchVersions();
    }
  }, [generationStatus, refetchVersions]);

  const handleSend = async (prompt: string, options?: { scope?: string }) => {
    const isFirst = versions.length === 0;
    const scope = !isFirst && options?.scope ? options.scope : "full";
    const scopeLabel = SCOPE_LABELS[scope] ?? "整体";

    addMessage("user", scope !== "full" ? `【${scopeLabel}】${prompt}` : prompt);
    addMessage(
      "assistant",
      scope !== "full"
        ? `已收到修改需求，正在按“${scopeLabel}”范围进行局部重生成。`
        : "已收到需求，正在依次执行 Product、Design Director、Architect、UI、Code、Media、QA 七个步骤。"
    );
    resetAgents();
    setGenerationStatus("running");

    try {
      const response = isFirst
        ? await projectsApi.generate(projectId, prompt)
        : await projectsApi.iterate(projectId, prompt, scope);

      const nextVersionId = response.data.version_id ?? response.data.version_ids?.[0] ?? null;
      if (nextVersionId) {
        setCurrentVersion(nextVersionId);
        setVersionData({
          projectId,
          schema_json: null,
          code_json: null,
          status: "queued",
        });
      }

      refetchVersions();
    } catch {
      addMessage("assistant", "生成请求失败，请稍后重试。");
      setGenerationStatus("failed");
    }
  };

  const handleAssetUpload = async (files: File[]) => {
    if (!files.length) return;
    setUploadingAssets(true);
    try {
      await projectsApi.uploadAssets(projectId, files);
      await refetchAssets();
      addMessage(
        "assistant",
        `已上传 ${files.length} 个素材，后续生成会将这些图片或资料纳入上下文并优先用于页面视觉。`
      );
    } catch {
      addMessage("assistant", "素材上传失败，请稍后重试。");
    } finally {
      setUploadingAssets(false);
    }
  };

  const handleAssetDelete = async (asset: ProjectAsset) => {
    try {
      await projectsApi.deleteAsset(projectId, asset.id);
      await refetchAssets();
      addMessage("assistant", `已移除素材：${asset.original_name}`);
    } catch {
      addMessage("assistant", "素材删除失败，请稍后重试。");
    }
  };

  const isGenerating =
    generationStatus === "running" ||
    versions.some((version) => version.status === "running" || version.status === "queued");

  const panelStatus =
    (versionData?.projectId === projectId ? versionData.status : null) ??
    (generationStatus === "running"
      ? "running"
      : generationStatus === "failed"
        ? "failed"
        : "idle");

  const activeVersionData = versionData?.projectId === projectId ? versionData : null;

  if (!mounted || !hasHydrated) {
    return <div className="min-h-screen bg-slate-100" />;
  }

  return (
    <div
      className={`flex h-screen flex-col overflow-hidden ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
          : "bg-slate-100"
      }`}
    >
      {isCyber && (
        <>
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] bg-[size:88px_88px] opacity-25" />
          <div className="pointer-events-none absolute left-[12%] top-[12%] h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl" />
          <div className="pointer-events-none absolute right-[8%] top-[20%] h-80 w-80 rounded-full bg-sky-500/8 blur-3xl" />
        </>
      )}

      <div className="relative z-10 flex h-full flex-col">
        <VersionBar
          projectId={projectId}
          projectName={project?.name ?? "加载中..."}
          versions={versions}
          currentVersionId={currentVersionId}
          onVersionChange={(id) => {
            setCurrentVersion(id);
            const version = versions.find((item) => item.id === id);
            if (version) {
              setVersionData({
                projectId,
                schema_json: version.schema_json,
                code_json: version.code_json,
                status: version.status,
              });
            }
          }}
        />

        <div className="flex flex-1 overflow-hidden">
          <div className="w-80 flex-shrink-0">
            <ChatPanel
              onSend={handleSend}
              disabled={isGenerating}
              canScopeIterate={versions.length > 0}
              assets={assets}
              uploadingAssets={uploadingAssets}
              onUploadAssets={handleAssetUpload}
              onDeleteAsset={handleAssetDelete}
            />
          </div>

          <div className="min-w-0 flex-1">
            <PreviewPanel
              schemaJson={activeVersionData?.schema_json ?? null}
              codeJson={activeVersionData?.code_json ?? null}
              status={panelStatus}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
