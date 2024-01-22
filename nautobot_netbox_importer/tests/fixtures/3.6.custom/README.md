# Custom NetBox Importer Test

This folder contains data fixtures for testing the NetBox Importer app.

To dump and use data from a NetBox instance, run the following command:

```bash
./manage.py dumpdata \
    --traceback \
    --format=json \
    --indent=2 \
    --natural-primary \
    --natural-foreign \
    --output=/tmp/netbox_data.json \
    contenttypes.ContentType \
    extras.CustomField \
    auth.Group \
    auth.User \
    tenancy.TenantGroup \
    tenancy.Tenant \
    ipam.FHRPGroup \
    extras.JournalEntry \
    extras.ObjectChange \

diff -u /tmp/netbox_data.json ./input.json
mv /tmp/netbox_data.json ./input.json
```

