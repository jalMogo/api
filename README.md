[![Build Status](https://circleci.com/gh/jalmogo/api.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/jalmogo/api.svg?style=shield&circle-token=:circle-token)

Mapseed API
===============

The Mapseed API is the data storage and data management component that
powers the Mapseed web application.
It is a REST API for flexibly storing data about places and an UI for managing
and exporting your data.

## Installation

Note that on MacOS, if you are having error building psycopg2, you may need the following:

```
env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pip install psycopg2
```
https://stackoverflow.com/a/39244687