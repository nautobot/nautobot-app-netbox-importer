# Tagging Importer Issues

This document outlines the feature to tag Nautobot records during import with associated issues.

## Feature Overview

The tagging importer feature allows users to tag Nautobot records during the import process. This is useful for investigating and managing records that were imported with some issues.

## Usage

To tag issues during import, users can use the `--tag-issues` option in `nautobot-server import-netbox` command. This option enables the tagging feature. It's also possible to use this flag with `invoke import-netbox` command, that is a wrapper to the previous one.

After the import process, users can view the tagged records in Nautobot. To see all tags, open `Organization` > `Tags` in the Nautobot UI. The tags will be listed there, and users can show related records in the tag detail view.
