from io import StringIO
from receptus import Receptus

def test_callable_options_and_format_return_value_and_tuple(monkeypatch):
    # options is a callable -> covers get_current_options()
    calls = {"n": 0}
    def dyn_opts():
        calls["n"] += 1
        return {"alpha": "Alpha", "bravo": "Bravo"}

    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)

    # First, return_format=value (single select)
    seq = iter(["alpha"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(options=dyn_opts, return_format="value")
    assert res == "Alpha" and calls["n"] >= 1

    # Next, return_format=tuple via multi-select
    seq = iter(["alpha,bravo"])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res2 = r.get_input(options=dyn_opts, allow_multi=True, return_format="tuple")
    assert res2 == [("alpha","Alpha"), ("bravo","Bravo")]
    assert calls["n"] >= 2  # callable re-evaluated

def test_max_input_len_guard(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    # 1 attempt; oversize input triggers the guard and returns None
    long = "x" * 1000
    seq = iter([long])
    monkeypatch.setattr("builtins.input", lambda _ : next(seq))
    res = r.get_input(options={"a":"Alpha"}, attempts=1, max_input_len=10)
    assert res is None
    assert "Input too long" in buf.getvalue()
