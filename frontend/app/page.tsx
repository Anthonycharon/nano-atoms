"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";
import type { HomeTheme } from "@/stores/themeStore";
import {
  appendStarterParams,
  buildExampleStarter,
  buildTemplateStarter,
  persistStarterIntent,
} from "@/lib/starter";

const templates = [
  { name: "线索收集", icon: "表", desc: "适合收集客户信息、表单提交与状态跟进。" },
  { name: "任务管理", icon: "务", desc: "适合看板、列表、审批和团队协作场景。" },
  { name: "活动落地页", icon: "页", desc: "适合营销页面、报名页和产品介绍页。" },
  { name: "反馈工具", icon: "评", desc: "适合评分、反馈收集与问卷场景。" },
];

const examples = [
  "帮我做一个销售线索录入工具，需要客户信息、跟进状态和备注记录",
  "创建一个任务管理仪表盘，可以新增、完成和筛选任务",
  "做一个产品发布页，带亮点介绍、倒计时和报名表单",
];

const features = [
  {
    title: "多智能体协作",
    desc: "需求理解、结构设计、视觉生成和交互配置按流水线协同完成。",
  },
  {
    title: "实时预览与文件",
    desc: "生成完成后直接查看页面效果和完整项目文件树，便于继续修改。",
  },
  {
    title: "持续迭代",
    desc: "每次修改都会形成新版本，方便对比、回退和继续优化。",
  },
];

function LandingActions({ theme }: { theme: HomeTheme }) {
  const { isAuthenticated, user, hasHydrated } = useAuthStore();
  const { logout } = useAuth();
  const isCyber = theme === "cyber";

  if (!hasHydrated) {
    return (
      <div className="flex gap-3">
        <div
          className={`h-10 w-24 animate-pulse rounded-lg ${
            isCyber ? "bg-slate-800/80" : "bg-slate-200/80"
          }`}
        />
        <div
          className={`h-10 w-28 animate-pulse rounded-lg ${
            isCyber ? "bg-slate-800/80" : "bg-slate-200/80"
          }`}
        />
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <div className={`text-sm font-medium ${isCyber ? "text-slate-100" : "text-slate-800"}`}>
            已登录
          </div>
          <div
            className={`max-w-48 truncate text-xs ${
              isCyber ? "text-slate-400" : "text-slate-500"
            }`}
          >
            {user?.email}
          </div>
        </div>
        <Link
          href="/dashboard"
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
            isCyber
              ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.28)] hover:bg-cyan-300"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
        >
          进入工作台
        </Link>
        <button
          onClick={logout}
          className={`px-4 py-2 text-sm transition-colors ${
            isCyber ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          退出登录
        </button>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <Link
        href="/login"
        className={`px-4 py-2 text-sm transition-colors ${
          isCyber ? "text-slate-300 hover:text-white" : "text-slate-600 hover:text-slate-900"
        }`}
      >
        登录
      </Link>
      <Link
        href="/register"
        className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
          isCyber
            ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.28)] hover:bg-cyan-300"
            : "bg-indigo-600 text-white hover:bg-indigo-700"
        }`}
      >
        免费开始
      </Link>
    </div>
  );
}

function ExampleEntry({
  example,
  theme,
}: {
  example: string;
  theme: HomeTheme;
}) {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const starter = buildExampleStarter(example);
  const isCyber = theme === "cyber";

  const baseClass = isCyber
    ? "group flex w-full items-center justify-between rounded-2xl border border-cyan-400/15 bg-slate-950/65 px-5 py-4 text-left text-sm text-slate-100 shadow-[0_18px_50px_rgba(2,8,23,0.4)] transition-all hover:-translate-y-0.5 hover:border-cyan-300/40 hover:shadow-[0_22px_56px_rgba(6,182,212,0.16)]"
    : "group flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left text-sm text-slate-700 shadow-sm transition-colors hover:border-indigo-300";

  const hintClass = isCyber
    ? "text-xs text-cyan-300 opacity-0 transition-opacity group-hover:opacity-100"
    : "text-xs text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100";

  if (hasHydrated && isAuthenticated) {
    return (
      <button
        type="button"
        onClick={() => {
          persistStarterIntent(starter);
          router.push("/dashboard");
        }}
        className={baseClass}
      >
        <span>{example}</span>
        <span className={hintClass}>一键开始</span>
      </button>
    );
  }

  return (
    <Link href={appendStarterParams("/register", starter)} className={baseClass}>
      <span>{example}</span>
      <span className={hintClass}>用这个开始</span>
    </Link>
  );
}

function TemplateEntry({
  name,
  icon,
  desc,
  theme,
}: {
  name: string;
  icon: string;
  desc: string;
  theme: HomeTheme;
}) {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const starter = buildTemplateStarter(name, desc);
  const isCyber = theme === "cyber";

  const baseClass = isCyber
    ? "rounded-2xl border border-cyan-400/15 bg-slate-950/65 p-5 text-center shadow-[0_18px_50px_rgba(2,8,23,0.4)] transition-all hover:-translate-y-0.5 hover:border-cyan-300/40 hover:shadow-[0_22px_56px_rgba(6,182,212,0.16)]"
    : "rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm transition-all hover:-translate-y-0.5 hover:border-indigo-300";

  const iconClass = isCyber
    ? "mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 font-semibold text-cyan-200"
    : "mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-semibold text-indigo-700";

  const content = (
    <>
      <div className={iconClass}>{icon}</div>
      <div className={`mb-1 text-sm font-medium ${isCyber ? "text-slate-100" : "text-slate-900"}`}>
        {name}
      </div>
      <div className={`text-xs leading-5 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
        {desc}
      </div>
    </>
  );

  if (hasHydrated && isAuthenticated) {
    return (
      <button
        type="button"
        onClick={() => {
          persistStarterIntent(starter);
          router.push("/dashboard");
        }}
        className={baseClass}
      >
        {content}
      </button>
    );
  }

  return (
    <Link href={appendStarterParams("/register", starter)} className={baseClass}>
      {content}
    </Link>
  );
}

export default function LandingPage() {
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const primaryHref = hasHydrated && isAuthenticated ? "/dashboard" : "/register";
  const secondaryHref = hasHydrated && isAuthenticated ? "/dashboard" : "/login";
  const isCyber = theme === "cyber";

  return (
    <main
      className={`relative min-h-screen overflow-hidden transition-colors duration-300 ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_30%,#040814_70%,#02040a_100%)] text-slate-100"
          : "bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_38%,#f8fafc_100%)] text-slate-900"
      }`}
    >
      {isCyber ? (
        <>
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(34,211,238,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.08)_1px,transparent_1px)] bg-[size:88px_88px] opacity-35" />
          <div className="pointer-events-none absolute left-[-8%] top-[-8%] h-72 w-72 rounded-full bg-cyan-400/14 blur-3xl" />
          <div className="pointer-events-none absolute right-[-10%] top-[12%] h-80 w-80 rounded-full bg-sky-500/12 blur-3xl" />
          <div className="pointer-events-none absolute bottom-[-12%] left-[18%] h-96 w-96 rounded-full bg-teal-400/10 blur-3xl" />
        </>
      ) : (
        <>
          <div className="pointer-events-none absolute left-[-10%] top-[-10%] h-72 w-72 rounded-full bg-indigo-100/60 blur-3xl" />
          <div className="pointer-events-none absolute right-[-8%] top-[10%] h-80 w-80 rounded-full bg-sky-100/70 blur-3xl" />
        </>
      )}

      <header
        className={`relative z-10 flex items-center justify-between border-b px-6 py-4 backdrop-blur ${
          isCyber
            ? "border-cyan-400/15 bg-slate-950/60"
            : "border-slate-200/80 bg-white/80"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-xl text-sm font-bold shadow-sm ${
              isCyber
                ? "bg-cyan-400 text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.28)]"
                : "bg-indigo-600 text-white"
            }`}
          >
            N
          </div>
          <div className="flex flex-col">
            <span className={`text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
              Nano Atoms
            </span>
            <span className={`text-xs ${isCyber ? "text-slate-400" : "text-slate-400"}`}>
              {isCyber ? "Dark Sci-Fi Mode" : "Classic Light Mode"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
          <LandingActions theme={theme} />
        </div>
      </header>

      <section className="relative z-10 mx-auto max-w-6xl px-6 pb-16 pt-24 text-center">
        <div
          className={`mb-8 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm shadow-sm ${
            isCyber
              ? "border-cyan-400/20 bg-slate-950/70 text-cyan-200 shadow-[0_0_30px_rgba(34,211,238,0.12)]"
              : "border-indigo-100 bg-white text-indigo-600"
          }`}
        >
          <span
            className={`h-2 w-2 animate-pulse rounded-full ${
              isCyber ? "bg-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.9)]" : "bg-indigo-500"
            }`}
          />
          {isCyber ? "高质感应用生成模式" : "多智能体应用生成平台"}
        </div>

        <h1 className="mb-6 text-5xl font-bold leading-tight tracking-tight md:text-6xl">
          用一句话描述需求，
          <br />
          {isCyber ? "生成更具未来感的应用体验与代码" : "生成可交互的应用原型与代码"}
        </h1>

        <p
          className={`mx-auto mb-10 max-w-3xl text-xl leading-8 ${
            isCyber ? "text-slate-300" : "text-slate-600"
          }`}
        >
          从需求拆解、页面结构、视觉风格到交互逻辑，平台会自动生成完整结果，并支持继续迭代、
          上传资料增强，以及质量守护与自动修复。
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href={primaryHref}
            className={`rounded-xl px-8 py-3 text-base font-semibold transition-all ${
              isCyber
                ? "bg-cyan-400 text-slate-950 shadow-[0_0_30px_rgba(34,211,238,0.24)] hover:bg-cyan-300"
                : "bg-indigo-600 text-white shadow-sm hover:bg-indigo-700"
            }`}
          >
            {hasHydrated && isAuthenticated ? "进入工作台" : "立即开始"}
          </Link>
          <Link
            href={secondaryHref}
            className={`rounded-xl border px-8 py-3 text-base transition-colors ${
              isCyber
                ? "border-cyan-400/20 bg-slate-950/55 text-slate-200 hover:border-cyan-300/40 hover:text-white"
                : "border-slate-300 bg-white text-slate-700 hover:border-slate-400"
            }`}
          >
            {hasHydrated && isAuthenticated ? "查看项目" : "已有账号登录"}
          </Link>
        </div>

        <div
          className={`mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-4 rounded-[28px] border p-5 text-left md:grid-cols-3 ${
            isCyber
              ? "border-cyan-400/15 bg-slate-950/45 shadow-[0_30px_90px_rgba(2,8,23,0.45)]"
              : "border-slate-200 bg-white/80 shadow-[0_20px_60px_rgba(15,23,42,0.08)]"
          }`}
        >
          {[
            ["更高质量", "Design Director + Quality Guardian 让首版结果更完整。"],
            ["更可控", "支持局部重生成，不必每次都推翻整版应用。"],
            ["更有上下文", "支持上传图片、PDF、CSV 等素材参与生成。"],
          ].map(([title, desc]) => (
            <div
              key={title}
              className={`rounded-2xl border px-4 py-4 ${
                isCyber
                  ? "border-cyan-400/10 bg-slate-900/70"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className={`text-sm font-semibold ${isCyber ? "text-cyan-200" : "text-slate-900"}`}>
                {title}
              </div>
              <div className={`mt-2 text-sm leading-6 ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
                {desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-4xl px-6 pb-16">
        <p className={`mb-4 text-center text-sm ${isCyber ? "text-slate-400" : "text-slate-500"}`}>
          示例需求，一键开始
        </p>
        <div className="flex flex-col gap-3">
          {examples.map((example) => (
            <ExampleEntry key={example} example={example} theme={theme} />
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto max-w-5xl px-6 pb-20">
        <h2 className={`mb-8 text-center text-2xl font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
          常见起步模板
        </h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {templates.map((template) => (
            <TemplateEntry
              key={template.name}
              name={template.name}
              icon={template.icon}
              desc={template.desc}
              theme={theme}
            />
          ))}
        </div>
      </section>

      <section
        className={`relative z-10 border-t px-6 py-16 ${
          isCyber
            ? "border-cyan-400/10 bg-slate-950/45"
            : "border-slate-200 bg-white/70"
        }`}
      >
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className={`rounded-2xl border p-6 ${
                isCyber
                  ? "border-cyan-400/12 bg-slate-950/70 shadow-[0_18px_50px_rgba(2,8,23,0.4)]"
                  : "border-slate-200 bg-white shadow-sm"
              }`}
            >
              <div className={`mb-2 text-lg font-semibold ${isCyber ? "text-white" : "text-slate-900"}`}>
                {feature.title}
              </div>
              <div className={`text-sm leading-6 ${isCyber ? "text-slate-400" : "text-slate-600"}`}>
                {feature.desc}
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
