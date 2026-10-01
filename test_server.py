"""Mocked tests for the server-side Gemini request boundary."""

import base64
import http.client
import io
import json
import os
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError

import server


class FakeGeminiResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


class GeminiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.PrototypeHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def post(self, payload, origin=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = json.dumps(payload).encode("utf-8")
        connection.request(
            "POST",
            "/api/generate",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Origin": origin or f"http://127.0.0.1:{self.port}",
            },
        )
        response = connection.getresponse()
        result = response.status, json.loads(response.read().decode("utf-8"))
        connection.close()
        return result

    def test_missing_key_returns_safe_configuration_error_without_calling_google(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), patch(
            "server.urlopen", side_effect=AssertionError("provider must not be called")
        ):
            status, data = self.post({"consent": True, "input": "hello"})
        self.assertEqual(status, 503)
        self.assertEqual(data["error"]["code"], "not_configured")

    def test_endpoint_rejects_missing_consent_and_cross_origin_requests(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", side_effect=AssertionError("provider must not be called")
        ):
            status, data = self.post({"input": "private notes"})
            self.assertEqual(status, 403)
            self.assertEqual(data["error"]["code"], "consent_required")
            status, data = self.post(
                {"consent": True, "input": "private notes"},
                origin="https://unrelated.example",
            )
            self.assertEqual(status, 403)
            self.assertEqual(data["error"]["code"], "origin_rejected")

    def test_text_and_json_image_responses_are_normalized(self):
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
        mock = FakeGeminiResponse(
            {"candidates": [{"content": {"parts": [{"text": '{"topics": ["Math"]}'}]}}]}
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", return_value=mock
        ) as call:
            status, data = self.post(
                {
                    "consent": True,
                    "json": True,
                    "input": [
                        {"role": "system", "content": "Read the page."},
                        {"role": "user", "content": "What is shown?"},
                        {"role": "assistant", "content": "It appears to be a lesson page."},
                        {"role": "user", "content": "Extract its topic."},
                    ],
                    "images": [{"mimeType": "image/png", "data": png}],
                }
            )
        self.assertEqual(status, 200)
        self.assertEqual(data["text"], '{"topics": ["Math"]}')
        self.assertEqual(data["json"], {"topics": ["Math"]})
        self.assertTrue(data["jsonValid"])
        request = call.call_args.args[0]
        self.assertNotIn("test-only-key", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "test-only-key")
        provider_payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(provider_payload["systemInstruction"]["parts"][0]["text"], "Read the page.")
        self.assertEqual(
            provider_payload["contents"][-1]["parts"][-1]["inline_data"]["mime_type"],
            "image/png",
        )
        self.assertEqual(
            [item["role"] for item in provider_payload["contents"]],
            ["user", "model", "user"],
        )
        self.assertEqual(
            provider_payload["generationConfig"]["responseMimeType"],
            "application/json",
        )

    def test_text_response_is_returned_without_json_mode(self):
        mock = FakeGeminiResponse(
            {"candidates": [{"content": {"parts": [{"text": "A short tutor answer."}]}}]}
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", return_value=mock
        ):
            status, data = self.post({"consent": True, "input": "Explain this."})
        self.assertEqual(status, 200)
        self.assertEqual(data, {"text": "A short tutor answer."})

    def test_rate_limit_and_provider_errors_are_normalized_without_upstream_details(self):
        private_detail = b"secret-like-provider-diagnostic"
        rate_error = HTTPError(
            server.GEMINI_URL, 429, "limited", {}, io.BytesIO(private_detail)
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", side_effect=rate_error
        ):
            status, data = self.post({"consent": True, "input": "Try this."})
        self.assertEqual(status, 429)
        self.assertEqual(data["error"]["code"], "rate_limited")
        self.assertNotIn(private_detail.decode(), json.dumps(data))
        self.assertNotIn("test-only-key", json.dumps(data))

        provider_error = HTTPError(
            server.GEMINI_URL, 503, "unavailable", {}, io.BytesIO(private_detail)
        )
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", side_effect=provider_error
        ):
            status, data = self.post({"consent": True, "input": "Try again."})
        self.assertEqual(status, 502)
        self.assertEqual(data["error"]["code"], "provider_error")
        self.assertNotIn(private_detail.decode(), json.dumps(data))
        self.assertNotIn("test-only-key", json.dumps(data))

    def test_bad_image_data_is_rejected_before_provider_call(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}), patch(
            "server.urlopen", side_effect=AssertionError("provider must not be called")
        ):
            status, data = self.post(
                {
                    "consent": True,
                    "input": "Describe this.",
                    "images": [{"mimeType": "image/gif", "data": "not-an-image"}],
                }
            )
        self.assertEqual(status, 400)
        self.assertEqual(data["error"]["code"], "invalid_images")


if __name__ == "__main__":
    unittest.main()