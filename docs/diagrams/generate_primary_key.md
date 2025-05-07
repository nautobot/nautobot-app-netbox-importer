# Nautobot Primary Key Generation Flowchart

Here's a flowchart showing how primary keys are generated in the Nautobot importer, starting with `get_pk_from_data`:

```mermaid
flowchart TD
    start("get_pk_from_data(data)")
    customFunc{"Custom\n_get_pk_from_data\nexists?"}
    useCustomFunc["Use custom function\nto generate PK"]
    checkIdentifiers{"Are identifiers\ndefined?"}
    usePkField["Use data[pk_field.name]\nas UID"]
    checkDataUidCache{"Is data UID\nin cache?"}
    returnCachedUid["Return cached UID"]
    getFromIdentifiers["Get PK from identifiers"]
    cacheResult["Cache result"]
    returnResult["Return result"]
    
    getPkFromIdentifiers["get_pk_from_identifiers(data)"]
    identifiersInCache{"Are identifiers\nin cache?"}
    returnIdentifiersCache["Return cached value"]
    tryNautobot["Try to get instance\nfrom Nautobot"]
    nautonotExists{"Instance\nexists?"}
    useNautobotUid["Use Nautobot UID"]
    fallbackUid["Fall back to get_pk_from_uid()"]
    
    getPkFromUid["get_pk_from_uid(uid)"]
    uidInCache{"Is UID in cache?"}
    returnUidCache["Return cached value"]
    checkFieldType{"What is\nPK field type?"}
    useUuid["Generate UUID from\nsource_pk_to_uuid()"]
    useAutoIncrement["Increment counter\nand use as PK"]
    unsupportedType["Raise error:\nUnsupported type"]
    cacheUid["Cache UID mapping"]
    
    start --> customFunc
    customFunc -->|Yes| useCustomFunc --> returnResult
    customFunc -->|No| checkIdentifiers
    
    checkIdentifiers -->|No| usePkField --> getPkFromUid
    checkIdentifiers -->|Yes| checkDataUidCache
    
    checkDataUidCache -->|Yes| returnCachedUid --> returnResult
    checkDataUidCache -->|No| getFromIdentifiers
    getFromIdentifiers --> getPkFromIdentifiers
    getPkFromIdentifiers --> identifiersInCache
    
    identifiersInCache -->|Yes| returnIdentifiersCache --> cacheResult
    identifiersInCache -->|No| tryNautobot --> nautonotExists
    
    nautonotExists -->|Yes| useNautobotUid --> cacheResult
    nautonotExists -->|No| fallbackUid --> getPkFromUid
    
    getPkFromUid --> uidInCache
    uidInCache -->|Yes| returnUidCache --> returnResult
    uidInCache -->|No| checkFieldType
    
    checkFieldType -->|UUID| useUuid --> cacheUid
    checkFieldType -->|Auto increment| useAutoIncrement --> cacheUid
    checkFieldType -->|Other| unsupportedType
    
    cacheUid --> returnResult
    cacheResult --> returnResult
```

This flowchart shows:

1. How the process starts by checking for a custom function
2. The branching logic based on whether identifiers are defined
3. Multiple caching points to avoid redundant lookups
4. How the system looks for existing Nautobot instances
5. How different field types (UUID vs auto-increment) are handled differently
6. The final caching and return of the result

The process ensures each record gets a consistent primary key that can be reliably referenced throughout the import process.
