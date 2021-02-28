# Nautobot NetBox Importer

A plugin for [Nautobot](https://github.com/nautobot/nautobot).

## Installation

The plugin is available as a Python package in PyPI and can be installed with pip:

```shell
pip install nautobot-netbox-importer
```

> The plugin is compatible with Nautobot 1.0 and can handle JSON data exported from NetBox 2.10.3 and 2.10.4 at present.

Once installed, the plugin needs to be enabled in your `nautobot_config.py`:

```python
PLUGINS = ["nautobot_netbox_importer"]
```

**Note**: For those of you coming from Netbox, this does not work as a normal Netbox plugin. This is a CLI Plugin only, in fact your Nautobot installation won't work while this is set in the plugins. So add it to plugins, run the migration as detailed below, and then remove it from the plugins key in your config again when you're done.

## Usage

### Getting a data export from NetBox

From the NetBox root directory, run the following command:

```shell
python netbox/manage.py dumpdata \
    --traceback --format=json \
    --exclude admin.logentry --exclude sessions.session \
    --exclude extras.ObjectChange --exclude extras.Script --exclude extras.Report \
    > /tmp/netbox_data.json
```

### Importing the data into Nautobot

From the Nautobot root directory, run `nautobot-server import_netbox_json <json_file> <netbox_version>`, for example `nautobot-server import_netbox_json /tmp/netbox_data.json 2.10.3`.

## Contributing

Most of the internal logic of this plugin is based on the [DiffSync](https://github.com/networktocode/diffsync) library, which in turn is built atop [Pydantic](https://github.com/samuelcolvin/pydantic/).
A basic understanding of these two libraries will be helpful to those wishing to contribute to this project.

Pull requests are welcomed and automatically built and tested against multiple version of Python and multiple versions of Nautobot through TravisCI.

The project is packaged with a light development environment based on `docker-compose` to help with the local development of the project and to run the tests within TravisCI.

The project is following Network to Code software development guideline and is leveraging:
- Black, Pylint, Bandit and pydocstyle for Python linting and formatting.
- Django unit test to ensure the plugin is working properly.
- Poetry for packaging and dependency management.

### CLI Helper Commands

The project includes a CLI helper based on [invoke](http://www.pyinvoke.org/) to help setup the development environment. The commands are listed below in 3 categories `dev environment`, `utility` and `testing`.

Each command can be executed with `invoke <command>`. All commands support the argument `--python-ver` if you want to manually define the version of Python to use. Each command also has its own help `invoke <command> --help`

#### Local dev environment
```
  build            Build all docker images.
  debug            Start Nautobot and its dependencies in debug mode.
  destroy          Destroy all containers and volumes.
  restart          Restart Nautobot and its dependencies.
  start            Start Nautobot and its dependencies in detached mode.
  stop             Stop Nautobot and its dependencies.
```

#### Utility
```
  cli              Launch a bash shell inside the running Nautobot container.
  create-user      Create a new user in django (default: admin), will prompt for password.
  makemigrations   Run Make Migration in Django.
  nbshell          Launch a nbshell session.
```
#### Testing

```
  bandit           Run bandit to validate basic static code security analysis.
  black            Run black to check that Python files adhere to its style standards.
  flake8           This will run flake8 for the specified name and Python version.
  pydocstyle       Run pydocstyle to validate docstring formatting adheres to standards.
  pylint           Run pylint code analysis.
  tests            Run all tests for this plugin.
  unittest         Run Django unit tests for the plugin.
```

## Questions

For any questions or comments, please check the [FAQ](FAQ.md) first and feel free to swing by the [#nautobot slack channel](https://networktocode.slack.com/).
Sign up [here](http://slack.networktocode.com/)

## Screenshots

![Screenshot of the start of synchronization](https://raw.githubusercontent.com/nautobot/nautobot-plugin-netbox-importer/develop/media/screenshot1.png "Beginning synchronization")

![Screenshot of the completed process](https://raw.githubusercontent.com/nautobot/nautobot-plugin-netbox-importer/develop/media/screenshot2.png "Synchronization complete!")
