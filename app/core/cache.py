from collections.abc import Callable
from hashlib import sha256
from typing import Any

from fastapi import Request, Response


def merchant_cache_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,
    *args: Any,
    **kwargs: Any,
) -> str:
    del response, args

    merchant_id = "anonymous"
    if "merchant_id" in kwargs:
        merchant_id = str(kwargs["merchant_id"])
    elif request is not None:
        api_key = request.headers.get("x-api-key", "")
        merchant_id = api_key.split(":", maxsplit=1)[0] if api_key else merchant_id

    path = request.url.path if request is not None else func.__name__
    query = request.url.query if request is not None else ""
    raw_key = f"{namespace}:{path}:{query}:{merchant_id}"
    return sha256(raw_key.encode()).hexdigest()
