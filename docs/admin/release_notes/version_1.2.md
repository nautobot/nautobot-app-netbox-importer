# v1.2 Release Notes

This document describes all new features and changes in the release `1.2`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## v1.2.1 (2021-04-20)

### Fixed

- `#37` - Custom fields are now handled correctly on the second pass of the importer as well

## v1.2.0 (2021-04-14)

### Added

- `#33` - Now supports the Django parameters `--no-color` and `--force-color`

### Changed

- `#29` - Improved formatting of log output, added dynamic progress bars using `tqdm` library

### Fixed

- `#31` - Records containing outdated custom field data should now be updated successfully
- `#32` - Status objects should not show as changed when resyncing data
