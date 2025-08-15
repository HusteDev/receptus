from io import StringIO
from receptus import Receptus

def _mk(with_buf=True):
    buf = StringIO()
    r = Receptus(force_no_color=True, output=buf)
    return r, buf

def test_allow_free_text_with_no_options_and_enter(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    monkeypatch.setattr("builtins.input", lambda _ : "")
    # allow_free_text=True and no options -> empty string result
    res = r.get_input(allow_free_text=True, options=None, attempts=1)
    assert res == ""

def test_display_prompt_shows_free_text_hint():
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    r._display_prompt(
        prompt="Enter",
        current_options={"a": "Alpha"},           # non-empty options
        option_enabled={"a": True},
        formatter=r.default_formatter,
        allow_free_text=True,
        quit_word=None,
        help_word=None,
        current_value=None,
        default=None,
    )
    s = buf.getvalue()
    assert "(___) Enter value" in s
    assert "(a) Alpha" in s

def test_display_prompt_prints_options():
    r, buf = _mk()
    r._display_prompt("Pick", {"a":"Alpha"}, {"a":True}, r.default_formatter,
                      True, "quit", "help", None, None)
    s = buf.getvalue()
    assert "Pick" in s and "(a) Alpha" in s and "(quit) Exit Program" in s and "(help) Show Options" in s

def test_handle_free_text_transform_and_validate():
    r, _ = _mk()
    # transformer ok + validator ok
    out = r._handle_free_text_input("abc", lambda s: s.upper(), lambda v: (True, ""))
    assert out == "ABC"
    # transformer raises -> None
    assert r._handle_free_text_input("x", lambda _: (_ for _ in ()).throw(ValueError("boom")), None) is None
    # validator rejects -> None
    assert r._handle_free_text_input("abc", None, lambda v: (False, "bad")) is None

def test_free_text_validator_rejects_then_accepts(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    inputs = iter(["hi", "hello"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : True)
    res = r.get_input(
        allow_free_text=True,
        transformer=str.upper,
        validator=lambda v: (len(v) >= 3, "too short"),
        confirm=True,
    )
    assert res == "HELLO"

def test_empty_input_with_options_and_allow_free_text(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    inputs = iter(["", "a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    res = r.get_input(options={"a":"Alpha"}, allow_free_text=True, attempts=2)
    assert res == "a"
    assert "No input provided and no default/current value available" in buf.getvalue()
