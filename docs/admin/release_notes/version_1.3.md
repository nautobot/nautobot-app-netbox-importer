# v1.3 Release Notes

This document describes all new features and changes in the release `1.3`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## v1.3.0 (2021-05-11)

### Added

- `#40` - Added separate `import_netbox_objectchange_json` command that can be used to import `ObjectChange`
  (change logging) records, which are intentionally not included in the existing `import_netbox_json` command.
- `#43` - `ImageAttachment` records are now imported correctly, as are the `front_image` and `rear_image` fields
  on `Device` records.

### Fixed

- `#42` - Clarify in the README which NetBox versions are currently supported.
- `#43`- Work around nautobot/nautobot#393, an issue encountered when importing `VirtualChassis` records for which
  the `master` `Device` occupies a `vc_position` other than `1`.
- `#43` - Development and CI testing now defaults to Nautobot 1.0.0 instead of 1.0.0b3
- `#43` - Fix test approach to ensure that tests execute against the test database rather than the development database.

### Changed

- `#44` - Revised Docker development environment to use `nautobot-dev` image as base, removed Python packaging dependency on `nautobot` core package.
