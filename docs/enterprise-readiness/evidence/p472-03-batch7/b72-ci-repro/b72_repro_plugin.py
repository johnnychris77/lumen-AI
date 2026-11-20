"""B7.2 reproduction plugin: start a tenant-A-bound background scheduler for the
GET /api/pulse/command-center case; B72_GUARD=off disables the harness guard."""
import os

import pytest

_sched = []

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if "pulse/command-center" not in item.nodeid or "refused_and_change_nothing" not in item.nodeid:
        return
    mod = item.module
    if os.environ.get("B72_GUARD") == "off":
        mod._pause_running_schedulers = lambda found=None: []
    _sched.append(mod._tenant_bound_background_scheduler(mod.TENANT_A))

def pytest_runtest_teardown(item):
    while _sched:
        _sched.pop().shutdown(wait=False)
