"use client";

import type { CSSProperties, ReactNode } from "react";
import type { ActionDef, CodeBundle, ComponentNode, UITheme } from "@/types/schema";

interface RendererContext {
  state: Record<string, unknown>;
  setState: (key: string, val: unknown) => void;
  currentPage: string;
  navigate: (route: string) => void;
  formData: Record<string, Record<string, string>>;
  setFormField: (formId: string, field: string, value: string) => void;
  submitForm: (formId: string, bundle: CodeBundle | null) => void;
}

const kids = (node: ComponentNode) => (Array.isArray(node.children) ? node.children : []);
const strings = (value: unknown) =>
  Array.isArray(value)
    ? value.map((item) => String(item))
    : typeof value === "string" && value.trim()
      ? value
          .split(/[,\n，、/|]+/)
          .map((item) => item.trim())
          .filter(Boolean)
      : [];
const rows = (value: unknown) =>
  Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    : value && typeof value === "object"
      ? [value as Record<string, unknown>]
      : [];

function options(value: unknown, label?: string): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item));
  if (typeof value === "string" && value.trim()) {
    if (/^\{\{.+\}\}$/.test(value.trim())) {
      const base = label || "Option";
      return [`${base} 1`, `${base} 2`, `${base} 3`];
    }
    return strings(value);
  }
  return value && typeof value === "object" ? Object.keys(value as Record<string, unknown>) : [];
}

function links(value: unknown): Array<{ label: string; route: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (typeof item === "string") return { label: item, route: "/" };
      if (item && typeof item === "object") {
        const record = item as Record<string, unknown>;
        return {
          label: String(record.label ?? record.text ?? record.title ?? `Link ${index + 1}`),
          route: String(record.route ?? record.target ?? "/"),
        };
      }
      return null;
    })
    .filter((item): item is { label: string; route: string } => item !== null);
}

function featureItems(value: unknown): Array<{ title: string; description: string; badge?: string; icon?: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (typeof item === "string") return { title: item, description: "" };
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      return {
        title: String(record.title ?? record.label ?? `Feature ${index + 1}`),
        description: String(record.description ?? record.text ?? ""),
        badge: record.badge ? String(record.badge) : undefined,
        icon: record.icon ? String(record.icon) : undefined,
      };
    })
    .filter((item): item is { title: string; description: string; badge?: string; icon?: string } => item !== null);
}

function statItems(value: unknown): Array<{ label: string; value: string; caption: string }> {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, index) => {
      if (!item || typeof item !== "object") return null;
      const record = item as Record<string, unknown>;
      return {
        label: String(record.label ?? `Metric ${index + 1}`),
        value: String(record.value ?? record.number ?? "--"),
        caption: String(record.caption ?? record.change ?? ""),
      };
    })
    .filter((item): item is { label: string; value: string; caption: string } => item !== null);
}

function placeholder(label: string): string {
  const safe = (label || "Preview Image").trim() || "Preview Image";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" fill="none"><defs><linearGradient id="bg" x1="0" y1="0" x2="1200" y2="720" gradientUnits="userSpaceOnUse"><stop stop-color="#E0EAFF"/><stop offset="1" stop-color="#F8FBFF"/></linearGradient></defs><rect width="1200" height="720" rx="40" fill="url(#bg)"/><rect x="120" y="120" width="960" height="480" rx="28" fill="#FFFFFF" stroke="#C7D8F7" stroke-width="4"/><circle cx="330" cy="300" r="72" fill="#CFE0FF"/><path d="M210 520L410 360L560 470L710 320L990 520H210Z" fill="#DCE8FF"/><text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">${safe}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

const imageSource = (value: unknown, label: string) =>
  typeof value === "string" && value.trim() ? value.trim() : placeholder(label);

function darkTheme(theme?: UITheme): boolean {
  if (theme?.theme_mode === "dark") return true;
  if (!theme?.background_color?.startsWith("#")) return false;
  let hex = theme.background_color.slice(1);
  if (hex.length === 3) hex = hex.split("").map((char) => char + char).join("");
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return false;
  const r = Number.parseInt(hex.slice(0, 2), 16);
  const g = Number.parseInt(hex.slice(2, 4), 16);
  const b = Number.parseInt(hex.slice(4, 6), 16);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.45;
}

export function renderComponent(node: ComponentNode, ctx: RendererContext, bundle: CodeBundle | null, theme?: UITheme): ReactNode {
  const extra = theme?.component_styles?.[node.id]?.className ?? "";
  const children = kids(node);
  const dark = darkTheme(theme);
  const panel: CSSProperties = { borderColor: "var(--na-border)", backgroundColor: "var(--na-surface)", color: "var(--na-surface-text)", boxShadow: "var(--na-shadow)" };
  const subtle: CSSProperties = { borderColor: "var(--na-border)", backgroundColor: "var(--na-subtle-surface)", color: "var(--na-surface-text)" };
  const primary: CSSProperties = { background: "var(--na-button-bg)", color: "var(--na-button-text)", boxShadow: "var(--na-shadow)" };
  const secondary: CSSProperties = { borderColor: "var(--na-border)", backgroundColor: dark ? "rgba(255,255,255,0.04)" : "var(--na-surface)", color: "var(--na-surface-text)" };
  const input: CSSProperties = { borderColor: "var(--na-border)", backgroundColor: "var(--na-input-bg)", color: "var(--na-surface-text)" };
  const muted: CSSProperties = { color: "var(--na-muted)" };
  const text: CSSProperties = { color: "var(--na-surface-text)" };
  const badge: CSSProperties = { backgroundColor: "var(--na-accent-soft)", color: "var(--na-primary)" };
  const shell: CSSProperties = { maxWidth: "var(--na-shell-width)" };
  const authShell: CSSProperties = { maxWidth: "var(--na-auth-width)" };
  const handle = (action: ActionDef) => {
    if (action.type === "navigate" && action.payload?.route) ctx.navigate(String(action.payload.route));
    else if (action.type === "submit_form" && action.payload?.form_id) ctx.submitForm(String(action.payload.form_id), bundle);
    else if (action.type === "set_value" && action.payload?.key) ctx.setState(String(action.payload.key), action.payload.value);
  };
  const actionBtn = (label: string, route: unknown, variant: "primary" | "secondary") => (
    <button type="button" onClick={() => route && ctx.navigate(String(route))} className={`rounded-full border px-5 py-3 text-sm font-semibold transition-opacity hover:opacity-95 ${variant === "primary" ? "border-transparent" : ""}`} style={variant === "primary" ? primary : secondary}>{label}</button>
  );

  switch (node.type) {
    case "heading": return <h2 key={node.id} className={`mb-4 text-2xl font-bold ${extra}`} style={text}>{String(node.props.text ?? node.props.children ?? "Heading")}</h2>;
    case "text": return <p key={node.id} className={`mb-3 leading-relaxed ${extra}`} style={muted}>{String(node.props.text ?? node.props.children ?? "")}</p>;
    case "button": return <button key={node.id} className={`rounded-lg px-5 py-2.5 text-sm font-medium transition-opacity hover:opacity-95 ${extra}`} style={primary} onClick={() => (node.actions ?? []).forEach(handle)}>{String(node.props.label ?? node.props.text ?? "Button")}</button>;
    case "input": {
      const formId = typeof node.props.form_id === "string" ? node.props.form_id : undefined;
      const name = String(node.props.name ?? node.id);
      return <div key={node.id} className="mb-4">{!!node.props.label && <label className="mb-1 block text-sm font-medium" style={muted}>{String(node.props.label)}</label>}<input type={String(node.props.type ?? "text")} placeholder={String(node.props.placeholder ?? "")} value={formId ? (ctx.formData[formId]?.[name] ?? "") : ""} onChange={(event) => formId && ctx.setFormField(formId, name, event.target.value)} className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none ${extra}`} style={input} /></div>;
    }
    case "select": {
      const formId = typeof node.props.form_id === "string" ? node.props.form_id : undefined;
      const name = String(node.props.name ?? node.id);
      return <div key={node.id} className="mb-4">{!!node.props.label && <label className="mb-1 block text-sm font-medium" style={muted}>{String(node.props.label)}</label>}<select value={formId ? (ctx.formData[formId]?.[name] ?? "") : ""} onChange={(event) => formId && ctx.setFormField(formId, name, event.target.value)} className={`w-full rounded-lg border px-4 py-2.5 text-sm outline-none ${extra}`} style={input}><option value="">{String(node.props.placeholder ?? "Please select")}</option>{options(node.props.options, String(node.props.label ?? node.props.name ?? "")).map((item) => <option key={item} value={item}>{item}</option>)}</select></div>;
    }
    case "form": return <form key={node.id} className={`space-y-4 ${extra}`} onSubmit={(event) => { event.preventDefault(); ctx.submitForm(node.id, bundle); }}>{children.map((child) => renderComponent(child, ctx, bundle, theme))}</form>;
    case "card": return <div key={node.id} className={`rounded-xl border p-5 ${extra}`} style={panel}>{!!node.props.title && <h3 className="mb-3 font-semibold" style={text}>{String(node.props.title)}</h3>}{children.map((child) => renderComponent(child, ctx, bundle, theme))}{children.length === 0 && !!node.props.content && <p className="text-sm" style={muted}>{String(node.props.content)}</p>}</div>;
    case "stat-card": return <div key={node.id} className={`rounded-xl border p-5 ${extra}`} style={panel}><p className="mb-1 text-sm" style={muted}>{String(node.props.label ?? "Metric")}</p><p className="text-3xl font-bold" style={text}>{String(node.props.value ?? "--")}</p>{!!node.props.change && <p className="mt-1 text-xs" style={{ color: dark ? "#4ade80" : "#16a34a" }}>+ {String(node.props.change)}</p>}</div>;
    case "table": {
      const cols = strings(node.props.columns);
      const data = rows(node.props.rows);
      return <div key={node.id} className={`overflow-x-auto rounded-xl border ${extra}`} style={panel}><table className="w-full text-left text-sm"><thead className="border-b" style={{ borderColor: "var(--na-border)", backgroundColor: "var(--na-subtle-surface)" }}><tr>{cols.map((col) => <th key={col} className="px-4 py-3 font-medium" style={text}>{col}</th>)}</tr></thead><tbody className="divide-y" style={{ borderColor: "var(--na-border)" }}>{data.map((row, index) => <tr key={index}>{cols.map((col) => <td key={col} className="px-4 py-3" style={muted}>{String(row[col] ?? "--")}</td>)}</tr>)}{data.length === 0 && <tr><td colSpan={Math.max(cols.length, 1)} className="px-4 py-8 text-center" style={muted}>No data</td></tr>}</tbody></table></div>;
    }
    case "navbar": return <nav key={node.id} className={`mx-auto flex w-full items-center justify-between border-b px-6 py-4 ${extra}`} style={{ ...panel, ...shell }}><span className="font-semibold" style={text}>{String(node.props.title ?? "Application")}</span><div className="flex gap-4">{links(node.props.links).map((link) => <button key={`${node.id}-${link.label}-${link.route}`} onClick={() => ctx.navigate(link.route)} className="text-sm transition-opacity hover:opacity-90" style={muted}>{link.label}</button>)}</div></nav>;
    case "tag": return <span key={node.id} className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${extra}`} style={badge}>{String(node.props.text ?? node.props.label ?? "Tag")}</span>;
    case "image": {
      const fallback = placeholder(String(node.props.alt ?? node.props.label ?? node.props.title ?? "Preview image"));
      const src = typeof node.props.src === "string" && node.props.src.trim() ? node.props.src.trim() : fallback;
      return <div key={node.id} className={`overflow-hidden rounded-xl ${extra}`} style={{ ...subtle, height: node.props.height ? String(node.props.height) : "200px" }}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={src} alt={String(node.props.alt ?? "")} className="h-full w-full object-cover" onError={(event) => { if (event.currentTarget.src !== fallback) event.currentTarget.src = fallback; }} /></div>;
    }
    case "hero": {
      const src = imageSource(node.props.image_src, String(node.props.image_alt ?? node.props.title ?? "Hero image"));
      const stats = statItems(node.props.stats);
      return <section key={node.id} className={`overflow-hidden px-4 pt-6 md:px-6 md:pt-8 ${extra}`}><div className="mx-auto grid w-full gap-8 rounded-[28px] border p-6 backdrop-blur md:grid-cols-[1.05fr_0.95fr] md:p-8" style={{ ...panel, ...shell }}><div className="flex flex-col justify-center">{!!node.props.eyebrow && <div className="mb-4 inline-flex w-fit rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-[0.18em]" style={badge}>{String(node.props.eyebrow)}</div>}<h1 className="max-w-2xl text-4xl font-black leading-tight md:text-6xl" style={text}>{String(node.props.title ?? "Built for better first impressions")}</h1>{!!node.props.description && <p className="mt-5 max-w-xl text-base leading-8 md:text-lg" style={muted}>{String(node.props.description)}</p>}<div className="mt-8 flex flex-wrap gap-3">{!!node.props.primary_cta_label && actionBtn(String(node.props.primary_cta_label), node.props.primary_cta_route, "primary")}{!!node.props.secondary_cta_label && actionBtn(String(node.props.secondary_cta_label), node.props.secondary_cta_route, "secondary")}</div>{stats.length > 0 && <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-4">{stats.map((item) => <div key={`${node.id}-${item.label}`} className="rounded-2xl border p-4" style={subtle}><div className="text-2xl font-black" style={text}>{item.value}</div><div className="mt-1 text-sm font-medium" style={text}>{item.label}</div>{!!item.caption && <div className="mt-1 text-xs leading-5" style={muted}>{item.caption}</div>}</div>)}</div>}</div><div className="overflow-hidden rounded-[24px]" style={{ ...subtle, boxShadow: "var(--na-shadow)" }}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={src} alt={String(node.props.image_alt ?? "")} className="h-full min-h-[280px] w-full object-cover" onError={(event) => { const fallback = placeholder(String(node.props.image_alt ?? node.props.title ?? "Hero image")); if (event.currentTarget.src !== fallback) event.currentTarget.src = fallback; }} /></div></div></section>;
    }
    case "feature-grid": {
      const items = featureItems(node.props.items);
      const columns = Math.max(1, Math.min(Number(node.props.columns ?? 3), 4));
      const columnClass = columns >= 4 ? "md:grid-cols-4" : columns === 2 ? "md:grid-cols-2" : "md:grid-cols-3";
      return <section key={node.id} className={`px-4 md:px-6 ${extra}`}><div className="mx-auto w-full rounded-[28px] border p-6" style={{ ...panel, ...shell }}>{!!node.props.title && <h2 className="text-2xl font-black md:text-3xl" style={text}>{String(node.props.title)}</h2>}{!!node.props.description && <p className="mt-3 max-w-2xl text-sm leading-7 md:text-base" style={muted}>{String(node.props.description)}</p>}<div className={`mt-6 grid grid-cols-1 gap-4 ${columnClass}`}>{items.map((item) => <article key={`${node.id}-${item.title}`} className="rounded-2xl border p-5" style={subtle}>{(item.badge || item.icon) && <div className="mb-3 flex items-center gap-2">{!!item.icon && <span className="text-lg" style={{ color: "var(--na-primary)" }}>{item.icon}</span>}{!!item.badge && <span className="rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]" style={badge}>{item.badge}</span>}</div>}<h3 className="text-lg font-bold" style={text}>{item.title}</h3>{!!item.description && <p className="mt-2 text-sm leading-6" style={muted}>{item.description}</p>}</article>)}</div></div></section>;
    }
    case "stats-band": return <section key={node.id} className={`px-4 md:px-6 ${extra}`}><div className="mx-auto grid w-full grid-cols-2 gap-4 rounded-[28px] border p-5 md:grid-cols-4" style={{ ...panel, ...shell }}>{statItems(node.props.items).map((item) => <div key={`${node.id}-${item.label}`} className="rounded-2xl p-4 text-center" style={subtle}><div className="text-3xl font-black" style={text}>{item.value}</div><div className="mt-2 text-sm font-semibold" style={text}>{item.label}</div>{!!item.caption && <div className="mt-1 text-xs leading-5" style={muted}>{item.caption}</div>}</div>)}</div></section>;
    case "split-section": {
      const src = imageSource(node.props.image_src, String(node.props.image_alt ?? node.props.title ?? "Section image"));
      const bullets = strings(node.props.bullets);
      const reverse = Boolean(node.props.reverse);
      return <section key={node.id} className={`px-4 md:px-6 ${extra}`}><div className="mx-auto w-full rounded-[28px] border p-6 md:p-8" style={{ ...panel, ...shell }}><div className="grid items-center gap-8 md:grid-cols-2"><div className={reverse ? "md:order-2" : ""}>{!!node.props.eyebrow && <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--na-primary)" }}>{String(node.props.eyebrow)}</div>}<h2 className="text-3xl font-black leading-tight md:text-4xl" style={text}>{String(node.props.title ?? "Section title")}</h2>{!!node.props.description && <p className="mt-4 text-sm leading-7 md:text-base" style={muted}>{String(node.props.description)}</p>}{bullets.length > 0 && <ul className="mt-5 space-y-3">{bullets.map((item) => <li key={item} className="flex items-start gap-3 text-sm" style={text}><span className="mt-1 h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "var(--na-primary)" }} /><span>{item}</span></li>)}</ul>}<div className="mt-6 flex flex-wrap gap-3">{!!node.props.primary_cta_label && actionBtn(String(node.props.primary_cta_label), node.props.primary_cta_route, "primary")}{!!node.props.secondary_cta_label && actionBtn(String(node.props.secondary_cta_label), node.props.secondary_cta_route, "secondary")}</div></div><div className={`overflow-hidden rounded-[24px] ${reverse ? "md:order-1" : ""}`} style={{ ...subtle, boxShadow: "var(--na-shadow)" }}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={src} alt={String(node.props.image_alt ?? "")} className="h-full min-h-[260px] w-full object-cover" onError={(event) => { const fallback = placeholder(String(node.props.image_alt ?? node.props.title ?? "Section image")); if (event.currentTarget.src !== fallback) event.currentTarget.src = fallback; }} /></div></div></div></section>;
    }
    case "cta-band": return <section key={node.id} className={`px-4 pb-4 md:px-6 ${extra}`}><div className="mx-auto w-full rounded-[30px] px-6 py-8 text-white md:px-8 md:py-10" style={{ ...shell, background: dark ? "linear-gradient(135deg, rgba(15,23,42,0.96), rgba(30,41,59,0.92))" : "linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,41,59,0.9))", boxShadow: "var(--na-shadow)" }}><div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-center"><div><h2 className="text-3xl font-black leading-tight md:text-4xl">{String(node.props.title ?? "Move from idea to launch faster")}</h2>{!!node.props.description && <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">{String(node.props.description)}</p>}</div><div className="flex flex-wrap gap-3">{!!node.props.primary_cta_label && actionBtn(String(node.props.primary_cta_label), node.props.primary_cta_route, "primary")}{!!node.props.secondary_cta_label && <button type="button" onClick={() => node.props.secondary_cta_route && ctx.navigate(String(node.props.secondary_cta_route))} className="rounded-full border px-5 py-3 text-sm font-semibold text-white" style={{ borderColor: "rgba(255,255,255,0.16)", backgroundColor: "rgba(255,255,255,0.06)" }}>{String(node.props.secondary_cta_label)}</button>}</div></div></div></section>;
    case "auth-card": {
      const src = imageSource(node.props.image_src, String(node.props.image_alt ?? node.props.title ?? "Authentication visual"));
      return <section key={node.id} className={`px-4 py-8 md:px-6 md:py-10 ${extra}`}><div className="mx-auto grid w-full overflow-hidden rounded-[32px] border md:grid-cols-[0.92fr_1.08fr]" style={{ ...panel, ...authShell }}><div className="relative min-h-[280px] overflow-hidden" style={{ background: dark ? "linear-gradient(180deg, rgba(15,23,42,0.98), rgba(2,6,23,0.98))" : "linear-gradient(180deg, rgba(15,23,42,0.92), rgba(30,41,59,0.96))" }}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={src} alt={String(node.props.image_alt ?? "")} className="absolute inset-0 h-full w-full object-cover opacity-80" onError={(event) => { const fallback = placeholder(String(node.props.image_alt ?? node.props.title ?? "Authentication visual")); if (event.currentTarget.src !== fallback) event.currentTarget.src = fallback; }} /><div className="relative flex h-full flex-col justify-end bg-gradient-to-t from-slate-950 via-slate-900/55 to-transparent p-8 text-white"><div className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">{String(node.props.aside_title ?? "Nano Atoms")}</div><div className="mt-3 text-3xl font-black leading-tight">{String(node.props.title ?? "Welcome back")}</div>{!!node.props.aside_text && <p className="mt-3 max-w-md text-sm leading-7 text-white/80">{String(node.props.aside_text)}</p>}</div></div><div className="p-6 md:p-10"><h2 className="text-3xl font-black" style={text}>{String(node.props.title ?? "Welcome back")}</h2>{!!node.props.description && <p className="mt-3 text-sm leading-7" style={muted}>{String(node.props.description)}</p>}<div className="mt-6 space-y-4">{children.map((child) => renderComponent(child, ctx, bundle, theme))}</div>{!!node.props.footer_text && <div className="mt-5 text-sm" style={muted}>{String(node.props.footer_text)} {!!node.props.footer_link_label && <button type="button" className="font-semibold" style={{ color: "var(--na-primary)" }} onClick={() => node.props.footer_link_route && ctx.navigate(String(node.props.footer_link_route))}>{String(node.props.footer_link_label)}</button>}</div>}</div></div></section>;
    }
    case "modal": return <div key={node.id} className={`rounded-xl border border-dashed p-4 ${extra}`} style={subtle}>{children.length > 0 ? children.map((child) => renderComponent(child, ctx, bundle, theme)) : <p className="text-sm" style={muted}>Modal content pending</p>}</div>;
    default: return <div key={node.id} className="rounded-lg border border-dashed p-3 text-xs" style={{ borderColor: "var(--na-border)", backgroundColor: "var(--na-subtle-surface)", color: "var(--na-muted)" }}>[{node.type}]</div>;
  }
}
