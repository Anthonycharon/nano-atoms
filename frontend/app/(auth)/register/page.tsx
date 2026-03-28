"use client";

import axios from "axios";
import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AuthMascotCats from "@/components/auth/AuthMascotCats";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import AtomBrandMark from "@/components/ui/AtomBrandMark";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
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
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");
  const [passwordFocused, setPasswordFocused] = useState(false);
  const [error, setError] = useState("");
  const [emailExists, setEmailExists] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [codeSent, setCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [deliveryHint, setDeliveryHint] = useState("");
  const starterIntent = getStarterIntentFromSearchParams(searchParams);
  const isCyber = theme === "cyber";
  const loginHref = starterIntent ? appendStarterParams("/login", starterIntent) : "/login";

  useEffect(() => {
    if (!hasHydrated) return;
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [hasHydrated, isAuthenticated, router]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(() => setCountdown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  const canSendCode = useMemo(() => {
    return !!email.trim() && countdown === 0 && !sendingCode;
  }, [email, countdown, sendingCode]);

  if (!hasHydrated) {
    return <div className="min-h-screen bg-slate-50" />;
  }

  const handleSendCode = async () => {
    setError("");
    setEmailExists(false);
    if (!email.trim()) {
      setError("请先输入注册邮箱");
      return;
    }

    setSendingCode(true);
    try {
      const { data } = await authApi.sendRegisterCode(email.trim());
      setVerificationToken(data.verification_token);
      setCodeSent(true);
      setCountdown(data.resend_after_seconds || 60);
      setDeliveryHint(`验证码已发送到 ${email.trim()}，请检查收件箱、垃圾箱或广告邮件。`);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail === "Email already registered") {
        setEmailExists(true);
        setError("该邮箱已注册，请直接登录");
      } else if (axios.isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("验证码发送失败，请稍后重试");
      }
      setDeliveryHint("");
    } finally {
      setSendingCode(false);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setEmailExists(false);

    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }
    if (!verificationToken) {
      setError("请先获取邮箱验证码");
      return;
    }
    if (!verificationCode.trim()) {
      setError("请输入邮箱验证码");
      return;
    }

    setLoading(true);
    try {
      if (starterIntent) {
        persistStarterIntent(starterIntent);
      }
      await register(email.trim(), password, verificationToken, verificationCode.trim());
    } catch (err) {
      if (
        axios.isAxiosError(err) &&
        (err.response?.data?.detail === "Invalid email verification code" ||
          err.response?.data?.detail === "Invalid email verification")
      ) {
        setError("邮箱验证码错误，请重新输入");
      } else if (axios.isAxiosError(err) && err.response?.data?.detail === "Email verification expired") {
        setError("邮箱验证码已过期，请重新获取");
        setVerificationToken("");
        setCodeSent(false);
        setCountdown(0);
        setDeliveryHint("");
      } else if (axios.isAxiosError(err) && err.response?.data?.detail === "Email already registered") {
        setEmailExists(true);
        setError("该邮箱已注册，请直接登录");
      } else if (axios.isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("注册失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`relative min-h-screen overflow-hidden ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
          : "bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_45%,#f8fafc_100%)]"
      }`}
    >
      <div className="absolute right-6 top-6 z-20">
        <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
      </div>

      {isCyber ? (
        <>
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(34,211,238,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.08)_1px,transparent_1px)] bg-[size:88px_88px] opacity-35" />
          <div className="pointer-events-none absolute left-[10%] top-[12%] h-64 w-64 rounded-full bg-cyan-400/12 blur-3xl" />
          <div className="pointer-events-none absolute right-[6%] top-[18%] h-72 w-72 rounded-full bg-sky-500/10 blur-3xl" />
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
                  isCyber ? "border-cyan-400/20 bg-slate-900/80" : "border-slate-200 bg-white"
                }`}
              >
                <AtomBrandMark className="h-9 w-9" />
              </span>
              <span>
                <span className={`block text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
                  Nano Atoms
                </span>
                <span className={`block text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                  AI 应用生成工作台
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
              邮箱注册
            </div>

            <h1
              className={`relative mt-5 max-w-2xl text-4xl font-black leading-tight md:text-5xl ${
                isCyber ? "text-white" : "text-slate-900"
              }`}
            >
              注册后立刻开始构建你的 AI 应用。
            </h1>
            <p
              className={`relative mt-4 max-w-2xl text-sm leading-7 md:text-base ${
                isCyber ? "text-slate-300" : "text-slate-600"
              }`}
            >
              注册邮箱会收到真实验证码。完成验证后即可进入工作台，继续生成、迭代和发布你的应用。
            </p>

            <div className="relative mt-8 grid gap-3 sm:grid-cols-3">
              {[
                ["真实邮箱验证", "验证码会发送到你的注册邮箱，确认身份后再完成注册。"],
                ["应用持续迭代", "注册成功后即可继续对话，优化布局、文案和风格。"],
                ["发布链路打通", "预览、代码与发布流程保持一致，方便直接交付。"],
              ].map(([title, description]) => (
                <div
                  key={title}
                  className={`rounded-2xl border p-4 ${
                    isCyber ? "border-cyan-400/12 bg-slate-900/72" : "border-slate-200 bg-white/80"
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

            <AuthMascotCats passwordFocused={passwordFocused} isCyber={isCyber} className="relative mt-8 md:mt-10" />
          </section>

          <section
            className={`rounded-[32px] border p-6 md:p-8 ${
              isCyber
                ? "border-cyan-400/15 bg-slate-950/72 text-white shadow-[0_28px_80px_rgba(2,12,27,0.42)]"
                : "border-slate-200 bg-white text-slate-900 shadow-[0_28px_80px_rgba(15,23,42,0.1)]"
            }`}
          >
            <div className="mb-8">
              <h2 className={`text-2xl font-bold ${isCyber ? "text-white" : "text-slate-900"}`}>创建账号</h2>
              <p className={`mt-2 text-sm leading-7 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                输入邮箱、获取验证码并设置密码，即可完成注册。
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

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {error && (
                <div
                  className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${
                    isCyber ? "border-rose-400/30 bg-rose-400/10 text-rose-200" : "border-red-200 bg-red-50 text-red-600"
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
                <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>邮箱</label>
                <div className="flex gap-3">
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className={`flex-1 rounded-2xl border px-4 py-3 text-sm outline-none transition-colors ${
                      isCyber
                        ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                        : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
                    }`}
                    placeholder="you@example.com"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => void handleSendCode()}
                    disabled={!canSendCode}
                    className={`min-w-[128px] rounded-2xl border px-4 py-3 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
                      isCyber
                        ? "border-cyan-400/20 bg-slate-900/85 text-cyan-200 hover:border-cyan-300/40"
                        : "border-slate-300 bg-white text-slate-700 hover:border-indigo-400"
                    }`}
                  >
                    {sendingCode ? "发送中..." : countdown > 0 ? `${countdown}s 后重发` : "发送验证码"}
                  </button>
                </div>
              </div>

              <div>
                <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>邮箱验证码</label>
                <input
                  type="text"
                  value={verificationCode}
                  onChange={(event) => setVerificationCode(event.target.value)}
                  className={`w-full rounded-2xl border px-4 py-3 text-sm tracking-[0.28em] outline-none transition-colors ${
                    isCyber
                      ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
                      : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
                  }`}
                  placeholder={codeSent ? "请输入邮箱中的 6 位验证码" : "请先发送验证码"}
                  autoComplete="one-time-code"
                  maxLength={6}
                  required
                />
                <p className={`mt-2 text-xs ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                  {codeSent ? "验证码已发送到注册邮箱，10 分钟内有效。" : "点击右侧按钮后，验证码将发送到你的邮箱。"}
                </p>
                {deliveryHint && (
                  <div
                    className={`mt-3 rounded-2xl border px-4 py-3 text-xs leading-6 ${
                      isCyber
                        ? "border-cyan-400/18 bg-cyan-400/10 text-cyan-100"
                        : "border-sky-200 bg-sky-50 text-sky-700"
                    }`}
                  >
                    {deliveryHint}
                  </div>
                )}
              </div>

              <div>
                <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>密码</label>
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
                  placeholder="至少 6 位"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading || !verificationToken}
                className={`mt-1 w-full rounded-2xl py-3 text-sm font-semibold transition-all disabled:opacity-50 ${
                  isCyber
                    ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.2)] hover:bg-cyan-300"
                    : "bg-indigo-600 text-white hover:bg-indigo-700"
                }`}
              >
                {loading ? "注册中..." : "创建账号"}
              </button>
            </form>

            <p className={`mt-5 text-center text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
              已有账号？{" "}
              <Link
                href={loginHref}
                className={isCyber ? "text-cyan-300 hover:text-cyan-200" : "text-indigo-600 hover:text-indigo-700"}
              >
                直接登录
              </Link>
            </p>
          </section>
        </div>
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
