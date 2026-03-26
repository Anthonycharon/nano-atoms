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
    targets = _collect_image_targets(schema)

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
                        component=target["component"],
                    )
                    size = _pick_image_size(target["component"])
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
            target["component"]["props"][target["prop_key"]] = src
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
    if not base_url:
        raise ValueError("image API base URL is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    prefers_chat_completions = base_url.endswith("/chat/completions")

    if prefers_chat_completions:
        return await _generate_image_via_chat(
            client=client,
            endpoint=base_url,
            headers=headers,
            prompt=prompt,
        )

    image_error: Exception | None = None
    try:
        return await _generate_image_via_images_api(
            client=client,
            endpoint=f"{base_url}/images/generations",
            headers=headers,
            prompt=prompt,
            size=size,
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
) -> str:
    base_payload = {
        "model": settings.OPENAI_IMAGE_MODEL,
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


async def _generate_image_via_chat(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict[str, str],
    prompt: str,
) -> str:
    payload = {
        "model": settings.OPENAI_IMAGE_MODEL,
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
    item = (payload.get("data") or [{}])[0]
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
    raise ValueError("image API returned no renderable asset")


def _is_missing_images_endpoint(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {404, 405}
    return False


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
    if not _should_insert_visual_slot(app_schema, project_prompt):
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

    image_component = _build_visual_slot(app_schema, first_page)
    insert_at = _pick_insert_index(components)
    components.insert(insert_at, image_component)
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


def _build_visual_slot(app_schema: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    page_id = str(page.get("id") or "page")
    title = str(app_schema.get("title") or "Generated App").strip() or "Generated App"
    app_type = str(app_schema.get("app_type") or "").strip().lower()
    height = "320px" if app_type in {"landing", "marketing", "showcase"} else "260px"
    label = f"{title} hero visual"

    return {
        "id": f"{page_id}_hero_image",
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

    def walk(node: dict[str, Any], page_name: str) -> None:
        props = node.get("props", {})
        if isinstance(props, dict):
            image_prop = _get_image_prop_key(node)
            if image_prop and _needs_generated_image(props.get(image_prop)):
                targets.append(
                    {
                        "page_name": page_name,
                        "component": node,
                        "prop_key": image_prop,
                    }
                )

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child, page_name)

    for page in app_schema.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = str(page.get("name") or page.get("id") or "Page")
        for component in page.get("components", []) or []:
            if isinstance(component, dict):
                walk(component, page_name)

    return targets


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
    props = component.get("props", {})
    signal = " ".join(
        str(value)
        for value in (
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
        return "1536x1024"
    if any(token in signal for token in ("portrait", "avatar", "profile", "person")):
        return "1024x1536"
    return "1024x1024"


def _build_image_prompt(
    project_prompt: str,
    app_schema: dict[str, Any],
    page_name: str,
    component: dict[str, Any],
) -> str:
    props = component.get("props", {})
    label = str(
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
        f"Component type: {component.get('type', 'image')}\n"
        f"Image purpose: {label}\n"
        f"Original request: {project_prompt}\n"
        f"Visual direction: {visual_style}\n"
        f"Color hints: {palette or 'soft blue and neutral white'}\n"
        "Requirements: no text, no letters, no watermarks, no logos, no UI chrome, no frames. "
        "Keep it bright, product-ready, and suitable for embedding inside a polished app screen."
    )
