#!/usr/bin/env python3
"""fuzz_parse.py — Atheris harness driving ciscoconfparse's CiscoConfParse() parser.

Feeds fuzzer-derived config text (split into statements) through the parser under a
randomly-chosen, upstream-valid `syntax`, exercising the tokenizer / brace handling /
line-classification paths. Run via the /mayhem/fuzz-parse ELF launcher (Mayhem needs an
ELF target), which exec()s `python3 mayhem/fuzz_parse.py`; the Python process IS the
libFuzzer/Atheris target.

`instrument_imports(include=['ciscoconfparse'])` scopes Atheris coverage to the fuzzed
package only (a bare instrument-all balloons fork-child startup — see the atheris fork-mode
trap). loguru's default sink is removed and stdout/stderr are muted so parser chatter does
not swamp the run.

A per-input SIGALRM watchdog guards against a single pathological config hanging the parse.
"""
import atheris
import io
import sys
import signal

import fuzz_helpers

with atheris.instrument_imports(include=['ciscoconfparse']):
    from ciscoconfparse import CiscoConfParse

# ciscoconfparse logs through loguru; silence it so parser chatter does not dominate output.
try:
    import loguru
    loguru.logger.remove()
except Exception:
    pass

import contextlib


@contextlib.contextmanager
def nostdout():
    save_out, save_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        yield
    finally:
        sys.stdout, sys.stderr = save_out, save_err


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _alarm)

# Upstream ALL_VALID_SYNTAX (ciscoconfparse 1.9.x). 'junos' is brace-delimited.
syntax_to_comment = {
    'ios': '!',
    'nxos': '!',
    'iosxr': '!',
    'asa': '!',
    'junos': '#',
}
syntaxes = list(syntax_to_comment.keys())


def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    syntax = fdp.PickValueInList(syntaxes) if hasattr(fdp, 'PickValueInList') else \
        syntaxes[fdp.ConsumeIntInRange(0, len(syntaxes) - 1)]
    comment = syntax_to_comment[syntax]
    config_stmts = fdp.ConsumeRemainingString().splitlines()

    signal.setitimer(signal.ITIMER_REAL, 10.0)
    try:
        with nostdout():
            CiscoConfParse(config_stmts, syntax=syntax, comment=comment)
    except _Timeout:
        return -1
    except (AssertionError, NotImplementedError, AttributeError, ValueError, KeyError, IndexError):
        return -1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
