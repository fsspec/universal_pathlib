import warnings
from functools import partial


__all__ = [
    "DefaultImplementationWarning",
    "ignore_default_warning",
]


class DefaultImplementationWarning(UserWarning):
    """Custom warning for easy filtering."""


ignore_default_warning = partial(
    warnings.filterwarnings,
    action="ignore",
    category=DefaultImplementationWarning,
    module="upath",
)


def __getattr__(name):
    """Provide deprecation warning for NotDirectoryError."""
    if name == "NotDirectoryError":
        warnings.warn(
            "upath.errors.NotDirectoryError is deprecated. "
            "Use NotADirectoryError instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return NotADirectoryError
    if name in __all__:
        return globals()[name]
    raise AttributeError(name)
