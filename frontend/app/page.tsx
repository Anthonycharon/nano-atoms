"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useAuthStore } from "@/stores/authStore";
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
    desc: "需求理解、结构设计、视觉生成、交互配置按流水线协同完成。",
  },
  {
    title: "实时预览",
    desc: "生成完成后直接在工作区体验页面和交互，不必手动拼接。",
  },
  {
    title: "持续迭代",
    desc: "每次修改都会形成新版本，方便对比、回退和继续优化。",
  },
];

function LandingActions() {
  const { isAuthenticated, user, hasHydrated } = useAuthStore();
  const { logout } = useAuth();

  if (!hasHydrated) {
    return (
      <div className="flex gap-3">
        <div className="h-10 w-24 animate-pulse rounded-lg bg-slate-200/80" />
        <div className="h-10 w-28 animate-pulse rounded-lg bg-slate-200/80" />
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <div className="text-sm font-medium text-slate-800">已登录</div>
          <div className="max-w-48 truncate text-xs text-slate-500">{user?.email}</div>
        </div>
        <Link
          href="/dashboard"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
        >
          进入工作台
        </Link>
        <button
          onClick={logout}
          className="px-4 py-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
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
        className="px-4 py-2 text-sm text-slate-600 transition-colors hover:text-slate-900"
      >
        登录
      </Link>
      <Link
        href="/register"
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
      >
        免费开始
      </Link>
    </div>
  );
}

function ExampleEntry({ example }: { example: string }) {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const starter = buildExampleStarter(example);

  if (hasHydrated && isAuthenticated) {
    return (
      <button
        type="button"
        onClick={() => {
          persistStarterIntent(starter);
          router.push("/dashboard");
        }}
        className="group flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 text-left text-sm text-slate-700 shadow-sm transition-colors hover:border-indigo-300"
      >
        <span>{example}</span>
        <span className="text-xs text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
          一键开始
        </span>
      </button>
    );
  }

  return (
    <Link
      href={appendStarterParams("/register", starter)}
      className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-700 shadow-sm transition-colors hover:border-indigo-300"
    >
      <span>{example}</span>
      <span className="text-xs text-indigo-600 opacity-0 transition-opacity group-hover:opacity-100">
        用这个开始
      </span>
    </Link>
  );
}

function TemplateEntry({
  name,
  icon,
  desc,
}: {
  name: string;
  icon: string;
  desc: string;
}) {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const starter = buildTemplateStarter(name, desc);

  if (hasHydrated && isAuthenticated) {
    return (
      <button
        type="button"
        onClick={() => {
          persistStarterIntent(starter);
          router.push("/dashboard");
        }}
        className="rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm transition-all hover:-translate-y-0.5 hover:border-indigo-300"
      >
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-semibold text-indigo-700">
          {icon}
        </div>
        <div className="mb-1 text-sm font-medium">{name}</div>
        <div className="text-xs leading-5 text-slate-500">{desc}</div>
      </button>
    );
  }

  return (
    <Link
      href={appendStarterParams("/register", starter)}
      className="rounded-2xl border border-slate-200 bg-white p-5 text-center shadow-sm transition-all hover:-translate-y-0.5 hover:border-indigo-300"
    >
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 font-semibold text-indigo-700">
        {icon}
      </div>
      <div className="mb-1 text-sm font-medium">{name}</div>
      <div className="text-xs leading-5 text-slate-500">{desc}</div>
    </Link>
  );
}

export default function LandingPage() {
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const primaryHref = hasHydrated && isAuthenticated ? "/dashboard" : "/register";
  const secondaryHref = hasHydrated && isAuthenticated ? "/dashboard" : "/login";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_38%,#f8fafc_100%)] text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200/80 bg-white/80 px-6 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-sm">
            N
          </div>
          <span className="text-lg font-semibold">Nano Atoms</span>
        </div>
        <LandingActions />
      </header>

      <section className="mx-auto max-w-5xl px-6 pb-16 pt-24 text-center">
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white px-4 py-1.5 text-sm text-indigo-600 shadow-sm">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
          多智能体生成平台
        </div>

        <h1 className="mb-6 text-5xl font-bold leading-tight tracking-tight md:text-6xl">
          用一句话描述需求，
          <br />
          生成可交互的应用原型与代码
        </h1>

        <p className="mx-auto mb-10 max-w-3xl text-xl leading-8 text-slate-600">
          从需求拆解、页面结构、视觉风格到交互逻辑，平台会自动生成完整结果，并支持继续迭代与发布。
        </p>

        <div className="flex justify-center gap-4">
          <Link
            href={primaryHref}
            className="rounded-xl bg-indigo-600 px-8 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            {hasHydrated && isAuthenticated ? "进入工作台" : "立即开始"}
          </Link>
          <Link
            href={secondaryHref}
            className="rounded-xl border border-slate-300 bg-white px-8 py-3 text-base text-slate-700 transition-colors hover:border-slate-400"
          >
            {hasHydrated && isAuthenticated ? "查看项目" : "已有账号登录"}
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 pb-16">
        <p className="mb-4 text-center text-sm text-slate-500">示例需求，一键开始</p>
        <div className="flex flex-col gap-3">
          {examples.map((example) => (
            <ExampleEntry key={example} example={example} />
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <h2 className="mb-8 text-center text-2xl font-semibold">常见起步模板</h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {templates.map((template) => (
            <TemplateEntry
              key={template.name}
              name={template.name}
              icon={template.icon}
              desc={template.desc}
            />
          ))}
        </div>
      </section>

      <section className="border-t border-slate-200 bg-white/70 px-6 py-16">
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="mb-2 text-lg font-semibold">{feature.title}</div>
              <div className="text-sm leading-6 text-slate-600">{feature.desc}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
