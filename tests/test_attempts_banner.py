from io import StringIO
from receptus import Receptus

def test_attempts_exhausted_prints_banner(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    # One empty input, no default/current -> loop ends and banner prints
    monkeypatch.setattr("builtins.input", lambda _ : "")
    res = r.get_input(options={"a":"Alpha"}, attempts=1, confirm=False)
    assert res is None
    assert "Maximum attempts reached" in buf.getvalue()
