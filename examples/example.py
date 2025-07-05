import random
from receptus import Receptus

# Demo usage: demonstrates all main features of PromptToolkit.
def demo():
    toolkit = Receptus()

    def extra_help():
        print("\n\033[94m--- EXTRA HELP ---")
        print("You can pick a color by typing its key or name.")
        print("If you need more info, visit: https://example.com/colors")
        print("------------------\033[0m\n")

    # Each block below demonstrates a major feature, such as validation,
    # custom formatting, dynamic disabling, confirmation, multi-select, etc.

    print("\n=== Basic Option Selection ===")
    print("\n===  With help callback()  ===")
    color = toolkit.get_input(
        prompt="Pick a color (type 'help' for instructions):",
        options={'r': 'Red', 'g': 'Green', 'b': 'Blue'},
        help_word='help',
        help_callback=extra_help,
        confirm=True,
        confirm_message="Confirm color: {value}?"
    )
    if color is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", color)

    print("\n=== Free Text Input With Validation/Transformation ===")
    def is_valid_age(s):
        try:
            val = int(s)
            return (0 < val < 120, "Age must be between 1 and 119")
        except Exception:
            return (False, "Age must be a number")
    age = toolkit.get_input(
        prompt="Enter your age:",
        allow_free_text=True,
        validator=is_valid_age,
        transformer=int,
        attempts=3,
        confirm=True,
        confirm_message="Confirm age: {value}"
    )
    if age is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", age)

    print("\n=== Password/Secret Entry (Masked Input) ===")
    print("\n=== NOTE: 'confirm=True' will display masked input!! ===")
    password = toolkit.get_input(
        prompt="Enter your password:",
        allow_free_text=True,
        mask_input=True,
        validator=lambda s: (len(s) >= 8, "Password must be at least 8 characters"),
        attempts=2,
        confirm=True,
        confirm_message="You entered a password of length {value}."
    )
    if password is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Password length:", len(password) if password else None)

    print("\n=== Multi-Select, Disabled/Enabled Choices, Custom Formatter, Auto-Complete, Fuzzy Match ===")
    disabled_keys = {'o', 'g'}  # Orange and Grape disabled
    def custom_formatter(text, style_type, **kwargs):
        styles = {
            "prompt": "\033[95m{}\033[0m",
            "option": "\033[94m{}\033[0m",
            "disabled_option": "\033[90m{}\033[0m",
            "error": "\033[91m{}\033[0m",
            "selected": "\033[92m{}\033[0m",
            "default": "{}"
        }
        return styles.get(style_type, "{}").format(text)
    fruits = toolkit.get_input(
        prompt="Select your favorite fruits (comma separated):",
        options=[('a', 'Apple'), ('b', 'Banana'), ('o', 'Orange'), ('g', 'Grape')],
        allow_multi=True,
        min_choices=2,
        max_choices=3,
        disabled_keys=disabled_keys,
        formatter=custom_formatter,
        confirm=True,
        confirm_message="You picked: {values}. Continue?",
        auto_complete=True,
        fuzzy_match=True
    )
    if fruits is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", fruits)

    print("\n=== Dynamic Choice Disabling/Enabling (Randomly disables Banana or Apple) ===")
    def is_enabled(key, value):
        if key == 'a' and random.choice([True, False]):
            return False
        if key == 'b' and random.choice([True, False]):
            return False
        return True
    dynamic = toolkit.get_input(
        prompt="Pick one fruit (dynamically disabled!):",
        options={'a': 'Apple', 'b': 'Banana', 'o': 'Orange'},
        is_enabled=is_enabled,
        confirm=True,
        confirm_message="Selected: {value}. Is this your final answer?",
    )
    if dynamic is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", dynamic)

    print("\n=== Custom Help/Quit Words ===")
    env = toolkit.get_input(
        prompt="Choose environment:",
        options={1: 'Development', 2: 'Staging', 3: 'Production'},
        current_value=2,
        help_word="?",
        quit_word="exitnow",
        confirm=True,
        confirm_message="Switch to environment: {value}?"
    )
    if env is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", env)

    print("\n=== Timeout Demo (Timeout=5s, auto-fallback) ===")
    def on_timeout():
        print("\nTimeout occurred. Returning 'timeout_value'.")
        return "timeout_value"
    timeout_result = toolkit.get_input(
        prompt="Enter something in 5 seconds:",
        allow_free_text=True,
        timeout_seconds=5,
        on_timeout=on_timeout
    )
    if timeout_result is toolkit.USER_QUIT:
        print("User exited.")
        return
    print("Result:", timeout_result)

if __name__ == "__main__":
    demo()