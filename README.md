# Nautobot NetBox Importer

A plugin for [Nautobot](https://github.com/nautobot/nautobot).

## Installation

The plugin is available as a Python package in PyPI and can be installed with pip:

```shell
pip install nautobot-netbox-importer
```

> The plugin is compatible with Nautobot 1.0.0b3 and later and can handle JSON data exported from NetBox 2.10.3 thru 2.10.8  at present.

Once installed, the plugin needs to be enabled in your `nautobot_config.py`:

```python
PLUGINS = ["nautobot_netbox_importer"]
```

## Usage

### Getting a data export from NetBox

From the NetBox root directory, run the following command to produce a JSON file (here, `/tmp/netbox_data.json`) describing the contents of your NetBox database:

```shell
python netbox/manage.py dumpdata \
    --traceback --format=json \
    --exclude admin.logentry --exclude sessions.session \
    --exclude extras.ObjectChange --exclude extras.Script --exclude extras.Report \
    > /tmp/netbox_data.json
```

### Importing the data into Nautobot

From within the Nautobot application environment, run `nautobot-server import_netbox_json <json_file> <netbox_version>`, for example `nautobot-server import_netbox_json /tmp/netbox_data.json 2.10.3`.

### Importing change logging (ObjectChange) records

Because the database change log can be a massive amount of data, and often this historical information does not need to be imported, `ObjectChange` records are not included in the database export command above and are not handled by the `import_netbox_json` command. To import `ObjectChange` records specifically, **after** the previous Netbox import process has succeeded, you can do the following.

#### Getting a data export from NetBox with ONLY ObjectChange items

```shell
python netbox/manage.py dumpdata extras.ObjectChange\
    --traceback --format=json \
    > /tmp/netbox_only_objectchange.json
```

#### Importing the ObjectChanges into Nautobot

From within the Nautobot application environment, run `nautobot-server import_netbox_json <json_file_without_objectchanges> <json_file_only_objectchanges> <netbox_version>`, for example `nautobot-server import_netbox_objectchange_json imp/script/import_netbox_json.json imp/script/netbox_only_objectchange.json 2.10.3`.

## Contributing

Most of the internal logic of this plugin is based on the [DiffSync](https://github.com/networktocode/diffsync) library, which in turn is built atop [Pydantic](https://github.com/samuelcolvin/pydantic/).
A basic understanding of these two libraries will be helpful to those wishing to contribute to this project.

Pull requests are welcomed and automatically built and tested against multiple version of Python and multiple versions of Nautobot through TravisCI.

The project is packaged with a light development environment based on `docker-compose` to help with the local development of the project and to run the tests within TravisCI.

The project is following Network to Code software development guideline and is leveraging:

- Black, Pylint, Bandit and pydocstyle for Python linting and formatting.
- Django unit test to ensure the plugin is working properly.
- Poetry for packaging and dependency management.

### Development Environment

The development environment can be used in 2 ways. First, with a local poetry environment if you wish to develop outside of Docker. Second, inside of a docker container.

#### Invoke tasks

The [PyInvoke](http://www.pyinvoke.org/) library is used to provide some helper commands based on the environment.  There are a few configuration parameters which can be passed to PyInvoke to override the default configuration:

* `nautobot_ver`: the version of Nautobot to use as a base for any built docker containers (default: develop-latest)
* `project_name`: the default docker compose project name (default: nautobot-netbox-importer)
* `python_ver`: the version of Python to use as a base for any built docker containers (default: 3.6)
* `local`: a boolean flag indicating if invoke tasks should be run on the host or inside the docker containers (default: False, commands will be run in docker containers)
* `compose_dir`: the full path to a directory containing the project compose files
* `compose_files`: a list of compose files applied in order (see [Multiple Compose files](https://docs.docker.com/compose/extends/#multiple-compose-files) for more information)

Using PyInvoke these configuration options can be overridden using [several methods](http://docs.pyinvoke.org/en/stable/concepts/configuration.html).  Perhaps the simplest is simply setting an environment variable `INVOKE_NAUTOBOT-NETBOX-IMPORTER_VARIABLE_NAME` where `VARIABLE_NAME` is the variable you are trying to override.  The only exception is `compose_files`, because it is a list it must be overridden in a yaml file.  There is an example `invoke.yml` in this directory which can be used as a starting point.

#### Local Poetry Development Environment

1.  Copy `development/creds.example.env` to `development/creds.env` (This file will be ignored by git and docker)
2.  Uncomment the `POSTGRES_HOST`, `REDIS_HOST`, and `NAUTOBOT_ROOT` variables in `development/creds.env`
3.  Create an invoke.yml with the following contents at the root of the repo:

```shell
---
nautobot_netbox_importer:
  local: true
  compose_files:
    - "docker-compose.requirements.yml"
```

3.  Run the following commands:

```shell
poetry shell
poetry install
pip install nautobot
export $(cat development/dev.env | xargs)
export $(cat development/creds.env | xargs)
```

4.  You can now run nautobot-server commands as you would from the [Nautobot documentation](https://nautobot.readthedocs.io/en/latest/) for example to start the development server:

```shell
nautobot-server runserver 0.0.0.0:8080 --insecure
```

Nautobot server can now be accessed at [http://localhost:8080](http://localhost:8080).

#### Docker Development Environment

This project is managed by [Python Poetry](https://python-poetry.org/) and has a few requirements to setup your development environment:

1.  Install Poetry, see the [Poetry Documentation](https://python-poetry.org/docs/#installation) for your operating system.
2.  Install Docker, see the [Docker documentation](https://docs.docker.com/get-docker/) for your operating system.

Once you have Poetry and Docker installed you can run the following commands to install all other development dependencies in an isolated python virtual environment:

```shell
poetry shell
poetry install
invoke start
```

Nautobot server can now be accessed at [http://localhost:8080](http://localhost:8080).

### CLI Helper Commands

The project includes a CLI helper based on [invoke](http://www.pyinvoke.org/) to help setup the development environment. The commands are listed below in 3 categories `dev environment`, `utility` and `testing`.

Each command can be executed with `invoke <command>`. Environment variables `INVOKE_NAUTOBOT_NETBOX_IMPORTER_PYTHON_VER` and `INVOKE_NAUTOBOT_NETBOX_IMPORTER_NAUTOBOT_VER` may be specified to override the default versions. Each command also has its own help `invoke <command> --help`

#### Docker dev environment

```no-highlight
  build               Build Nautobot docker image.
  debug               Start Nautobot and its dependencies in debug mode.
  destroy             Destroy all containers and volumes.
  restart             Gracefully restart all containers.
  start               Start Nautobot and its dependencies in detached mode.
  stop                Stop Nautobot and its dependencies.
```

#### Utility

```no-highlight
  check-migrations    Check for missing migrations.
  cli                 Launch a bash shell inside the running Nautobot container.
  createsuperuser     Create a new Nautobot superuser account (default: "admin"), will prompt for password.
  generate-packages   Generate all Python packages inside docker and copy the file locally under dist/.
  makemigrations      Perform makemigrations operation in Django.
  migrate             Perform migrate operation in Django.
  nbshell             Launch an interactive nbshell session.
  post-upgrade        Performs Nautobot common post-upgrade operations using a single entrypoint.
  vscode              Launch Visual Studio Code with the appropriate Environment variables to run in a container.
```

#### Testing

```no-highlight
  bandit              Run bandit to validate basic static code security analysis.
  black               Check Python code style with Black.
  flake8              Check for PEP8 compliance and other style issues.
  hadolint            Check Dockerfile for hadolint compliance and other style issues.
  pydocstyle          Run pydocstyle to validate docstring formatting adheres to standards.
  pylint              Run pylint code analysis.
  tests               Run all tests for this plugin.
  unittest            Run Django unit tests for the plugin.
  unittest-coverage   Report on code test coverage as measured by 'invoke unittest'.
```

## Questions

For any questions or comments, please check the [FAQ](FAQ.md) first and feel free to swing by the [#nautobot slack channel](https://networktocode.slack.com/).
Sign up [here](http://slack.networktocode.com/)

## Screenshots

![Screenshot of the start of synchronization](https://raw.githubusercontent.com/nautobot/nautobot-plugin-netbox-importer/develop/media/screenshot1.png "Beginning synchronization")

![Screenshot of the completed process](https://raw.githubusercontent.com/nautobot/nautobot-plugin-netbox-importer/develop/media/screenshot2.png "Synchronization complete!")
