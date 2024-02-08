"""Utility functions and classes for nautobot_netbox_importer."""
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
