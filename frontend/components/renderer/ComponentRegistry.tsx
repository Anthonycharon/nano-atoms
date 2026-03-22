"use client";

import type { ReactNode } from "react";
import type { ActionDef, CodeBundle, ComponentNode } from "@/types/schema";

interface RendererContext {
  state: Record<string, unknown>;
  setState: (key: string, val: unknown) => void;
  currentPage: string;
  navigate: (route: string) => void;
  formData: Record<string, Record<string, string>>;
  setFormField: (formId: string, field: string, value: string) => void;
  submitForm: (formId: string, bundle: CodeBundle | null) => void;
}

function getChildren(node: ComponentNode): ComponentNode[] {
  return Array.isArray(node.children) ? node.children : [];
}

function getStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value === "string" && value.trim()) return [value];
  return [];
}

function getOptions(value: unknown, label?: string): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value === "string" && value.trim()) {
    const text = value.trim();
    if (/^\{\{.+\}\}$/.test(text)) {
      const base = label || "选项";
      return [`${base} 1`, `${base} 2`, `${base} 3`];
    }
    return text
      .split(/[,\n，、|/]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (value && typeof value === "object") return Object.keys(value as Record<string, unknown>);
  return [];
}

function getRows(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) {
    return value.filter((item): item is Record<string, unknown> => !!item && typeof item === "object");
  }
  if (value && typeof value === "object") return [value as Record<string, unknown>];
  return [];
}

function getLinks(value: unknown): Array<{ label: string; route: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (typeof item === "string") {
        return { label: item, route: "/" };
      }
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        return {
          label: String(
            record.label ?? record.text ?? record.title ?? record.route ?? `Link ${index + 1}`
          ),
          route: String(record.route ?? record.target ?? "/"),
        };
      }
      return null;
    })
    .filter((item): item is { label: string; route: string } => item !== null);
}

function buildImagePlaceholderSrc(label: string): string {
  const safeLabel = (label || "Preview Image").trim() || "Preview Image";
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="720" gradientUnits="userSpaceOnUse">
      <stop stop-color="#E0EAFF"/>
      <stop offset="1" stop-color="#F8FBFF"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="720" rx="40" fill="url(#bg)"/>
  <rect x="120" y="120" width="960" height="480" rx="28" fill="#FFFFFF" stroke="#C7D8F7" stroke-width="4"/>
  <circle cx="330" cy="300" r="72" fill="#CFE0FF"/>
  <path d="M210 520L410 360L560 470L710 320L990 520H210Z" fill="#DCE8FF"/>
  <text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">${safeLabel}</text>
</svg>`.trim();
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function renderComponent(
  node: ComponentNode,
  ctx: RendererContext,
  bundle: CodeBundle | null,
  theme?: Record<string, { className?: string }>
): ReactNode {
  const extraClass = theme?.[node.id]?.className ?? "";
  const children = getChildren(node);

  const handleAction = (action: ActionDef) => {
    if (action.type === "navigate" && action.payload?.route) {
      ctx.navigate(String(action.payload.route));
    } else if (action.type === "submit_form" && action.payload?.form_id) {
      ctx.submitForm(String(action.payload.form_id), bundle);
    } else if (action.type === "set_value" && action.payload?.key) {
      ctx.setState(String(action.payload.key), action.payload.value);
    }
  };

  switch (node.type) {
    case "heading":
      return (
        <h2 key={node.id} className={`mb-4 text-2xl font-bold text-gray-900 ${extraClass}`}>
          {String(node.props.text ?? node.props.children ?? "标题")}
        </h2>
      );

    case "text":
      return (
        <p key={node.id} className={`mb-3 leading-relaxed text-gray-600 ${extraClass}`}>
          {String(node.props.text ?? node.props.children ?? "")}
        </p>
      );

    case "button":
      return (
        <button
          key={node.id}
          className={`rounded-lg bg-indigo-500 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-600 ${extraClass}`}
          onClick={() => (node.actions ?? []).forEach(handleAction)}
        >
          {String(node.props.label ?? node.props.text ?? "按钮")}
        </button>
      );

    case "input": {
      const formId = typeof node.props.form_id === "string" ? node.props.form_id : undefined;
      const fieldName = String(node.props.name ?? node.id);
      return (
        <div key={node.id} className="mb-4">
          {!!node.props.label && (
            <label className="mb-1 block text-sm font-medium text-gray-700">
              {String(node.props.label)}
            </label>
          )}
          <input
            type={String(node.props.type ?? "text")}
            placeholder={String(node.props.placeholder ?? "")}
            value={formId ? (ctx.formData[formId]?.[fieldName] ?? "") : ""}
            onChange={(e) => {
              if (formId) ctx.setFormField(formId, fieldName, e.target.value);
            }}
            className={`w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none transition-colors focus:border-indigo-500 ${extraClass}`}
          />
        </div>
      );
    }

    case "select": {
      const formId = typeof node.props.form_id === "string" ? node.props.form_id : undefined;
      const fieldName = String(node.props.name ?? node.id);
      const options = getOptions(node.props.options, String(node.props.label ?? node.props.name ?? ""));
      return (
        <div key={node.id} className="mb-4">
          {!!node.props.label && (
            <label className="mb-1 block text-sm font-medium text-gray-700">
              {String(node.props.label)}
            </label>
          )}
          <select
            value={formId ? (ctx.formData[formId]?.[fieldName] ?? "") : ""}
            onChange={(e) => {
              if (formId) ctx.setFormField(formId, fieldName, e.target.value);
            }}
            className={`w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 ${extraClass}`}
          >
            <option value="">{String(node.props.placeholder ?? "请选择...")}</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      );
    }

    case "form":
      return (
        <form
          key={node.id}
          className={`space-y-4 ${extraClass}`}
          onSubmit={(e) => {
            e.preventDefault();
            ctx.submitForm(node.id, bundle);
          }}
        >
          {children.map((child) => renderComponent(child, ctx, bundle, theme))}
        </form>
      );

    case "card":
      return (
        <div
          key={node.id}
          className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm ${extraClass}`}
        >
          {!!node.props.title && (
            <h3 className="mb-3 font-semibold text-gray-900">{String(node.props.title)}</h3>
          )}
          {children.map((child) => renderComponent(child, ctx, bundle, theme))}
          {children.length === 0 && !!node.props.content && (
            <p className="text-sm text-gray-600">{String(node.props.content)}</p>
          )}
        </div>
      );

    case "stat-card":
      return (
        <div
          key={node.id}
          className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm ${extraClass}`}
        >
          <p className="mb-1 text-sm text-gray-500">{String(node.props.label ?? "指标")}</p>
          <p className="text-3xl font-bold text-gray-900">{String(node.props.value ?? "--")}</p>
          {!!node.props.change && (
            <p className="mt-1 text-xs text-green-500">+ {String(node.props.change)}</p>
          )}
        </div>
      );

    case "table": {
      const columns = getStringArray(node.props.columns);
      const rows = getRows(node.props.rows);
      return (
        <div
          key={node.id}
          className={`overflow-x-auto rounded-xl border border-gray-200 ${extraClass}`}
        >
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="px-4 py-3 font-medium text-gray-700">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row, i) => (
                <tr key={i} className="transition-colors hover:bg-gray-50">
                  {columns.map((col) => (
                    <td key={col} className="px-4 py-3 text-gray-600">
                      {String(row[col] ?? "--")}
                    </td>
                  ))}
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={Math.max(columns.length, 1)}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      );
    }

    case "navbar":
      return (
        <nav
          key={node.id}
          className={`flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 ${extraClass}`}
        >
          <span className="font-semibold text-gray-900">
            {String(node.props.title ?? "应用")}
          </span>
          <div className="flex gap-4">
            {getLinks(node.props.links).map((link) => (
              <button
                key={`${node.id}-${link.label}-${link.route}`}
                onClick={() => ctx.navigate(link.route)}
                className="text-sm text-gray-500 transition-colors hover:text-gray-900"
              >
                {link.label}
              </button>
            ))}
          </div>
        </nav>
      );

    case "tag":
      return (
        <span
          key={node.id}
          className={`inline-block rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 ${extraClass}`}
        >
          {String(node.props.text ?? node.props.label ?? "标签")}
        </span>
      );

    case "image":
      const fallbackSrc = buildImagePlaceholderSrc(
        String(node.props.alt ?? node.props.label ?? node.props.title ?? "Preview image")
      );
      const imageSrc =
        typeof node.props.src === "string" && node.props.src.trim()
          ? node.props.src.trim()
          : fallbackSrc;
      return (
        <div
          key={node.id}
          className={`overflow-hidden rounded-xl bg-gray-100 ${extraClass}`}
          style={{ height: node.props.height ? String(node.props.height) : "200px" }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageSrc}
            alt={String(node.props.alt ?? "")}
            className="h-full w-full object-cover"
            onError={(event) => {
              if (event.currentTarget.src !== fallbackSrc) {
                event.currentTarget.src = fallbackSrc;
              }
            }}
          />
        </div>
      );

    case "modal":
      return (
        <div
          key={node.id}
          className={`rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 p-4 ${extraClass}`}
        >
          {children.length > 0 ? (
            children.map((child) => renderComponent(child, ctx, bundle, theme))
          ) : (
            <p className="text-sm text-slate-500">模态内容待补充</p>
          )}
        </div>
      );

    default:
      return (
        <div
          key={node.id}
          className="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-3 text-xs text-gray-400"
        >
          [{node.type}]
        </div>
      );
  }
}
