"""R07 authorized byte attachment: no temporary/local filename on the web path."""
from unittest.mock import Mock

import pytest


PDF = b"%PDF-1.7\nsynthetic-authorized-plan\n%%EOF"


def test_authorized_pdf_bytes_precede_legacy_path_and_never_open_files(monkeypatch):
    from web.services import email_service

    send = Mock(return_value=True)
    path = Mock(side_effect=AssertionError("The byte attachment must not open a path"))
    monkeypatch.setattr(email_service, "_send", send)
    monkeypatch.setattr(email_service, "Path", path)
    assert email_service.send_plan_generated("synthetic@example.invalid", "Synthetic Client",
                                           "legacy-private-path.pdf", pdf_content=PDF)
    path.assert_not_called()
    assert send.call_args.kwargs["attachments"] == [{"filename": "plan.pdf", "content": list(PDF)}]


@pytest.mark.parametrize("payload", [b"", b"not a PDF", "%PDF-string", bytearray(PDF), PDF * 5])
def test_invalid_or_oversized_byte_attachment_never_sends_or_falls_back(payload, monkeypatch):
    from web.services import email_service

    send = Mock()
    path = Mock(side_effect=AssertionError("Invalid bytes cannot select a legacy path"))
    monkeypatch.setattr(email_service, "_send", send)
    monkeypatch.setattr(email_service, "Path", path)
    monkeypatch.setattr(email_service, "MAX_OBJECT_BYTES", len(PDF), raising=False)
    assert email_service.send_plan_generated("synthetic@example.invalid", "Synthetic Client",
                                           "legacy-private-path.pdf", pdf_content=payload) is False
    path.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize("source", ["bytes", "legacy"])
def test_plan_name_is_html_escaped_and_subject_cannot_inject_headers(source, monkeypatch):
    from web.services import email_service

    send = Mock(return_value=True)
    monkeypatch.setattr(email_service, "_send", send)
    name = '<img src=x onerror="synthetic()">\r\nBcc: synthetic@example.invalid'
    kwargs = {"pdf_content": PDF} if source == "bytes" else {}
    assert email_service.send_plan_generated("synthetic@example.invalid", name, **kwargs)
    _, subject, html = send.call_args.args
    assert "<img" not in html and "&lt;img" in html
    assert "\r" not in subject and "\n" not in subject


def test_legacy_path_and_optional_attachment_remain_compatible(tmp_path, monkeypatch):
    from web.services import email_service

    send = Mock(return_value=True)
    monkeypatch.setattr(email_service, "_send", send)
    legacy = tmp_path / "legacy.pdf"
    legacy.write_bytes(PDF)
    assert email_service.send_plan_generated("synthetic@example.invalid", "Synthetic", str(legacy))
    assert send.call_args.kwargs["attachments"] == [{"filename": "legacy.pdf", "content": list(PDF)}]
    assert email_service.send_plan_generated("synthetic@example.invalid", "Synthetic")
    assert send.call_args.kwargs["attachments"] is None
