import base64


DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
_CURSOR_PREFIX = b"v1\x00"


def encode_cursor(filename: str) -> str:
    """Encode the last logical filename into an opaque, URL-safe cursor."""
    payload = _CURSOR_PREFIX + filename.encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> str:
    """Decode and validate a pagination cursor."""
    try:
        padding = "=" * (-len(cursor) % 4)
        payload = base64.b64decode(
            cursor + padding,
            altchars=b"-_",
            validate=True,
        )
        if not payload.startswith(_CURSOR_PREFIX):
            raise ValueError("Unsupported cursor version")
        filename = payload[len(_CURSOR_PREFIX) :].decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid pagination cursor") from exc

    if not filename:
        raise ValueError("Invalid pagination cursor")
    return filename
