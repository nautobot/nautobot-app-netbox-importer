# NetBox Importer Test Fixtures

NetBox importer tests are using stored fixtures to verify that the import process is working as expected.

## Fixtures Folder

This folder contains a list of folders, each for a specific Nautobot minor version.

## Nautobot Minor Version Folder

Each Nautobot folder (e.g. `fixtures/nautobot-v2.2`) contains a Nautobot database dump `dump.sql` and folders with fixtures for individual test cases.

The database dump contains `ContentType` instances to keep the content type IDs consistent across tests. The dump can be created after a successful test run using the following command:

```shell
invoke dump-test-environment
```

## Test Case Folder

Each test case folder (e.g. `fixtures/nautobot-v2.2/3.7.custom`) should be named using ASCII lowercase letters, underscores, and dots only. For each folder, one test case is created in `class TestImport`. The folder should contain the following files:

- `input.json`: NetBox JSON data to be imported.
- `samples`: Folder with Nautobot samples to compare with the imported data. For each content type, 3 instances are stored.
- `summary.json`: Expected summary of the import.
- `summary.txt`: Expected summary of the import in human-readable format.

Summaries are re-generated after each test run. It's possible to use a `diff` tool to compare the expected and actual summaries. Tests compare the number of imported objects and issues.

It's also possible to generate and overwrite the fixtures by setting the environment variable `BUILD_FIXTURES=True`, or by using the `invoke unittest --build-fixtures` option when running the tests.
