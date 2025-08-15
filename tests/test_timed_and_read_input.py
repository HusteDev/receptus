# tests/test_timed_and_read_input.py
from io import StringIO
import types, sys, builtins, pytest
from receptus import Receptus, ReceptusTimeout

def test_timed_input_posix(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("platform.system", lambda: "Linux")
    # fake signal module with SIGALRM
    sig = types.SimpleNamespace(
        SIGALRM=14,
        signal=lambda *_: None,
        alarm=lambda _n: None,
    )
    monkeypatch.setitem(sys.modules, "signal", sig)
    monkeypatch.setattr("builtins.input", lambda p: "ok")
    assert r._timed_input(": ", 1) == "ok"

def test_timed_input_windows_with_inputimeout(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("platform.system", lambda: "Windows")
    # fake inputimeout module
    mod = types.SimpleNamespace()
    class TimeoutOccurred(Exception): pass
    mod.TimeoutOccurred = TimeoutOccurred
    def _io(prompt, timeout):
        return "win-ok"
    mod.inputimeout = _io
    monkeypatch.setitem(sys.modules, "inputimeout", mod)
    assert r._timed_input(": ", 2) == "win-ok"

def test_read_input_with_mask_and_timeout_warning(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf)
    # when mask + timeout -> warning + fall back to _timed_input
    monkeypatch.setattr(r, "_timed_input", lambda p, t: "masked")
    out = r._read_input_with_timeout(": ", timeout_seconds=1, mask_input=True)
    assert out == "masked"
    assert "does not support timeout" in buf.getvalue()

def test_read_input_with_mask_getpass(monkeypatch):
    r = Receptus(output=StringIO())
    gp = types.SimpleNamespace(getpass=lambda prompt: "secret")
    monkeypatch.setitem(sys.modules, "getpass", gp)
    assert r._read_input_with_timeout(": ", timeout_seconds=None, mask_input=True) == "secret"

def test_read_input_timeout_path(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf)
    def _ti(prompt, t): raise ReceptusTimeout
    monkeypatch.setattr(r, "_timed_input", _ti)
    assert r._read_input_with_timeout(": ", timeout_seconds=1, mask_input=False) is None
    assert "Input timed out" in buf.getvalue()

def test_timed_input_windows_without_inputimeout(monkeypatch):
    r = Receptus(output=StringIO())
    # Force Windows path in _timed_input
    monkeypatch.setattr("platform.system", lambda: "Windows")

    # Ensure it's not already cached
    monkeypatch.delitem(sys.modules, "inputimeout", raising=False)

    # Capture the real importer *before* patching
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "inputimeout":
            # Simulate not installed
            raise ImportError("simulated absence of inputimeout")
        return real_import(name, *args, **kwargs)

    # Patch just for this test
    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Fallback should be plain input()
    monkeypatch.setattr("builtins.input", lambda p: "fallback")
    assert r._timed_input(": ", 1) == "fallback"

def test_timed_input_posix_raises_and_clears_alarm(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("platform.system", lambda: "Linux")

    # fake signal with SIGALRM and track alarm clearing
    cleared = {"ok": False}
    def alarm(n):
        # when input raises, code should clear with alarm(0)
        if n == 0:
            cleared["ok"] = True
    sig = types.SimpleNamespace(SIGALRM=14, signal=lambda *_: None, alarm=alarm)
    monkeypatch.setitem(sys.modules, "signal", sig)

    # input raises ReceptusTimeout -> _timed_input should propagate after clearing alarm
    monkeypatch.setattr("builtins.input", lambda _ : (_ for _ in ()).throw(ReceptusTimeout))
    with pytest.raises(ReceptusTimeout):
        r._timed_input(": ", 1)
    assert cleared["ok"] is True

def test_timed_input_windows_timeoutoccurred(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("platform.system", lambda: "Windows")

    class TimeoutOccurred(Exception): ...
    def fake_inputimeout(prompt, timeout=None, **kwargs):
        raise TimeoutOccurred

    mod = types.SimpleNamespace(TimeoutOccurred=TimeoutOccurred, inputimeout=fake_inputimeout)
    monkeypatch.setitem(sys.modules, "inputimeout", mod)

    with pytest.raises(ReceptusTimeout):
        r._timed_input(": ", 2)

def test_timed_input_posix_calls_handler(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr("platform.system", lambda: "Linux")

    captured = {"handler": None}

    # Fake signal module that captures the handler and triggers it on alarm(timeout>0)
    def _signal(_sig, handler):
        captured["handler"] = handler
    def _alarm(n):
        if n:  # when alarm set to non-zero, immediately invoke captured handler
            captured["handler"](14, None)

    fake_signal = types.SimpleNamespace(SIGALRM=14, signal=_signal, alarm=_alarm)
    monkeypatch.setitem(sys.modules, "signal", fake_signal)

    # input() won't be reached because alarm triggers the handler first
    with pytest.raises(ReceptusTimeout):
        r._timed_input(": ", 1)

def test_timeout_no_on_timeout_default_confirm_decline_then_accept(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)

    # First timed input -> raise (so _read_input_with_timeout returns None).
    # Second timed input -> return "a".
    steps = iter(["raise", "return"])
    def fake_timed(prompt, t):
        if next(steps) == "raise":
            raise ReceptusTimeout
        return "a"
    monkeypatch.setattr(r, "_timed_input", fake_timed)

    # First confirmation (for default) -> False, second (for "a") -> True
    confirms = iter([False, True])
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : next(confirms))

    res = r.get_input(
        prompt="P",
        options={"a": "Alpha", "b": "Bravo"},
        default="b",
        confirm=True,
        timeout_seconds=1,
    )
    assert res == "a"  # ended via second iteration single-select

def test_timeout_no_default_no_current_confirm_true_returns_none(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    monkeypatch.setattr(r, "_timed_input", lambda _p, _t: (_ for _ in ()).throw(ReceptusTimeout))
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : True)
    res = r.get_input(options=None, confirm=True, timeout_seconds=1)
    assert res is None  # result was None and confirmed

def test_timeout_with_on_timeout_callback(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    monkeypatch.setattr(r, "_timed_input", lambda _p, _t: (_ for _ in ()).throw(ReceptusTimeout))
    res = r.get_input(options={"a":"Alpha"}, timeout_seconds=1, on_timeout=lambda: "TIMEOUT_VALUE")
    assert res == "TIMEOUT_VALUE"