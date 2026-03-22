"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { projectsApi, versionApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import ChatPanel from "@/components/workspace/ChatPanel";
import PreviewPanel from "@/components/workspace/PreviewPanel";
import VersionBar from "@/components/workspace/VersionBar";

interface Props {
  params: Promise<{ projectId: string }>;
}

export default function WorkspacePage({ params }: Props) {
  const { projectId: projectIdStr } = use(params);
  const projectId = Number(projectIdStr);
  const router = useRouter();

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
    schema_json: string | null;
    code_json: string | null;
    status: string;
  } | null>(null);

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

  useEffect(() => {
    if (versions.length === 0) return;

    setVersions(versions);
    if (!currentVersionId) {
      setCurrentVersion(project?.latest_version_id ?? versions[0].id);
    }
  }, [versions, project, currentVersionId, setVersions, setCurrentVersion]);

  useEffect(() => {
    if (!currentVersionId) return;

    const currentVersion = versions.find((version) => version.id === currentVersionId);
    if (!currentVersion) return;

    setVersionData((prev) => ({
      schema_json: currentVersion.schema_json ?? prev?.schema_json ?? null,
      code_json: currentVersion.code_json ?? prev?.code_json ?? null,
      status: currentVersion.status,
    }));
  }, [versions, currentVersionId]);

  useEffect(() => {
    if (!currentVersionId) return;
    versionApi
      .get(currentVersionId)
      .then((response) => {
        setVersionData({
          schema_json: response.data.schema_json,
          code_json: response.data.code_json,
          status: response.data.status,
        });
      })
      .catch(() => {});
  }, [currentVersionId]);

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
          "已进入自动生成流程，正在依次执行 Product、Architect、UI、Code、Media、QA 六个步骤。"
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

  const handleSend = async (prompt: string) => {
    addMessage("user", prompt);
    addMessage(
      "assistant",
      "已收到需求，正在依次执行 Product、Architect、UI、Code、Media、QA 六个步骤。"
    );
    resetAgents();
    setGenerationStatus("running");

    try {
      const isFirst = versions.length === 0;
      const response = isFirst
        ? await projectsApi.generate(projectId, prompt)
        : await projectsApi.iterate(projectId, prompt);

      const nextVersionId = response.data.version_id ?? response.data.version_ids?.[0] ?? null;
      if (nextVersionId) {
        setCurrentVersion(nextVersionId);
        setVersionData({
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

  const isGenerating =
    generationStatus === "running" ||
    versions.some((version) => version.status === "running" || version.status === "queued");

  const panelStatus =
    versionData?.status ??
    (generationStatus === "running"
      ? "running"
      : generationStatus === "failed"
        ? "failed"
        : "idle");

  if (!mounted || !hasHydrated) {
    return <div className="min-h-screen bg-slate-100" />;
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-100">
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
              schema_json: version.schema_json,
              code_json: version.code_json,
              status: version.status,
            });
          }
        }}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="w-80 flex-shrink-0">
          <ChatPanel onSend={handleSend} disabled={isGenerating} />
        </div>

        <div className="min-w-0 flex-1">
          <PreviewPanel
            schemaJson={versionData?.schema_json ?? null}
            codeJson={versionData?.code_json ?? null}
            status={panelStatus}
          />
        </div>
      </div>
    </div>
  );
}
