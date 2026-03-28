"use client";

import { notFound } from "next/navigation";
import { useEffect, useState } from "react";
import AtomBrandMark from "@/components/ui/AtomBrandMark";
import ThemeToggleButton from "@/components/ui/ThemeToggleButton";
import { parseCodeArtifact } from "@/lib/codeArtifacts";
import { useThemeStore } from "@/stores/themeStore";

interface Props {
  params: Promise<{ slug: string }>;
}

async function getPublishedData(slug: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const response = await fetch(`${baseUrl}/api/published/${slug}`, { cache: "no-store" });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export default function PublicAppPageClient({ params }: Props) {
  const [data, setData] = useState<{
    schema_json: string | null;
    code_json: string | null;
  } | null>(null);
  const [loaded, setLoaded] = useState(false);
  const theme = useThemeStore((state) => state.theme);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const isCyber = theme === "cyber";

  useEffect(() => {
    let active = true;

    void (async () => {
      const { slug } = await params;
      const result = await getPublishedData(slug);
      if (!active) return;

      if (!result || !result.code_json) {
        setLoaded(true);
        setData(null);
        return;
      }

      setData(result);
      setLoaded(true);
    })();

    return () => {
      active = false;
    };
  }, [params]);

  if (loaded && !data?.code_json) {
    notFound();
  }

  if (!loaded || !data?.code_json) {
    return (
      <div
        className={`flex min-h-screen items-center justify-center ${
          isCyber
            ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)] text-slate-300"
            : "bg-slate-50 text-slate-500"
        }`}
      >
        加载中...
      </div>
    );
  }

  const artifact = parseCodeArtifact(data.code_json, data.schema_json);
  const previewHtml = artifact?.preview_html ?? null;

  return (
    <div
      className={`min-h-screen ${
        isCyber
          ? "bg-[radial-gradient(circle_at_top,#12304f_0%,#07111f_34%,#040814_74%,#02040a_100%)]"
          : "bg-gray-50"
      }`}
    >
      {isCyber && (
        <>
          <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] bg-[size:88px_88px] opacity-25" />
          <div className="pointer-events-none fixed left-[12%] top-[10%] h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl" />
          <div className="pointer-events-none fixed right-[8%] top-[18%] h-80 w-80 rounded-full bg-sky-500/8 blur-3xl" />
        </>
      )}

      <div
        className={`sticky top-0 z-20 flex items-center justify-between border-b px-4 py-2.5 backdrop-blur ${
          isCyber
            ? "border-cyan-400/12 bg-slate-950/70"
            : "border-gray-200 bg-white"
        }`}
      >
        <div className={`flex items-center gap-2 text-sm ${isCyber ? "text-slate-300" : "text-gray-500"}`}>
          <div
            className={`flex h-6 w-6 items-center justify-center rounded border ${
              isCyber
                ? "border-cyan-400/18 bg-slate-950/72 shadow-[0_0_16px_rgba(34,211,238,0.14)]"
                : "border-slate-200 bg-white"
            }`}
          >
            <AtomBrandMark className="h-4 w-4" />
          </div>
          <span>由 Nano Atoms 生成</span>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggleButton theme={theme} onToggle={toggleTheme} />
          <a
            href="/"
            className={`text-xs hover:underline ${
              isCyber ? "text-cyan-300" : "text-indigo-500"
            }`}
          >
            创建你的应用 →
          </a>
        </div>
      </div>

      <div className="relative z-10">
        {previewHtml ? (
          <iframe
            title="published-app-preview"
            srcDoc={previewHtml}
            sandbox="allow-scripts allow-forms"
            className="min-h-[calc(100vh-56px)] w-full border-0 bg-white"
          />
        ) : (
          <div
            className={`flex min-h-[calc(100vh-56px)] items-center justify-center px-6 text-center ${
              isCyber ? "text-slate-300" : "text-slate-500"
            }`}
          >
            当前发布版本没有生成可用的页面预览。
          </div>
        )}
      </div>
    </div>
  );
}
