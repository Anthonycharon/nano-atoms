"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import LoginMascotCat from "@/components/auth/LoginMascotCat";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import AtomBrandMark from "@/components/ui/AtomBrandMark";
import { useAuth } from "@/hooks/useAuth";
import {
  appendStarterParams,
  getStarterIntentFromSearchParams,
  persistStarterIntent,
} from "@/lib/starter";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const isCyber = theme === "cyber";

  useEffect(() => {
    if (!hasHydrated) return;
    if (isAuthenticated) router.replace("/dashboard");
  }, [hasHydrated, isAuthenticated, router]);

  if (!hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  const starterIntent = getStarterIntentFromSearchParams(searchParams);
  const registerHref = starterIntent ? appendStarterParams("/register", starterIntent) : "/register";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (starterIntent) {
        persistStarterIntent(starterIntent);
      }
      await login(email, password);
    } catch {
      setError("邮箱或密码错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`relative min-h-screen overflow-hidden ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#15395f_0%,#081221_34%,#040814_72%,#020409_100%)]"
          : "bg-[radial-gradient(circle_at_top,#eff6ff_0%,#f8fafc_42%,#f8fafc_100%)]"
      }`}
    >
      <div className="absolute right-6 top-6 z-20">
        <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
      </div>

      {isCyber ? (
        <>
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(34,211,238,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.08)_1px,transparent_1px)] bg-[size:88px_88px] opacity-35" />
          <div className="pointer-events-none absolute left-[10%] top-[14%] h-72 w-72 rounded-full bg-cyan-400/12 blur-3xl" />
          <div className="pointer-events-none absolute right-[8%] top-[20%] h-80 w-80 rounded-full bg-sky-500/10 blur-3xl" />
        </>
      ) : (
        <>
          <div className="pointer-events-none absolute left-[8%] top-[12%] h-64 w-64 rounded-full bg-sky-200/35 blur-3xl" />
          <div className="pointer-events-none absolute right-[10%] top-[18%] h-72 w-72 rounded-full bg-indigo-100/60 blur-3xl" />
        </>
      )}

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-10 md:px-6">
        <div className="grid w-full gap-6 lg:grid-cols-[1.06fr_0.94fr]">
          <section
            className={`relative overflow-hidden rounded-[32px] border p-6 md:p-8 ${
              isCyber
                ? "border-cyan-400/15 bg-slate-950/68 text-white"
                : "border-slate-200 bg-white/85 text-slate-900 shadow-[0_28px_80px_rgba(15,23,42,0.1)]"
            }`}
          >
            <div
              className={`pointer-events-none absolute inset-0 ${
                isCyber
                  ? "bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_44%)]"
                  : "bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.14),transparent_42%)]"
              }`}
            />

            <Link href="/" className="relative inline-flex items-center gap-3">
              <span
                className={`flex h-12 w-12 items-center justify-center rounded-2xl border ${
                  isCyber
                    ? "border-cyan-400/20 bg-slate-900/80"
                    : "border-slate-200 bg-white"
                }`}
              >
                <AtomBrandMark className="h-9 w-9" />
              </span>
              <span>
                <span className={`block text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
                  Nano Atoms
                </span>
                <span className={`block text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                  AI 网站生成工作台
                </span>
              </span>
            </Link>

            <div
              className={`relative mt-8 inline-flex rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] ${
                isCyber
                  ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-200"
                  : "border-slate-200 bg-white/70 text-slate-600"
              }`}
            >
              完整网站生成
            </div>

            <h1 className={`relative mt-5 max-w-2xl text-4xl font-black leading-tight md:text-5xl ${isCyber ? "text-white" : "text-slate-900"}`}>
              登录后继续生成、修改并发布你的网站。
            </h1>
            <p className={`relative mt-4 max-w-2xl text-sm leading-7 md:text-base ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
              一句话生成完整网站，多页面共享导航、统一视觉和交互流程，后续还可以继续迭代文案、结构与样式。
            </p>

            <div className="relative mt-8 grid gap-3 sm:grid-cols-3">
              {[
                ["完整结构", "不是单页草图，而是连贯的网站信息架构"],
                ["持续迭代", "继续对话就能改布局、文案和视觉"],
                ["快速发布", "预览、代码和发布流程保持连贯"],
              ].map(([title, description]) => (
                <div
                  key={title}
                  className={`rounded-2xl border p-4 ${
                    isCyber
                      ? "border-cyan-400/12 bg-slate-900/72"
                      : "border-slate-200 bg-white/80"
                  }`}
                >
                  <div className={`text-sm font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
                    {title}
                  </div>
                  <div className={`mt-2 text-xs leading-6 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                    {description}
                  </div>
                </div>
              ))}
            </div>

            <LoginMascotCat passwordFocused={passwordFocused} isCyber={isCyber} className="relative mt-8 md:mt-10" />
          </section>

          <section
            className={`rounded-[32px] border p-6 md:p-8 ${
              isCyber
                ? "border-cyan-400/15 bg-slate-950/72 text-white shadow-[0_28px_80px_rgba(2,12,27,0.42)]"
                : "border-slate-200 bg-white text-slate-900 shadow-[0_28px_80px_rgba(15,23,42,0.1)]"
            }`}
          >
            <div className="mb-8">
              <h2 className={`text-2xl font-bold ${isCyber ? "text-white" : "text-slate-900"}`}>
                欢迎回来
              </h2>
              <p className={`mt-2 text-sm leading-7 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                登录你的工作区，继续推进正在生成的网站与应用。
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {error && (
                <div
                  className={`rounded-2xl border px-4 py-3 text-sm ${
                    isCyber
                      ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
                      : "border-red-200 bg-red-50 text-red-600"
                  }`}
                >
                  {error}
                </div>
              )}

              <div>
                <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
                  邮箱
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className={`w-full rounded-2xl border px-4 py-3 text-sm outline-none transition-colors ${
                    isCyber
                      ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                      : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
                  }`}
                  placeholder="you@example.com"
                  required
                />
              </div>

              <div>
                <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
                  密码
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  onFocus={() => setPasswordFocused(true)}
                  onBlur={() => setPasswordFocused(false)}
                  className={`w-full rounded-2xl border px-4 py-3 text-sm outline-none transition-colors ${
                    isCyber
                      ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                      : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
                  }`}
                  placeholder="请输入密码"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`mt-2 w-full rounded-2xl py-3 text-sm font-semibold transition-all disabled:opacity-50 ${
                  isCyber
                    ? "bg-cyan-400 text-slate-950 shadow-[0_0_26px_rgba(34,211,238,0.24)] hover:bg-cyan-300"
                    : "bg-indigo-600 text-white hover:bg-indigo-700"
                }`}
              >
                {loading ? "登录中..." : "登录"}
              </button>
            </form>

            <p className={`mt-5 text-center text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
              还没有账号？{" "}
              <Link
                href={registerHref}
                className={isCyber ? "text-cyan-300 hover:text-cyan-200" : "text-indigo-600 hover:text-indigo-700"}
              >
                免费注册
              </Link>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
