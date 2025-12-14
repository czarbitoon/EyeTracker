import importlib


def test_core_main_callable():
    from app.core.app import main
    assert callable(main)


def test_import_panic_overlay():
    from app.ui.panic_overlay import PanicOverlay  # noqa: F401


def test_run_module_entry():
    spec = importlib.util.find_spec("MonocularTracker.core.app")
    assert spec is not None, "core.app module should be discoverable"
