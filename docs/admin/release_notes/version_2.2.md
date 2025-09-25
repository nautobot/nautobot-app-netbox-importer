
# v2.2 Release Notes

This document describes all new features and changes in the release. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release Overview

- Major features or milestones
- Changes to compatibility with Nautobot and/or other apps, libraries etc.

## [v2.2.0 (2025-06-03)](https://github.com/nautobot/nautobot-app-netbox-importer/releases/tag/v2.2.0)

### Added

- [#197](https://github.com/nautobot/nautobot-app-netbox-importer/issues/197) - Added NetBox v4.2 tests.
- [#200](https://github.com/nautobot/nautobot-app-netbox-importer/issues/200) - Added calling `super.save()` on Nautobot instances where `save()` fails.
- [#202](https://github.com/nautobot/nautobot-app-netbox-importer/issues/202) - Added source record reference to issues summary.
- [#203](https://github.com/nautobot/nautobot-app-netbox-importer/issues/203) - Added TimeZone field support.
- [#204](https://github.com/nautobot/nautobot-app-netbox-importer/issues/204) - Added auto-incremental field importer support.
- [#205](https://github.com/nautobot/nautobot-app-netbox-importer/issues/205) - Added post-import hook.
- [#207](https://github.com/nautobot/nautobot-app-netbox-importer/issues/207) - Added tagging all Nautobot instances with issues.
- [#208](https://github.com/nautobot/nautobot-app-netbox-importer/issues/208) - Added `customizations` option to the `import_netbox` command.
- [#209](https://github.com/nautobot/nautobot-app-netbox-importer/issues/209) - Added configurable PK getter.
- [#209](https://github.com/nautobot/nautobot-app-netbox-importer/issues/209) - Added placeholders.
- [#212](https://github.com/nautobot/nautobot-app-netbox-importer/issues/212) - Added feature to de-duplicate IPAM prefixes and IP addresses.
- [#213](https://github.com/nautobot/nautobot-app-netbox-importer/issues/213) - Added NetBox version argument to be able to distinguish between NetBox versions in the code.
- [#214](https://github.com/nautobot/nautobot-app-netbox-importer/issues/214) - Added feature to create missing cable terminations.
- [#217](https://github.com/nautobot/nautobot-app-netbox-importer/issues/217) - Added NetBox checker script.

### Changed

- [#201](https://github.com/nautobot/nautobot-app-netbox-importer/issues/201) - Changed import order to allow console server ports imports.
- [#215](https://github.com/nautobot/nautobot-app-netbox-importer/issues/215) - Changed TaggedObjects import to support NetBox V4.
- [#216](https://github.com/nautobot/nautobot-app-netbox-importer/issues/216) - Separated content types definitions to distinct module.

### Fixed

- [#191](https://github.com/nautobot/nautobot-app-netbox-importer/issues/191) - Fixed imports with `--sitegroup-parent-always-region` flag enabled.

### Dependencies

- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Added new dependency netaddr `v0.10.1`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Added new dependency packaging `v24.1`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Bumped Nautobot to `v2.4.9`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Bumped colorama to `v0.4.6`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Bumped Markdown to `v3.6`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Bumped python-dateutil to `v2.9.0`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Removed Support for Nautobot `v2.0`, ``v2.1`, and `v2.2`.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Removed Support for Python `v3.8.X`, ``v3.9.1`, and `v3.9.2`.
- [#219](https://github.com/nautobot/nautobot-app-netbox-importer/issues/219) - Bumped diffsync to `v2.1`.
- [#219](https://github.com/nautobot/nautobot-app-netbox-importer/issues/219) - Bumped pydantic to `v2.11.5`.

### Housekeeping

- [#190](https://github.com/nautobot/nautobot-app-netbox-importer/issues/190) - Update the version parsing function to retrieve version using _get_docker_nautobot_version.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Change particular test failures to warnings.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Test samples generation uses already sampled IDs.
- [#218](https://github.com/nautobot/nautobot-app-netbox-importer/issues/218) - Added `--test-input` option to `import-netbox` command to allow using test fixtures, e.g. `invoke import-netbox --test-input=2.4/3.7.custom`.
- Rebaked from the cookie `nautobot-app-v2.4.0`.
- Rebaked from the cookie `nautobot-app-v2.4.1`.
- Rebaked from the cookie `nautobot-app-v2.4.2`.
- Rebaked from the cookie `nautobot-app-v2.5.0`.
