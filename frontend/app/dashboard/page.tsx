"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { clearStarterIntent, peekStarterIntent } from "@/lib/starter";

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: () =>
      projectsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onClose();
      router.push(`/workspace/${res.data.id}`);
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_24px_60px_rgba(15,23,42,0.16)]">
        <h2 className="mb-2 text-lg font-semibold text-slate-900">新建项目</h2>
        <p className="mb-5 text-sm text-slate-500">
          先创建项目，再在工作区里继续用一句话发起生成。
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
          className="flex flex-col gap-4"
        >
          <div>
            <label className="mb-1 block text-sm text-slate-600">项目名称</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
              placeholder="例如：销售线索助手"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-600">需求描述（可选）</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full resize-none rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
              placeholder="例如：帮我生成一个可录入客户信息并跟踪跟进状态的应用"
            />
          </div>

          {mutation.isError && <p className="text-xs text-red-600">创建失败，请重试</p>}

          <div className="mt-1 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-300 py-2.5 text-sm text-slate-600 transition-colors hover:border-slate-400"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={mutation.isPending || !name.trim()}
              className="flex-1 rounded-xl bg-indigo-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
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
  const [showCreate, setShowCreate] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [starterLaunching, setStarterLaunching] = useState(false);
  const [starterLabel, setStarterLabel] = useState("");
  const [starterError, setStarterError] = useState("");
  const starterLockRef = useRef(false);

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
        const createRes = await projectsApi.create({
          name: starterIntent.title,
          description: starterIntent.description || starterIntent.prompt,
        });
        const projectId = createRes.data.id;

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
    queryFn: () => projectsApi.list().then((r) => r.data),
    enabled: hasHydrated && isAuthenticated,
  });

  if (!mounted || !hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  if (starterLaunching) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,#edf4ff_0%,#f8fafc_42%,#f8fafc_100%)] px-6">
        <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-[0_24px_60px_rgba(15,23,42,0.12)]">
          <div className="mx-auto mb-5 h-14 w-14 animate-spin rounded-full border-4 border-indigo-100 border-t-indigo-600" />
          <h1 className="text-2xl font-semibold text-slate-900">正在一键开始</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            正在为你创建项目并发起生成：{starterLabel || "快速开始项目"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#edf4ff_0%,#f8fafc_42%,#f8fafc_100%)]">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-4 backdrop-blur">
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-sm transition-transform group-hover:-translate-y-0.5">
            N
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-slate-900">Nano Atoms</span>
            <span className="text-xs text-slate-400 group-hover:text-slate-500">返回首页</span>
          </div>
        </Link>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-500">{user?.email}</span>
          <button
            onClick={() => logout()}
            className="text-sm text-slate-600 transition-colors hover:text-slate-900"
          >
            退出
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">我的项目</h1>
            <p className="mt-1 text-sm text-slate-500">从一句话需求开始生成应用与代码。</p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            + 新建项目
          </button>
        </div>

        {starterError && (
          <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {starterError}
          </div>
        )}

        {isLoading ? (
          <div className="py-20 text-center text-slate-500">加载中...</div>
        ) : projects?.length === 0 ? (
          <div className="rounded-3xl border border-slate-200 bg-white py-24 text-center shadow-sm">
            <div className="mb-4 mt-6 text-5xl">[]</div>
            <p className="mb-6 text-slate-600">还没有项目，先创建一个开始生成。</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mb-8 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
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
                className="group rounded-3xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-indigo-300"
              >
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-50 text-sm font-semibold text-indigo-700">
                    {project.name.trim().slice(0, 1).toUpperCase() || "N"}
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-500">
                    项目
                  </span>
                </div>

                <h3 className="mb-2 font-semibold text-slate-900 transition-colors group-hover:text-indigo-700">
                  {project.name}
                </h3>

                <p className="mb-4 min-h-[60px] line-clamp-3 text-sm leading-6 text-slate-500">
                  {project.description || "进入工作区后，用一句话描述需求，平台会自动判断应用形态。"}
                </p>

                <div className="flex items-center justify-between border-t border-slate-100 pt-4">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs ${
                      project.latest_version_id
                        ? "bg-emerald-50 text-emerald-600"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {project.latest_version_id ? "已生成" : "未生成"}
                  </span>
                  <span className="text-xs text-slate-400">
                    {new Date(project.updated_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {showCreate && <CreateProjectModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
