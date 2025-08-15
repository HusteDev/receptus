from io import StringIO
from receptus import Receptus

def _mk(with_buf=True):
    buf = StringIO()
    r = Receptus(force_no_color=True, output=buf)
    return r, buf

def test_handle_multi_select_bad_and_bounds():
    r, buf = _mk()
    processed = {"a":"a","b":"b"}
    hot = {"a":"a","b":"b"}
    enabled = {"a":True, "b":True}

    # Bad token path
    assert r._handle_multi_select("a,x", processed, hot, enabled, r.default_formatter,
                                  1, None, lambda k:k) is None
    # Below min_choices
    assert r._handle_multi_select("", processed, hot, enabled, r.default_formatter,
                                  2, None, lambda k:k) is None
    # Above max_choices
    assert r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                  1, 1, lambda k:k) is None

def test_handle_single_select_disabled_branch():
    r, buf = _mk()
    processed = {"a":"a"}
    hot = {}
    # option exists but disabled -> return None and print error
    assert r._handle_single_select("a", processed, hot, {"a": False},
                                   r.default_formatter, False, 0.75, {}, lambda k:k) is None

def test_handle_multi_select_good_and_disabled(capsys):
    r, _ = _mk()
    processed = {"a":"a","b":"b"}
    hot = {"a":"a","b":"b"}
    enabled = {"a":True,"b":False}
    # disabled should return None and print error
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter, 1, None, lambda k:k)
    assert res is None
    # valid selection
    enabled["b"] = True
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter, 1, None, lambda k:k)
    assert res == ["a","b"]

def test_handle_single_select_exact_hotkey_and_fuzzy(monkeypatch):
    r, buf = _mk()
    processed = {"apple":"apple","banana":"banana"}
    hot = {"a":"apple","b":"banana"}
    # exact
    assert r._handle_single_select("banana", processed, hot, {"banana":True}, r.default_formatter, False, 0.75, {}, lambda k:k) == "banana"
    # hotkey
    assert r._handle_single_select("a", processed, hot, {"apple":True}, r.default_formatter, False, 0.75, {}, lambda k:k) == "apple"
    # fuzzy suggestion prints and returns None
    res = r._handle_single_select("aple", processed, hot, {"apple":True}, r.default_formatter, True, 0.75, {}, lambda k:k)
    assert res is None
    assert "Did you mean:" in buf.getvalue()

def test_multi_hotkey_only_success():
    r, buf = _mk()
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}    # hotkeys resolve to long keys
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res == ["alpha", "beta"]

def test_multi_mixed_processed_and_hotkeys_success():
    r, buf = _mk()
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": True}
    # first via processed key, second via hotkey
    res = r._handle_multi_select("alpha,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res == ["alpha", "beta"]

def test_multi_disabled_via_hotkey_goes_to_bad():
    buf_r = Receptus(output=StringIO(), force_no_color=True)
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": False}  # 'b' disabled
    res = buf_r._handle_multi_select("a,b", processed, hot, enabled, buf_r.default_formatter,
                                     min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Invalid option(s): b" in buf_r.line_output.getvalue()

def test_multi_with_empty_tokens_and_whitespace_reports_invalid():
    buf_r = Receptus(output=StringIO(), force_no_color=True)
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": True}
    # contains empty tokens after splitting/stripping
    res = buf_r._handle_multi_select(" a ,  , b , ", processed, hot, enabled, buf_r.default_formatter,
                                     min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Invalid option(s):" in buf_r.line_output.getvalue()

def test_multi_duplicates_and_case_insensitive_kept_in_order():
    r, buf = _mk()
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": True}
    # duplicates + upper/lower mix; duplicates should be preserved
    res = r._handle_multi_select("A,a,b,B", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res == ["alpha", "alpha", "beta", "beta"]

def test_multi_above_maxchoices_blocked():
    buf_r = Receptus(output=StringIO(), force_no_color=True)
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": True}
    res = buf_r._handle_multi_select("a,b", processed, hot, enabled, buf_r.default_formatter,
                                     min_choices=1, max_choices=1, format_return=lambda x: x)
    assert res is None
    assert "Select between 1 and 1 options." in buf_r.line_output.getvalue()

def test_multi_maxchoices_zero_is_unbounded_truthiness_check():
    # max_choices=0 is falsy; branch `(max_choices and ...)` should not trigger
    r, buf = _mk()
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=0, format_return=lambda x: x)
    assert res == ["alpha", "beta"]

def _dicts():
    processed = {"alpha": "alpha", "beta": "beta"}
    hot = {"a": "alpha", "b": "beta"}
    return processed, hot

def test_success_only_hotkeys():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    out = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert out == ["alpha", "beta"]

def test_success_only_processed():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    out = r._handle_multi_select("alpha,beta", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert out == ["alpha", "beta"]

def test_mixed_processed_and_hotkey():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    out = r._handle_multi_select("alpha,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert out == ["alpha", "beta"]

def test_disabled_via_processed_goes_bad():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": False, "beta": True}
    res = r._handle_multi_select("alpha,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Invalid option(s): alpha" in r.line_output.getvalue()

def test_disabled_via_hotkey_goes_bad():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": False}
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Invalid option(s): b" in r.line_output.getvalue()

def test_unknown_token_goes_bad():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("alpha,x", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Invalid option(s): x" in r.line_output.getvalue()

def test_empty_tokens_and_spaces_report_invalid():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select(" ,  , ", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res is None
    msg = r.line_output.getvalue()
    assert "Invalid option(s):" in msg  # list includes empty strings after strip

def test_below_min_choices_blocked():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("a", processed, hot, enabled, r.default_formatter,
                                 min_choices=2, max_choices=None, format_return=lambda x: x)
    assert res is None
    assert "Select between 2 and ∞ options." in r.line_output.getvalue()

def test_above_max_choices_blocked():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=1, format_return=lambda x: x)
    assert res is None
    assert "Select between 1 and 1 options." in r.line_output.getvalue()

def test_max_choices_zero_is_unbounded():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("a,b", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=0, format_return=lambda x: x)
    assert res == ["alpha", "beta"]

def test_order_and_duplicates_preserved_case_insensitive():
    r, buf = _mk()
    processed, hot = _dicts()
    enabled = {"alpha": True, "beta": True}
    res = r._handle_multi_select("A,a,b,B", processed, hot, enabled, r.default_formatter,
                                 min_choices=1, max_choices=None, format_return=lambda x: x)
    assert res == ["alpha", "alpha", "beta", "beta"]

def test_single_select_confirm_declined_then_accept(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    inputs = iter(["a", "a"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    confirms = iter([False, True])
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : next(confirms))
    res = r.get_input(options={"a":"Alpha"}, confirm=True)
    assert res == "a"

def test_multi_select_confirm_declined_then_accept(monkeypatch):
    r = Receptus(output=StringIO(), force_no_color=True)
    inputs = iter(["a,b", "a,b"])
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    confirms = iter([False, True])
    monkeypatch.setattr(r, "_get_confirmation", lambda _ : next(confirms))
    res = r.get_input(options={"a":"Alpha","b":"Bravo"}, allow_multi=True, confirm=True)
    assert res == ["a","b"]

def test_is_enabled_blocks_disabled_then_allows_other(monkeypatch):
    buf = StringIO()
    r = Receptus(output=buf, force_no_color=True)
    inputs = iter(["b", "a"])  # try disabled 'b', then pick 'a'
    monkeypatch.setattr("builtins.input", lambda _ : next(inputs))
    res = r.get_input(
        options={"a":"Alpha", "b":"Beta"},
        is_enabled=lambda k, v: k != "b",
    )
    assert res == "a"
    assert "DISABLED" in buf.getvalue()