# v1.1 Release Notes

This document describes all new features and changes in the release `1.1`. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

## v1.1.0 (2021-04-07)

### Added

- Now supports import from NetBox versions up to 2.10.8
- Now compatible with Nautobot 1.0.0b3

### Changed

- #28 - Rework of internal data representations to use primary keys instead of natural keys for most models.
  This should fix many "duplicate object" problems reported by earlier versions of this plugin (#11, #19, #25, #26, #27)

### Fixed

- #10 - Catch `ObjectDoesNotExist` exceptions instead of erroring out
- #12 - Duplicate object reports should include primary key
- #13 - Allow import of objects with custom field data referencing custom fields that no longer exist
- #14 - Allow import of objects with old custom field data not matching latest requirements
- #24 - Allow import of EUI MACAddress records

### Removed

- No longer compatible with Nautobot 1.0.0b2 and earlier
