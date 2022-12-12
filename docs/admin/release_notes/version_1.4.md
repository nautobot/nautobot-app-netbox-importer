# v1.4 Release Notes

This document describes all new features and changes in the release `1.4`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## 1.4.2 (2022-02-16)

### Changed

- #68 - Switched from Travis CI to GitHub Actions.

### Fixed

- #63 - Fixed failure importing CustomField records into Nautobot 1.2.3 and later.
- #64 - Fixed failure importing ObjectPermissions containing a list of multiple constraints.

## 1.4.0 (2021-06-29)

### Added

- #52 - Added `--bypass-data-validation` optional flag on import for users who absolutely need to be able to import data from NetBox that will fail Nautobot's data validation checks.

### Fixed

- #47 - `ChangeLogged` objects honour `created` date when they are imported and also a related "updated" `ObjectChange` is created as result of the migration.
- #51 - Potential `KeyError` when importing certain `JobResult` records.
