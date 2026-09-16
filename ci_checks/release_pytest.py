"""Opt-in pytest plugin: observe source binding before/after actual execution.

Usage: pytest -p release_pytest --release-root PROJECT --junitxml=NEW.xml ...
Existing report/binding paths are rejected before any test runs.
"""
import json
import os
from pathlib import Path

import pytest

from release_evidence import VERSION, sources, summary, sidecar


def pytest_addoption(parser):
    parser.addoption('--release-root', help='Bind test execution to this runtime tree')


def pytest_sessionstart(session):
    root = session.config.getoption('--release-root')
    if not root:
        raise pytest.UsageError('release_pytest requires --release-root')
    xml = session.config.getoption('xmlpath', default=None)
    if not xml:
        raise pytest.UsageError('release_pytest requires --junitxml')
    report = Path(xml).resolve()
    if report.exists() or sidecar(report).exists():
        raise pytest.UsageError('Test report must use a new path; previous evidence is immutable')
    session.config._release_capture = (Path(root).resolve(), report, sources(root))


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    yield  # JUnit must first finish writing its report.
    captured = getattr(session.config, '_release_capture', None)
    if captured is None:
        return
    root, path, before = captured
    after = sources(root)
    report = summary(path)
    record = {'version': VERSION, 'sources_before': before, 'sources_after': after,
              'junit_sha256': report['sha256'], 'cases': report['cases'], 'exit_code': int(exitstatus)}
    with sidecar(path).open('x') as out:
        json.dump(record, out, sort_keys=True, ensure_ascii=False)
        out.flush(); os.fsync(out.fileno())
