"use client";

export interface StarterIntent {
  source: "example" | "template";
  title: string;
  prompt: string;
  description?: string;
}

const STORAGE_KEY = "nano_pending_starter";

function compactText(value: string, maxLength: number) {
  const cleaned = value.replace(/\s+/g, " ").trim();
  return cleaned.length <= maxLength ? cleaned : `${cleaned.slice(0, maxLength).trim()}...`;
}

function deriveTitleFromPrompt(prompt: string) {
  const firstLine = prompt.split(/[\r\n]/)[0] ?? "";
  const firstClause = firstLine.split(/[，。,.!?！？]/)[0]?.trim() || "";
  return compactText(firstClause || "Quick Start Project", 18);
}

export function buildExampleStarter(prompt: string): StarterIntent {
  return {
    source: "example",
    title: deriveTitleFromPrompt(prompt),
    prompt,
    description: compactText(prompt, 120),
  };
}

export function buildTemplateStarter(name: string, description: string): StarterIntent {
  return {
    source: "template",
    title: name,
    description,
    prompt: `创建一个${name}应用。要求：${description} 页面完整、可交互，并提供适合该场景的默认内容与视觉呈现。`,
  };
}

export function persistStarterIntent(intent: StarterIntent) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(intent));
}

export function peekStarterIntent(): StarterIntent | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as StarterIntent;
    if (!parsed?.prompt || !parsed?.title) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearStarterIntent() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export function appendStarterParams(path: string, intent: StarterIntent) {
  const params = new URLSearchParams();
  params.set("starterSource", intent.source);
  params.set("starterTitle", intent.title);
  params.set("starterPrompt", intent.prompt);
  if (intent.description) {
    params.set("starterDescription", intent.description);
  }
  return `${path}?${params.toString()}`;
}

export function getStarterIntentFromSearchParams(searchParams: {
  get: (key: string) => string | null;
}): StarterIntent | null {
  const starterPrompt = searchParams.get("starterPrompt");
  const starterTitle = searchParams.get("starterTitle");
  if (!starterPrompt || !starterTitle) return null;

  const source = searchParams.get("starterSource");
  return {
    source: source === "template" ? "template" : "example",
    title: starterTitle,
    prompt: starterPrompt,
    description: searchParams.get("starterDescription") || undefined,
  };
}
