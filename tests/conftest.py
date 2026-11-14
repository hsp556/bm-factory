import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("BM_SYSTEM3") == "1":
        return
    skip = pytest.mark.skip(reason="needs the live Capitaline desktop; set BM_SYSTEM3=1 on System 3")
    for item in items:
        if "system3" in item.keywords:
            item.add_marker(skip)
