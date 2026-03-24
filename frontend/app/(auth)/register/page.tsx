"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
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
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [emailExists, setEmailExists] = useState(false);
  const [loading, setLoading] = useState(false);
  const starterIntent = getStarterIntentFromSearchParams(searchParams);
  const isCyber = theme === "cyber";

  useEffect(() => {
    if (!hasHydrated) return;
    if (isAuthenticated) router.replace("/dashboard");
  }, [hasHydrated, isAuthenticated, router]);

  if (!hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
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

  const loginHref = starterIntent ? appendStarterParams("/login", starterIntent) : "/login";

  return (
    <div
      className={`relative flex min-h-screen items-center justify-center overflow-hidden px-4 ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
          : "bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_45%,#f8fafc_100%)]"
      }`}
    >
      {isCyber && (
        <>
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(34,211,238,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.08)_1px,transparent_1px)] bg-[size:88px_88px] opacity-35" />
          <div className="pointer-events-none absolute left-[10%] top-[12%] h-64 w-64 rounded-full bg-cyan-400/12 blur-3xl" />
          <div className="pointer-events-none absolute right-[6%] top-[18%] h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
        </>
      )}

      <div className="absolute right-6 top-6 z-10">
        <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
      </div>

      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-8 text-center">
          <Link href="/" className="mb-6 inline-flex items-center gap-2">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-xl text-sm font-bold ${
                isCyber
                  ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.28)]"
                  : "bg-indigo-600 text-white"
              }`}
            >
              N
            </div>
            <span className={`text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
              Nano Atoms
            </span>
          </Link>
          <h1 className={`text-2xl font-bold ${isCyber ? "text-white" : "text-slate-900"}`}>
            创建账号
          </h1>
          <p className={`mt-1 text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
            开始构建你的 AI 应用
          </p>
          {starterIntent && (
            <div
              className={`mt-4 rounded-2xl border px-4 py-3 text-left text-xs leading-5 ${
                isCyber
                  ? "border-cyan-400/15 bg-slate-950/70 text-slate-300"
                  : "border-indigo-100 bg-indigo-50 text-slate-600"
              }`}
            >
              <div>登录后将为你一键启动：{starterIntent.title}</div>
              <div className="mt-1 line-clamp-3">{starterIntent.prompt}</div>
            </div>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className={`flex flex-col gap-4 rounded-3xl border p-6 shadow-[0_18px_50px_rgba(15,23,42,0.12)] ${
            isCyber
              ? "border-cyan-400/15 bg-slate-950/70"
              : "border-slate-200 bg-white"
          }`}
        >
          {error && (
            <div
              className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
                isCyber
                  ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
                  : "border-red-200 bg-red-50 text-red-600"
              }`}
            >
              <span>{error}</span>
              {emailExists && (
                <button
                  type="button"
                  onClick={() => router.push(loginHref)}
                  className={isCyber ? "text-cyan-300 underline hover:text-cyan-200" : "text-indigo-600 underline hover:text-indigo-700"}
                >
                  去登录
                </button>
              )}
            </div>
          )}

          <div>
            <label className={`mb-1 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
              邮箱
            </label>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={`w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors ${
                isCyber
                  ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                  : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
              }`}
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label className={`mb-1 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={`w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors ${
                isCyber
                  ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                  : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
              }`}
              placeholder="至少 6 位"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`mt-1 w-full rounded-xl py-2.5 text-sm font-medium transition-all disabled:opacity-50 ${
              isCyber
                ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.2)] hover:bg-cyan-300"
                : "bg-indigo-600 text-white hover:bg-indigo-700"
            }`}
          >
            {loading ? "创建中..." : "创建账号"}
          </button>
        </form>

        <p className={`mt-4 text-center text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
          已有账号？{" "}
          <Link
            href={loginHref}
            className={isCyber ? "text-cyan-300 hover:text-cyan-200" : "text-indigo-600 hover:text-indigo-700"}
          >
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
