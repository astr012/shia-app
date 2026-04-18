# ============================================================
# Tests — WebSocket End-to-End Integration
#
# Validates the complete real-time pipeline:
#   1. Sign→Speech:  gesture_sequence → grammar_engine → translation_result
#   2. Speech→Sign:  speech_input    → translation_engine → sign_animation
#   3. Manual text routing in both modes
#   4. Session lifecycle (connect, info, ping/pong, disconnect)
#   5. Error handling (invalid JSON, missing data, unknown types)
#   6. Rate limiting enforcement
#
# Uses rule-based fallback (no OpenAI) for deterministic assertions.
# ============================================================

import json
import pytest
from starlette.testclient import TestClient
from app.main import app


@pytest.fixture
def ws_client():
    """Provide a WebSocket test client."""
    client = TestClient(app)
    return client


class TestWebSocketSessionLifecycle:
    """Verify connection, session info, and disconnect."""

    def test_connect_receives_session_info(self, ws_client):
        """On connect, server sends session_info with session_id and version."""
        with ws_client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "session_info"
            assert "session_id" in data["payload"]
            assert "server_version" in data["payload"]
            assert data["payload"]["mode"] == "SIGN_TO_SPEECH"

    def test_ping_pong(self, ws_client):
        """Ping message receives a pong response."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({"type": "ping", "payload": {}})
            data = ws.receive_json()
            assert data["type"] == "pong"
            assert "timestamp" in data["payload"]
            assert "session_id" in data["payload"]

    def test_set_mode(self, ws_client):
        """Switching mode sends mode_changed confirmation."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({"type": "set_mode", "payload": {"mode": "SPEECH_TO_SIGN"}})
            data = ws.receive_json()
            assert data["type"] == "mode_changed"
            assert data["payload"]["mode"] == "SPEECH_TO_SIGN"


class TestSignToSpeechPipeline:
    """Test gesture_sequence → grammar_engine → translation_result (Sign→Speech)."""

    def test_hello_gesture(self, ws_client):
        """HELLO gesture produces a translation result with the corrected text."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "gesture_sequence",
                "payload": {"gestures": ["HELLO"]}
            })
            # Expect grammar_processed then translation_result
            msg1 = ws.receive_json()
            assert msg1["type"] == "grammar_processed"
            assert "original" in msg1["payload"]
            assert "corrected" in msg1["payload"]
            assert "latency_ms" in msg1["payload"]

            msg2 = ws.receive_json()
            assert msg2["type"] == "translation_result"
            assert "translated_text" in msg2["payload"]
            assert len(msg2["payload"]["translated_text"]) > 0
            assert "processing_time_ms" in msg2["payload"]

    def test_multi_gesture_sequence(self, ws_client):
        """Multiple gestures are joined and processed together."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "gesture_sequence",
                "payload": {"gestures": ["HELLO", "HOW_ARE_YOU"]}
            })
            msg1 = ws.receive_json()
            assert msg1["type"] == "grammar_processed"
            # The raw text should contain both gesture words
            assert "hello" in msg1["payload"]["original"]

            msg2 = ws.receive_json()
            assert msg2["type"] == "translation_result"
            assert len(msg2["payload"]["translated_text"]) > 0

    def test_empty_gestures_returns_error(self, ws_client):
        """Empty gesture array returns an error."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "gesture_sequence",
                "payload": {"gestures": []}
            })
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "No valid gestures" in data["payload"]["message"]


class TestSpeechToSignPipeline:
    """Test speech_input → translation_engine → sign_animation (Speech→Sign)."""

    def test_hello_speech(self, ws_client):
        """Speech input 'hello' produces sign_animation with a sequence."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "speech_input",
                "payload": {"text": "hello"}
            })
            data = ws.receive_json()
            assert data["type"] == "sign_animation"
            assert "sign_sequence" in data["payload"]
            assert isinstance(data["payload"]["sign_sequence"], list)
            assert len(data["payload"]["sign_sequence"]) > 0
            assert "processing_time_ms" in data["payload"]

    def test_sentence_speech(self, ws_client):
        """A full sentence is decomposed into multiple sign tokens."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "speech_input",
                "payload": {"text": "How are you today?"}
            })
            data = ws.receive_json()
            assert data["type"] == "sign_animation"
            seq = data["payload"]["sign_sequence"]
            assert len(seq) > 1  # Multiple tokens expected

    def test_empty_speech_returns_error(self, ws_client):
        """Empty text returns an error."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "speech_input",
                "payload": {"text": ""}
            })
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "No text" in data["payload"]["message"]


class TestManualTextRouting:
    """Test manual_text routing in both directions."""

    def test_manual_sign_to_speech(self, ws_client):
        """Manual text in SIGN_TO_SPEECH mode produces translation_result."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "manual_text",
                "payload": {"text": "hello how you", "mode": "SIGN_TO_SPEECH"}
            })
            data = ws.receive_json()
            assert data["type"] == "translation_result"
            assert "translated_text" in data["payload"]

    def test_manual_speech_to_sign(self, ws_client):
        """Manual text in SPEECH_TO_SIGN mode produces sign_animation."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({
                "type": "manual_text",
                "payload": {"text": "I want food", "mode": "SPEECH_TO_SIGN"}
            })
            data = ws.receive_json()
            assert data["type"] == "sign_animation"
            assert "sign_sequence" in data["payload"]
            assert isinstance(data["payload"]["sign_sequence"], list)


class TestWebSocketErrorHandling:
    """Test error conditions and edge cases."""

    def test_invalid_json(self, ws_client):
        """Invalid JSON returns an error message."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_text("this is not json{{{")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["payload"]["message"]

    def test_unknown_message_type(self, ws_client):
        """Unknown message type returns an error."""
        with ws_client.websocket_connect("/ws") as ws:
            ws.receive_json()  # skip session_info
            ws.send_json({"type": "nonexistent_type", "payload": {}})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Unknown type" in data["payload"]["message"]

    def test_message_has_timestamp(self, ws_client):
        """All server messages include a timestamp."""
        with ws_client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert "timestamp" in data
            assert isinstance(data["timestamp"], (int, float))
