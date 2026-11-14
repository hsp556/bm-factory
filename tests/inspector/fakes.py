"""Fake UI elements exposing only the read-only surface the inspector may use; anything else fails the test."""

_ALLOWED_INFO = {"control_type", "automation_id", "class_name"}


class _Info:
    def __init__(self, control_type, automation_id, class_name):
        self.__dict__["_d"] = {"control_type": control_type, "automation_id": automation_id, "class_name": class_name}

    def __getattr__(self, name):
        if name in _ALLOWED_INFO:
            return self.__dict__["_d"][name]
        raise AssertionError(f"inspector touched element_info.{name}")

    def __setattr__(self, name, value):
        raise AssertionError(f"inspector set element_info.{name}")


class Fake:
    def __init__(self, text="", ctype="Button", auto_id="", cls="", kids=()):
        self.__dict__["_text"] = text
        self.__dict__["_kids"] = list(kids)
        self.__dict__["_info"] = _Info(ctype, auto_id, cls)

    def __getattr__(self, name):
        d = self.__dict__
        if name == "children":
            return lambda: d["_kids"]
        if name == "window_text":
            return lambda: d["_text"]
        if name == "element_info":
            return d["_info"]
        raise AssertionError(f"inspector touched {name}")

    def __setattr__(self, name, value):
        raise AssertionError(f"inspector set {name}")
