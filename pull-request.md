# Closes: NaN

## What's Changed

- Dropped NetBox 2.x support.
- Dropped ChangeLog import.
- Implemented NetBox 3.0 - 3.4 support.
- Dropped Nautobot 1.x support.
- Implemented Nautobot 2.0 support.

## To Do

- [x] Implement tests.
- [x] Create `CablePath` objects after importing to Nautobot.
    - `CablePath` objects seems to be created out of the box.
- [x] Write developer documentation.
- [x] Test for number of validation errors.
- [x] Auto skip fields not present in Nautobot model.
- [x] Use `dcim.cabletermination[x]` as a source model.
- [ ] Better output content_types and fields mappings.
- [ ] Implement writing `created` and `last_updated` fields.
- [ ] Test to re-run the import.
- [ ] Parametrize importer to fail if any validation fails.
- [ ] Summarize overall stats including validation errors types with counts.
- [ ] Resolve TBDs in `nautobot_netbox_importer/diffsync/netbox.py`.
- [ ] Refactor fields factories.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: ['Rack R308 (Row 3) and power panel Panel 4 (MDF) are in different locations']`.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: {'parent': ['A Location of type Location may only have a Location of the same type as its parent.']}`.
- [ ] Remove debug prints.

## Later

- [ ] Implement SSoT Job.
    - [ ] Allow DiffSync deleting in Nautobot?
    - [ ] Add-only `ManyToMany` field values?
    - [ ] Add-only custom field values?
