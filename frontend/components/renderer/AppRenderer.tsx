"use client";

import { useCallback, useState } from "react";
import type { CSSProperties } from "react";
import type { AppSchema, CodeBundle } from "@/types/schema";
import { renderComponent } from "./ComponentRegistry";

interface Props {
  schema: AppSchema;
  codeBundle: CodeBundle | null;
}

function getCanvasClass(mode?: string) {
  switch (mode) {
    case "contrast":
      return "bg-[radial-gradient(circle_at_top,#e0ecff_0%,#f8fafc_24%,#eef2ff_100%)]";
    case "editorial":
      return "bg-[linear-gradient(180deg,#fffaf2_0%,#f7efe5_24%,#fffdf8_100%)]";
    case "spotlight":
      return "bg-[radial-gradient(circle_at_top_right,#dbeafe_0%,#f8fafc_34%,#eff6ff_100%)]";
    default:
      return "bg-[radial-gradient(circle_at_top,#eef4ff_0%,#f8fafc_34%,#ffffff_100%)]";
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
    return <div className="p-8 text-sm text-gray-400">无可渲染页面</div>;
  }

  const theme =
    schema.ui_theme && typeof schema.ui_theme.component_styles === "object"
      ? schema.ui_theme.component_styles
      : undefined;
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
  const primaryColor = schema.ui_theme?.primary_color ?? "#6366f1";
  const fontFamily = schema.ui_theme?.font_family ?? "inherit";
  const canvasMode = schema.ui_theme?.canvas_mode ?? "soft";
  const density = schema.ui_theme?.density ?? "balanced";
  const textColor = schema.ui_theme?.text_color ?? "#111827";
  const backgroundColor = schema.ui_theme?.background_color ?? "#ffffff";
  const shellClass = getCanvasClass(canvasMode);
  const stackClass = getDensityClass(density);

  return (
    <div
      className={`min-h-full ${shellClass}`}
      style={
        {
          fontFamily,
          "--color-primary": primaryColor,
          backgroundColor,
          color: textColor,
        } as CSSProperties
      }
    >
      <div className={`pb-20 ${stackClass}`}>
        {components.map((node) => renderComponent(node, ctx, codeBundle, theme))}
      </div>

      {Object.entries(submitResults).map(([formId, ok]) =>
        ok ? (
          <div
            key={formId}
            className="fixed bottom-4 right-4 rounded-xl bg-green-500 px-4 py-3 text-sm text-white shadow-lg"
          >
            提交成功
          </div>
        ) : null
      )}

      {pages.length > 1 && (
        <div className="fixed bottom-4 left-1/2 flex -translate-x-1/2 gap-1.5">
          {pages.map((page) => (
            <button
              key={page.id}
              onClick={() => setCurrentRoute(page.route)}
              className={`h-2 w-2 rounded-full transition-all ${
                currentRoute === page.route
                  ? "w-6 bg-indigo-500"
                  : "bg-gray-300 hover:bg-gray-400"
              }`}
              title={page.name}
            />
          ))}
        </div>
      )}
    </div>
  );
}
