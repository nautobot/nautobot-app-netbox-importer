# Demo Execution of NetBox Importer

## Prerequisites

- Docker along with Docker Compose plugin
- Python version 3.8 or higher
- [Invoke](http://www.pyinvoke.org/)

## Configuration

To configure the environment, execute the following commands:

```bash
git clone https://github.com/nautobot/nautobot-app-netbox-importer.git
cd nautobot-app-netbox-importer
cp development/creds.example.env development/creds.env

invoke build
```

These commands will clone the NetBox Importer repository, create a copy of the example credentials file, and build the Docker image for the NetBox Importer.

Example output from the `invoke build` command:

```
Building Nautobot with Python 3.11...
Running docker compose command "build"
#0 building with "default" instance using docker driver

#1 [nautobot internal] load build definition from Dockerfile
#1 transferring dockerfile: 3.94kB done
#1 DONE 0.0s

#2 [nautobot internal] load metadata for ghcr.io/nautobot/nautobot-dev:2.0.6-py3.11
#2 DONE 0.5s

...

#15 [nautobot stage-0 11/11] COPY development/nautobot_config.py /opt/nautobot/nautobot_config.py
#15 DONE 0.3s

#16 [nautobot] exporting to image
#16 exporting layers
#16 exporting layers 3.2s done
#16 writing image sha256:5b25fc8b27c938dd299878bd224a9a8d5fceed83e0a0122c7b7fb82ce8ec83b4
#16 writing image sha256:5b25fc8b27c938dd299878bd224a9a8d5fceed83e0a0122c7b7fb82ce8ec83b4 done
#16 naming to docker.io/nautobot-netbox-importer/nautobot:2.0.6-py3.11 0.0s done
#16 DONE 3.2s
```

## Start Nautobot

To start Nautobot, execute the following command:

```bash
invoke debug --service nautobot
```

This command will launch a local instance of Nautobot with the NetBox Importer plugin installed, operating in debug mode. The Docker Compose logs for Nautobot will be displayed in the current terminal, allowing you to monitor the activity.

Example debug logs from Nautobot:

```
Starting nautobot in debug mode...
Running docker compose command "up"
 Network nautobot-netbox-importer_default  Creating
 Network nautobot-netbox-importer_default  Created
 Volume "nautobot-netbox-importer_postgres_data"  Creating
 Volume "nautobot-netbox-importer_postgres_data"  Created
 Container nautobot-netbox-importer-redis-1  Creating
 Container nautobot-netbox-importer-db-1  Creating
 Container nautobot-netbox-importer-db-1  Created
 Container nautobot-netbox-importer-redis-1  Created
 Container nautobot-netbox-importer-nautobot-1  Creating
 Container nautobot-netbox-importer-nautobot-1  Created
Attaching to nautobot-netbox-importer-nautobot-1
nautobot-netbox-importer-nautobot-1  | 09:45:17.828 DEBUG   nautobot.core.celery __init__.py        import_jobs_as_celery_tasks() :
nautobot-netbox-importer-nautobot-1  |   Importing system Jobs
nautobot-netbox-importer-nautobot-1  | 09:45:17.830 DEBUG   nautobot.core.celery __init__.py                      register_jobs() :
nautobot-netbox-importer-nautobot-1  |   Registering job nautobot.core.jobs.GitRepositorySync
nautobot-netbox-importer-nautobot-1  | 09:45:17.833 DEBUG   nautobot.core.celery __init__.py                      register_jobs() :
nautobot-netbox-importer-nautobot-1  |   Registering job nautobot.core.jobs.GitRepositoryDryRun
nautobot-netbox-importer-nautobot-1  | Performing database migrations...
nautobot-netbox-importer-nautobot-1  | Operations to perform:
nautobot-netbox-importer-nautobot-1  |   Apply all migrations: admin, auth, circuits, contenttypes, database, dcim, django_celery_beat, django_celery_results, extras, ipam, sessions, social_django, taggit, ten
ancy, users, virtualization
nautobot-netbox-importer-nautobot-1  | Running migrations:
nautobot-netbox-importer-nautobot-1  |   Applying contenttypes.0001_initial... OK
nautobot-netbox-importer-nautobot-1  |   Applying contenttypes.0002_remove_content_type_name... OK

...

nautobot-netbox-importer-nautobot-1  |   Applying virtualization.0026_change_virtualmachine_primary_ip_fields... OK

...

nautobot-netbox-importer-nautobot-1  | Starting development server at http://0.0.0.0:8080/
nautobot-netbox-importer-nautobot-1  | Quit the server with CONTROL-C.
nautobot-netbox-importer-nautobot-1  | 09:46:22.951 INFO    nautobot             __init__.py                              setup() :
nautobot-netbox-importer-nautobot-1  |   Nautobot initialized!
```

After Nautobot is installed and operational, the web interface is accessible at `http://localhost:8080/` using the default username and password: `admin`.

## Verifying Importer Options

To review available options for the importer, execute:

```bash
invoke import-netbox --help

Usage: inv[oke] [--core-opts] import-netbox [--options] [other tasks here ...]

Docstring:
  Import NetBox data into Nautobot.

Options:
  -b, --bypass-data-validation             Bypass as much of Nautobot's internal data validation logic as possible, allowing the import of data from NetBox that would be rejected as invalid if entered as-is through the GUI or REST API. USE WITH CAUTION: it is generally more desirable to *take note* of any data validation errors, *correct* the invalid data in NetBox, and *re-import* with the corrected data! (default: False)
  -d STRING, --demo-version=STRING         Version of the demo data to import from public NetBox repository (default: empty).
  -f STRING, --file=STRING                 Path to the JSON file to import.
  -i, --[no-]fields-mapping                Show a mapping of NetBox fields to Nautobot fields. Only printed when `--summary` is also specified. (default: True)
  -p, --update-paths                       Call management command `trace_paths` to update paths after the import. (default: False)
  -r, --[no-]dry-run                       Do not write any data to the database. (default: False)
  -s STRING, --save-mappings-file=STRING   File path to write the JSON mapping to. (default: generated-mappings.json)
  -t, --sitegroup-parent-always-region     When importing `dcim.sitegroup` to `dcim.locationtype`, always set the parent of a site group, to be a `Region` location type. This is a workaround to fix validation issues `'A Location of type Location may only have a Location of the same type as its parent.'`. (default: False)
  -u, --[no-]summary                       Show a summary of the import. (default: True)
  -x, --fix-powerfeed-locations            Fix panel location to match rack location based on powerfeed. (default: False)
```

This command displays usage information, a brief description, and a list of command-line options for the `import-netbox` invoke task.

## Start the Importer

To import public NetBox demo data into your local Nautobot instance, run the following command:

```bash
invoke import-netbox \
  --demo-version 3.6 \
  --save-mappings-file=generated-mappings.json \
  --no-dry-run
```

This command initiates the import of the specified version of NetBox demo data into Nautobot without a dry run, meaning changes will be saved to the database.

## Examine the Importer Log Output

The command above will produce a significant amount of output, which constitutes the import process log. The output will look similar to what is described in the following chapters.

### Starting Import

The initial output of the import process will resemble the following:

```
Running docker compose command "ps --services --filter status=running"
Running docker compose command "exec nautobot nautobot-server import_netbox --save-mappings-file=generated-mappings.json --bypass-data-validation --dry-run --field-mapping  --sitegroup-parent-always-region --summary  --no-color https://raw.githubusercontent.com/netbox-community/netbox-demo-data/master/json/netbox-demo-v3.6.json"
11:01:05.550 DEBUG   nautobot.core.celery __init__.py        import_jobs_as_celery_tasks() :
  Importing system Jobs
11:01:05.552 DEBUG   nautobot.core.celery __init__.py                      register_jobs() :
  Registering job nautobot.core.jobs.GitRepositorySync
11:01:05.554 DEBUG   nautobot.core.celery __init__.py                      register_jobs() :
  Registering job nautobot.core.jobs.GitRepositoryDryRun
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, database, dcim, django_celery_beat, django_celery_results, extras, ipam, sessions, social_django, taggit, tenancy, users, virtualization
Running migrations:
  No migrations to apply.
11:01:06.464 DEBUG   nautobot.core.celery __init__.py        import_jobs_as_celery_tasks() :
  Importing system Jobs
11:01:06.484 INFO    nautobot.extras.utils utils.py        refresh_job_model_from_job_class() :
  Refreshed Job "System Jobs: Git Repository: Sync" from <GitRepositorySync>
11:01:06.492 INFO    nautobot.extras.utils utils.py        refresh_job_model_from_job_class() :
  Refreshed Job "System Jobs: Git Repository: Dry-Run" from <GitRepositoryDryRun>
```

### Source Structure Setup

As the next step, the importer will set up the source structure. This is a process of mapping NetBox data to Nautobot data. The output will look similar to the following:

```
11:01:06.541 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuit id InternalFieldType.UUID_FIELD
11:01:06.541 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuit status_id InternalFieldType.STATUS_FIELD
11:01:06.541 DEBUG   nautobot-netbox-importer nautobot.py                           __init__() :
  Created NautobotModelWrapper<circuits.circuit>
11:01:06.541 DEBUG   nautobot-netbox-importer source.py                             __init__() :
  Created SourceModelWrapper<circuits.circuit -> circuits.circuit>
11:01:06.541 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuittermination id InternalFieldType.UUID_FIELD
11:01:06.541 DEBUG   nautobot-netbox-importer nautobot.py                           __init__() :
  Created NautobotModelWrapper<circuits.circuittermination>
11:01:06.541 DEBUG   nautobot-netbox-importer source.py                             __init__() :
  Created SourceModelWrapper<circuits.circuittermination -> circuits.circuittermination>
11:01:06.542 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field extras.role id InternalFieldType.UUID_FIELD
11:01:06.542 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field extras.role content_types InternalFieldType.MANY_TO_MANY_FIELD
11:01:06.542 DEBUG   nautobot-netbox-importer nautobot.py                           __init__() :
  Created NautobotModelWrapper<extras.role>

...

  Created SourceModelWrapper<dcim.locationtype -> dcim.locationtype>
11:01:06.543 DEBUG   nautobot-netbox-importer source.py                         cache_record() :
  Cached SourceModelWrapper<dcim.locationtype -> dcim.locationtype> 6003e66c-d3f2-5a36-9c06-5ee450898936 {'id': 'Region', 'name': 'Region', 'nestable': True}
11:01:06.543 DEBUG   nautobot-netbox-importer source.py                         cache_record() :
  Cached SourceModelWrapper<dcim.locationtype -> dcim.locationtype> 8fceb641-4563-5da8-9004-963f9ed1965a {'id': 'Site', 'name': 'Site', 'nestable': False, 'parent': UUID('6003e66c-d3f2-5a36-9c06-5ee450898936')}
11:01:06.543 DEBUG   nautobot-netbox-importer source.py                         cache_record() :
  Cached SourceModelWrapper<dcim.locationtype -> dcim.locationtype> 22004273-2182-50fd-b410-5e152ed9431a {'id': 'Location', 'name': 'Location', 'nestable': True, 'parent': UUID('8fceb641-4563-5da8-9004-963f9ed1965a')}

...

11:01:06.671 DEBUG   nautobot-netbox-importer source.py                             __init__() :
  Created disabled SourceModelWrapper<tenancy.contactassignment -> tenancy.contactassignment>

...

11:01:06.679 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuit commit_rate InternalFieldType.POSITIVE_INTEGER_FIELD
11:01:06.679 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuittermination location_id InternalFieldType.FOREIGN_KEY
11:01:06.679 DEBUG   nautobot-netbox-importer nautobot.py                          add_field() :
  Adding nautobot field circuits.circuittermination created InternalFieldType.DATE_TIME_FIELD

...
```

### Importing Data

The next step is to import the data. The output will look similar to the following:

```
11:01:06.768 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Importing record SourceModelWrapper<contenttypes.contenttype -> contenttypes.contenttype> {'app_label': 'admin', 'model': 'logentry'}
11:01:06.770 DEBUG   nautobot-netbox-importer nautobot.py                     diffsync_class() :
  Created DiffSync Model {'__annotations__': {'id': <class 'int'>, 'app_label': typing.Optional[str], 'model': typing.Optional[str]}, '_attributes': ['app_label', 'model'], '_identifiers': ['id'], '_modelname': 'contenttypes_contenttype', '_wrapper': <nautobot_netbox_importer.generator.nautobot.NautobotModelWrapper object at 0x7fa657dd41d0>, 'id': FieldInfo(default=PydanticUndefined, extra={}), 'app_label': FieldInfo(extra={}), 'model': FieldInfo(extra={})}
11:01:06.771 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 35 {'app_label': 'admin', 'model': 'logentry'}
11:01:06.771 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Importing record SourceModelWrapper<contenttypes.contenttype -> contenttypes.contenttype> {'app_label': 'auth', 'model': 'permission'}
11:01:06.772 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 23 {'app_label': 'auth', 'model': 'permission'}
11:01:06.772 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Importing record SourceModelWrapper<contenttypes.contenttype -> contenttypes.contenttype> {'app_label': 'auth', 'model': 'group'}
11:01:06.773 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 24 {'app_label': 'auth', 'model': 'group'}
11:01:06.773 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Importing record SourceModelWrapper<contenttypes.contenttype -> contenttypes.contenttype> {'app_label': 'auth', 'model': 'user'}
11:01:06.774 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 126 {'app_label': 'auth', 'model': 'user'}
11:01:06.774 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Importing record SourceModelWrapper<contenttypes.contenttype -> contenttypes.contenttype> {'app_label': 'contenttypes', 'model': 'contenttype'}
11:01:06.775 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 26 {'app_label': 'contenttypes', 'model': 'contenttype'}

...

11:01:06.827 INFO    nautobot-netbox-importer nautobot.py                           __init__() :
  Skipping unknown model dcim.virtualdevicecontext
11:01:06.827 DEBUG   nautobot-netbox-importer nautobot.py                           __init__() :
  Created NautobotModelWrapper<dcim.virtualdevicecontext>
11:01:06.827 DEBUG   nautobot-netbox-importer source.py                             __init__() :
  Created disabled SourceModelWrapper<dcim.virtualdevicecontext -> dcim.virtualdevicecontext>

...

  Importing record SourceModelWrapper<circuits.circuit -> circuits.circuit> {'created': '2020-12-30T00:00:00Z', 'last_updated': '2023-04-12T19:32:03.833Z', 'custom_field_data': {}, 'description': '', 'comments': '', 'cid': 'KKDG4923', 'provider': 5, 'provider_account': None, 'type': 2, 'status': 'active', 'tenant': 5, 'install_date': None, 'termination_date': None, 'commit_rate': None, 'termination_a': 48, 'termination_z': 1, 'id': 1}
11:01:06.861 DEBUG   nautobot-netbox-importer nautobot.py                     diffsync_class() :
  Created DiffSync Model {'__annotations__': {'id': <class 'uuid.UUID'>, 'status_id': typing.Optional[uuid.UUID], 'circuit_type_id': typing.Optional[uuid.UUID], 'circuit_termination_a_id': typing.Optional[uuid.UUID], 'circuit_termination_z_id': typing.Optional[uuid.UUID], 'created': typing.Optional[datetime.datetime], 'last_updated': typing.Optional[datetime.datetime], 'custom_field_data': typing.Optional[typing.Any], 'description': typing.Optional[str], 'comments': typing.Optional[str], 'cid': typing.Optional[str], 'provider_id': typing.Optional[uuid.UUID], 'tenant_id': typing.Optional[uuid.UUID], 'install_date': typing.Optional[datetime.date], 'commit_rate': typing.Optional[int]}, '_attributes': ['status_id', 'circuit_type_id', 'circuit_termination_a_id', 'circuit_termination_z_id', 'created', 'last_updated', 'custom_field_data', 'description', 'comments', 'cid', 'provider_id', 'tenant_id', 'install_date', 'commit_rate'], '_identifiers': ['id'], '_modelname': 'circuits_circuit', '_wrapper': <nautobot_netbox_importer.generator.nautobot.NautobotModelWrapper object at 0x7fa657e3ec50>, 'id': FieldInfo(default=PydanticUndefined, extra={}), 'status_id': FieldInfo(extra={}), 'circuit_type_id': FieldInfo(extra={}), 'circuit_termination_a_id': FieldInfo(extra={}), 'circuit_termination_z_id': FieldInfo(extra={}), 'created': FieldInfo(extra={}), 'last_updated': FieldInfo(extra={}), 'custom_field_data': FieldInfo(extra={}), 'description': FieldInfo(extra={}), 'comments': FieldInfo(extra={}), 'cid': FieldInfo(extra={}), 'provider_id': FieldInfo(extra={}), 'tenant_id': FieldInfo(extra={}), 'install_date': FieldInfo(extra={}), 'commit_rate': FieldInfo(extra={})}
11:01:06.862 DEBUG   nautobot-netbox-importer source.py                         cache_record() :
  Cached SourceModelWrapper<extras.status -> extras.status> 1801b68a-1ac3-4fe3-b88d-450662824819 {'name': 'Active'}
11:01:06.862 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: extras.status 1801b68a-1ac3-4fe3-b88d-450662824819
11:01:06.862 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: tenancy.tenant 80f6b934-9627-5da1-9928-fc0e5e03f2f0
11:01:06.862 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: circuits.circuittermination f76b03e6-a853-51a6-b8f2-20c86bc424e7
11:01:06.862 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: circuits.circuittype 0c9d650f-39cd-5060-809c-8cbc291e9fbb
11:01:06.863 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: circuits.provider 30efd662-fc9b-5892-b2be-adeb8091cb29
11:01:06.863 DEBUG   nautobot-netbox-importer source.py                        add_reference() :
  Adding reference from: circuits.circuit to: circuits.circuittermination a82c9a9a-678f-5c23-a73d-bb16b30eb407
11:01:06.863 DEBUG   nautobot-netbox-importer source.py                        import_record() :
  Imported 8037ffad-6a28-5267-9839-2e6459305d3c {'status_id': UUID('1801b68a-1ac3-4fe3-b88d-450662824819'), 'circuit_type_id': UUID('0c9d650f-39cd-5060-809c-8cbc291e9fbb'), 'circuit_termination_a_id': UUID('f76b03e6-a853-51a6-b8f2-20c86bc424e7'), 'circuit_termination_z_id': UUID('a82c9a9a-678f-5c23-a73d-bb16b30eb407'), 'created': datetime.datetime(2020, 12, 30, 0, 0, tzinfo=datetime.timezone.utc), 'last_updated': None, 'custom_field_data': None, 'description': None, 'comments': None, 'cid': 'KKDG4923', 'provider_id': UUID('30efd662-fc9b-5892-b2be-adeb8091cb29'), 'tenant_id': UUID('80f6b934-9627-5da1-9928-fc0e5e03f2f0'), 'install_date': None, 'commit_rate': None}

...

11:01:10.075 INFO    nautobot-netbox-importer source.py                          post_import() :
  Imported 1 extras_customfield
11:01:10.075 INFO    nautobot-netbox-importer source.py                          post_import() :
  Imported 6 extras_status
11:01:10.075 INFO    nautobot-netbox-importer source.py                          post_import() :
  Imported 18 extras_role
11:01:10.075 INFO    nautobot-netbox-importer source.py                          post_import() :
  Imported 6 dcim_locationtype
11:01:10.075 INFO    nautobot-netbox-importer source.py                          post_import() :
  Imported 95 dcim_location
```

### DiffSync

The next step is to perform a DiffSync. The output will look similar to the following:

```
2024-01-29 11:01:10 debug     Diff calculation between these two datasets will involve 6068 models dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> src=<NetBoxAdapter "NetBox">
2024-01-29 11:01:10 info      Beginning diff calculation     dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> src=<NetBoxAdapter "NetBox">
2024-01-29 11:01:10 debug     Skipping due to IGNORE flag on source object dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=contenttypes_contenttype src=<NetBoxAdapter "NetBox"> unique_id=35
2024-01-29 11:01:10 debug     Skipping due to IGNORE flag on source object dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=contenttypes_contenttype src=<NetBoxAdapter "NetBox"> unique_id=23

...

2024-01-29 11:01:10 debug     Skipping due to IGNORE flag on source object dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=contenttypes_contenttype src=<NetBoxAdapter "NetBox"> unique_id=170
2024-01-29 11:01:10 info      Diff calculation complete      dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> src=<NetBoxAdapter "NetBox">
2024-01-29 11:01:10 info      Beginning sync                 dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> src=<NetBoxAdapter "NetBox">
2024-01-29 11:01:10 debug     Attempting model create        action=create diffs={'+': {'content_types': {116}, 'key': 'cust_id', 'created': datetime.datetime(2021, 9, 9, 0, 0, tzinfo=datetime.timezone.utc), 'last_updated': None, 'type': 'text', 'label': 'Customer ID', 'description': None, 'required': False, 'filter_logic': 'exact', 'default': None, 'weight': 100, 'validation_minimum': None, 'validation_maximum': None, 'validation_regex': '^[A-Z]{3}\\d{2}$'}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=extras_customfield src=<NetBoxAdapter "NetBox"> unique_id=e4fa5680-4657-50ea-837c-604617c7fc0d
2024-01-29 11:01:10 info      Created successfully           action=create diffs={'+': {'content_types': {116}, 'key': 'cust_id', 'created': datetime.datetime(2021, 9, 9, 0, 0, tzinfo=datetime.timezone.utc), 'last_updated': None, 'type': 'text', 'label': 'Customer ID', 'description': None, 'required': False, 'filter_logic': 'exact', 'default': None, 'weight': 100, 'validation_minimum': None, 'validation_maximum': None, 'validation_regex': '^[A-Z]{3}\\d{2}$'}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=extras_customfield src=<NetBoxAdapter "NetBox"> status=success unique_id=e4fa5680-4657-50ea-837c-604617c7fc0d
2024-01-29 11:01:10 debug     Attempting model create        action=create diffs={'+': {'content_types': {12, 13, 14, 7}, 'name': 'Unknown'}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=extras_status src=<NetBoxAdapter "NetBox"> unique_id=623acb70-22ce-5f69-bd7e-76bc921aa6c4
2024-01-29 11:01:10 info      Created successfully           action=create diffs={'+': {'content_types': {12, 13, 14, 7}, 'name': 'Unknown'}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=extras_status src=<NetBoxAdapter "NetBox"> status=success unique_id=623acb70-22ce-5f69-bd7e-76bc921aa6c4

...

2024-01-29 11:01:28 debug     Attempting model create        action=create diffs={'+': {'created': datetime.datetime(2021, 4, 2, 0, 0, tzinfo=datetime.timezone.utc), 'last_updated': None, 'custom_field_data': None, 'name': 'South America', 'description': None}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=virtualization_clustergroup src=<NetBoxAdapter "NetBox"> unique_id=aa168442-0c73-5681-b8bd-243f5f93842f
2024-01-29 11:01:28 info      Created successfully           action=create diffs={'+': {'created': datetime.datetime(2021, 4, 2, 0, 0, tzinfo=datetime.timezone.utc), 'last_updated': None, 'custom_field_data': None, 'name': 'South America', 'description': None}} dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> model=virtualization_clustergroup src=<NetBoxAdapter "NetBox"> status=success unique_id=aa168442-0c73-5681-b8bd-243f5f93842f
2024-01-29 11:01:28 info      Sync complete                  dst=<NautobotAdapter "Nautobot"> flags=<DiffSyncFlags.NONE: 0> src=<NetBoxAdapter "NetBox">
```

### Summary

The last part of the import process is to display a summary of the import [described in the user documentation](../user/summary.md).

## Generated Mappings

To examine the mappings generated by the importer, check the `generated-mappings.json` file in the current directory. This file describes the mapping of NetBox data to Nautobot data. It can be used to compare mapping changes between different NetBox versions or during the development of the importer.

```bash
[
    {
        "content_type": "auth.group",
        "content_type_id": 3,
        "extends_content_type": null,
        "nautobot.content_type": "auth.group",
        "nautobot.content_type_id": 24,
        "disable_reason": "",
        "identifiers": [
            "name"
        ],
        "disable_related_reference": false,
        "forward_references": null,
        "pre_import": null,
        "fields": [
            {
                "name": "id",
                "nautobot.name": "id",
                "nautobot.internal_type": "AutoField",
                "nautobot.can_import": true,
                "importer": null,
                "definition": "id",
                "from_data": false,
                "is_custom": true,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "permissions",
                "nautobot.name": null,
                "nautobot.internal_type": null,
                "nautobot.can_import": null,
                "importer": null,
                "definition": null,
                "from_data": true,
                "is_custom": true,
                "default_value": null,
                "disable_reason": "Permissions import is not implemented yet"
            },
            {
                "name": "name",
                "nautobot.name": "name",
                "nautobot.internal_type": "CharField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "name",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            }
        ],
        "flags": "DiffSyncModelFlags.NONE",
        "nautobot.flags": "DiffSyncModelFlags.SKIP_UNMATCHED_DST",
        "default_reference_uid": null,
        "imported_count": 1
    },
    {
        "content_type": "auth.permission",
        "content_type_id": 2,
        "extends_content_type": null,
        "nautobot.content_type": "auth.permission",
        "nautobot.content_type_id": 23,
        "disable_reason": "Handled via a Nautobot model and may not be a 1 to 1.",
        "identifiers": null,
        "disable_related_reference": false,
        "forward_references": null,
        "pre_import": null,
        "fields": [
            {
                "name": "id",
                "nautobot.name": "id",
                "nautobot.internal_type": "AutoField",
                "nautobot.can_import": true,
                "importer": null,
                "definition": "id",
                "from_data": false,
                "is_custom": true,
                "default_value": null,
                "disable_reason": ""
            }
        ],
        "flags": "DiffSyncModelFlags.NONE",
        "nautobot.flags": "DiffSyncModelFlags.SKIP_UNMATCHED_DST",
        "default_reference_uid": null,
        "imported_count": 0
    },
    {
        "content_type": "auth.user",
        "content_type_id": 4,
        "extends_content_type": null,
        "nautobot.content_type": "users.user",
        "nautobot.content_type_id": 117,
        "disable_reason": "",
        "identifiers": [
            "username"
        ],
        "disable_related_reference": false,
        "forward_references": null,
        "pre_import": null,
        "fields": [
            {
                "name": "id",
                "nautobot.name": "id",
                "nautobot.internal_type": "UUIDField",
                "nautobot.can_import": true,
                "importer": null,
                "definition": "id",
                "from_data": false,
                "is_custom": true,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "last_login",
                "nautobot.name": null,
                "nautobot.internal_type": null,
                "nautobot.can_import": null,
                "importer": null,
                "definition": null,
                "from_data": true,
                "is_custom": true,
                "default_value": null,
                "disable_reason": "Should not be attempted to migrate"
            },
            {
                "name": "password",
                "nautobot.name": null,
                "nautobot.internal_type": null,
                "nautobot.can_import": null,
                "importer": null,
                "definition": null,
                "from_data": true,
                "is_custom": true,
                "default_value": null,
                "disable_reason": "Should not be attempted to migrate"
            },
            {
                "name": "user_permissions",
                "nautobot.name": null,
                "nautobot.internal_type": null,
                "nautobot.can_import": null,
                "importer": null,
                "definition": null,
                "from_data": true,
                "is_custom": true,
                "default_value": null,
                "disable_reason": "Permissions import is not implemented yet"
            },
            {
                "name": "is_superuser",
                "nautobot.name": "is_superuser",
                "nautobot.internal_type": "BooleanField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "is_superuser",
                "from_data": true,
                "is_custom": false,
                "default_value": false,
                "disable_reason": ""
            },
            {
                "name": "username",
                "nautobot.name": "username",
                "nautobot.internal_type": "CharField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "username",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "first_name",
                "nautobot.name": "first_name",
                "nautobot.internal_type": "CharField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "first_name",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "last_name",
                "nautobot.name": "last_name",
                "nautobot.internal_type": "CharField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "last_name",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "email",
                "nautobot.name": "email",
                "nautobot.internal_type": "CharField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "email",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "is_staff",
                "nautobot.name": "is_staff",
                "nautobot.internal_type": "BooleanField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "is_staff",
                "from_data": true,
                "is_custom": false,
                "default_value": false,
                "disable_reason": ""
            },
            {
                "name": "is_active",
                "nautobot.name": "is_active",
                "nautobot.internal_type": "BooleanField",
                "nautobot.can_import": true,
                "importer": "value_importer",
                "definition": "is_active",
                "from_data": true,
                "is_custom": false,
                "default_value": true,
                "disable_reason": ""
            },
            {
                "name": "date_joined",
                "nautobot.name": "date_joined",
                "nautobot.internal_type": "DateTimeField",
                "nautobot.can_import": true,
                "importer": "datetime_importer",
                "definition": "date_joined",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            },
            {
                "name": "groups",
                "nautobot.name": "groups",
                "nautobot.internal_type": "ManyToManyField",
                "nautobot.can_import": true,
                "importer": "identifiers_importer",
                "definition": "groups",
                "from_data": true,
                "is_custom": false,
                "default_value": null,
                "disable_reason": ""
            }
        ],
        "flags": "DiffSyncModelFlags.NONE",
        "nautobot.flags": "DiffSyncModelFlags.SKIP_UNMATCHED_DST",
        "default_reference_uid": null,
        "imported_count": 6
    },

...

]
```
