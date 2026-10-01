"""Serve FocusMate and proxy approved AI requests to Google's Gemini API."""

import base64
import binascii
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


INDEX = Path(__file__).with_name("index.html")
GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
MAX_REQUEST_BYTES = 28 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGES = 4
MAX_MESSAGES = 12
MAX_MESSAGE_CHARS = 20_000
MAX_TOTAL_CHARS = 80_000
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ApiProblem(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def build_gemini_payload(body):
    """Validate the small app-specific request shape and make Gemini contents."""
    if not isinstance(body, dict):
        raise ApiProblem(400, "invalid_request", "The AI request was not valid.")
    if body.get("consent") is not True:
        raise ApiProblem(403, "consent_required", "Student consent is required.")

    raw_input = body.get("input")
    if isinstance(raw_input, str):
        messages = [{"role": "user", "content": raw_input}]
    elif isinstance(raw_input, list) and 0 < len(raw_input) <= MAX_MESSAGES:
        messages = raw_input
    else:
        raise ApiProblem(400, "invalid_request", "The AI request was not valid.")

    system_text = []
    contents = []
    total_chars = 0
    for message in messages:
        if not isinstance(message, dict):
            raise ApiProblem(400, "invalid_request", "The AI request was not valid.")
        role = message.get("role")
        text = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(text, str):
            raise ApiProblem(400, "invalid_request", "The AI request was not valid.")
        if len(text) > MAX_MESSAGE_CHARS:
            raise ApiProblem(413, "request_too_large", "The AI request is too long.")
        total_chars += len(text)
        if total_chars > MAX_TOTAL_CHARS:
            raise ApiProblem(413, "request_too_large", "The AI request is too long.")
        if role == "system":
            system_text.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"].append({"text": text})
        else:
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

    if not contents or not any(item["role"] == "user" for item in contents):
        raise ApiProblem(400, "invalid_request", "The AI request was not valid.")

    images = body.get("images", [])
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise ApiProblem(400, "invalid_images", "Too many images were attached.")
    total_image_bytes = 0
    for image in images:
        if not isinstance(image, dict):
            raise ApiProblem(400, "invalid_images", "An attached image was not valid.")
        mime_type = image.get("mimeType")
        encoded = image.get("data")
        if mime_type not in IMAGE_TYPES or not isinstance(encoded, str):
            raise ApiProblem(400, "invalid_images", "Use a JPG, PNG, or WebP image.")
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise ApiProblem(400, "invalid_images", "An attached image was not valid.")
        if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
            raise ApiProblem(413, "request_too_large", "An attached image is too large.")
        total_image_bytes += len(image_bytes)
        if total_image_bytes > MAX_TOTAL_IMAGE_BYTES:
            raise ApiProblem(413, "request_too_large", "The attached images are too large.")
        contents[-1]["parts"].append(
            {"inline_data": {"mime_type": mime_type, "data": encoded}}
        )

    payload = {"contents": contents}
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_text)}]}
    if body.get("json") is True:
        payload["generationConfig"] = {
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096,
        }
    else:
        payload["generationConfig"] = {"maxOutputTokens": 4096}
    return payload


def generate_with_gemini(body, api_key=None):
    """Call Gemini without allowing provider details or credentials to escape."""
    payload = build_gemini_payload(body)
    key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ApiProblem(
            503,
            "not_configured",
            "Gemini is not configured on this app. Built-in samples are still available.",
        )
    request = Request(
        GEMINI_URL,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=75) as response:
            provider_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 429:
            raise ApiProblem(
                429,
                "rate_limited",
                "Gemini's current rate limit was reached. Try again later.",
            )
        if error.code in (400, 403):
            raise ApiProblem(
                502,
                "provider_error",
                "Gemini could not process this request. Check the key and try again.",
            )
        raise ApiProblem(
            502,
            "provider_error",
            "Gemini is temporarily unavailable. Try again later.",
        )
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ApiProblem(
            502,
            "provider_error",
            "Gemini is temporarily unavailable. Try again later.",
        )

    candidates = provider_data.get("candidates") if isinstance(provider_data, dict) else None
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        raise ApiProblem(
            502,
            "refused",
            "Gemini could not answer that request. Try asking differently.",
        )
    content = candidates[0].get("content")
    parts = content.get("parts", []) if isinstance(content, dict) else []
    if not isinstance(parts, list):
        parts = []
    text = "\n".join(part["text"] for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str)).strip()
    if not text:
        raise ApiProblem(
            502,
            "refused",
            "Gemini could not answer that request. Try asking differently.",
        )

    result = {"text": text}
    if body.get("json") is True:
        try:
            result["json"] = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            result["jsonValid"] = False
        else:
            result["jsonValid"] = True
    return result


class PrototypeHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            # A browser may cancel while the upstream request is still running.
            pass

    def do_GET(self):
        self.serve_page()

    def do_HEAD(self):
        self.serve_page(head_only=True)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/generate":
            self.send_error(404)
            return
        origin = urlsplit(self.headers.get("Origin", ""))
        allowed_hosts = {
            self.headers.get("Host", "").lower(),
            self.headers.get("X-Forwarded-Host", "").split(",", 1)[0].strip().lower(),
        }
        if origin.scheme not in {"http", "https"} or origin.netloc.lower() not in allowed_hosts:
            self._send_json(403, {"error": {"code": "origin_rejected", "message": "Use the FocusMate app to make AI requests."}})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send_json(415, {"error": {"code": "invalid_request", "message": "Send a JSON request."}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": {"code": "request_too_large", "message": "The AI request is too large."}})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            result = generate_with_gemini(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": {"code": "invalid_request", "message": "Send a valid JSON request."}})
            return
        except ApiProblem as error:
            self._send_json(error.status, {"error": {"code": error.code, "message": error.message}})
            return
        self._send_json(200, result)

    def serve_page(self, head_only=False):
        path = urlsplit(self.path).path
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = INDEX.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(page)

    def log_message(self, format_string, *args):
        # Do not log request bodies, upstream details, or credential-bearing data.
        super().log_message(format_string, *args)


if __name__ == "__main__":
    port = int(os.environ.get("FOCUSMATE_INTERNAL_PORT", "5001"))
    print(f"FocusMate AI service running on internal port {port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), PrototypeHandler).serve_forever()