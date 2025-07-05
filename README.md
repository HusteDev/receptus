# Receptus

```bash
  RRRRR  EEEEE  CCCCC  EEEEE  PPPPP  TTTTT  U   U  SSSSS
  R   R  E      C      E      P   P    T    U   U  S
  RRRRR  EEEE   C      EEEE   PPPPP    T    U   U  SSSSS
  R R    E      C      E      P        T    U   U      S
  R  RR  EEEEE  CCCCC  EEEEE  P        T     UUU   SSSSS
```


**Receptus** — from the Latin *"received (text)"* — is a Python CLI prompt toolkit built for humans.

It enables the creation of intelligent and secure terminal interfaces with advanced input features like:

- Option selection (single & multi)
- Free-form text input
- Input validation and transformation
- Fuzzy matching and auto-complete
- Password masking
- ANSI and ASCII-compatible output
- Timeout and retry handling
- Input history
- Event logging hooks (`on_event`)
- Quit/help commands
- Dynamic option lists

---

## Installation

Receptus is a single-file drop-in module. Just copy `receptus.py` into your project.

You can also install it via GitHub (PyPI coming soon):

```bash
pip install git+https://github.com/hustedev/receptus.git
```

---

## Quick Start

```python
from receptus import Receptus

prompt = Receptus()

color = prompt.get_input(
    prompt="Choose a color:",
    options={"r": "Red", "g": "Green", "b": "Blue"},
    default="g"
)

print(f"You chose: {color}")
```

---

## Features

### Prompt with Options

```python
options = {
    "1": "Low",
    "2": "Medium",
    "3": "High"
}

choice = Receptus().get_input(
    prompt="Select difficulty:",
    options=options,
    default="2"
)
```

---

### Free Text + Validation + Transform

```python
def validate_port(s):
    try:
        port = int(s)
        return (0 < port < 65536, "Must be a valid port number")
    except:
        return (False, "Not a number")

def transform_port(s):
    return int(s)

port = Receptus().get_input(
    prompt="Enter port:",
    allow_free_text=True,
    validator=validate_port,
    transformer=transform_port
)
```

---

### Multi-Select

```python
files = Receptus().get_input(
    prompt="Select files:",
    options={"1": "fileA", "2": "fileB", "3": "fileC"},
    allow_multi=True,
    min_choices=1,
    max_choices=2
)
```

---

### Fuzzy Match & Auto-Complete

```python
name = Receptus().get_input(
    prompt="Enter country:",
    options={"us": "USA", "uk": "United Kingdom", "uae": "United Arab Emirates"},
    fuzzy_match=True,
    auto_complete=True
)
```

---

### Password Masking + Timeout

```python
secret = Receptus().get_input(
    prompt="Enter password:",
    mask_input=True,
    timeout_seconds=15
)
```

---

### Event Logging via `on_event`

```python
def logger(event_type, ctx):
    print(f"[{event_type}] -> {ctx}")

Receptus(on_event=logger).get_input(
    prompt="Choose something:",
    options={"1": "One", "2": "Two"},
)
```

---

## Return Formats

You can control what `get_input()` returns:

```python
return_format="key"     # (default) -> "1"
return_format="value"   # -> "One"
return_format="tuple"   # -> ("1", "One")
```

---

## Environment Variables

* `FORCE_ASCII=1` — disables Unicode output
* `NO_COLOR=1` — disables ANSI color

---

## License

MIT License — do anything you want, but attribution appreciated.

(c) 2025 James Husted — [james@husted.dev](mailto:james@husted.dev)

---

## 🚧 Roadmap

* [ ] PyPI release
* [ ] TypeScript wrapper for Node CLI tools
* [ ] Native zsh/bash integration helpers
* [ ] Dynamic theming

---

## Contributing

Pull requests welcome! Just fork, branch, and submit.

---
