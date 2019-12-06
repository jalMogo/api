[![Build Status](https://circleci.com/gh/jalmogo/api.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/jalmogo/api.svg?style=shield&circle-token=:circle-token)

Mapseed API
===============

The Mapseed API is the data storage and data management component that
powers the Mapseed web application.
It is a REST API for flexibly storing data about places and an UI for managing
and exporting your data.

## Prereq's

 * python 3.7
 * virtualenv
   * virtualenv can be made with the following command: `mkvirtualenv --python=python3.7 ms-api`
 * Docker
 * docker-compose


## Installation

### pip install deps

```
pip install -r requirements.txt
```

Note that on MacOS, if you are having error building psycopg2, you may need the following:

```
env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pip install psycopg2
```
https://stackoverflow.com/a/39244687

## contributing

We use [Black](https://github.com/psf/black) as our code formatter, along with [isort](https://pypi.org/project/isort/). Editor integration is encouraged.

You can format the entire project in one command with `black .` from the project root. Tests will be check by running `black --check .` from the project root.

*TOOD: consider using pre-commit hook as described [here](https://dev.to/notsag/python-code-formatting-using-black-2fe1) and [here](https://adamj.eu/tech/2019/06/20/all-is-turned-to-black/)*