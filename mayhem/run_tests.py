#!/usr/bin/python3
"""run_tests.py — RUN ciscoconfparse's own pytest suite and print a parseable summary.

Invoked via the /mayhem/ciscoconfparse-tests ELF launcher (NOT python directly), so the
verify-repo sabotage oracle can neuter the launcher and prove the test oracle is behavioral.

ciscoconfparse ships known-answer pytest cases under tests/ (test_CiscoConfParse.py,
test_Ccp_Util.py, test_Ccp_Abc.py, test_Models_Cisco.py, test_Models_Asa.py,
test_Models_Junos.py) — they assert parsed-config structure, interface/IP object math, and
model classification EXACTLY. A no-op / "exit(0)" / behavior-altering patch to ciscoconfparse
cannot pass them.

It runs the suite, writes a JUnit XML, parses the counts, and prints one line:

    RUNTESTS tests=<n> passed=<p> failed=<f> skipped=<s>

Exit 0 iff failed == 0. mayhem/test.sh parses that line into a CTRF report.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

import pytest

SRC = os.environ.get("SRC", "/mayhem")
XML = "/tmp/ciscoconfparse-junit.xml"
TESTS_DIR = os.path.join(SRC, "tests")


def main() -> int:
    # Run from the tests/ dir (matches upstream runtests.sh; conftest does sys.path.insert(0,"..")).
    os.chdir(TESTS_DIR)
    pytest.main([
        "-q", "-p", "no:cacheprovider",
        # UPSTREAM (d804b5a, ciscoconfparse 1.7.16) predates test_Ccp_Abc.py and the
        # IPv4-in-IPv6 Python-3.13 deselect the current v2 harness carries for 1.9.52 —
        # neither exists in tests/ at this commit (BACKPORT.md: old code, current harness).
        "test_CiscoConfParse.py",
        "test_Ccp_Util.py",
        # At UPSTREAM, test_dns_lookup only catches dns.exception.Timeout, not
        # dns.resolver.NoNameservers — the gate's air-gapped (--network none) re-run of this
        # suite hits the latter and fails, which every honest patch would too. Deselect it;
        # the other 462 assertions stay as the behavioral oracle.
        "--deselect", "test_Ccp_Util.py::test_dns_lookup",
        "test_Models_Cisco.py",
        "test_Models_Asa.py",
        "test_Models_Junos.py",
        "--junitxml", XML,
    ])

    root = ET.parse(XML).getroot()
    suites = root.findall("testsuite") or ([root] if root.tag == "testsuite" else [])
    if not suites:
        print("RUNTESTS tests=0 passed=0 failed=1 skipped=0")
        return 1

    tests = failed = skipped = 0
    for s in suites:
        tests += int(s.get("tests", 0))
        failed += int(s.get("failures", 0)) + int(s.get("errors", 0))
        skipped += int(s.get("skipped", 0))
    passed = tests - failed - skipped

    print(f"RUNTESTS tests={tests} passed={passed} failed={failed} skipped={skipped}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
