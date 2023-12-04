# Closes: NaN

## What's Changed

- Implemented NetBox 3.0 support.

## To Do

- [ ] Implement tests.
- [ ] Implement SSoT Job.
- [ ] Resolve TBDs in `nautobot_netbox_importer/diffsync/netbox.py`.
- [ ] Write developer documentation.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: ['Rack R308 (Row 3) and power panel Panel 4 (MDF) are in different locations']`.
- [ ] Resolve validation error: `django.core.exceptions.ValidationError: {'parent': ['A Location of type Location may only have a Location of the same type as its parent.']}`.
- [ ] Create `CablePath` objects after importing to Nautobot.
- [ ] Allow DiffSync Deleting in Nautobot?
- [ ] Add `ManyToMany` field values only?
