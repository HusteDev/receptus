##
##      RRRRR  EEEEE  CCCCC  EEEEE  PPPPP  TTTTT  U   U  SSSSS
##      R   R  E      C      E      P   P    T    U   U  S
##      RRRRR  EEEE   C      EEEE   PPPPP    T    U   U  SSSS
##      R R    E      C      E      P        T    U   U     S
##      R  RR  EEEEE  CCCCC  EEEEE  P        T     UUU   SSSS
##
## Receptus - A Python CLI Prompt Toolkit
##
## a Latin term meaning "received" or "received text"
##
## - Provides option selection, free text, multi-select, masking, timeouts, history, and fuzzy matching.
## - Supports ANSI color, ASCII-only, and custom formatters.
## - Intended for building robust, user-friendly CLI interfaces.
##
## Author: James Husted             email: james@husted.dev
##
## License: MIT
##


import sys
import os
import unicodedata
from typing import Callable, Optional, Any, Dict, List, Union, Sequence, Tuple

# Optionally enable colored output via colorama, if available.
try:
    import colorama
    colorama.init()
except ImportError:
    pass  # No colorama, fallback to raw output

# Allow options to be provided as a dict, list of tuples, or a callable returning either.
OptionsType = Union[
    Dict[Any, str],
    Sequence[tuple],
    Callable[[], Union[Dict[Any, str], Sequence[tuple]]]
]

class ReceptusTimeout(Exception):
    """Raised when user input times out."""
    pass

class UserQuit:
    def __repr__(self):
        return "<UserQuit>"

class Receptus:
    # Sentinel value for quitting, to be returned if user chooses to exit.
    USER_QUIT = UserQuit()

    def __init__(
            self, 
            *, 
            force_ascii=None, 
            force_no_color=None, 
            output=None,
            line_clear=True,
            line_sep=" ",
            line_end='\n',
            on_event: Optional[Callable[[str, dict], None]] = None
            ):
        """
        Initialize the Receptus with formatting and output controls.
        """
        self.force_ascii = force_ascii if force_ascii is not None else (os.environ.get("FORCE_ASCII") or "--ascii" in sys.argv)
        self.force_no_color = force_no_color if force_no_color is not None else (os.environ.get("NO_COLOR") or "--no-color" in sys.argv)
        self.line_output = output or sys.stdout

        self.line_clear = line_clear
        self.line_sep = line_sep
        self.line_end = line_end
        self.on_event = on_event or (lambda event_type, context: None)


    def supports_ansi(self):
        """
        Returns True if the terminal supports ANSI color codes.
        """
        if not sys.stdout.isatty():
            return False
        if os.name != "nt":
            return True
        return ("ANSICON" in os.environ) or ("WT_SESSION" in os.environ) or ("TERM" in os.environ and os.environ["TERM"] == "xterm")

    def sanitize_input(self, text, ascii_only=False):
        """
        Normalize and optionally strip accents and non-ASCII characters from input.
        """
        if ascii_only is None:
            ascii_only = self.force_ascii
        text = unicodedata.normalize('NFKC', text)
        if ascii_only:
            # Strip accents/diacritics
            text = ''.join(
                c for c in text
                if not unicodedata.combining(c)
            )
            # Remove all non-ascii chars
            text = text.encode('ascii', 'ignore').decode('ascii')
        return text
    
    def out(self, *args, line_clear=None, line_sep=None, line_end=None):
        """
        Print to output, optionally clearing the line and normalizing to ASCII.
        """
        if line_clear is None:
            line_clear = self.line_clear
        if line_sep is None:
            line_sep = self.line_sep
        if line_end is None:
            line_end = self.line_end
        suffix = "\033[K" if line_clear else ""
        print(*(self.sanitize_input(str(a)) for a in args), end=suffix + line_end, sep=line_sep, file=self.line_output, flush=True)


    def color_wrap(self, text, code):
        """
        Apply ANSI color codes to text, unless color is disabled.
        """
        if self.force_no_color or not self.supports_ansi():
            return text
        return f"\033[{code}m{text}\033[0m"

    def default_formatter(self, text, style_type, **kwargs):
        """
        Default formatting for different UI elements (prompt, option, error, etc).
        """
        styles = {
            "prompt":   "96",   # cyan
            "option":   "92",   # green
            "disabled_option": "90", # grey
            "error":    "91",   # red
            "selected": "93",   # yellow
            "default":  None,
        }
        code = styles.get(style_type)
        if code:
            return self.color_wrap(text, code)
        return text

    def _timed_input(self, prompt, timeout):
        """
        Wait for input with a timeout, using inputimeout (Windows) or signal (UNIX).
        Raises ReceptusTimeout on timeout.
        """
        import platform
        if platform.system() != "Windows":
            import signal
            def handler(signum, frame):
                raise ReceptusTimeout
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
            try:
                result = input(prompt)
                signal.alarm(0)
                return result
            except ReceptusTimeout:
                signal.alarm(0)
                raise
        else:
            try:
                from inputimeout import inputimeout, TimeoutOccurred
                try:
                    return inputimeout(prompt, timeout=timeout)
                except TimeoutOccurred:
                    raise ReceptusTimeout
            except ImportError:
                # No timeout support on Windows without the inputimeout module.
                return input(prompt)


    def _get_confirmation(self, confirm_prompt: str) -> bool:
        """Ask user for confirmation, Y/N."""
        while True:
            conf = input(confirm_prompt)
            if conf.strip().lower() in ("y", "yes"):
                return True
            if conf.strip().lower() in ("n", "no", ""):
                return False
            self.out("Please enter Y or N.")

    def _format_return(self, key: Any, current_options: Dict, return_format: str) -> Any:
        """Format return value according to requested return_format."""
        if return_format == "key":
            return key
        if return_format == "value":
            return current_options[key]
        if return_format == "tuple":
            return (key, current_options[key])
        return key

    def _display_prompt(
        self,
        prompt: Optional[str],
        current_options: Dict,
        option_enabled: Dict,
        formatter: Callable,
        allow_free_text: bool,
        quit_word: Optional[str],
        help_word: Optional[str],
        current_value: Optional[str],
        default: Optional[str],
    ):
        """Displays the prompt, options, and other contextual information."""
        if prompt:
            self.out(f'\n{prompt}')

        if current_options:
            if allow_free_text:
                self.out(f'    (___) Enter value [Free text]')
            for key, value in current_options.items():
                enabled = option_enabled.get(key, True)
                if not str(key).startswith("*"):
                    if enabled:
                        self.out(formatter(f'    ({key}) {value}', "option"))
                    else:
                        self.out(formatter(f'    ({key}) {value} [DISABLED]', "disabled_option"))
        elif allow_free_text:
            pass

        if quit_word:
            self.out(f'    ({quit_word}) Exit Program')
        if help_word:
            self.out(f'    ({help_word}) Show Options')

        if current_value is not None:
            self.out(f' Current Value:   {current_value}')
            self.out(f'>>  Press [Enter] to use this value.')
        elif default is not None:
            self.out(f'>>  Press [Enter] to use default: {current_options.get(default, default)}')

    def _read_input_with_timeout(self, prompt: str, timeout_seconds: Optional[int], mask_input: bool) -> Optional[str]:
        """Reads input, handling masking and timeouts."""
        if mask_input:
            try:
                from getpass import getpass
                if timeout_seconds is not None:
                    self.out("## Warning: Password masking does not support timeout. Input will not be masked. ##")
                    return self._timed_input(prompt, timeout_seconds)
                return getpass(prompt)
            except Exception:
                return input(prompt)

        if timeout_seconds is not None:
            try:
                return self._timed_input(prompt, timeout_seconds)
            except ReceptusTimeout:
                self.out("## Input timed out ##")
                # self.on_event("timeout", {"prompt": prompt})  # Optional
                return None

        return input(prompt)


    def _confirm_value(
        self,
        value: Any,
        confirm: bool,
        confirm_prompt: str,
        confirm_message: Optional[str],
    ) -> bool:
        """Handles the confirmation logic for a selection. Returns True if confirmed."""
        if not confirm:
            return True

        if confirm_message:
            try:
                msg = confirm_message.format(value=value, values=value if isinstance(value, list) else [value], input=value)
            except Exception:
                msg = str(confirm_message)
            self.out(msg)
        else:
            self.out(f"You selected: {value}")

        return self._get_confirmation(confirm_prompt)

    def _handle_quit_and_help(self, usr_input_lower, quit_word, help_word, help_callback, confirm, confirm_prompt):
        if usr_input_lower == quit_word.lower() if quit_word else False:
            if confirm and not self._get_confirmation(confirm_prompt):
                self.out("Selection not confirmed. Please try again.\n")
                return "retry"
            return self.USER_QUIT

        if usr_input_lower == help_word.lower() if help_word else False:
            if help_callback:
                help_callback()
            return "retry"

        return None

    def _handle_multi_select(self, usr_input, processed_keys, hotkeys, option_enabled, formatter, min_choices, max_choices, format_return):
        parts = [part.strip() for part in usr_input.split(",")]
        chosen, bad = [], []

        for part in parts:
            key_candidate = processed_keys.get(part.lower()) or hotkeys.get(part.lower())
            enabled = option_enabled.get(key_candidate, True)
            if not enabled:
                bad.append(part)
                continue
            if part.lower() in processed_keys:
                chosen.append(processed_keys[part.lower()])
            elif part.lower() in hotkeys:
                chosen.append(hotkeys[part.lower()])
            else:
                bad.append(part)

        if bad:
            self.out(f'## Invalid option(s): {", ".join(bad)} ##')
            return None
        if len(chosen) < min_choices or (max_choices and len(chosen) > max_choices):
            self.out(f'## Select between {min_choices} and {max_choices or "∞"} options. ##')
            return None

        return [format_return(c) for c in chosen]

    def _handle_single_select(self, usr_input, processed_keys, hotkeys, option_enabled, formatter, fuzzy_match, fuzzy_cutoff, current_options, format_return):
        import difflib

        usr_input_lower = usr_input.lower()
        key = None

        if usr_input_lower in processed_keys:
            key = processed_keys[usr_input_lower]
        elif usr_input_lower in hotkeys:
            key = hotkeys[usr_input_lower]
        elif fuzzy_match and processed_keys:
            matches = difflib.get_close_matches(usr_input_lower, processed_keys, n=3, cutoff=fuzzy_cutoff)
            if matches:
                self.out(f'Did you mean: {", ".join(matches)}?')
                return None

        if key is not None:
            if not option_enabled.get(key, True):
                self.out(formatter(f"## Option '{usr_input}' is disabled. ##", "error"))
                return None
            return format_return(key)

        return None

    def _handle_free_text_input(self, usr_input, transformer, validator):
        value = usr_input
        if transformer:
            try:
                value = transformer(value)
            except Exception as e:
                self.out(f'## Input transformation failed: {e} ##')
                return None
        if validator:
            valid, msg = validator(value)
            if not valid:
                self.out(f'## {msg or "Invalid input"} ##')
                return None
        return value


    def get_input(
            self,
            prompt: Optional[str] = None,
            options: Optional[OptionsType] = None,
            default: Optional[str] = None,
            current_value: Optional[str] = None,
            attempts: int = -1,
            allow_free_text: bool = False,
            validator: Optional[Callable[[str], Tuple[bool, str]]] = None,
            transformer: Optional[Callable[[str], Any]] = None,
            quit_word: Optional[str] = "quit",
            help_word: Optional[str] = "help",
            help_callback: Optional[Callable[[], None]] = None,
            allow_multi: bool = False,
            min_choices: int = 1,
            max_choices: Optional[int] = None,
            timeout_seconds: Optional[int] = None,
            on_timeout: Optional[Callable[[], Any]] = None,
            disabled_keys: Optional[set] = None,
            is_enabled: Optional[Callable[[Any, Any], bool]] = None,
            formatter: Optional[Callable[[str, str], str]] = None,
            line_clear: bool = True,
            line_sep = " ",
            line_end = '\n',
            max_input_len: Optional[int] = 500,
            mask_input: bool = False,
            auto_complete: bool = False,
            fuzzy_match: bool = False,
            fuzzy_cutoff: float = 0.75,
            history_file: Optional[str] = None,
            return_format: str = "key",  # "key", "value", "tuple"
            confirm: bool = False,
            confirm_prompt: Optional[str] = "Are you sure? [y/N]: ",
            confirm_message: Optional[str] = None,
        ) -> Union[Any, List[Any], None, UserQuit]:
        """
        Prompt the user for input with many options and features.

        Handles:
        - Option lists (static/dynamic)
        - Disabled/dynamically enabled options
        - Multi-select
        - Free text
        - Confirmation
        - Help/Quit commands
        - Input validation and transformation
        - Timeout and masking
        - History and fuzzy search
        """

        # Dynamic options: allow options to be callable to re-evaluate every time.
        if callable(options):
            def get_current_options():
                opts = options()
                return dict(opts) if not isinstance(opts, dict) else opts
        else:
            _static_opts = dict(options) if options else {}
            def get_current_options():
                return _static_opts

        if fuzzy_match:
            import difflib    # For close match suggestions

        # Optionally enable tab-completion for choices.
        readline = None
        if auto_complete:
            try:
                import readline
            except ImportError:
                pass # readline not available

        def format_return(key):
            # Format return value according to requested return_format.
            if return_format == "key":
                return key
            if return_format == "value":
                return current_options[key]
            if return_format == "tuple":
                return (key, current_options[key])
            return key

        attempts_remaining = attempts
        infinite_attempts = (attempts == -1)

        formatter = formatter or self.default_formatter
        disabled_keys = set(disabled_keys or [])
        
        # Enable input history (if available and requested)
        if history_file and readline:
            try:
                if os.path.exists(history_file):
                    readline.read_history_file(history_file)
            except Exception as e:
                print(f"Warning: Could not load history file: {e}")

        try:
            # Loop until valid input or attempts exhausted.
            while infinite_attempts or attempts_remaining > 0:
                current_options = get_current_options()
                # Evaluate which options are currently enabled.
                option_enabled = {key: is_enabled(key, value) if is_enabled else True for key, value in current_options.items()}

                # Map of input keys and hotkeys (1-char options)
                processed_keys = {str(k).lower(): k for k in current_options}
                hotkeys = {str(k)[0].lower(): k for k in current_options if isinstance(k, str) and len(str(k)) == 1}
                option_choices = list(processed_keys.keys())

                if auto_complete and readline:
                    def completer(text, state):
                        matches = [c for c in option_choices if c.startswith(text.lower())]
                        return matches[state] if state < len(matches) else None
                    readline.set_completer(completer)
                    readline.parse_and_bind('tab: complete')

                self._display_prompt(
                    prompt, current_options, option_enabled, formatter,
                    allow_free_text, quit_word, help_word, current_value, default
                )

                usr_input_raw = self._read_input_with_timeout(": ", timeout_seconds, mask_input)

                if usr_input_raw is None:
                    # If timed out, call handler or fallback.
                    if on_timeout:
                        return on_timeout()
                    
                    result = current_value if current_value is not None else default
                    if self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                        return result
                    else:
                        if not infinite_attempts:
                            attempts_remaining -= 1
                        continue
                else:
                    usr_input_cleaned = usr_input_raw.strip()
                    usr_input_lower = usr_input_cleaned.lower()
                    self.on_event("input_received", {
                        "raw": usr_input_raw,
                        "cleaned": usr_input_cleaned,
                        "prompt": prompt
                    })

                # Handle quit/help commands.
                # if usr_input_lower == quit_word.lower() if quit_word else False:
                #     if confirm:
                #         if not self._get_confirmation(confirm_prompt):
                #             self.out("Selection not confirmed. Please try again.\n")
                #             if not infinite_attempts:
                #                 attempts_remaining -= 1
                #             continue                        
                #     return self.USER_QUIT
                # if usr_input_lower == help_word.lower() if help_word else False:
                #     if help_callback:
                #         help_callback()
                #     continue
                quit_help_result = self._handle_quit_and_help(
                    usr_input_lower, quit_word, help_word, help_callback, confirm, confirm_prompt
                )
                if quit_help_result == "retry":
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue
                if quit_help_result is not None:
                    return quit_help_result


                # Max input length enforcement
                if max_input_len and len(usr_input_cleaned) > max_input_len:
                    self.out(f'## Input too long. Max input size: {max_input_len} characters. ##')
                    self.on_event("input_invalid", {
                        "input": usr_input_cleaned,
                        "reason": "Input too long",
                        "max_len": max_input_len,
                    })
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue

                # Handle pressing enter (empty input).
                if not usr_input_cleaned:
                    result = None
                    if current_value is not None:
                        result = current_value
                    elif default is not None:
                        result = default
                    
                    if result is not None:
                        if self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                            return result
                        if not infinite_attempts:
                            attempts_remaining -= 1
                        continue
                    if allow_free_text and not current_options:
                        return ""
                    self.out(f'## No input provided and no default/current value available. ##\n')
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue

                # Multi-select logic: handle comma-separated choices, check if all are enabled.
                # if allow_multi and processed_keys:
                #     parts = [part.strip() for part in usr_input_cleaned.split(",")]
                #     chosen = []
                #     bad = []
                #     for part in parts:
                #         key_candidate = processed_keys.get(part.lower()) or hotkeys.get(part.lower())
                #         enabled = option_enabled.get(key_candidate, True)
                #         if not enabled:
                #             bad.append(part)
                #             continue
                #         if part.lower() in processed_keys:
                #             chosen.append(processed_keys[part.lower()])
                #         elif part.lower() in hotkeys:
                #             chosen.append(hotkeys[part.lower()])
                #         else:
                #             bad.append(part)
                #     if bad:
                #         self.out(f'## Invalid option(s): {", ".join(bad)} ##')
                #         if not infinite_attempts:
                #             attempts_remaining -= 1
                #         continue
                #     if len(chosen) < min_choices or (max_choices and len(chosen) > max_choices):
                #         self.out(f'## Select between {min_choices} and {max_choices or "∞"} options. ##')
                #         if not infinite_attempts:
                #             attempts_remaining -= 1
                #         continue
                    
                #     result = [format_return(c) for c in chosen]
                #     if self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                #         return result
                #     if not infinite_attempts:
                #         attempts_remaining -= 1
                #     continue
                if allow_multi and processed_keys:
                    result = self._handle_multi_select(
                        usr_input_cleaned, processed_keys, hotkeys, option_enabled, formatter,
                        min_choices, max_choices, format_return
                    )
                    if result is not None and self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                        return result
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue

                # Single-select: resolve to key or hotkey, then check if enabled.
                # key = None
                # if processed_keys and usr_input_lower in processed_keys:
                #     key = processed_keys[usr_input_lower]
                # elif hotkeys and usr_input_lower in hotkeys:
                #     key = hotkeys[usr_input_lower]
                # else:
                #     if fuzzy_match and processed_keys:
                #         matches = difflib.get_close_matches(usr_input_lower, processed_keys, n=3, cutoff=fuzzy_cutoff)
                #         if matches:
                #             self.out(f'Did you mean: {", ".join(matches)}?')
                #             if not infinite_attempts:
                #                 attempts_remaining -= 1
                #             continue

                # if key is not None:
                #     enabled = option_enabled.get(key, True)
                #     if not enabled:
                #         self.out(formatter(f"## Option '{usr_input_cleaned}' is disabled. ##", "error"))
                #         if not infinite_attempts:
                #             attempts_remaining -= 1
                #         continue
                #     result = format_return(key)
                #     if self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                #         return result
                #     if not infinite_attempts:
                #         attempts_remaining -= 1
                #     continue
                result = self._handle_single_select(
                    usr_input_cleaned, processed_keys, hotkeys, option_enabled, formatter,
                    fuzzy_match, fuzzy_cutoff, current_options, format_return
                )
                if result is not None and self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                    return result
                if result is not None:
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue


                # Free text fallback: optional transformer and validator.
                # if allow_free_text:
                #     value = usr_input_cleaned
                #     if transformer:
                #         try:
                #             value = transformer(value)
                #         except Exception as e:
                #             self.out(f'## Input transformation failed: {e} ##')
                #             if not infinite_attempts:
                #                 attempts_remaining -= 1
                #             continue
                #     if validator:
                #         valid, msg = validator(value)
                #         if not valid:
                #             self.out(f'## {msg or "Invalid input"} ##')
                #             if not infinite_attempts:
                #                 attempts_remaining -= 1
                #             continue
                #     if self._confirm_value(value, confirm, confirm_prompt, confirm_message):
                #         return value
                #     if not infinite_attempts:
                #         attempts_remaining -= 1
                #     continue
                if allow_free_text:
                    result = self._handle_free_text_input(usr_input_cleaned, transformer, validator)
                    if result is not None and self._confirm_value(result, confirm, confirm_prompt, confirm_message):
                        return result
                    if not infinite_attempts:
                        attempts_remaining -= 1
                    continue
                

                self.out(f'## "{usr_input_cleaned}" is not a valid option. ##\n')
                self.on_event("input_invalid", {
                    "input": usr_input_cleaned,
                    "reason": "Unknown option",
                    "valid_keys": list(current_options.keys())
                })
                if not infinite_attempts:
                    attempts_remaining -= 1

            # If here, attempts exhausted
            if not infinite_attempts and attempts > 0:
                self.out(f'## Maximum attempts reached. ##\n')
            return current_value if current_value is not None else default
        
        finally:
            # Always clear readline completer and save history if needed
            if auto_complete and readline:
                readline.set_completer(None)

            if history_file and readline:
                try:
                    readline.write_history_file(history_file)
                except Exception as e:
                    print(f"Warning: Could not save history file: {e}")