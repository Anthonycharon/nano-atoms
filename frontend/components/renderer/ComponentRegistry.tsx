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

function getFeatureItems(value: unknown): Array<{
  title: string;
  description: string;
  badge?: string;
  icon?: string;
}> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (typeof item === "string") {
        return { title: item, description: "" };
      }
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        return {
          title: String(record.title ?? record.label ?? `Feature ${index + 1}`),
          description: String(record.description ?? record.text ?? ""),
          badge: record.badge ? String(record.badge) : undefined,
          icon: record.icon ? String(record.icon) : undefined,
        };
      }
      return null;
    })
    .filter(
      (
        item
      ): item is { title: string; description: string; badge?: string; icon?: string } =>
        item !== null
    );
}

function getStatItems(value: unknown): Array<{ label: string; value: string; caption: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      return {
        label: String(record.label ?? `Metric ${index + 1}`),
        value: String(record.value ?? record.number ?? "--"),
        caption: record.caption ? String(record.caption) : record.change ? String(record.change) : "",
      };
    })
    .filter((item): item is { label: string; value: string; caption: string } => item !== null);
}

function getImageSource(value: unknown, label: string): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  return buildImagePlaceholderSrc(label);
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

    case "hero": {
      const heroImage = getImageSource(
        node.props.image_src,
        String(node.props.image_alt ?? node.props.title ?? "Hero image")
      );
      const stats = getStatItems(node.props.stats);
      return (
        <section
          key={node.id}
          className={`overflow-hidden px-4 pt-6 md:px-6 md:pt-8 ${extraClass}`}
        >
          <div className="mx-auto grid max-w-6xl gap-8 rounded-[28px] border border-white/60 bg-white/85 p-6 shadow-[0_28px_80px_rgba(15,23,42,0.12)] backdrop-blur md:grid-cols-[1.05fr_0.95fr] md:p-8">
            <div className="flex flex-col justify-center">
              {!!node.props.eyebrow && (
                <div className="mb-4 inline-flex w-fit rounded-full bg-orange-100 px-4 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-orange-700">
                  {String(node.props.eyebrow)}
                </div>
              )}
              <h1 className="max-w-2xl text-4xl font-black leading-tight text-slate-950 md:text-6xl">
                {String(node.props.title ?? "Built for better first impressions")}
              </h1>
              {!!node.props.description && (
                <p className="mt-5 max-w-xl text-base leading-8 text-slate-600 md:text-lg">
                  {String(node.props.description)}
                </p>
              )}
              <div className="mt-8 flex flex-wrap gap-3">
                {!!node.props.primary_cta_label && (
                  <button
                    type="button"
                    onClick={() => {
                      if (node.props.primary_cta_route) {
                        ctx.navigate(String(node.props.primary_cta_route));
                      }
                    }}
                    className="rounded-full px-6 py-3 text-sm font-semibold text-white shadow-lg"
                    style={{ backgroundColor: "var(--color-primary)" }}
                  >
                    {String(node.props.primary_cta_label)}
                  </button>
                )}
                {!!node.props.secondary_cta_label && (
                  <button
                    type="button"
                    onClick={() => {
                      if (node.props.secondary_cta_route) {
                        ctx.navigate(String(node.props.secondary_cta_route));
                      }
                    }}
                    className="rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-400"
                  >
                    {String(node.props.secondary_cta_label)}
                  </button>
                )}
              </div>
              {stats.length > 0 && (
                <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">
                  {stats.map((item) => (
                    <div
                      key={`${node.id}-${item.label}`}
                      className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                    >
                      <div className="text-2xl font-black text-slate-900">{item.value}</div>
                      <div className="mt-1 text-sm font-medium text-slate-700">{item.label}</div>
                      {!!item.caption && (
                        <div className="mt-1 text-xs leading-5 text-slate-500">{item.caption}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="overflow-hidden rounded-[24px] bg-slate-100 shadow-[0_24px_64px_rgba(15,23,42,0.14)]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={heroImage}
                alt={String(node.props.image_alt ?? "")}
                className="h-full min-h-[280px] w-full object-cover"
                onError={(event) => {
                  const fallback = buildImagePlaceholderSrc(
                    String(node.props.image_alt ?? node.props.title ?? "Hero image")
                  );
                  if (event.currentTarget.src !== fallback) {
                    event.currentTarget.src = fallback;
                  }
                }}
              />
            </div>
          </div>
        </section>
      );
    }

    case "feature-grid": {
      const items = getFeatureItems(node.props.items);
      const columns = Math.max(1, Math.min(Number(node.props.columns ?? 3), 4));
      const columnClass =
        columns >= 4
          ? "md:grid-cols-4"
          : columns === 2
            ? "md:grid-cols-2"
            : "md:grid-cols-3";
      return (
        <section key={node.id} className={`px-4 md:px-6 ${extraClass}`}>
          <div className="mx-auto max-w-6xl rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-[0_24px_60px_rgba(15,23,42,0.08)]">
            {!!node.props.title && (
              <h2 className="text-2xl font-black text-slate-950 md:text-3xl">
                {String(node.props.title)}
              </h2>
            )}
            {!!node.props.description && (
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 md:text-base">
                {String(node.props.description)}
              </p>
            )}
            <div className={`mt-6 grid grid-cols-1 gap-4 ${columnClass}`}>
              {items.map((item) => (
                <article
                  key={`${node.id}-${item.title}`}
                  className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5"
                >
                  {(item.badge || item.icon) && (
                    <div className="mb-3 flex items-center gap-2">
                      {!!item.icon && (
                        <span className="text-lg text-[color:var(--color-primary)]">{item.icon}</span>
                      )}
                      {!!item.badge && (
                        <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-indigo-600">
                          {item.badge}
                        </span>
                      )}
                    </div>
                  )}
                  <h3 className="text-lg font-bold text-slate-900">{item.title}</h3>
                  {!!item.description && (
                    <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
                  )}
                </article>
              ))}
            </div>
          </div>
        </section>
      );
    }

    case "stats-band": {
      const items = getStatItems(node.props.items);
      return (
        <section key={node.id} className={`px-4 md:px-6 ${extraClass}`}>
          <div className="mx-auto grid max-w-6xl grid-cols-2 gap-4 rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-[0_24px_60px_rgba(15,23,42,0.08)] md:grid-cols-4">
            {items.map((item) => (
              <div key={`${node.id}-${item.label}`} className="rounded-2xl bg-slate-50/80 p-4 text-center">
                <div className="text-3xl font-black text-slate-900">{item.value}</div>
                <div className="mt-2 text-sm font-semibold text-slate-700">{item.label}</div>
                {!!item.caption && (
                  <div className="mt-1 text-xs leading-5 text-slate-500">{item.caption}</div>
                )}
              </div>
            ))}
          </div>
        </section>
      );
    }

    case "split-section": {
      const bullets = getStringArray(node.props.bullets);
      const splitImage = getImageSource(
        node.props.image_src,
        String(node.props.image_alt ?? node.props.title ?? "Section image")
      );
      const reverse = Boolean(node.props.reverse);
      return (
        <section key={node.id} className={`px-4 md:px-6 ${extraClass}`}>
          <div className="mx-auto max-w-6xl rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-[0_24px_60px_rgba(15,23,42,0.08)] md:p-8">
            <div className="grid items-center gap-8 md:grid-cols-2">
              <div className={reverse ? "md:order-2" : ""}>
                {!!node.props.eyebrow && (
                  <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--color-primary)]">
                    {String(node.props.eyebrow)}
                  </div>
                )}
                <h2 className="text-3xl font-black leading-tight text-slate-950 md:text-4xl">
                  {String(node.props.title ?? "Section title")}
                </h2>
                {!!node.props.description && (
                  <p className="mt-4 text-sm leading-7 text-slate-600 md:text-base">
                    {String(node.props.description)}
                  </p>
                )}
                {bullets.length > 0 && (
                  <ul className="mt-5 space-y-3">
                    {bullets.map((bullet) => (
                      <li key={bullet} className="flex items-start gap-3 text-sm text-slate-700">
                        <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[color:var(--color-primary)]" />
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="mt-6 flex flex-wrap gap-3">
                  {!!node.props.primary_cta_label && (
                    <button
                      type="button"
                      onClick={() => {
                        if (node.props.primary_cta_route) {
                          ctx.navigate(String(node.props.primary_cta_route));
                        }
                      }}
                      className="rounded-full px-5 py-3 text-sm font-semibold text-white"
                      style={{ backgroundColor: "var(--color-primary)" }}
                    >
                      {String(node.props.primary_cta_label)}
                    </button>
                  )}
                  {!!node.props.secondary_cta_label && (
                    <button
                      type="button"
                      onClick={() => {
                        if (node.props.secondary_cta_route) {
                          ctx.navigate(String(node.props.secondary_cta_route));
                        }
                      }}
                      className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700"
                    >
                      {String(node.props.secondary_cta_label)}
                    </button>
                  )}
                </div>
              </div>
              <div
                className={`overflow-hidden rounded-[24px] bg-slate-100 shadow-[0_24px_64px_rgba(15,23,42,0.14)] ${
                  reverse ? "md:order-1" : ""
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={splitImage}
                  alt={String(node.props.image_alt ?? "")}
                  className="h-full min-h-[260px] w-full object-cover"
                  onError={(event) => {
                    const fallback = buildImagePlaceholderSrc(
                      String(node.props.image_alt ?? node.props.title ?? "Section image")
                    );
                    if (event.currentTarget.src !== fallback) {
                      event.currentTarget.src = fallback;
                    }
                  }}
                />
              </div>
            </div>
          </div>
        </section>
      );
    }

    case "cta-band":
      return (
        <section key={node.id} className={`px-4 pb-4 md:px-6 ${extraClass}`}>
          <div className="mx-auto max-w-6xl rounded-[30px] bg-slate-950 px-6 py-8 text-white shadow-[0_32px_80px_rgba(15,23,42,0.24)] md:px-8 md:py-10">
            <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
              <div>
                <h2 className="text-3xl font-black leading-tight md:text-4xl">
                  {String(node.props.title ?? "Move from idea to launch faster")}
                </h2>
                {!!node.props.description && (
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                    {String(node.props.description)}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-3">
                {!!node.props.primary_cta_label && (
                  <button
                    type="button"
                    onClick={() => {
                      if (node.props.primary_cta_route) {
                        ctx.navigate(String(node.props.primary_cta_route));
                      }
                    }}
                    className="rounded-full px-5 py-3 text-sm font-semibold text-white"
                    style={{ background: "linear-gradient(135deg, var(--color-primary), #fb7185)" }}
                  >
                    {String(node.props.primary_cta_label)}
                  </button>
                )}
                {!!node.props.secondary_cta_label && (
                  <button
                    type="button"
                    onClick={() => {
                      if (node.props.secondary_cta_route) {
                        ctx.navigate(String(node.props.secondary_cta_route));
                      }
                    }}
                    className="rounded-full border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white"
                  >
                    {String(node.props.secondary_cta_label)}
                  </button>
                )}
              </div>
            </div>
          </div>
        </section>
      );

    case "auth-card": {
      const authImage = getImageSource(
        node.props.image_src,
        String(node.props.image_alt ?? node.props.title ?? "Authentication visual")
      );
      return (
        <section key={node.id} className={`px-4 py-8 md:px-6 md:py-10 ${extraClass}`}>
          <div className="mx-auto grid max-w-5xl overflow-hidden rounded-[32px] border border-white/60 bg-white/90 shadow-[0_30px_90px_rgba(15,23,42,0.14)] md:grid-cols-[0.92fr_1.08fr]">
            <div className="relative min-h-[280px] overflow-hidden bg-slate-950">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={authImage}
                alt={String(node.props.image_alt ?? "")}
                className="absolute inset-0 h-full w-full object-cover opacity-80"
                onError={(event) => {
                  const fallback = buildImagePlaceholderSrc(
                    String(node.props.image_alt ?? node.props.title ?? "Authentication visual")
                  );
                  if (event.currentTarget.src !== fallback) {
                    event.currentTarget.src = fallback;
                  }
                }}
              />
              <div className="relative flex h-full flex-col justify-end bg-gradient-to-t from-slate-950 via-slate-900/55 to-transparent p-8 text-white">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">
                  {String(node.props.aside_title ?? "Nano Atoms")}
                </div>
                <div className="mt-3 text-3xl font-black leading-tight">
                  {String(node.props.title ?? "Welcome back")}
                </div>
                {!!node.props.aside_text && (
                  <p className="mt-3 max-w-md text-sm leading-7 text-white/80">
                    {String(node.props.aside_text)}
                  </p>
                )}
              </div>
            </div>
            <div className="p-6 md:p-10">
              <h2 className="text-3xl font-black text-slate-950">
                {String(node.props.title ?? "Welcome back")}
              </h2>
              {!!node.props.description && (
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  {String(node.props.description)}
                </p>
              )}
              <div className="mt-6 space-y-4">
                {children.map((child) => renderComponent(child, ctx, bundle, theme))}
              </div>
              {!!node.props.footer_text && (
                <div className="mt-5 text-sm text-slate-500">
                  {String(node.props.footer_text)}{" "}
                  {!!node.props.footer_link_label && (
                    <button
                      type="button"
                      className="font-semibold text-[color:var(--color-primary)]"
                      onClick={() => {
                        if (node.props.footer_link_route) {
                          ctx.navigate(String(node.props.footer_link_route));
                        }
                      }}
                    >
                      {String(node.props.footer_link_label)}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      );
    }

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
