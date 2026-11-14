import pytest

from bmfactory.inspector.coverage import ControlInfo


@pytest.mark.system3
def test_dump_capitaline_window():
    from bmfactory.inspector.dump import dump_window

    controls = dump_window("Capitaline")
    assert len(controls) >= 10
    assert all(isinstance(c, ControlInfo) for c in controls)
