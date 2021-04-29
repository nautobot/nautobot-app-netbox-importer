# Changelog

## v1.3.0 (2021-04-29)

### Added

- #40 - Added separate `import_netbox_objectchange_json` command that can be used to import `ObjectChange`
  (change logging) records, which are intentionally not included in the existing `import_netbox_json` command.
- #43 - `ImageAttachment` records are now imported correctly, as are the `front_image` and `rear_image` fields
  on `Device` records.

### Fixed

- #42 - Clarify in the README which NetBox versions are currently supported.
- #43 - Work around nautobot/nautobot#393, an issue encountered when importing `VirtualChassis` records for which
  the `master` `Device` occupies a `vc_position` other than `1`.
- #43 - Development and CI testing now defaults to Nautobot 1.0.0 instead of 1.0.0b3
- #43 - Fix test approach to ensure that tests execute against the test database rather than the development database.

## v1.2.1 (2021-04-20)

### Fixed

- #37 - Custom fields are now handled correctly on the second pass of the importer as well

## v1.2.0 (2021-04-14)

### Added

- #33 - Now supports the Django parameters `--no-color` and `--force-color`

### Changed

- #29 - Improved formatting of log output, added dynamic progress bars using `tqdm` library

### Fixed

- #31 - Records containing outdated custom field data should now be updated successfully
- #32 - Status objects should not show as changed when resyncing data


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
