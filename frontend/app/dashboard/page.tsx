"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AtomBrandMark from "@/components/ui/AtomBrandMark";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import { projectsApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import { clearStarterIntent, peekStarterIntent } from "@/lib/starter";

function CreateProjectModal({
  onClose,
  theme,
}: {
  onClose: () => void;
  theme: "classic" | "cyber";
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const router = useRouter();
  const isCyber = theme === "cyber";

  const mutation = useMutation({
    mutationFn: () =>
      projectsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
      }),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
      router.push(`/workspace/${response.data.id}`);
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 backdrop-blur-sm">
      <div
        className={`w-full max-w-md rounded-3xl border p-6 shadow-[0_24px_60px_rgba(15,23,42,0.16)] ${
          isCyber
            ? "border-cyan-400/15 bg-slate-950/88"
            : "border-slate-200 bg-white"
        }`}
      >
        <h2 className={`mb-2 text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
          新建项目
        </h2>
        <p className={`mb-5 text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
          先创建项目，再在工作区里用一句话发起生成。
        </p>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
          className="flex flex-col gap-4"
        >
          <div>
            <label className={`mb-1 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
              项目名称
            </label>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={`w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors ${
                isCyber
                  ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                  : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
              }`}
              placeholder="例如：销售线索助手"
              required
            />
          </div>

          <div>
            <label className={`mb-1 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
              需求描述（可选）
            </label>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className={`w-full resize-none rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors ${
                isCyber
                  ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                  : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
              }`}
              placeholder="例如：帮我生成一个可录入客户信息并跟踪跟进状态的应用"
            />
          </div>

          {mutation.isError && (
            <p className={`text-xs ${isCyber ? "text-rose-300" : "text-red-600"}`}>创建失败，请重试</p>
          )}

          <div className="mt-1 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className={`flex-1 rounded-xl border py-2.5 text-sm transition-colors ${
                isCyber
                  ? "border-cyan-400/15 text-slate-300 hover:border-cyan-300/40 hover:text-white"
                  : "border-slate-300 text-slate-600 hover:border-slate-400"
              }`}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || !name.trim()}
              className={`flex-1 rounded-xl py-2.5 text-sm font-medium transition-all disabled:opacity-50 ${
                isCyber
                  ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.2)] hover:bg-cyan-300"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
            >
              {mutation.isPending ? "创建中..." : "创建并进入"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout, hasHydrated } = useAuthStore();
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [showCreate, setShowCreate] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [starterLaunching, setStarterLaunching] = useState(false);
  const [starterLabel, setStarterLabel] = useState("");
  const [starterError, setStarterError] = useState("");
  const starterLockRef = useRef(false);
  const isCyber = theme === "cyber";

  const deleteProjectMutation = useMutation({
    mutationFn: (targetProjectId: number) => projectsApi.delete(targetProjectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !hasHydrated) return;
    if (!isAuthenticated) router.push("/login");
  }, [mounted, hasHydrated, isAuthenticated, router]);

  useEffect(() => {
    if (!mounted || !hasHydrated || !isAuthenticated) return;
    if (starterLockRef.current) return;

    const starterIntent = peekStarterIntent();
    if (!starterIntent) return;

    starterLockRef.current = true;
    setStarterLaunching(true);
    setStarterLabel(starterIntent.title);
    setStarterError("");

    void (async () => {
      try {
        const createResponse = await projectsApi.create({
          name: starterIntent.title,
          description: starterIntent.description || starterIntent.prompt,
        });
        const projectId = createResponse.data.id;

        clearStarterIntent();
        queryClient.invalidateQueries({ queryKey: ["projects"] });

        try {
          await projectsApi.generate(projectId, starterIntent.prompt);
        } finally {
          router.push(`/workspace/${projectId}`);
        }
      } catch {
        clearStarterIntent();
        starterLockRef.current = false;
        setStarterLaunching(false);
        setStarterError("一键开始失败，请重试一次。");
      }
    })();
  }, [mounted, hasHydrated, isAuthenticated, queryClient, router]);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list().then((response) => response.data),
    enabled: hasHydrated && isAuthenticated,
  });

  if (!mounted || !hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  if (starterLaunching) {
    return (
      <div
        className={`flex min-h-screen items-center justify-center px-6 ${
          isCyber
            ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
            : "bg-[radial-gradient(circle_at_top,#edf4ff_0%,#f8fafc_42%,#f8fafc_100%)]"
        }`}
      >
        <div
          className={`w-full max-w-lg rounded-3xl border p-8 text-center shadow-[0_24px_60px_rgba(15,23,42,0.12)] ${
            isCyber
              ? "border-cyan-400/15 bg-slate-950/80"
              : "border-slate-200 bg-white"
          }`}
        >
          <div
            className={`mx-auto mb-5 h-14 w-14 animate-spin rounded-full border-4 ${
              isCyber ? "border-cyan-400/15 border-t-cyan-300" : "border-indigo-100 border-t-indigo-600"
            }`}
          />
          <h1 className={`text-2xl font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
            正在一键开始
          </h1>
          <p className={`mt-3 text-sm leading-6 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            正在为你创建项目并发起生成：{starterLabel || "快速开始项目"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`min-h-screen ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
          : "bg-[radial-gradient(circle_at_top,#edf4ff_0%,#f8fafc_42%,#f8fafc_100%)]"
      }`}
    >
      <header
        className={`flex items-center justify-between border-b px-6 py-4 backdrop-blur ${
          isCyber
            ? "border-cyan-400/12 bg-slate-950/60"
            : "border-slate-200 bg-white/80"
        }`}
      >
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
            <span className={`font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
              Nano Atoms
            </span>
            <span className={`text-xs ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
              返回首页
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
          <span className={`hidden text-sm sm:block ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            {user?.email}
          </span>
          <button
            onClick={() => logout()}
            className={`text-sm transition-colors ${
              isCyber ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            退出
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <h1 className={`text-3xl font-bold ${isCyber ? "text-white" : "text-slate-900"}`}>
              我的项目
            </h1>
            <p className={`mt-1 text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
              从一句话需求开始生成应用与代码。
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className={`rounded-xl px-5 py-2.5 text-sm font-medium transition-all ${
              isCyber
                ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.18)] hover:bg-cyan-300"
                : "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700"
            }`}
          >
            + 新建项目
          </button>
        </div>

        {starterError && (
          <div
            className={`mb-6 rounded-2xl border px-4 py-3 text-sm ${
              isCyber
                ? "border-amber-400/20 bg-amber-400/10 text-amber-200"
                : "border-amber-200 bg-amber-50 text-amber-700"
            }`}
          >
            {starterError}
          </div>
        )}

        {isLoading ? (
          <div className={`py-20 text-center ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            加载中...
          </div>
        ) : projects?.length === 0 ? (
          <div
            className={`rounded-3xl border py-24 text-center ${
              isCyber
                ? "border-cyan-400/12 bg-slate-950/70 shadow-[0_18px_50px_rgba(2,8,23,0.4)]"
                : "border-slate-200 bg-white shadow-sm"
            }`}
          >
            <div className="mb-4 mt-6 text-5xl">[]</div>
            <p className={`mb-6 ${isCyber ? "text-slate-400" : "text-slate-600"}`}>
              还没有项目，先创建一个开始生成。
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className={`mb-8 rounded-xl px-6 py-3 text-sm font-medium transition-all ${
                isCyber
                  ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.18)] hover:bg-cyan-300"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
            >
              创建第一个项目
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {projects?.map((project) => (
              <Link
                key={project.id}
                href={`/workspace/${project.id}`}
                className={`group rounded-3xl border p-5 transition-all hover:-translate-y-0.5 ${
                  isCyber
                    ? "border-cyan-400/12 bg-slate-950/70 shadow-[0_18px_50px_rgba(2,8,23,0.4)] hover:border-cyan-300/35"
                    : "border-slate-200 bg-white shadow-sm hover:border-indigo-300"
                }`}
              >
                <div className="mb-4 flex items-start justify-between">
                  <div
                    className={`flex h-11 w-11 items-center justify-center rounded-2xl text-sm font-semibold ${
                      isCyber
                        ? "border border-cyan-400/15 bg-cyan-400/10 text-cyan-200"
                        : "bg-indigo-50 text-indigo-700"
                    }`}
                  >
                    {project.name.trim().slice(0, 1).toUpperCase() || "N"}
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs ${
                        isCyber
                          ? "bg-slate-900 text-slate-400"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      项目
                    </span>
                    <button
                      type="button"
                      disabled={deleteProjectMutation.isPending}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        if (!window.confirm(`确定删除项目「${project.name}」吗？该操作不可恢复。`)) {
                          return;
                        }
                        deleteProjectMutation.mutate(project.id);
                      }}
                      className={`rounded-full px-2.5 py-1 text-xs transition-colors disabled:opacity-40 ${
                        isCyber
                          ? "bg-rose-400/10 text-rose-300 hover:bg-rose-400/20"
                          : "bg-rose-50 text-rose-600 hover:bg-rose-100"
                      }`}
                    >
                      {deleteProjectMutation.isPending ? "删除中" : "删除"}
                    </button>
                  </div>
                </div>

                <h3
                  className={`mb-2 font-semibold transition-colors ${
                    isCyber
                      ? "text-white group-hover:text-cyan-200"
                      : "text-slate-900 group-hover:text-indigo-700"
                  }`}
                >
                  {project.name}
                </h3>

                <p
                  className={`mb-4 min-h-[60px] line-clamp-3 text-sm leading-6 ${
                    isCyber ? "text-slate-400" : "text-slate-500"
                  }`}
                >
                  {project.description || "进入工作区后，用一句话描述需求，平台会自动判断应用形态。"}
                </p>

                <div
                  className={`flex items-center justify-between border-t pt-4 ${
                    isCyber ? "border-cyan-400/10" : "border-slate-100"
                  }`}
                >
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs ${
                      project.latest_version_id
                        ? isCyber
                          ? "bg-emerald-400/10 text-emerald-300"
                          : "bg-emerald-50 text-emerald-600"
                        : isCyber
                          ? "bg-slate-900 text-slate-400"
                          : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {project.latest_version_id ? "已生成" : "未生成"}
                  </span>
                  <span className={`text-xs ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
                    {new Date(project.updated_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {showCreate && <CreateProjectModal onClose={() => setShowCreate(false)} theme={theme} />}
    </div>
  );
}
