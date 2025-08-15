import builtins, importlib, sys
import types
import receptus as receptus_mod  # already imported by other tests

def test_reload_with_colorama(monkeypatch):
    # Ensure a colorama-like module exists and has init()
    fake_colorama = types.SimpleNamespace(init=lambda: None)
    monkeypatch.setitem(sys.modules, "colorama", fake_colorama)
    importlib.reload(receptus_mod)  # re-executes top-level try: colorama.init()
    # sanity: Receptus is still present
    assert hasattr(receptus_mod, "Receptus")

def test_reload_without_colorama(monkeypatch):
    # Remove colorama and make import raise ImportError
    monkeypatch.delitem(sys.modules, "colorama", raising=False)
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "colorama":
            raise ImportError("no colorama")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    importlib.reload(receptus_mod)  # exercises except ImportError: pass
    assert hasattr(receptus_mod, "Receptus")
