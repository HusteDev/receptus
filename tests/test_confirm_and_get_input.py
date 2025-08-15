# tests/test_confirm_and_get_input.py
from io import StringIO
import types, sys
from receptus import Receptus, UserQuit, ReceptusTimeout

def _mk(buf=True):
    out = StringIO()
    r = Receptus(force_no_color=True, output=out)
    return r, out

def test_confirm_value_yes(monkeypatch):
    r, _ = _mk()
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    assert r._confirm_value("X", True, "?", "Chosen: {value}")

def test_confirm_value_no(monkeypatch):
    r, _ = _mk()
    monkeypatch.setattr(r, "_get_confirmation", lambda _: False)
    assert r._confirm_value("X", True, "?", None) is False

def test_get_input_single_select_with_confirm(monkeypatch):
    r, _ = _mk()
    inputs = iter(["a"])  # choose 'a'
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    # confirm yes
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    res = r.get_input(prompt="P", options={"a":"Alpha","b":"Beta"}, confirm=True)
    assert res == "a"

def test_get_input_multi_select(monkeypatch):
    r, _ = _mk()
    inputs = iter(["a,b"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    res = r.get_input(options={"a":"Alpha","b":"Beta"}, allow_multi=True)
    assert res == ["a","b"]

def test_get_input_default_on_empty_with_confirm(monkeypatch):
    r, _ = _mk()
    inputs = iter([""])  # press Enter
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    res = r.get_input(options={"a":"Alpha","b":"Beta"}, default="b")
    assert res == "b"

def test_get_input_help_then_quit(monkeypatch):
    r, _ = _mk()
    seq = iter(["help", "quit", "y"])  # help triggers retry, then quit confirm yes
    monkeypatch.setattr("builtins.input", lambda _: next(seq))
    res = r.get_input(options={"a":"Alpha"}, confirm=True)
    assert isinstance(res, UserQuit)

def test_get_input_free_text_transform_validate(monkeypatch):
    r, _ = _mk()
    seq = iter(["hello"])
    monkeypatch.setattr("builtins.input", lambda _: next(seq))
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    res = r.get_input(allow_free_text=True,
                      transformer=str.upper,
                      validator=lambda v: (len(v) >= 3, "too short"),
                      confirm=True)
    assert res == "HELLO"

def test_get_input_timeout_uses_on_timeout(monkeypatch):
    r, _ = _mk()
    # force timed input path to raise
    monkeypatch.setattr(r, "_timed_input", lambda _p, _t: (_ for _ in ()).throw(ReceptusTimeout))
    res = r.get_input(prompt="P", options={"a":"Alpha"}, timeout_seconds=1, on_timeout=lambda: "TIMEOUT")
    assert res == "TIMEOUT"

def test_get_input_disabled_option_rejected(monkeypatch):
    r, _ = _mk()
    seq = iter(["b", "a"])  # first try disabled 'b', then 'a'
    monkeypatch.setattr("builtins.input", lambda _: next(seq))
    monkeypatch.setattr(r, "_get_confirmation", lambda _: True)
    res = r.get_input(options={"a":"Alpha","b":"Beta"},
                      is_enabled=lambda k, v: (k != "b"))
    assert res == "a"

def test_confirm_message_format_exception(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    # bad format string forces except branch
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : True)
    assert r._confirm_value("X", True, "?", "{not_a_key}") is True

def test_get_confirmation_invalid_then_no(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf)
    seq = iter(["maybe", "n"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    assert r._get_confirmation("sure? ") is False
    assert "Please enter Y or N." in buf.getvalue()

def test_single_select_no_match_prints_error(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    seq = iter(["zzz", "a"])  # first invalid, then valid
    monkeypatch.setattr("builtins.input", lambda _:"zzz")
    res = r.get_input(options={"a":"Alpha"}, attempts=1)  # will print error then return None (attempts exhausted)
    assert res is None

def test_disabled_option_branch(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    seq = iter(["b","a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(
        options={"a":"Alpha", "b":"Beta"},
        is_enabled=lambda k, v: k != "b",
        confirm=False,
    )
    assert res == "a"

def test_get_confirmation_yes(monkeypatch):
    r, _ = _mk()
    monkeypatch.setattr("builtins.input", lambda _: "y")
    assert r._get_confirmation("sure?")

def test_masking_falls_back_to_input_on_getpass_failure(monkeypatch):
    r = Receptus(output=StringIO())
    mod = types.SimpleNamespace(getpass=lambda prompt: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setitem(sys.modules, "getpass", mod)
    monkeypatch.setattr("builtins.input", lambda _ : "plain")
    assert r._read_input_with_timeout(": ", timeout_seconds=None, mask_input=True) == "plain"

def test_plain_input_no_timeout(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("builtins.input", lambda _ : "x")
    assert r._read_input_with_timeout(": ", timeout_seconds=None, mask_input=False) == "x"

def test_no_input_with_options_no_defaults(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    # press Enter once; attempts=1 so loop exits returning None
    monkeypatch.setattr("builtins.input", lambda _ : "")
    res = r.get_input(options={"a":"Alpha"}, attempts=1, allow_free_text=True)
    assert res is None
    s = buf.getvalue()
    assert "No input provided and no default/current value available" in s

def test_quit_confirm_decline_then_retry_then_quit(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    inputs = iter(["quit", "quit"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    confirms = iter([False, True])  # decline first, then accept
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : next(confirms))
    res = r.get_input(options={"a":"Alpha"}, confirm=True)
    assert isinstance(res, UserQuit)
    s = buf.getvalue()
    assert "Selection not confirmed. Please try again." in s  # retry branch

def test_masked_input_with_timeout_warns_and_uses_timed(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    # Make getpass importable so code hits the warning branch
    import types, sys
    gp = types.SimpleNamespace(getpass=lambda prompt: "should_not_be_used")
    monkeypatch.setitem(sys.modules, "getpass", gp)
    # Timed path should be taken and return this value
    monkeypatch.setattr(r, "_timed_input", lambda _p, _t: "SECRET")
    res = r.get_input(allow_free_text=True, mask_input=True, timeout_seconds=2)
    assert res == "SECRET"
    assert "Password masking does not support timeout" in buf.getvalue()