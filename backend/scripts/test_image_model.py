"""Direct smoke-test for the image API used by Nano Atoms."""

from __future__ import annotations

import argparse
import asyncio
import base64
import pathlib
import sys

import httpx

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.image_generation import _generate_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an image model endpoint directly.")
    parser.add_argument(
        "--api-key",
        default="",
        help="API key for the image request. Falls back to OPENAI_IMAGE_API_KEY / OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Image API base URL, MiniMax /v1/image_generation endpoint, or full /chat/completions endpoint. Falls back to OPENAI_IMAGE_BASE_URL / OPENAI_BASE_URL.",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Image model name. Falls back to OPENAI_IMAGE_MODEL.",
    )
    parser.add_argument(
        "--prompt",
        default="A black cat sitting in a dark studio, cinematic lighting, minimalist composition",
        help="Prompt sent to the image model.",
    )
    parser.add_argument(
        "--size",
        default="1920x1920",
        help="Image size passed to the model.",
    )
    parser.add_argument(
        "--output",
        default="output/image-smoke-test.png",
        help="Output file path when the response is a data URL.",
    )
    parser.add_argument(
        "--disable-proxy",
        action="store_true",
        help="Ignore HTTP(S)_PROXY / ALL_PROXY for this test process.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    api_key = args.api_key or settings.OPENAI_IMAGE_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        print("--api-key not provided and OPENAI_IMAGE_API_KEY / OPENAI_API_KEY are empty", file=sys.stderr)
        return 1

    base_url = args.base_url or settings.OPENAI_IMAGE_BASE_URL or settings.OPENAI_BASE_URL
    if not base_url:
        print("--base-url not provided and OPENAI_IMAGE_BASE_URL / OPENAI_BASE_URL are empty", file=sys.stderr)
        return 1

    model = args.model or settings.OPENAI_IMAGE_MODEL
    if not model:
        print("--model not provided and OPENAI_IMAGE_MODEL is empty", file=sys.stderr)
        return 1

    settings.OPENAI_IMAGE_BASE_URL = base_url
    settings.OPENAI_IMAGE_MODEL = model

    print(f"image_base_url={base_url}")
    print(f"image_model={model}")
    print(f"disable_proxy={args.disable_proxy}")

    timeout_seconds = max(30, settings.OPENAI_TIMEOUT_SECONDS)
    async with httpx.AsyncClient(
        timeout=float(timeout_seconds),
        trust_env=not args.disable_proxy,
    ) as client:
        src = await _generate_image(
            client=client,
            api_key=api_key,
            prompt=args.prompt,
            size=args.size,
        )

    if src.startswith("data:image/"):
        header, encoded = src.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        output_path = pathlib.Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        print(f"ok:data-url -> {output_path.resolve()}")
        print(f"mime={header.split(';', 1)[0]}")
        return 0

    print(f"ok:url -> {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
