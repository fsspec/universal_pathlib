import warnings


def __getattr__(name):
    if name == "NotDirectoryError":
        warnings.warn(
            "upath.errors.NotDirectoryError is deprecated. "
            "Use NotADirectoryError instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return NotADirectoryError
    raise AttributeError(name)
