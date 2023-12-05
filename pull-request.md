# Closes: NaN

## What's Changed

- Dropped NetBox 2.x support.
- Implemented NetBox 3.0 support.
- Implemented NetBox 3.1 support.
- Implemented NetBox 3.2 support.
- Dropped Nautobot 1.x support.
- Implemented Nautobot 2.0 support.

## To Do

- [x] Implement tests.
- [x] Create `CablePath` objects after importing to Nautobot.
    - `CablePath` objects seems to be created out of the box.
- [ ] Implement SSoT Job.
- [ ] Resolve TBDs in `nautobot_netbox_importer/diffsync/netbox.py`.
- [ ] Write developer documentation.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: ['Rack R308 (Row 3) and power panel Panel 4 (MDF) are in different locations']`.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: {'parent': ['A Location of type Location may only have a Location of the same type as its parent.']}`.
- [ ] Allow DiffSync deleting in Nautobot?
- [ ] Add only `ManyToMany` field values?
- [ ] Implement NetBox 3.3 support.
- [ ] Implement NetBox 3.4 support.
