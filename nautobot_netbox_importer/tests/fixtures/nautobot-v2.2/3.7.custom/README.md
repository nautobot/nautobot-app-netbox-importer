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
    auth.Group \
    auth.User \
    contenttypes.ContentType \
    dcim.Cable \
    dcim.CableTermination \
    dcim.Device \
    dcim.DeviceRole \
    dcim.DeviceType \
    dcim.Manufacturer \
    dcim.RackRole \
    dcim.Rack \
    dcim.Site \
    extras.ConfigContext \
    extras.CustomField \
    extras.CustomFieldChoiceSet \
    extras.JournalEntry \
    extras.ObjectChange \
    ipam.FHRPGroup \
    ipam.IPAddress \
    ipam.Role \
    ipam.Prefix \
    tenancy.Tenant \
    tenancy.TenantGroup \
    users.ObjectPermission \

diff -u /tmp/netbox_data.json ./input.json
v /tmp/netbox_data.json ./input.json
```
