"use client";

import { useCallback, useState } from "react";
import type { CSSProperties } from "react";
import type { AppSchema, CodeBundle, LayoutArchetype, Page, UITheme } from "@/types/schema";
import { renderComponent } from "./ComponentRegistry";

interface Props {
  schema: AppSchema;
  codeBundle: CodeBundle | null;
}

function hexToRgb(value?: string): [number, number, number] | null {
  if (!value || !value.startsWith("#")) return null;
  let hex = value.slice(1).trim();
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((char) => char + char)
      .join("");
  }
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return null;
  return [
    Number.parseInt(hex.slice(0, 2), 16),
    Number.parseInt(hex.slice(2, 4), 16),
    Number.parseInt(hex.slice(4, 6), 16),
  ];
}

function hexToRgba(value: string | undefined, alpha: number, fallback: string): string {
  const rgb = hexToRgb(value);
  if (!rgb) return fallback;
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function inferThemeMode(theme?: UITheme): "light" | "dark" | "mixed" {
  if (theme?.theme_mode === "light" || theme?.theme_mode === "dark" || theme?.theme_mode === "mixed") {
    return theme.theme_mode;
  }
  const rgb = hexToRgb(theme?.background_color);
  if (!rgb) return "light";
  const luminance = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
  return luminance < 0.45 ? "dark" : "light";
}

function getCanvasBackground(theme?: UITheme): string {
  if (theme?.page_background?.trim()) return theme.page_background;

  const mode = inferThemeMode(theme);
  const background = theme?.background_color ?? (mode === "dark" ? "#020617" : "#ffffff");
  switch (theme?.canvas_mode) {
    case "editorial":
      return mode === "dark"
        ? `linear-gradient(180deg, ${background} 0%, #111827 34%, #020617 100%)`
        : "linear-gradient(180deg, #fffaf2 0%, #f7efe5 24%, #fffdf8 100%)";
    case "spotlight":
      return mode === "dark"
        ? `radial-gradient(circle at top right, #1d4ed8 0%, ${background} 28%, #020617 100%)`
        : "radial-gradient(circle at top right, #dbeafe 0%, #f8fafc 34%, #eff6ff 100%)";
    case "contrast":
      return mode === "dark"
        ? `radial-gradient(circle at top, #1e293b 0%, ${background} 26%, #020617 100%)`
        : "radial-gradient(circle at top, #e0ecff 0%, #f8fafc 24%, #eef2ff 100%)";
    default:
      return mode === "dark"
        ? `radial-gradient(circle at top, #0f172a 0%, ${background} 36%, #020617 100%)`
        : "radial-gradient(circle at top, #eef4ff 0%, #f8fafc 34%, #ffffff 100%)";
  }
}

function getDensityClass(density?: string) {
  switch (density) {
    case "compact":
      return "space-y-4 md:space-y-5";
    case "airy":
      return "space-y-8 md:space-y-10";
    default:
      return "space-y-6 md:space-y-8";
  }
}

function inferLayoutArchetype(schema: AppSchema, page: Page | undefined): LayoutArchetype {
  const raw = page?.layout_archetype ?? schema.layout_archetype ?? schema.design_brief?.layout_archetype;
  if (
    raw === "marketing" ||
    raw === "editorial" ||
    raw === "dashboard" ||
    raw === "centered-auth" ||
    raw === "workspace" ||
    raw === "immersive"
  ) {
    return raw;
  }

  const appType = schema.app_type.toLowerCase();
  if (/(auth|login|register|signup|signin)/.test(appType)) return "centered-auth";
  if (/(blog|editorial|article|journal|content)/.test(appType)) return "editorial";
  if (/(landing|marketing|campaign|launch|showcase)/.test(appType)) return "marketing";
  if (/(dashboard|analytics|admin|crm|report)/.test(appType)) return "dashboard";
  if (/(studio|workspace|assistant|tool|internal|copilot)/.test(appType)) return "workspace";
  return "workspace";
}

function getLayoutVars(layout: LayoutArchetype): CSSProperties {
  switch (layout) {
    case "marketing":
      return {
        "--na-shell-width": "1180px",
        "--na-reading-width": "780px",
        "--na-auth-width": "1080px",
      } as CSSProperties;
    case "editorial":
      return {
        "--na-shell-width": "960px",
        "--na-reading-width": "760px",
        "--na-auth-width": "980px",
      } as CSSProperties;
    case "dashboard":
      return {
        "--na-shell-width": "1320px",
        "--na-reading-width": "860px",
        "--na-auth-width": "1040px",
      } as CSSProperties;
    case "centered-auth":
      return {
        "--na-shell-width": "960px",
        "--na-reading-width": "700px",
        "--na-auth-width": "920px",
      } as CSSProperties;
    case "immersive":
      return {
        "--na-shell-width": "1480px",
        "--na-reading-width": "860px",
        "--na-auth-width": "1120px",
      } as CSSProperties;
    default:
      return {
        "--na-shell-width": "1380px",
        "--na-reading-width": "860px",
        "--na-auth-width": "1080px",
      } as CSSProperties;
  }
}

function getShellClass(layout: LayoutArchetype): string {
  switch (layout) {
    case "centered-auth":
      return "flex min-h-screen items-center justify-center px-4 py-8 md:px-6 md:py-12";
    case "editorial":
      return "px-4 py-8 md:px-6 md:py-12";
    case "dashboard":
    case "workspace":
      return "px-4 py-6 md:px-6 md:py-8";
    case "immersive":
    case "marketing":
    default:
      return "py-0";
  }
}

function getPageClass(layout: LayoutArchetype, densityClass: string): string {
  switch (layout) {
    case "centered-auth":
      return `w-full ${densityClass}`;
    case "editorial":
      return `mx-auto w-full max-w-[var(--na-reading-width)] ${densityClass}`;
    case "dashboard":
    case "workspace":
      return `mx-auto w-full max-w-[var(--na-shell-width)] ${densityClass}`;
    case "immersive":
      return `mx-auto w-full ${densityClass}`;
    case "marketing":
    default:
      return `mx-auto w-full ${densityClass}`;
  }
}

function getShadow(theme?: UITheme): string {
  const mode = inferThemeMode(theme);
  switch (theme?.shadow_strength) {
    case "strong":
      return mode === "dark"
        ? "0 32px 90px rgba(2, 6, 23, 0.55)"
        : "0 28px 80px rgba(15, 23, 42, 0.18)";
    case "medium":
      return mode === "dark"
        ? "0 24px 64px rgba(2, 6, 23, 0.44)"
        : "0 22px 56px rgba(15, 23, 42, 0.14)";
    default:
      return mode === "dark"
        ? "0 18px 48px rgba(2, 6, 23, 0.36)"
        : "0 20px 52px rgba(15, 23, 42, 0.1)";
  }
}

function getButtonBackground(theme?: UITheme): string {
  const primary = theme?.primary_color ?? "#6366f1";
  const secondary = theme?.secondary_color ?? "#a5b4fc";
  if (theme?.accent_style === "solid") return primary;
  return `linear-gradient(135deg, ${primary}, ${secondary})`;
}

function getThemeStyle(theme?: UITheme): CSSProperties {
  const mode = inferThemeMode(theme);
  const primary = theme?.primary_color ?? "#6366f1";
  const text = theme?.text_color ?? (mode === "dark" ? "#f8fafc" : "#111827");
  const secondary = theme?.secondary_color ?? (mode === "dark" ? "#38bdf8" : "#a5b4fc");
  const surface = theme?.surface_color ?? (mode === "dark" ? "rgba(15, 23, 42, 0.78)" : "rgba(255, 255, 255, 0.92)");
  const surfaceText = theme?.surface_text_color ?? (mode === "dark" ? "#f8fafc" : text);
  const border = theme?.border_color ?? (mode === "dark" ? "rgba(148, 163, 184, 0.18)" : "#dbe3f0");
  const muted = theme?.muted_text_color ?? (mode === "dark" ? "rgba(226, 232, 240, 0.72)" : "#64748b");
  const inputBackground = theme?.input_background ?? (mode === "dark" ? "rgba(15, 23, 42, 0.92)" : "#ffffff");
  const subtleSurface =
    theme?.subtle_surface_color ?? (mode === "dark" ? "rgba(30, 41, 59, 0.7)" : "rgba(248, 250, 252, 0.86)");
  const buttonText = theme?.button_text_color ?? (mode === "dark" ? "#f8fafc" : "#ffffff");

  return {
    fontFamily: theme?.font_family ?? "inherit",
    background: getCanvasBackground(theme),
    backgroundColor: theme?.background_color ?? (mode === "dark" ? "#020617" : "#ffffff"),
    color: text,
    "--color-primary": primary,
    "--na-primary": primary,
    "--na-secondary": secondary,
    "--na-text": text,
    "--na-surface": surface,
    "--na-surface-text": surfaceText,
    "--na-border": border,
    "--na-muted": muted,
    "--na-input-bg": inputBackground,
    "--na-subtle-surface": subtleSurface,
    "--na-button-bg": getButtonBackground(theme),
    "--na-button-text": buttonText,
    "--na-shadow": getShadow(theme),
    "--na-accent-soft": hexToRgba(primary, mode === "dark" ? 0.22 : 0.12, mode === "dark" ? "rgba(99, 102, 241, 0.22)" : "rgba(99, 102, 241, 0.12)"),
    "--na-secondary-soft": hexToRgba(secondary, mode === "dark" ? 0.24 : 0.14, mode === "dark" ? "rgba(56, 189, 248, 0.24)" : "rgba(165, 180, 252, 0.14)"),
  } as CSSProperties;
}

export default function AppRenderer({ schema, codeBundle }: Props) {
  const pages = Array.isArray(schema.pages) ? schema.pages : [];
  const [currentRoute, setCurrentRoute] = useState(pages[0]?.route ?? "/");
  const [appState, setAppState] = useState<Record<string, unknown>>(
    codeBundle?.initial_state ?? {}
  );
  const [formData, setFormData] = useState<Record<string, Record<string, string>>>({});
  const [submitResults, setSubmitResults] = useState<Record<string, boolean>>({});

  const navigate = useCallback(
    (route: string) => {
      const page = pages.find((item) => item.route === route);
      if (page) setCurrentRoute(route);
    },
    [pages]
  );

  const setState = useCallback((key: string, val: unknown) => {
    setAppState((prev) => ({ ...prev, [key]: val }));
  }, []);

  const setFormField = useCallback((formId: string, field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [formId]: { ...(prev[formId] ?? {}), [field]: value },
    }));
  }, []);

  const submitForm = useCallback((formId: string, bundle: CodeBundle | null) => {
    const handlers = Array.isArray(bundle?.form_handlers) ? bundle?.form_handlers : [];
    const handler = handlers.find((item) => item.form_id === formId);
    if (handler?.submit_action === "save_local") {
      setSubmitResults((prev) => ({ ...prev, [formId]: true }));
    }
  }, []);

  const currentPage = pages.find((item) => item.route === currentRoute) ?? pages[0];

  if (!currentPage) {
    return <div className="p-8 text-sm text-gray-400">No renderable page</div>;
  }

  const ctx = {
    state: appState,
    setState,
    currentPage: currentRoute,
    navigate,
    formData,
    setFormField,
    submitForm,
  };

  const components = Array.isArray(currentPage.components) ? currentPage.components : [];
  const stackClass = getDensityClass(schema.ui_theme?.density ?? "balanced");
  const layout = inferLayoutArchetype(schema, currentPage);
  const themeStyle = {
    ...getThemeStyle(schema.ui_theme),
    ...getLayoutVars(layout),
  };

  return (
    <div className="min-h-full" style={themeStyle}>
      <div className={getShellClass(layout)}>
        <div className={`${getPageClass(layout, stackClass)} pb-20`}>
          {components.map((node) => renderComponent(node, ctx, codeBundle, schema.ui_theme))}
        </div>
      </div>

      {Object.entries(submitResults).map(([formId, ok]) =>
        ok ? (
          <div
            key={formId}
            className="fixed bottom-4 right-4 rounded-xl px-4 py-3 text-sm shadow-lg"
            style={{
              background: "var(--na-button-bg)",
              color: "var(--na-button-text)",
              boxShadow: "var(--na-shadow)",
            }}
          >
            Submitted successfully
          </div>
        ) : null
      )}

      {pages.length > 1 && (
        <div
          className="fixed bottom-4 left-1/2 flex -translate-x-1/2 gap-1.5 rounded-full border px-3 py-2"
          style={{
            borderColor: "var(--na-border)",
            backgroundColor: "var(--na-surface)",
            boxShadow: "var(--na-shadow)",
          }}
        >
          {pages.map((page) => (
            <button
              key={page.id}
              onClick={() => setCurrentRoute(page.route)}
              className="h-2 w-2 rounded-full transition-all"
              style={{
                width: currentRoute === page.route ? "24px" : "8px",
                background:
                  currentRoute === page.route ? "var(--na-button-bg)" : "var(--na-border)",
              }}
              title={page.name}
            />
          ))}
        </div>
      )}
    </div>
  );
}
