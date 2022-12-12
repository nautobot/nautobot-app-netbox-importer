# v1.0 Release Notes

This document describes all new features and changes in the release `1.0`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## v1.0.1 (2021-03-09)

### Added

- #3 - Data exports from NetBox v2.10.5 are now permitted for importing.

### Changed

- Improved logging of messages when various errors are encountered and handled.
- Added more attributes to Device `_identifiers` list to further ensure uniqueness of individual Device records.

### Fixed

- #2 - `ObjectNotFound` is now caught when handling `GenericForeignKey` fields
- #4 - Django `ValidationError` is now caught when creating/updating Nautobot data
- #5 - Pydantic `ValidationError` is now caught when constructing internal data models
- `Device`s with no specified `name` can now be imported successfully.
- Device component templates are now imported _after_ `Device`s so as to avoid encountering errors when components are unexpectedly created from the templates.
- `VRF`s with no specified `rd` can now be imported successfully.
- #8 - Fixed errors in `Service` and `PowerOutletTemplate` model definitions that prevented them from being imported.

## v1.0.0 (2021-02-24)

Initial public release
