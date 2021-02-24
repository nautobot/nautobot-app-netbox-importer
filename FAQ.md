# Frequently Asked Questions

## Could this have been implemented as a standalone tool instead of a Nautobot plugin?

No. Or at least not while still being capable of importing as much data as it is. This plugin relies heavily on direct access to the Django object relational mapping (ORM) to populate the Nautobot database in ways that
are not always possible through even a REST API as full-featured as Nautobot's. It is also much faster to access the ORM directly instead of going through a remote API to bulk-populate data.

## The plugin was running, then suddenly I saw a "Killed" message appear and it stopped. What happened?

The plugin consumed too much memory and was killed by the system. You're most likely to see this issue if you're running the plugin inside a Docker container (such as the development environment) or similar resource-constrained environment, and/or if your database dump is a large file (hundreds of MB or more).

Unfortunately there's not much you can do about this other than adding more RAM. Importing an entire NetBox database dump into memory, then translating it on-the-fly into Nautobot database objects is a fairly memory-intensive process.
