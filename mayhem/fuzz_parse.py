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
"""
import atheris
import io
import sys

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


# Reconstructed from the mayhemheroes fork at FUZZED (a8f4bd8897297e1675d05104c6aae79cf2b5b2f0),
# not the live v2 harness: the live one added IndexError/KeyError to the caught-exceptions tuple,
# which swallows exactly the CWE-129 (array index) crashes run 9 found, and renamed/reordered the
# syntax map (dropping 'terraform', adding 'iosxr', changing asa/junos delimiters) — either change
# alone remaps the same fuzzer bytes onto a different syntax/delimiter and misses the original
# crash paths (BACKPORT.md, "Input-interface caveat").
syntax_to_comment = {
    'ios': '!',
    'nxos': '!',
    'asa': '"',
    'junos': '/',
    'terraform': '#',
}
syntaxes = list(syntax_to_comment.keys())


def TestOneInput(data):
    fdp = fuzz_helpers.EnhancedFuzzedDataProvider(data)
    syntax = fdp.PickValueInList(syntaxes)
    comment = syntax_to_comment[syntax]
    config_stmts = fdp.ConsumeRemainingString().splitlines()

    try:
        with nostdout():
            CiscoConfParse(config_stmts, syntax=syntax, comment=comment)
    except (AssertionError, NotImplementedError, AttributeError, ValueError):
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
