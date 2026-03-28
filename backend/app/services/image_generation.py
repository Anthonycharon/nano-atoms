"""Generate supporting image assets for previewable app components."""

from __future__ import annotations

import asyncio
import copy
import re
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


PLACEHOLDER_IMAGE_PREFIX = "data:image/svg+xml"
DOUBAO_MIN_PIXELS = 3_686_400
DEFAULT_IMAGE_SIZE = "1920x1920"
LANDSCAPE_IMAGE_SIZE = "2560x1440"
PORTRAIT_IMAGE_SIZE = "1440x2560"
MINIMAX_ASPECT_RATIOS: tuple[tuple[str, float], ...] = (
    ("1:1", 1.0),
    ("16:9", 16 / 9),
    ("4:3", 4 / 3),
    ("3:2", 3 / 2),
    ("2:3", 2 / 3),
    ("3:4", 3 / 4),
    ("9:16", 9 / 16),
    ("21:9", 21 / 9),
)
MINIMAX_IMAGE_MODELS = {"image-01", "image-01-live"}
VISUAL_APP_TYPES = {
    "landing",
    "marketing",
    "showcase",
    "portfolio",
    "blog",
    "media",
    "ecommerce",
    "store",
    "event",
    "campaign",
}
VISUAL_PROMPT_KEYWORDS = (
    "image",
    "illustration",
    "photo",
    "gallery",
    "hero",
    "banner",
    "cover",
    "visual",
    "marketing",
    "landing",
    "portfolio",
    "showcase",
    "brand",
    "travel",
    "restaurant",
    "product",
    "catalog",
    "图片",
    "配图",
    "插图",
    "照片",
    "画廊",
    "封面",
    "头图",
    "横幅",
    "宣传页",
    "落地页",
    "作品集",
    "商品图",
    "旅游",
    "餐厅",
    "品牌",
)


async def enrich_schema_with_generated_images(
    app_schema: dict[str, Any],
    project_prompt: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema = _ensure_visual_slots(copy.deepcopy(app_schema), project_prompt)
    targets = _build_visual_asset_targets(schema, project_prompt)

    if not targets:
        return schema, {
            "attempted": 0,
            "generated": 0,
            "skipped": 0,
            "summary": "No image components detected",
        }

    if not settings.OPENAI_IMAGE_ENABLED:
        omitted = _strip_unresolved_images(schema)
        return schema, {
            "attempted": len(targets),
            "generated": 0,
            "skipped": omitted,
            "summary": _build_skip_summary(omitted),
        }

    api_key = settings.OPENAI_IMAGE_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        omitted = _strip_unresolved_images(schema)
        return schema, {
            "attempted": len(targets),
            "generated": 0,
            "skipped": omitted,
            "summary": _build_skip_summary(omitted),
        }

    limit = max(0, settings.OPENAI_IMAGE_MAX_ASSETS)
    actionable = targets[:limit]
    generated = 0
    errors: list[str] = []
    image_concurrency = max(1, min(settings.OPENAI_IMAGE_CONCURRENCY, len(actionable) or 1))
    request_timeout = max(30, settings.OPENAI_TIMEOUT_SECONDS)

    async with httpx.AsyncClient(timeout=float(request_timeout)) as client:
        semaphore = asyncio.Semaphore(image_concurrency)

        async def generate_target(target: dict[str, Any]) -> tuple[dict[str, Any], str | None, str | None]:
            async with semaphore:
                try:
                    prompt = _build_image_prompt(
                        project_prompt=project_prompt,
                        app_schema=schema,
                        page_name=target["page_name"],
                        role=target["role"],
                        label=target["label"],
                        component=target.get("component"),
                        page_purpose=target.get("page_purpose"),
                    )
                    size = _pick_image_size(target)
                    src = await _generate_image(
                        client=client,
                        api_key=api_key,
                        prompt=prompt,
                        size=size,
                    )
                    return target, src, None
                except Exception as exc:
                    return target, None, f"{target['component']['id']}: {exc}"

        results = await asyncio.gather(*(generate_target(target) for target in actionable))
        for target, src, error in results:
            if error:
                errors.append(error)
                continue
            component = target.get("component")
            prop_key = target.get("prop_key")
            if isinstance(component, dict) and isinstance(prop_key, str):
                component.setdefault("props", {})
                if isinstance(component.get("props"), dict):
                    component["props"][prop_key] = src
            _register_generated_visual_asset(schema, target, src)
            generated += 1

    omitted = _strip_unresolved_images(schema)
    summary = _build_result_summary(generated, omitted)

    return schema, {
        "attempted": len(targets),
        "generated": generated,
        "skipped": omitted,
        "errors": errors,
        "summary": summary,
    }


async def _generate_image(
    client: httpx.AsyncClient,
    api_key: str,
    prompt: str,
    size: str,
) -> str:
    base_url = (settings.OPENAI_IMAGE_BASE_URL or settings.OPENAI_BASE_URL).rstrip("/")
    model = settings.OPENAI_IMAGE_MODEL
    return await _generate_image_with_config(
        client=client,
        api_key=api_key,
        prompt=prompt,
        size=size,
        base_url=base_url,
        model=model,
    )


async def generate_image_preview(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    size: str = DEFAULT_IMAGE_SIZE,
    disable_proxy: bool = False,
) -> str:
    timeout_seconds = max(30, settings.OPENAI_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(
        timeout=float(timeout_seconds),
        trust_env=not disable_proxy,
    ) as client:
        return await _generate_image_with_config(
            client=client,
            api_key=api_key,
            prompt=prompt,
            size=size,
            base_url=base_url.rstrip("/"),
            model=model,
        )


async def _generate_image_with_config(
    *,
    client: httpx.AsyncClient,
    api_key: str,
    prompt: str,
    size: str,
    base_url: str,
    model: str,
) -> str:
    if not base_url:
        raise ValueError("image API base URL is not configured")
    effective_model = _resolve_image_model_for_provider(base_url, model)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if _is_minimax_image_endpoint(base_url):
        return await _generate_image_via_minimax(
            client=client,
            endpoint=_resolve_minimax_image_endpoint(base_url),
            headers=headers,
            prompt=prompt,
            size=size,
            model=effective_model,
        )

    prefers_chat_completions = base_url.endswith("/chat/completions")

    if prefers_chat_completions:
        return await _generate_image_via_chat(
            client=client,
            endpoint=base_url,
            headers=headers,
            prompt=prompt,
            model=effective_model,
        )

    image_error: Exception | None = None
    try:
        return await _generate_image_via_images_api(
            client=client,
            endpoint=f"{base_url}/images/generations",
            headers=headers,
            prompt=prompt,
            size=size,
            model=effective_model,
        )
    except Exception as exc:
        image_error = exc
        if not _is_missing_images_endpoint(exc):
            raise

    chat_endpoint = f"{base_url}/chat/completions"
    try:
        return await _generate_image_via_chat(
            client=client,
            endpoint=chat_endpoint,
            headers=headers,
            prompt=prompt,
            model=effective_model,
        )
    except Exception as exc:
        if image_error:
            raise ValueError(
                f"image API failed on images endpoint ({image_error}) and chat completions fallback ({exc})"
            ) from exc
        raise


async def _generate_image_via_images_api(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict[str, str],
    prompt: str,
    size: str,
    model: str,
) -> str:
    base_payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    payload_variants = [
        {**base_payload, "output_format": "png"},
        {**base_payload, "response_format": "b64_json"},
        base_payload,
    ]

    last_error: Exception | None = None
    for payload in payload_variants:
        try:
            response = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return _extract_image_src(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 405}:
                raise
            if exc.response.status_code not in {400, 422}:
                raise
            last_error = exc
        except ValueError as exc:
            last_error = exc

    raise ValueError(str(last_error) if last_error else "image API returned no renderable asset")


async def _generate_image_via_minimax(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict[str, str],
    prompt: str,
    size: str,
    model: str,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "response_format": "base64",
        "prompt_optimizer": False,
        "aigc_watermark": False,
        **_build_minimax_size_payload(size),
    }
    response = await client.post(
        endpoint,
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return _extract_image_src(response.json())


async def _generate_image_via_chat(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict[str, str],
    prompt: str,
    model: str,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
    }
    response = await client.post(
        endpoint,
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    return _extract_image_src(response.json())


def _extract_image_src(payload: dict[str, Any]) -> str:
    minimax_data = payload.get("data") if isinstance(payload.get("data"), dict) else None
    if isinstance(minimax_data, dict):
        image_base64 = minimax_data.get("image_base64")
        if isinstance(image_base64, list):
            first_base64 = next((item for item in image_base64 if isinstance(item, str) and item.strip()), None)
            if first_base64:
                return f"data:image/jpeg;base64,{first_base64}"
        if isinstance(image_base64, str) and image_base64.strip():
            return f"data:image/jpeg;base64,{image_base64}"

        image_urls = minimax_data.get("image_urls")
        if isinstance(image_urls, list):
            first_url = next((item for item in image_urls if isinstance(item, str) and item.strip()), None)
            if first_url:
                return first_url

    data_items = payload.get("data") if isinstance(payload.get("data"), list) else []
    item = data_items[0] if data_items else None
    if isinstance(item, dict):
        if item.get("b64_json"):
            return f"data:image/png;base64,{item['b64_json']}"
        if item.get("url"):
            return str(item["url"])

    message = ((payload.get("choices") or [{}])[0] or {}).get("message") or {}
    if isinstance(message, dict):
        for image in message.get("images") or []:
            if not isinstance(image, dict):
                continue
            image_url = image.get("image_url")
            if isinstance(image_url, dict) and image_url.get("url"):
                return str(image_url["url"])
            if image.get("url"):
                return str(image["url"])

        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "image_url":
                    image_url = block.get("image_url")
                    if isinstance(image_url, dict) and image_url.get("url"):
                        return str(image_url["url"])

    base_resp = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
    status_msg = str(base_resp.get("status_msg") or "").strip()
    if status_msg:
        raise ValueError(f"image API returned no renderable asset: {status_msg}")
    raise ValueError("image API returned no renderable asset")


def _is_missing_images_endpoint(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {404, 405}
    return False


def _resolve_image_model_for_provider(base_url: str, model: str) -> str:
    normalized_model = str(model or "").strip()
    if _is_minimax_image_endpoint(base_url):
        if normalized_model in MINIMAX_IMAGE_MODELS:
            return normalized_model
        return "image-01"
    return normalized_model


def _is_minimax_image_endpoint(base_url: str) -> bool:
    normalized = (base_url or "").strip().lower()
    return "minimaxi.com" in normalized or normalized.endswith("/image_generation")


def _resolve_minimax_image_endpoint(base_url: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if normalized.endswith("/image_generation"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/image_generation"
    if re.search(r"/v\d+$", normalized):
        return f"{normalized}/image_generation"
    return f"{normalized}/v1/image_generation"


def _build_minimax_size_payload(size: str) -> dict[str, Any]:
    aspect_ratio = _closest_minimax_aspect_ratio(size)
    if aspect_ratio:
        return {"aspect_ratio": aspect_ratio}
    return {"aspect_ratio": "1:1"}


def _closest_minimax_aspect_ratio(size: str) -> str | None:
    width, height = _parse_size(size)
    if not width or not height:
        return None

    ratio = width / height
    return min(
        MINIMAX_ASPECT_RATIOS,
        key=lambda item: abs(item[1] - ratio),
    )[0]


def _parse_size(size: str) -> tuple[int | None, int | None]:
    value = str(size or "").strip().lower()
    match = re.fullmatch(r"(\d+)\s*x\s*(\d+)", value)
    if not match:
        return None, None
    try:
        return int(match.group(1)), int(match.group(2))
    except ValueError:
        return None, None


def _build_skip_summary(omitted: int) -> str:
    if omitted:
        return f"Optional image generation skipped; omitted {omitted} image slot(s)"
    return "Optional image generation skipped"


def _build_result_summary(generated: int, omitted: int) -> str:
    if generated == 0:
        return _build_skip_summary(omitted)
    if omitted:
        return f"Generated {generated} image asset(s); omitted {omitted} unresolved image slot(s)"
    return f"Generated {generated} image asset(s)"


def _ensure_visual_slots(app_schema: dict[str, Any], project_prompt: str) -> dict[str, Any]:
    if _collect_image_targets(app_schema):
        return app_schema

    pages = app_schema.get("pages")
    if not isinstance(pages, list) or not pages:
        return app_schema

    first_page = next((page for page in pages if isinstance(page, dict)), None)
    if not isinstance(first_page, dict):
        return app_schema

    components = first_page.setdefault("components", [])
    if not isinstance(components, list):
        first_page["components"] = []
        components = first_page["components"]

    preferred_slots = 2 if _should_insert_visual_slot(app_schema, project_prompt) else 1
    current_images = sum(1 for item in components if isinstance(item, dict) and item.get("type") == "image")
    while current_images < preferred_slots:
        image_component = _build_visual_slot(app_schema, first_page, current_images)
        insert_at = _pick_insert_index(components)
        components.insert(insert_at, image_component)
        current_images += 1
    return app_schema


def _strip_unresolved_images(app_schema: dict[str, Any]) -> int:
    removed = 0

    def prune(nodes: list[Any]) -> list[Any]:
        nonlocal removed
        kept: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict):
                kept.append(node)
                continue

            children = node.get("children", [])
            if isinstance(children, list):
                node["children"] = prune(children)

            props = node.get("props", {})
            if (
                node.get("type") == "image"
                and isinstance(props, dict)
                and _needs_generated_image(props.get("src"))
            ):
                removed += 1
                continue

            if isinstance(props, dict):
                image_prop = _get_image_prop_key(node)
                if image_prop and _needs_generated_image(props.get(image_prop)):
                    if node.get("type") == "image":
                        removed += 1
                        continue
                    label = str(
                        props.get("image_alt")
                        or props.get("alt")
                        or props.get("title")
                        or node.get("id")
                        or "Preview image"
                    )
                    props[image_prop] = _build_visual_placeholder(label)

            kept.append(node)
        return kept

    for page in app_schema.get("pages", []):
        if not isinstance(page, dict):
            continue
        components = page.get("components", [])
        if isinstance(components, list):
            page["components"] = prune(components)

    return removed


def _should_insert_visual_slot(app_schema: dict[str, Any], project_prompt: str) -> bool:
    app_type = str(app_schema.get("app_type") or "").strip().lower()
    if app_type in VISUAL_APP_TYPES:
        return True

    title = str(app_schema.get("title") or "")
    text = f"{project_prompt} {title}".lower()
    return any(keyword in text for keyword in VISUAL_PROMPT_KEYWORDS)


def _build_visual_slot(app_schema: dict[str, Any], page: dict[str, Any], index: int = 0) -> dict[str, Any]:
    page_id = str(page.get("id") or "page")
    title = str(app_schema.get("title") or "Generated App").strip() or "Generated App"
    app_type = str(app_schema.get("app_type") or "").strip().lower()
    height = "320px" if app_type in {"landing", "marketing", "showcase"} else "260px"
    label = f"{title} hero visual" if index == 0 else f"{title} supporting visual"

    return {
        "id": f"{page_id}_hero_image_{index + 1}",
        "type": "image",
        "props": {
            "alt": label,
            "title": label,
            "height": height,
        },
        "children": [],
        "actions": [],
        "style": {},
    }


def _pick_insert_index(components: list[Any]) -> int:
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            continue
        if component.get("type") in {"navbar", "heading"}:
            return index + 1
    return 0


def _collect_image_targets(app_schema: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []

    def walk(node: dict[str, Any], page_name: str, page_route: str, page_purpose: str) -> None:
        props = node.get("props", {})
        if isinstance(props, dict):
            image_prop = _get_image_prop_key(node)
            if image_prop and _needs_generated_image(props.get(image_prop)):
                label = str(
                    props.get("alt")
                    or props.get("image_alt")
                    or props.get("label")
                    or props.get("title")
                    or node.get("id")
                    or "supporting image"
                ).strip() or "supporting image"
                targets.append(
                    {
                        "page_name": page_name,
                        "page_route": page_route,
                        "page_purpose": page_purpose,
                        "component": node,
                        "prop_key": image_prop,
                        "role": _infer_component_visual_role(node, page_route, page_purpose),
                        "label": label,
                        "kind": "component",
                    }
                )

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child, page_name, page_route, page_purpose)

    for page in app_schema.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = str(page.get("name") or page.get("id") or "Page")
        page_route = str(page.get("route") or "/")
        page_purpose = str(page.get("purpose") or "")
        for component in page.get("components", []) or []:
            if isinstance(component, dict):
                walk(component, page_name, page_route, page_purpose)

    return targets


def _build_visual_asset_targets(app_schema: dict[str, Any], project_prompt: str) -> list[dict[str, Any]]:
    component_targets = _collect_image_targets(app_schema)
    targets: list[dict[str, Any]] = list(component_targets)
    seen = {
        (
            str(target.get("page_route") or "/"),
            str(target.get("role") or ""),
            str(target.get("label") or ""),
        )
        for target in component_targets
    }

    pages = [
        page
        for page in app_schema.get("pages", [])
        if isinstance(page, dict)
    ]
    if not pages:
        return targets

    def add_virtual_target(page: dict[str, Any], role: str, label: str) -> None:
        signature = (str(page.get("route") or "/"), role, label)
        if signature in seen:
            return
        seen.add(signature)
        targets.append(
            {
                "page_name": str(page.get("name") or page.get("id") or "Page"),
                "page_route": str(page.get("route") or "/"),
                "page_purpose": str(page.get("purpose") or ""),
                "component": None,
                "prop_key": None,
                "role": role,
                "label": label,
                "kind": "generated_asset",
            }
        )

    first_page = pages[0]
    title = str(app_schema.get("title") or "Generated App").strip() or "Generated App"
    add_virtual_target(first_page, "hero_visual", f"{title} hero visual")
    add_virtual_target(first_page, "ambient_background", f"{title} ambient background")

    for page in pages[1:]:
        role = _infer_page_visual_role(page, project_prompt)
        label = f"{str(page.get('name') or page.get('id') or 'Page')} {role.replace('_', ' ')}"
        add_virtual_target(page, role, label)

    limit = max(1, settings.OPENAI_IMAGE_MAX_ASSETS)
    return targets[:limit]


def _needs_generated_image(src: Any) -> bool:
    if not isinstance(src, str):
        return True

    value = src.strip()
    if not value:
        return True
    if value.startswith(PLACEHOLDER_IMAGE_PREFIX):
        return True
    if "placehold.co" in value or "placeholder" in value.lower():
        return True
    if re.fullmatch(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", value):
        return True
    return False


def _build_visual_placeholder(label: str) -> str:
    safe_label = (label or "Preview image").strip() or "Preview image"
    svg = f"""
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
  <text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">{safe_label}</text>
</svg>
""".strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"


def _get_image_prop_key(component: dict[str, Any]) -> str | None:
    component_type = component.get("type")
    if component_type == "image":
        return "src"
    if component_type in {"hero", "split-section", "auth-card"}:
        return "image_src"
    return None


def _pick_image_size(component: dict[str, Any]) -> str:
    component = component if isinstance(component, dict) else {}
    props = component.get("props", {}) if isinstance(component.get("props"), dict) else {}
    signal = " ".join(
        str(value)
        for value in (
            component.get("role"),
            component.get("label"),
            component.get("page_name"),
            component.get("page_purpose"),
            component.get("id"),
            props.get("alt"),
            props.get("image_alt"),
            props.get("label"),
            props.get("title"),
            component.get("type"),
        )
        if value
    ).lower()

    if any(token in signal for token in ("hero", "banner", "cover", "featured", "header", "background")):
        return LANDSCAPE_IMAGE_SIZE
    if any(token in signal for token in ("portrait", "avatar", "profile", "person")):
        return PORTRAIT_IMAGE_SIZE
    return DEFAULT_IMAGE_SIZE


def _build_image_prompt(
    project_prompt: str,
    app_schema: dict[str, Any],
    page_name: str,
    role: str,
    label: str,
    component: dict[str, Any] | None = None,
    page_purpose: str | None = None,
) -> str:
    component = component or {}
    props = component.get("props", {}) if isinstance(component.get("props"), dict) else {}
    purpose_label = str(label or "").strip() or str(
        props.get("alt")
        or props.get("image_alt")
        or props.get("label")
        or props.get("title")
        or component.get("id")
        or "supporting image"
    )
    theme = app_schema.get("ui_theme") or {}
    palette = ", ".join(
        str(color)
        for color in (
            theme.get("primary_color"),
            theme.get("secondary_color"),
            theme.get("background_color"),
        )
        if color
    )

    app_type = str(app_schema.get("app_type") or "app").lower()
    if app_type in {"landing", "marketing", "showcase"}:
        visual_style = "bright editorial hero illustration with premium product-marketing composition"
    elif app_type in {"dashboard", "admin", "tool", "internal"}:
        visual_style = "clean modern product illustration suitable for a SaaS dashboard"
    elif app_type in {"blog", "content", "media"}:
        visual_style = "editorial cover artwork with strong composition"
    else:
        visual_style = "clean modern illustration suitable for a web application"

    return (
        "Create one image asset for a generated web app preview.\n"
        f"Application: {app_schema.get('title', 'Generated App')}\n"
        f"Application type: {app_schema.get('app_type', 'app')}\n"
        f"Page: {page_name}\n"
        f"Page purpose: {page_purpose or 'Primary experience'}\n"
        f"Visual slot role: {role}\n"
        f"Component type: {component.get('type', 'image')}\n"
        f"Image purpose: {purpose_label}\n"
        f"Original request: {project_prompt}\n"
        f"Visual direction: {visual_style}\n"
        f"Color hints: {palette or 'soft blue and neutral white'}\n"
        "Requirements: no text, no letters, no watermarks, no logos, no UI chrome, no frames. "
        "Compose it as a polished website visual that can work as a background image, hero illustration, or supporting section artwork. "
        "Keep it visually rich, product-ready, and suitable for embedding inside a premium app or website screen."
    )


def _infer_component_visual_role(component: dict[str, Any], page_route: str, page_purpose: str) -> str:
    component_type = str(component.get("type") or "").strip().lower()
    text = f"{component_type} {page_route} {page_purpose}".lower()
    if component_type == "auth-card" or any(token in text for token in ("login", "signup", "register", "auth")):
        return "auth_illustration"
    if any(token in text for token in ("dashboard", "analytics", "workspace", "admin")):
        return "workspace_visual"
    if any(token in text for token in ("hero", "banner", "cover", "launch", "release", "marketing")):
        return "hero_visual"
    return "supporting_visual"


def _infer_page_visual_role(page: dict[str, Any], project_prompt: str) -> str:
    text = " ".join(
        str(value or "")
        for value in (
            page.get("name"),
            page.get("route"),
            page.get("purpose"),
            project_prompt,
        )
    ).lower()
    if any(token in text for token in ("login", "signin", "signup", "register", "auth", "登录", "注册")):
        return "auth_illustration"
    if any(token in text for token in ("dashboard", "analytics", "workspace", "admin", "kanban", "任务")):
        return "workspace_visual"
    if any(token in text for token in ("product", "catalog", "store", "shop", "商品", "产品")):
        return "product_showcase"
    if any(token in text for token in ("article", "blog", "story", "editorial", "内容", "博客")):
        return "editorial_cover"
    return "supporting_visual"


def _register_generated_visual_asset(app_schema: dict[str, Any], target: dict[str, Any], src: str) -> None:
    assets = app_schema.setdefault("generated_visual_assets", [])
    if not isinstance(assets, list):
        app_schema["generated_visual_assets"] = []
        assets = app_schema["generated_visual_assets"]

    route = str(target.get("page_route") or "/").strip() or "/"
    role = str(target.get("role") or "supporting_visual").strip() or "supporting_visual"
    label = str(target.get("label") or "Generated visual").strip() or "Generated visual"
    asset_id = f"{route}:{role}:{label}".replace("//", "/")
    normalized = {
        "id": asset_id,
        "route": route,
        "page_name": str(target.get("page_name") or "Page"),
        "page_purpose": str(target.get("page_purpose") or ""),
        "role": role,
        "label": label,
        "url": src,
        "source": "generated",
    }

    for index, existing in enumerate(assets):
        if not isinstance(existing, dict):
            continue
        if (
            str(existing.get("route") or "") == route
            and str(existing.get("role") or "") == role
            and str(existing.get("label") or "") == label
        ):
            assets[index] = normalized
            return
    assets.append(normalized)
