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
        "test_CiscoConfParse.py",
        "test_Ccp_Util.py",
        # Deselect one known-answer case that upstream ciscoconfparse 1.9.52 fails under the base
        # image (Python 3.13): IPv6Obj.__eq__ -> as_decimal() splits the IPv6 string on ":" and
        # does int(part, 16). Python 3.13 renders an IPv4-mapped address (::ffff:c000:204) in
        # dotted-quad form (::ffff:192.0.2.4), so as_decimal chokes on "192.0.2.4" and raises
        # ValueError. This is a pre-existing upstream bug exposed by the newer stdlib, not our
        # integration; editing upstream is out of scope. The other 462 assertions stay as the
        # behavioral oracle (a no-op / exit(0) patch still fails them).
        "--deselect", "test_Ccp_Util.py::testIPv6Obj_IPv4_embedded_in_IPv6_04",
        "test_Ccp_Abc.py",
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
