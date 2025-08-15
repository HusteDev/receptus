from io import StringIO
from receptus import Receptus, ReceptusTimeout, UserQuit

def test_fuzzy_suggestion_then_accept(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    inputs = iter(["aple", "apple"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    res = r.get_input(options={"apple":"Apple","banana":"Banana"}, fuzzy_match=True)
    assert res == "apple"
    assert "Did you mean:" in buf.getvalue()

def test_on_event_called(monkeypatch):
    events = {"called": False, "payload": None}
    def on_event(ev_type, ctx):
        if ev_type == "input_received":
            events["called"] = True
            events["payload"] = ctx

    r = Receptus(output=StringIO(), force_no_color=True, on_event=on_event)
    monkeypatch.setattr("builtins.input", lambda _ : "a")
    res = r.get_input(options={"a":"Alpha"})
    assert res == "a"
    assert events["called"] is True
    assert isinstance(events["payload"], dict) and "raw" in events["payload"]

def test_unknown_option_triggers_input_invalid_event(monkeypatch):
    events = {"invalid": False, "payload": None}
    def on_event(ev, ctx):
        if ev == "input_invalid":
            events["invalid"] = True
            events["payload"] = ctx

    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True, on_event=on_event)
    inputs = iter(["zzz", "a"])  # invalid first, then valid
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))

    res = r.get_input(options={"a": "Alpha"}, attempts=2)

    assert res == "a"
    assert events["invalid"] is True
    # Printed text includes the actual input:
    s = buf.getvalue()
    assert "not a valid option" in s  # e.g., ## "zzz" is not a valid option. ##
    # Event payload carries the reason string:
    assert events["payload"]["reason"] == "Unknown option"
    assert events["payload"]["input"] == "zzz"
    assert events["payload"]["valid_keys"] == ["a"]