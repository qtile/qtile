import asyncio
import builtins
import codeop
import contextlib
import io
import re
import traceback
from typing import Any

from libqtile.log_utils import logger

ATTR_MATCH = re.compile(r"([\w\.]+?)(?:\.([\w]*))?$")


def mark_unavailable(func):
    def _wrapper(*args, **kwargs):
        print(f"'{func.__name__}' is disabled in this REPL.")

    return _wrapper


def make_safer_env():
    """
    Returns a dict to be passed to the REPL's global environment.

    Can be used to block harmful commands.
    """

    # Interactive help blocks REPL and will cause qtile to hand
    original_help = builtins.help

    def safe_help(*args):
        """Print help on a specified object."""
        if not args:
            print("Interactive help() is disabled in this REPL.")
        else:
            return original_help(*args)

    # Store original help so we can still call it safely
    builtins.help = safe_help

    # Mask other builtins
    builtins.input = mark_unavailable(builtins.input)

    return {"__builtins__": builtins}


def parse_completion_expr(text):
    """
    Parses an input like 'qtile.win' or 'qtil' and splits it into:
    - object_expr: what to evaluate or look up ('qtile', 'qtil')
    - attr_prefix: what to complete ('', 'win', etc.)
    """
    match = ATTR_MATCH.search(text)
    if not match:
        return None, None
    obj_expr, attr_prefix = match.groups()
    return obj_expr, attr_prefix or ""


def get_completions(text, local_vars):
    expr, attr_prefix = parse_completion_expr(text)

    # Case 1: Completing a top-level variable name
    if "." not in text:
        return [name for name in local_vars if name.startswith(expr)]

    # Case 2: Completing an attribute
    try:
        base = eval(expr, {}, local_vars)
        options = [attr for attr in dir(base) if attr.startswith(attr_prefix)]
        options = [
            f"{expr}.{attr}" + ("(" if callable(getattr(base, attr)) else "") for attr in options
        ]
        options = list(filter(None, options))
        return options
    except Exception:
        return []


class QtileREPL:
    """
    Provides a REPL interface to allow users to inspect qtile's internals via
    a more intuitive/familiar interface compared to `qtile shell`.
    """

    def __init__(self):
        self.buffer = ""
        self.compiler = codeop.Compile()

    async def start(self, qtile) -> dict[str, Any]:
        logger.debug("Starting Qtile REPL")

        self.locals = {"qtile": qtile, **make_safer_env()}
        self.compiler = codeop.CommandCompiler()

        return {"output": "Connected to Qtile REPL\nPress Ctrl+C to exit.\n"}

    def evaluate_code(self, code):
        with io.StringIO() as stdout:
            # Capture any stdout and direct to a buffer
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stdout):
                try:
                    try:
                        # Try eval (for expressions)
                        expr_code = compile(code, "<stdin>", "eval")
                        result = eval(expr_code, self.locals)
                        if result is not None:
                            # We can use print here as we've redirected stdout
                            print(repr(result))
                    except SyntaxError:
                        # Fallback to exec (for statements)
                        exec(self.compiler(code), self.locals)
                except Exception:
                    traceback.print_exc()

            return stdout.getvalue()

    # `request` and the return could potentially be typed more strongly
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a REPL request by the client. Caller must check that the session isn't locked"""
        match request:
            case {"completion": prefix}:
                matches = get_completions(prefix, self.locals)
                return {"matches": matches}

            case {"code": code}:
                if not code.strip():
                    return {"output": ""}
                else:
                    output = await asyncio.to_thread(self.evaluate_code, code)
                    return {"output": output.strip()}

            case _:
                return {"output": "Internal REPL error\n"}
