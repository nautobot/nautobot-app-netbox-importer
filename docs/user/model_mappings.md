# NetBox to Nautobot Model and Field Mappings

Nautobot and NetBox share many of the same model and field names, however, there
are a few cases where different names are used, an incompatibility may exist, or
a model or field in NetBox does not exist in Nautobot. The below table documents
known differences.

<br>

| NetBox Model | Nautobot Model | Netbox Field | Nautobot Field |
| :----------: | :------------: | :----------: | :------------: |
| JournalEntry | Note | | |
| JournalEntry | Note | created_by | user |
| JournalEntry | Note | comments | note |
| CustomLink | CustomLink | url | target_url |
| ProviderNetwork | ProviderNetwork | service_id | *unsupported* |
