import { notFound } from "next/navigation";
import AppRenderer from "@/components/renderer/AppRenderer";
import { extractCodeBundle } from "@/lib/codeArtifacts";
import type { AppSchema } from "@/types/schema";

interface Props {
  params: Promise<{ slug: string }>;
}

async function getPublishedData(slug: string) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${baseUrl}/api/published/${slug}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function PublicAppPage({ params }: Props) {
  const { slug } = await params;
  const data = await getPublishedData(slug);

  if (!data || !data.schema_json) {
    notFound();
  }

  const schema: AppSchema = JSON.parse(data.schema_json);
  const codeBundle = extractCodeBundle(data.code_json);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 简单顶栏 */}
      <div className="bg-white border-b border-gray-200 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <div className="w-5 h-5 rounded bg-indigo-500 flex items-center justify-center text-white text-xs font-bold">N</div>
          <span>由 Nano Atoms 生成</span>
        </div>
        <a href="/" className="text-xs text-indigo-500 hover:underline">创建你的应用 →</a>
      </div>

      {/* 应用内容 */}
      <AppRenderer schema={schema} codeBundle={codeBundle} />
    </div>
  );
}
