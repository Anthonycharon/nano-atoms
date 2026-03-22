"use client";

import { useEffect, useState } from "react";
import { parseCodeArtifact } from "@/lib/codeArtifacts";
import type { GeneratedFile } from "@/types/schema";

interface Props {
  schemaJson: string | null;
  codeJson: string | null;
  status: string;
}

interface TreeNode {
  name: string;
  path: string;
  kind: "file" | "dir";
  children: TreeNode[];
}

function buildTree(files: GeneratedFile[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const file of files) {
    const parts = file.path.split("/");
    let currentLevel = root;
    let currentPath = "";

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const existing = currentLevel.find((node) => node.name === part);
      const isFile = index === parts.length - 1;

      if (existing) {
        currentLevel = existing.children;
        return;
      }

      const nextNode: TreeNode = {
        name: part,
        path: currentPath,
        kind: isFile ? "file" : "dir",
        children: [],
      };

      currentLevel.push(nextNode);
      currentLevel = nextNode.children;
    });
  }

  return root.sort((a, b) => {
    if (a.kind !== b.kind) {
      return a.kind === "dir" ? -1 : 1;
    }
    return a.name.localeCompare(b.name);
  });
}

function TreeView({
  nodes,
  selectedPath,
  onSelect,
  depth = 0,
}: {
  nodes: TreeNode[];
  selectedPath: string;
  onSelect: (path: string) => void;
  depth?: number;
}) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <div key={node.path}>
          {node.kind === "dir" ? (
            <div
              className="py-1 text-xs font-medium uppercase tracking-[0.12em] text-slate-500"
              style={{ paddingLeft: `${depth * 12}px` }}
            >
              {node.name}
            </div>
          ) : (
            <button
              onClick={() => onSelect(node.path)}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                selectedPath === node.path
                  ? "border border-indigo-100 bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
              style={{ marginLeft: `${depth * 12}px`, width: `calc(100% - ${depth * 12}px)` }}
            >
              {node.name}
            </button>
          )}

          {node.children.length > 0 && (
            <TreeView
              nodes={node.children.sort((a, b) => {
                if (a.kind !== b.kind) {
                  return a.kind === "dir" ? -1 : 1;
                }
                return a.name.localeCompare(b.name);
              })}
              selectedPath={selectedPath}
              onSelect={onSelect}
              depth={depth + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export default function CodePanel({ schemaJson, codeJson, status }: Props) {
  const artifact = parseCodeArtifact(codeJson, schemaJson);
  const files = artifact?.files ?? [];
  const [selectedPath, setSelectedPath] = useState<string>(files[0]?.path ?? "");

  useEffect(() => {
    if (!files.length) {
      setSelectedPath("");
      return;
    }
    if (!files.some((file) => file.path === selectedPath)) {
      setSelectedPath(files[0].path);
    }
  }, [files, selectedPath]);

  const selectedFile = files.find((file) => file.path === selectedPath) ?? files[0];
  const tree = buildTree(files);

  if ((status === "queued" || status === "running") && files.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center bg-slate-50 text-slate-500">
        <div className="mb-4 h-12 w-12 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin" />
        <p className="text-sm">代码文件整理中，请稍候...</p>
      </div>
    );
  }

  if (!files.length) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center bg-slate-50 text-slate-500">
        <div className="mb-3 text-4xl">{"</>"}</div>
        <p className="text-sm">生成完成后，这里会展示项目文件树</p>
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 bg-slate-50 p-5">
      <div className="grid h-full grid-cols-[280px_minmax(0,1fr)] gap-4">
        <aside className="overflow-auto rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-3">
            <div className="text-sm font-semibold text-slate-800">项目文件</div>
            <div className="mt-1 text-xs text-slate-500">
              {files.length} 个文件{artifact?.entry ? ` · 入口 ${artifact.entry}` : ""}
            </div>
          </div>
          <div className="p-3">
            <TreeView nodes={tree} selectedPath={selectedPath} onSelect={setSelectedPath} />
          </div>
        </aside>

        <section className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-slate-800">
                {selectedFile?.path ?? "未选择文件"}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {selectedFile?.language ?? "text"}
              </div>
            </div>
            {artifact?.title && (
              <div className="text-xs text-slate-500">导出项目：{artifact.title}</div>
            )}
          </div>

          <div className="h-[calc(100%-65px)] overflow-auto bg-slate-950">
            <pre className="min-w-max whitespace-pre p-4 text-[13px] leading-6 text-slate-100">
              {selectedFile?.content ?? ""}
            </pre>
          </div>
        </section>
      </div>
    </div>
  );
}
