# Changelog

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
- Device component templates are now imported *after* `Device`s so as to avoid encountering errors when components are unexpectedly created from the templates.
- `VRF`s with no specified `rd` can now be imported successfully.
- #8 - Fixed errors in `Service` and `PowerOutletTemplate` model definitions that prevented them from being imported.


## v1.0.0 (2021-02-24)

Initial public release
