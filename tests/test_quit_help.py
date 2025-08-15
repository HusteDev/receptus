# tests/test_internal_helpers.py
from io import StringIO
from receptus import Receptus, UserQuit

def _mk(with_buf=True):
    buf = StringIO()
    r = Receptus(force_no_color=True, output=buf)
    return r, buf

def test_handle_quit_and_help_paths(monkeypatch):
    r, _ = _mk()
    # help -> "retry"
    out = r._handle_quit_and_help("help", "quit", "help", lambda: None, False, "Are you sure?")
    assert out == "retry"
    # quit with confirm False -> USER_QUIT
    out = r._handle_quit_and_help("quit", "quit", "help", None, False, "Are you sure?")
    assert isinstance(out, UserQuit)
    # quit with confirm True but decline -> "retry"
    r2, _ = _mk()
    monkeypatch.setattr(r2, "_get_confirmation", lambda _: False)
    out = r2._handle_quit_and_help("quit", "quit", "help", None, True, "Are you sure?")
    assert out == "retry"

def test_get_input_quit_without_confirm(monkeypatch):
    r = Receptus(force_no_color=True)
    monkeypatch.setattr("builtins.input", lambda _ : "quit")
    res = r.get_input(options={"a": "Alpha"}, confirm=False)
    assert isinstance(res, UserQuit)

def test_help_word_invokes_callback(monkeypatch):
    called = {"v": False}
    def cb(): called["v"] = True

    r = Receptus(output=StringIO(), force_no_color=True)
    seq = iter(["help", "a"])  # first help → retry, then pick 'a'
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))

    res = r.get_input(options={"a": "Alpha"}, help_callback=cb)
    assert called["v"] is True
    assert res == "a"

def test_userquit_repr_and_formatreturn_default():
    # __repr__ branch
    assert repr(UserQuit()) == "<UserQuit>"

    # _format_return default branch (unknown return_format -> returns key)
    r = Receptus()
    opts = {"a": "Alpha"}
    assert r._format_return("a", opts, "does-not-exist") == "a"