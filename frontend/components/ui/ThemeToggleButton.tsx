"use client";

import type { HomeTheme } from "@/stores/themeStore";

export default function ThemeToggleButton({
  theme,
  onToggle,
}: {
  theme: HomeTheme;
  onToggle: () => void;
}) {
  const isCyber = theme === "cyber";

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`group inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-medium transition-all ${
        isCyber
          ? "border-cyan-400/30 bg-slate-950/80 text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,0.14)] hover:border-cyan-300/50 hover:text-white"
          : "border-slate-200 bg-white text-slate-600 shadow-sm hover:border-slate-300 hover:text-slate-900"
      }`}
      aria-label={isCyber ? "切换到经典明亮主题" : "切换到深色科幻主题"}
    >
      <span
        className={`h-2.5 w-2.5 rounded-full ${
          isCyber ? "bg-cyan-300 shadow-[0_0_14px_rgba(34,211,238,0.9)]" : "bg-indigo-500"
        }`}
      />
      <span>{isCyber ? "科幻主题" : "经典主题"}</span>
      <span className={isCyber ? "text-cyan-300/80" : "text-slate-400"}>
        {isCyber ? "切回明亮" : "切到深色"}
      </span>
    </button>
  );
}
