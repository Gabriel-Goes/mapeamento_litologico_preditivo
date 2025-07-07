# import qgis libs so that ve set the correct sip api version
try:  # noqa: SIM105 - simple try/except for optional dependency
    import qgis  # pylint: disable=W0611
except ImportError:  # pragma: no cover - optional dependency not present
    pass
