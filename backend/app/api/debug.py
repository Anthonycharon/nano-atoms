from __future__ import annotations

from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.schemas.debug import EmailTestRequest, EmailTestResponse, ImageTestRequest, ImageTestResponse
from app.services.email_verification_service import send_test_email
from app.services.image_generation import generate_image_preview

router = APIRouter(tags=["debug"])


def _resolve_image_config(body: ImageTestRequest) -> tuple[str, str, str]:
    api_key = (body.api_key or settings.OPENAI_IMAGE_API_KEY or settings.OPENAI_API_KEY or "").strip()
    base_url = (body.base_url or settings.OPENAI_IMAGE_BASE_URL or settings.OPENAI_BASE_URL or "").strip()
    model = (body.model or settings.OPENAI_IMAGE_MODEL or "").strip()

    if not api_key:
        raise HTTPException(status_code=400, detail="缺少 api_key，且后端当前也没有配置生图 key")
    if not base_url:
        raise HTTPException(status_code=400, detail="缺少 base_url，且后端当前也没有配置生图地址")
    if not model:
        raise HTTPException(status_code=400, detail="缺少 model，且后端当前也没有配置生图模型")

    return api_key, base_url, model


@router.post("/api/debug/image-test", response_model=ImageTestResponse)
async def image_test(body: ImageTestRequest):
    api_key, base_url, model = _resolve_image_config(body)

    try:
        image_src = await generate_image_preview(
            api_key=api_key,
            base_url=base_url,
            model=model,
            prompt=body.prompt,
            size=body.size,
            disable_proxy=body.disable_proxy,
        )
    except Exception as exc:
        return ImageTestResponse(
            ok=False,
            base_url=base_url,
            model=model,
            prompt=body.prompt,
            disable_proxy=body.disable_proxy,
            error=str(exc),
        )

    return ImageTestResponse(
        ok=True,
        image_src=image_src,
        source="data-url" if image_src.startswith("data:image/") else "url",
        base_url=base_url,
        model=model,
        prompt=body.prompt,
        disable_proxy=body.disable_proxy,
    )


@router.get("/debug/image-test", response_class=HTMLResponse)
def image_test_page():
    default_base_url = escape(settings.OPENAI_IMAGE_BASE_URL or settings.OPENAI_BASE_URL or "")
    default_model = escape(settings.OPENAI_IMAGE_MODEL or "")
    default_prompt = escape("一只黑猫，深色背景，电影感光影，极简构图")
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>生图接口测试</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #020617;
        --panel: rgba(15, 23, 42, 0.92);
        --line: rgba(148, 163, 184, 0.22);
        --text: #e2e8f0;
        --muted: #94a3b8;
        --accent: #38bdf8;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top, rgba(14, 165, 233, 0.18), transparent 30%),
          linear-gradient(180deg, #020617 0%, #0f172a 100%);
        color: var(--text);
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }}
      .wrap {{
        width: min(1100px, calc(100vw - 32px));
        margin: 32px auto;
        display: grid;
        gap: 20px;
        grid-template-columns: minmax(360px, 420px) minmax(0, 1fr);
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 24px 80px rgba(2, 6, 23, 0.4);
      }}
      h1 {{ margin: 0 0 8px; font-size: 28px; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.7; }}
      .fields {{ display: grid; gap: 14px; margin-top: 18px; }}
      label {{ display: grid; gap: 8px; font-size: 14px; }}
      input, textarea {{
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(15, 23, 42, 0.7);
        color: var(--text);
        padding: 12px 14px;
        font: inherit;
      }}
      textarea {{ min-height: 110px; resize: vertical; }}
      .row {{ display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }}
      .checkbox {{ display: flex; align-items: center; gap: 10px; margin-top: 4px; }}
      .checkbox input {{ width: auto; }}
      button {{
        margin-top: 6px;
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        background: linear-gradient(135deg, #0ea5e9, #38bdf8);
        color: #00111f;
        font-weight: 700;
        cursor: pointer;
      }}
      .status {{
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(15, 23, 42, 0.7);
        color: var(--muted);
        white-space: pre-wrap;
      }}
      .status.ok {{ color: #86efac; border-color: rgba(34, 197, 94, 0.35); }}
      .status.error {{ color: #fca5a5; border-color: rgba(239, 68, 68, 0.35); }}
      .preview {{
        display: grid;
        place-items: center;
        min-height: 520px;
        overflow: hidden;
      }}
      .preview img {{
        max-width: 100%;
        max-height: 72vh;
        border-radius: 20px;
        border: 1px solid var(--line);
        box-shadow: 0 20px 60px rgba(2, 6, 23, 0.45);
      }}
      .placeholder {{
        text-align: center;
        color: var(--muted);
        line-height: 1.8;
      }}
      code {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        color: #7dd3fc;
      }}
      @media (max-width: 960px) {{
        .wrap {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <section class="panel">
        <h1>生图接口测试</h1>
        <p>直接在浏览器里测试当前生图模型。参数留空时，会优先使用后端当前配置。</p>
        <div class="fields">
          <label>
            API Key
            <input id="apiKey" type="password" placeholder="留空则用后端当前配置" />
          </label>
          <label>
            Base URL
            <input id="baseUrl" type="text" value="{default_base_url}" placeholder="例如 https://api.minimaxi.com/v1/image_generation" />
          </label>
          <div class="row">
            <label>
              Model
              <input id="model" type="text" value="{default_model}" placeholder="例如 nanobanana-2pro" />
            </label>
            <label>
              Size
              <input id="size" type="text" value="1920x1920" />
            </label>
          </div>
          <label>
            Prompt
            <textarea id="prompt">{default_prompt}</textarea>
          </label>
          <label class="checkbox">
            <input id="disableProxy" type="checkbox" />
            <span>本次测试禁用代理环境变量</span>
          </label>
          <button id="submitBtn" type="button">开始测试</button>
        </div>
        <div id="statusBox" class="status">等待测试</div>
      </section>

      <section class="panel preview">
        <div id="previewBox" class="placeholder">
          这里会显示生成结果。<br />
          也可以直接调用 <code>POST /api/debug/image-test</code>。
        </div>
      </section>
    </div>

    <script>
      const submitBtn = document.getElementById("submitBtn");
      const statusBox = document.getElementById("statusBox");
      const previewBox = document.getElementById("previewBox");

      submitBtn.addEventListener("click", async () => {{
        submitBtn.disabled = true;
        statusBox.className = "status";
        statusBox.textContent = "请求中...";
        previewBox.innerHTML = '<div class="placeholder">正在请求生图接口，请稍候...</div>';

        const payload = {{
          api_key: document.getElementById("apiKey").value.trim() || null,
          base_url: document.getElementById("baseUrl").value.trim() || null,
          model: document.getElementById("model").value.trim() || null,
          prompt: document.getElementById("prompt").value.trim(),
          size: document.getElementById("size").value.trim() || "1920x1920",
          disable_proxy: document.getElementById("disableProxy").checked,
        }};

        try {{
          const response = await fetch("/api/debug/image-test", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(payload),
          }});
          const data = await response.json();
          if (!response.ok || !data.ok) {{
            throw new Error(data.detail || data.error || "请求失败");
          }}

          statusBox.className = "status ok";
          statusBox.textContent =
            "测试成功\\n" +
            "model=" + data.model + "\\n" +
            "base_url=" + data.base_url + "\\n" +
            "source=" + data.source;

          const img = document.createElement("img");
          img.src = data.image_src;
          img.alt = "generated image";
          previewBox.innerHTML = "";
          previewBox.appendChild(img);
        }} catch (error) {{
          statusBox.className = "status error";
          statusBox.textContent = "测试失败\\n" + (error?.message || String(error));
          previewBox.innerHTML = '<div class="placeholder">没有拿到图片结果。请检查 key、base url、model 和代理设置。</div>';
        }} finally {{
          submitBtn.disabled = false;
        }}
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(html)


@router.post("/api/debug/email-test", response_model=EmailTestResponse)
def email_test(body: EmailTestRequest):
    try:
        result = send_test_email(body.to_email)
    except HTTPException as exc:
        return EmailTestResponse(ok=False, error=str(exc.detail))
    except Exception as exc:
        return EmailTestResponse(ok=False, error=str(exc))
    return EmailTestResponse(ok=True, message=result["message"])


@router.get("/debug/email-test", response_class=HTMLResponse)
def email_test_page():
    default_recipient = escape(settings.SMTP_FROM_EMAIL or "")
    html = f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>邮件测试</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #020617;
        --panel: rgba(15, 23, 42, 0.92);
        --line: rgba(148, 163, 184, 0.22);
        --text: #e2e8f0;
        --muted: #94a3b8;
        --accent: #38bdf8;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top, rgba(14, 165, 233, 0.18), transparent 30%),
          linear-gradient(180deg, #020617 0%, #0f172a 100%);
        color: var(--text);
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      }}
      .wrap {{
        width: min(720px, calc(100vw - 32px));
        margin: 48px auto;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 24px 80px rgba(2, 6, 23, 0.4);
      }}
      h1 {{ margin: 0 0 8px; font-size: 28px; }}
      p {{ margin: 0; color: var(--muted); line-height: 1.7; }}
      label {{ display: grid; gap: 8px; margin-top: 18px; font-size: 14px; }}
      input {{
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: rgba(15, 23, 42, 0.7);
        color: var(--text);
        padding: 12px 14px;
        font: inherit;
      }}
      button {{
        margin-top: 18px;
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        background: linear-gradient(135deg, #0ea5e9, #38bdf8);
        color: #00111f;
        font-weight: 700;
        cursor: pointer;
      }}
      .status {{
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(15, 23, 42, 0.7);
        color: var(--muted);
        white-space: pre-wrap;
      }}
      .status.ok {{ color: #86efac; border-color: rgba(34, 197, 94, 0.35); }}
      .status.error {{ color: #fca5a5; border-color: rgba(239, 68, 68, 0.35); }}
      code {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        color: #7dd3fc;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <section class="panel">
        <h1>SMTP 邮件测试</h1>
        <p>用于验证当前 QQ 邮箱 SMTP 配置是否可用。成功后会向目标邮箱发送一封测试邮件。</p>
        <label>
          收件邮箱
          <input id="toEmail" type="email" value="{default_recipient}" placeholder="请输入要接收测试邮件的邮箱" />
        </label>
        <button id="submitBtn" type="button">发送测试邮件</button>
        <div id="statusBox" class="status">等待测试</div>
        <p style="margin-top:16px">接口：<code>POST /api/debug/email-test</code></p>
      </section>
    </div>
    <script>
      const submitBtn = document.getElementById("submitBtn");
      const statusBox = document.getElementById("statusBox");

      submitBtn.addEventListener("click", async () => {{
        submitBtn.disabled = true;
        statusBox.className = "status";
        statusBox.textContent = "请求中...";
        try {{
          const response = await fetch("/api/debug/email-test", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              to_email: document.getElementById("toEmail").value.trim(),
            }}),
          }});
          const data = await response.json();
          if (!response.ok || !data.ok) {{
            throw new Error(data.detail || data.error || "请求失败");
          }}
          statusBox.className = "status ok";
          statusBox.textContent = data.message || "测试邮件发送成功";
        }} catch (error) {{
          statusBox.className = "status error";
          statusBox.textContent = "测试失败\\n" + (error?.message || String(error));
        }} finally {{
          submitBtn.disabled = false;
        }}
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(html)
