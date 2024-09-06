"""Utility functions and classes for nautobot_netbox_importer."""

from typing import Any, Generator, Iterable, Tuple

from tqdm import tqdm


class ProgressBar(tqdm):
    """Custom subclass of tqdm progress bar implementation."""

    def __init__(self, *args, **kwargs):
        """Construct a progress bar."""
        if "bar_format" not in kwargs:
            kwargs["bar_format"] = "{l_bar}{bar}| {n_fmt:>6}/{total_fmt:>6} [{elapsed}]"
        if "verbosity" in kwargs:
            verbosity = kwargs.pop("verbosity")
            kwargs["disable"] = verbosity < 1
        super().__init__(*args, **kwargs)

    def diffsync_callback(self, stage, current, total):
        """Callback for diffsync progress."""
        if self.disable:
            return None
        if stage not in self.desc:
            if self.desc:
                self.update(self.total - self.n)
                self.refresh()
                self.fp.write("\n")
            self.set_description(stage)
            self.reset(total=total)
        return self.update(current - self.n)


def get_field_choices(items: Iterable) -> Generator[Tuple[Any, Any], None, None]:
    """Yield all choices from a model field, flattening nested iterables."""
    for key, value in items:
        if isinstance(value, (list, tuple)):
            yield from get_field_choices(value)
        else:
            yield key, value
