# Data Flow Diagram

A detailed description of the individual steps can be found in the developer [Generator Documentation](../dev//generator.md#stages) or the user [Using the App](../user/app_use_cases.md) documentation.

```mermaid
flowchart LR
    subgraph user[User Actions]
        direction TB
        A[Export Data from NetBox] --> |User exports JSON file| B[Execute 'import_netbox' Command]
    end
    subgraph importer[Importer Process]
        direction TB
        C[Configure Deviations] --> transaction
        subgraph transaction[Transaction Block]
            direction TB
            subgraph firstiter[First Input Iteration]
                direction TB
                FI1[Read SourceRecord]
                FI2[Create SourceModelWrappers and Field definitions]
                FI1 --> FI2
                FI2 --> FI1
            end
            E[First Iteration Over Data] --> firstiter
            firstiter --> F[Create Importers]
            F --> seconditer
            subgraph seconditer[Second Input Iteration]
                direction TB
                SI1[Read SourceRecord]
                SI2[Attempt to read Nautobot DiffSyncModel instance]
                SI3[Create NetBox DiffSyncModel instance]
                SI1 --> SI2
                SI2 --> SI3
                SI3 --> SI1
            end
            seconditer --> G[Assing content_types fields]
            G --> H[Evaluate Differences with DiffSync]
            H --> I[Synchronization into Nautobot]
        end
        transaction --> K[Print summary]
    end
    user --> | JSON file reference | importer
    %% Add legend
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style K fill:#bbf,stroke:#333,stroke-width:2px
```


