# Migrating Projects/Experiments between Comet Instances

As described in the [README](README.md), you can configure `cometx` to connect
to different Comet instances. This is useful when you want to migrate projects
or experiments between different Comet instances. This document describes how
to do this.

By default, `cometx` connects to the Comet Cloud SaaS instance, unless you have
configured it to connect to a different Comet instance. If you want to migrate
projects or experiments between different Comet instances, you need to
configure `cometx` to connect to the source and destination Comet instances.

You can either change the configuration in the `cometx` configuration file
(`~/.comet.config`) or use the `COMET_API_KEY` + `COMET_URL_OVERRIDE`
environment variables to specify the source and destination Comet instances.
But you must ensure to either update the configuration file or change the
environment variables between the source and destination Comet instances before
uploading data to the destination, so that `cometx` connects to the correct
Comet instance. This is because only one Comet instance can be configured at a
time.

## Migrating

Migrating your data is a two step process. First you must download the data
from the source Comet instance, and then upload it to the destination Comet
instance.

### Downloading Data

```shell
COMET_URL_OVERRIDE=http://comet.a.com/clientlib \
COMET_API_KEY=A-KEY \
cometx download <WORKSPACE>/<PROJECT>
```

The `cometx download` subcommand downloads all of the Comet experiment
data into local files. Note that `<WORKSPACE>/<PROJECT>` refers to a
workspace and project on `http://comet.a.com`.

##### Downloading a Single Experiment

If you want to download a single experiment, you can specify the experiment ID
in addition to the project name:

```shell
COMET_URL_OVERRIDE=http://comet.a.com/clientlib \
COMET_API_KEY=A-KEY \
cometx download <WORKSPACE>/<PROJECT>/<EXPERIMENT_ID>
```

Instead using the ID you may also use the project name.

##### Downloading an Entire Workspace

You can also omit the project name to download an entire workspace:

```shell
COMET_URL_OVERRIDE=http://comet.a.com/clientlib \
COMET_API_KEY=A-KEY \
cometx download <WORKSPACE>
```

#### Filtering Resources

You can also filter the resources that are downloaded by specifying them as
arguments to the `download` subcommand:

```shell
COMET_URL_OVERRIDE=http://comet.a.com/clientlib \
COMET_API_KEY=A-KEY \
cometx download <WORKSPACE>/<PROJECT> [RESOURCE ...]
```

Where `[RESOURCE ...]` is zero or more of the following names:

* `assets`
* `html`
* `metadata`
* `metrics`
* `others`
* `parameters`
* `project` - alias for: `project_notes`, `project_metadata`
* `run` - alias for: `code`, `git`, `output`, `graph`, and `requirements`
* system

If no `RESOURCE` is given it will download all of them.

### Uploading Data

The `download` subcommand will create a directory with the same name as the
project in the current working directory. You can then use the `copy`
subcommand to upload the data to the destination Comet instance.

```shell
COMET_URL_OVERRIDE=http://comet.b.com/clientlib \
COMET_API_KEY=B-KEY \
cometx copy <WORKSPACE>/<PROJECT> <NEW-WORKSPACE>/<NEW-PROJECT>
```

Note that `<WORKSPACE>/<PROJECT>` now refers to a directory, and
`<NEW-WORKSPACE>/<NEW-PROJECT>` refers to a workspace and project on
`http://comet.b.com`.

##### Uploading a Single Experiment

You can similarly copy a single experiment:

```shell
COMET_URL_OVERRIDE=http://comet.b.com/clientlib \
COMET_API_KEY=B-KEY \
cometx copy <WORKSPACE>/<PROJECT>/<EXPERIMENT_ID> <NEW-WORKSPACE>/<NEW-PROJECT>
```

Note the absence of the experiment ID in the destination path.

##### Uploading an Entire Workspace

As well as uploading an entire workspace:

```shell
COMET_URL_OVERRIDE=http://comet.b.com/clientlib \
COMET_API_KEY=B-KEY \
cometx copy <WORKSPACE> <NEW-WORKSPACE>
```

