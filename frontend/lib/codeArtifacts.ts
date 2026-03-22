import type {
  CodeBundle,
  GeneratedFile,
  GeneratedProjectArtifact,
} from "@/types/schema";

function parseRawJson(raw: string | null): unknown {
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCodeBundle(value: unknown): value is CodeBundle {
  return (
    isRecord(value) &&
    Array.isArray(value.form_handlers) &&
    Array.isArray(value.data_bindings) &&
    isRecord(value.initial_state)
  );
}

function isGeneratedFile(value: unknown): value is GeneratedFile {
  return (
    isRecord(value) &&
    typeof value.path === "string" &&
    typeof value.content === "string"
  );
}

function isGeneratedProjectArtifact(value: unknown): value is GeneratedProjectArtifact {
  return (
    isRecord(value) &&
    Array.isArray(value.files) &&
    value.files.every(isGeneratedFile) &&
    isCodeBundle(value.code_bundle)
  );
}

function buildLegacyArtifact(
  codeBundle: CodeBundle,
  schemaJson: string | null
): GeneratedProjectArtifact {
  const files: GeneratedFile[] = [
    {
      path: "code_bundle.json",
      language: "json",
      content: JSON.stringify(codeBundle, null, 2),
    },
  ];

  if (schemaJson) {
    try {
      files.push({
        path: "app_schema.json",
        language: "json",
        content: JSON.stringify(JSON.parse(schemaJson), null, 2),
      });
    } catch {
      files.push({
        path: "app_schema.json",
        language: "json",
        content: schemaJson,
      });
    }
  }

  return {
    format: "legacy_code_bundle",
    code_bundle: codeBundle,
    entry: files[0]?.path,
    files,
  };
}

export function parseCodeArtifact(
  raw: string | null,
  schemaJson: string | null = null
): GeneratedProjectArtifact | null {
  const parsed = parseRawJson(raw);
  if (isGeneratedProjectArtifact(parsed)) {
    return parsed;
  }
  if (isCodeBundle(parsed)) {
    return buildLegacyArtifact(parsed, schemaJson);
  }
  return null;
}

export function extractCodeBundle(raw: string | null): CodeBundle | null {
  const parsed = parseRawJson(raw);
  if (isGeneratedProjectArtifact(parsed)) {
    return parsed.code_bundle;
  }
  if (isCodeBundle(parsed)) {
    return parsed;
  }
  return null;
}
