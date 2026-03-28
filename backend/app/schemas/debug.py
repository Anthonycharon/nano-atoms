from pydantic import BaseModel


class ImageTestRequest(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    prompt: str
    size: str = "1920x1920"
    disable_proxy: bool = False


class ImageTestResponse(BaseModel):
    ok: bool
    image_src: str | None = None
    source: str | None = None
    base_url: str
    model: str
    prompt: str
    disable_proxy: bool
    error: str | None = None


class EmailTestRequest(BaseModel):
    to_email: str


class EmailTestResponse(BaseModel):
    ok: bool
    message: str | None = None
    error: str | None = None
