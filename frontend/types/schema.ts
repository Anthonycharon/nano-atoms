export type ComponentType =
  | "text"
  | "heading"
  | "image"
  | "button"
  | "input"
  | "select"
  | "table"
  | "card"
  | "form"
  | "modal"
  | "tag"
  | "navbar"
  | "stat-card"
  | "hero"
  | "feature-grid"
  | "stats-band"
  | "split-section"
  | "cta-band"
  | "auth-card";

export interface ActionDef {
  trigger: "click" | "submit" | "change";
  type: "navigate" | "submit_form" | "open_modal" | "close_modal" | "set_value";
  payload?: Record<string, unknown>;
}

export interface StyleProps {
  className?: string;
  [key: string]: unknown;
}

export interface ComponentNode {
  id: string;
  type: ComponentType;
  props: Record<string, unknown>;
  children?: ComponentNode[];
  actions?: ActionDef[];
  style?: StyleProps;
}

export interface Page {
  id: string;
  name: string;
  route: string;
  components: ComponentNode[];
}

export interface NavigationItem {
  label: string;
  route: string;
}

export interface DataModel {
  name: string;
  fields: string[];
}

export interface UITheme {
  primary_color: string;
  secondary_color: string;
  background_color: string;
  text_color: string;
  font_family: string;
  border_radius: string;
  spacing_unit: number;
  canvas_mode?: "soft" | "contrast" | "editorial" | "spotlight";
  surface_mode?: "flat" | "layered" | "glass";
  density?: "airy" | "balanced" | "compact";
  accent_style?: "solid" | "gradient";
  shadow_strength?: "soft" | "medium" | "strong";
  component_styles?: Record<string, { className?: string }>;
}

export interface DesignBrief {
  experience_goal?: string;
  primary_user_mindset?: string;
  visual_direction?: string;
  layout_density?: "airy" | "balanced" | "compact";
  tone_keywords?: string[];
  section_recommendations?: string[];
  quality_checklist?: string[];
  avoid_patterns?: string[];
}

export interface AppSchema {
  app_id: string;
  title: string;
  app_type: string;
  pages: Page[];
  navigation?: NavigationItem[];
  data_models?: DataModel[];
  design_brief?: DesignBrief;
  ui_theme?: UITheme;
}

export interface FormHandler {
  form_id: string;
  fields: string[];
  submit_action: "save_local" | "api_call";
  api_endpoint?: string;
  validation?: Record<string, string>;
}

export interface DataBinding {
  component_id: string;
  data_source: string;
  field_path: string;
}

export interface PageTransition {
  from_page: string;
  to_page: string;
  trigger_component: string;
}

export interface CodeBundle {
  form_handlers: FormHandler[];
  data_bindings: DataBinding[];
  initial_state: Record<string, unknown>;
  page_transitions?: PageTransition[];
}

export interface GeneratedFile {
  path: string;
  language: string;
  content: string;
}

export interface GeneratedProjectArtifact {
  format: string;
  title?: string;
  package_name?: string;
  entry?: string;
  code_bundle: CodeBundle;
  files: GeneratedFile[];
}
