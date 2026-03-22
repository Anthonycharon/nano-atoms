"use client";

import { useQuery } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

export function useProject(projectId: number | null) {
  const { isAuthenticated } = useAuthStore();

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId!).then((r) => r.data),
    enabled: isAuthenticated && !!projectId,
  });

  const versionsQuery = useQuery({
    queryKey: ["versions", projectId],
    queryFn: () => projectsApi.versions(projectId!).then((r) => r.data),
    enabled: isAuthenticated && !!projectId,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasRunning = data?.some(
        (v) => v.status === "running" || v.status === "queued"
      );
      return hasRunning ? 3000 : false;
    },
  });

  return {
    project: projectQuery.data,
    versions: versionsQuery.data ?? [],
    isLoading: projectQuery.isLoading,
    refetchVersions: versionsQuery.refetch,
  };
}
