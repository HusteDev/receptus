# tests/test_ansi_and_formatting.py
from io import StringIO
import os, sys
from receptus import Receptus

def _mk(with_buf=True):
    buf = StringIO()
    r = Receptus(force_no_color=True, output=buf)
    return r, buf

def test_supports_ansi_true_with_tty_and_env(monkeypatch):
    r = Receptus(output=StringIO())
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setenv("WT_SESSION", "1")
    assert r.supports_ansi() is True

def test_default_formatter_with_color(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=False)
    # make ANSI support true
    monkeypatch.setattr(r, "supports_ansi", lambda: True)
    out = r.default_formatter("msg", "prompt")
    assert out.startswith("\x1b[")

def test_default_formatter_unknown_returns_text():
    r = Receptus(output=StringIO(), force_no_color=True)
    assert r.default_formatter("msg", "does-not-exist") == "msg"

def test_out_without_clear_sanitizes_only():
    buf = StringIO()
    r = Receptus(force_ascii=True, force_no_color=True, output=buf)
    r.out("héllo", line_clear=False, line_end="")
    assert buf.getvalue() == "hello"

def test_sanitize_input_no_ascii_strip():
    r = Receptus(force_ascii=True)  # instance default True
    # override per-call to cover ascii_only=False branch
    assert r.sanitize_input("café", ascii_only=False) == "café"

def test_sanitize_ascii_strip():
    r = Receptus(force_ascii=True, force_no_color=True, output=StringIO())
    assert r.sanitize_input("café") == "cafe"

def test_supports_ansi_false_when_not_tty(monkeypatch):
    r = Receptus(force_no_color=False, output=StringIO())
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False, raising=False)
    assert r.supports_ansi() is False

def test_color_wrap_respects_force_no_color():
    r = Receptus(force_no_color=True, output=StringIO())
    assert r.color_wrap("txt", "31") == "txt"

def test_default_formatter_no_color():
    r = Receptus(force_no_color=True, output=StringIO())
    assert r.default_formatter("hello", "prompt") == "hello"  # no ANSI

def test_out_prints_and_clears_line():
    buf = StringIO()
    r = Receptus(force_ascii=True, force_no_color=True, output=buf)
    r.out("héllo", line_clear=True, line_sep="-", line_end="\n")
    s = buf.getvalue()
    assert "hello" in s and "\x1b[K" in s

def test_format_return_variants():
    r, _ = _mk()
    opts = {"a":"Alpha","b":"Beta"}
    assert r._format_return("a", opts, "key") == "a"
    assert r._format_return("a", opts, "value") == "Alpha"
    assert r._format_return("a", opts, "tuple") == ("a","Alpha")

def test_supports_ansi_posix_tty(monkeypatch):
    r = Receptus(output=StringIO())
    # TTY + non-Windows => True
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(os, "name", "posix")
    assert r.supports_ansi() is True

