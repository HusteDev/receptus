# tests/test_history_and_autocomplete.py
from io import StringIO
import types, sys
from receptus import Receptus

def test_history_file_and_autocomplete(monkeypatch, tmp_path):
    # fake readline module
    rl = types.SimpleNamespace(
        set_completer=lambda _f: None,
        parse_and_bind=lambda _s: None,
        read_history_file=lambda _p: None,
        write_history_file=lambda _p: None,
    )
    monkeypatch.setitem(sys.modules, "readline", rl)
    out = StringIO()
    r = Receptus(output=out, force_no_color=True)
    # one selection with auto_complete and history enabled
    seq = iter(["a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(
        prompt="P",
        options={"a":"Alpha","b":"Beta"},
        auto_complete=True,
        history_file=str(tmp_path/"hist.txt"),
    )
    assert res == "a"

def test_history_read_then_write_exception(monkeypatch, tmp_path):
    # Create a history file to trigger read_history_file path
    hist = tmp_path / "hist.txt"
    hist.write_text("1\n")

    # Fake readline that raises on write (to hit finally-except)
    calls = {"read": False, "write": False}
    rl = types.SimpleNamespace(
        set_completer=lambda _f: None,
        parse_and_bind=lambda _s: None,
        read_history_file=lambda p: calls.__setitem__("read", True),
        write_history_file=lambda p: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setitem(sys.modules, "readline", rl)

    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    seq = iter(["a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(options={"a":"Alpha"}, auto_complete=True, history_file=str(hist))
    assert res == "a"
    assert calls["read"] is True  # ensured read path executed
    # we don’t assert the warning text; just that no exception bubbles

def test_completer_invoked_and_history_written(monkeypatch, tmp_path):
    holder = {"first_completer": None, "wrote": False}

    def set_completer(fn):
        # Preserve the first non-None completer; ignore the final reset to None
        if fn is not None and holder["first_completer"] is None:
            holder["first_completer"] = fn

    def parse_and_bind(_): pass
    def read_history_file(_): pass
    def write_history_file(_): holder["wrote"] = True

    rl = types.SimpleNamespace(
        set_completer=set_completer,
        parse_and_bind=parse_and_bind,
        read_history_file=read_history_file,
        write_history_file=write_history_file,
    )
    monkeypatch.setitem(sys.modules, "readline", rl)

    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)

    # Use single-char keys so "a" is a valid hotkey
    seq = iter(["a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(
        options={"a":"Alpha","b":"Bravo"},
        auto_complete=True,
        history_file=str(tmp_path/"hist.txt"),
    )
    assert res == "a"

    # The completer closure should have been installed at least once
    comp = holder["first_completer"]
    assert comp is not None
    assert comp("a", 0) in ("a",)   # returns a match
    assert comp("zzz", 0) is None   # no matches

    # History write path executed
    assert holder["wrote"] is True