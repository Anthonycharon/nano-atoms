"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";
import {
  appendStarterParams,
  getStarterIntentFromSearchParams,
  persistStarterIntent,
} from "@/lib/starter";

function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [emailExists, setEmailExists] = useState(false);
  const [loading, setLoading] = useState(false);

  const starterIntent = getStarterIntentFromSearchParams(searchParams);

  useEffect(() => {
    if (!hasHydrated) return;
    if (isAuthenticated) router.replace("/dashboard");
  }, [hasHydrated, isAuthenticated, router]);

  if (!hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setEmailExists(false);

    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }

    setLoading(true);
    try {
      if (starterIntent) {
        persistStarterIntent(starterIntent);
      }
      await register(email, password);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail === "Email already registered") {
        setEmailExists(true);
        setError("该邮箱已注册，请直接登录");
      } else {
        setError("注册失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  const loginHref = starterIntent
    ? appendStarterParams("/login", starterIntent)
    : "/login";

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_45%,#f8fafc_100%)] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Link href="/" className="mb-6 inline-flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white">
              N
            </div>
            <span className="text-lg font-semibold">Nano Atoms</span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">创建账号</h1>
          <p className="mt-1 text-sm text-slate-500">开始构建你的 AI 应用</p>
          {starterIntent && (
            <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-left text-xs leading-5 text-slate-600">
              <div>将为你一键启动：{starterIntent.title}</div>
              <div className="mt-1 line-clamp-3">{starterIntent.prompt}</div>
            </div>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.08)]"
        >
          {error && (
            <div className="flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              <span>{error}</span>
              {emailExists && (
                <button
                  type="button"
                  onClick={() => router.push(loginHref)}
                  className="shrink-0 text-indigo-600 underline transition-colors hover:text-indigo-700"
                >
                  去登录
                </button>
              )}
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm text-slate-600">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:border-indigo-500"
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-slate-600">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:border-indigo-500"
              placeholder="至少 6 位"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-1 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "创建中..." : "创建账号"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          已有账号？{" "}
          <Link href={loginHref} className="text-indigo-600 transition-colors hover:text-indigo-700">
            直接登录
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
