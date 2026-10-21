"""Literal-template ARIA contract only; no assistive-technology claim."""
from html.parser import HTMLParser
from pathlib import Path


class Nodes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.clock = []
        self.status = []

    def handle_starttag(self, tag, attrs):
        value = dict(attrs)
        if "data-routine-clock" in value:
            self.clock.append((tag, value))
        if "data-routine-timer-status" in value:
            self.status.append(value)


def parsed():
    parser = Nodes()
    parser.feed((Path(__file__).resolve().parents[1] / "web/templates/rutinas_shared.html").read_text(encoding="utf8"))
    return parser


def test_changing_clock_has_timer_semantics_without_automatic_live_announcements():
    parser = parsed()
    assert len(parser.clock) == 1
    tag, attrs = parser.clock[0]
    assert tag == "output"
    assert attrs.get("role") == "timer"
    assert attrs.get("aria-live") == "off"
    assert attrs.get("aria-label")


def test_explicit_timer_state_messages_remain_polite():
    parser = parsed()
    assert len(parser.status) == 1
    assert parser.status[0].get("role") == "status"
    assert parser.status[0].get("aria-live") == "polite"
