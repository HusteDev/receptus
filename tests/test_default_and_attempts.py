# tests/test_default_and_attempts.py
from io import StringIO
from receptus import Receptus

def test_enter_uses_current_value(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    monkeypatch.setattr("builtins.input", lambda _ : "")
    res = r.get_input(options={"a":"Alpha"}, current_value="a", confirm=False)
    assert res == "a"

def test_no_input_no_default_attempts_exhausted(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    seq = iter([""])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(options={"a":"Alpha"}, attempts=1, confirm=False)
    assert res is None

def test_display_prompt_shows_default_line():
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    r._display_prompt(
        prompt="P",
        current_options={"a": "Alpha"},
        option_enabled={"a": True},
        formatter=r.default_formatter,
        allow_free_text=False,
        quit_word=None,
        help_word=None,
        current_value=None,
        default="a",
    )
    s = buf.getvalue()
    assert "Press [Enter] to use default: Alpha" in s

def test_get_input_returns_default_when_attempts_zero():
    r = Receptus(force_no_color=True)
    res = r.get_input(options={"a": "Alpha"}, default="a", attempts=0)
    assert res == "a"
