# tsgen 0.1.0

tsgen is a lightweight library for building typescript interfaces and client side accessor boilerplate based on Python types and (Flask) route definitions.

## Who is it for?
Mainly for myself ;) I built it because it was fun to build from scratch and learn a bit more about python type hint introspection.

It can be useful for anyone who is setting up a new web project with a typescript frontend and a Python/Flask backend and want to build/prototype something quickly without having to write client code boilerplate or set up more complicated client code generation systems.

## Installation instructions
Due to the feature incompleteness, hacky nature of the project and lack of current commitment to updating the project, it's currently not added to pypi.

You can install the package using a git reference, e.g.: `pip install git+git://github.com/freider/tsgen.git`.

To enable the code generation cli tool, add the `tsgen.flask.cli_blueprint` to your flask app:

```python
from flask import Flask
from tsgen.flask_integration import cli_blueprint

app = Flask(__name__)
app.register_blueprint(cli_blueprint)
```
The blueprint registers no routes, but adds the `tsgen` group of command line tools to your flask app (e.g. `flask tsgen build`)

## Features
* Generation of typescript interfaces based on Python data classes ([PEP 557](https://www.python.org/dev/peps/pep-0557/)).
* Generation of typescript client side accessor functions using `fetch` to get/post typed data to/from flask routes.
* Payload data injection for flask views, to access http body payload data as typed data instead of untyped json-like structures

### Example

The flask integration relies on typing hints in the flask endpoint declarations to generate typescript source code for accessing the endpoints.

To prepare an endpoint for source generation, make sure it has a python return type annotation and decorate your flask route with the `@tsgen.flask.typed` decorator:

```python
from dataclasses import dataclass

from flask import Flask
from tsgen.flask_integration import typed, cli_blueprint

app = Flask(__name__)
app.register_blueprint(cli_blueprint)


@dataclass
class Foo:
    one_field: str


@app.route("/foo/<id>")
@typed()
def get_foo(id) -> Foo:
    return Foo(one_field=f"hello {id}")
```
__IMPORTANT__: The `typed` decorator must currently be applied before to the flask endpoint registration. This means it must be written after the `route` decorator in source code order.

To generate the typescript source files, run the following command in the context of your flask app:

```shell
flask tsgen build /some/output/dir
```

Using the above route example, the following typescript interface and function is generated:
```typescript
interface Foo {
  oneField: string;
}

export const getFoo = async (id: string): Promise<Foo> => {
  const resp = await fetch(`/foo/${id}`, {
    method: 'GET'
  });
  const data: Foo = await resp.json();
  return data;
}
```

### Flask payload injection
The `typed()` decorator described above also adds typed *data injection* to your flask view functions on the python side. Add a type annotated argument to your flask view function and it will be automatically populated with data from the request payload (the contents of `flask.request.json`)

```python
@dataclass
class Bar:
    sub_field: Foo
    other_field: str


@app.route("/bar/", methods=["POST"])
@typed()
def create_bar(bar: Bar) -> Foo:
    return bar.sub_field
```

The added argument also ensures that the generated typescript client function takes the same typed parameter as an argument:
```typescript
interface Bar {
  subField: Foo;
  otherField: string;
}

export const createBar = async (bar: Bar): Promise<Foo> => {
  const resp = await fetch(`/bar/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(bar),
  });
  const data: Foo = await resp.json();
  return data;
}
```

Data injection currently only supports a single dataclass injection representing a single top level json object in the request body.

### Currently supported type translations

| Python type   | Typescript type | Note   |
| ------------- | --------------- | ------ |
| dataclass     | interface       |        |
| int           | number          |        |
| float         | number          |        |
| bool          | boolean         |        |
| list          | Array           |*type*[]|

It should be relatively straight forward to add support for additional data types as needs arises (e.g. dicts and date/datetime objects)

### Name formatting
tsgen translates python *snake_case* field names and function names into *camelCase* variables and functions in typescript to conform with standard linting rules in each context. This renaming rule is currently non-optional.

### "Hot reloading"
Add a `dev_reload_hook` call at the bottom of your flask app file to have the client code be automatically generated whenever you change your code in flask `development` mode (i.e. every time that flask reloads the app)

```python
from flask import Flask
from tsgen.flask_integration import dev_reload_hook

app = Flask(__name__)

# ... add routes
dev_reload_hook(app, "/your/output/path")
```

Together with HMR support on the bundler side (using parcel or webpack or similar) this can be extremely powerful as you can basically change stuff in your backend api and have the changes reflect in your browser without a hard page refresh.



## Dev/Testing instructions
The examples dir serves as a simple development environment for the library, as well as a "manual" integration test. To build and run it using docker-compose, run the following command:
```shell
docker-compose -f docker-compose.dev.yml up --build
```
You can then inspect the test results by navigating to http://localhost:1234

The architecture of the simple example is similar to what you might have in production as well:
* A rest-like api defined in flask
* A frontend in html + js/typescript, including the tsgen-generated api client code
* Node + Parcel to build a deliverable html bundle.

## Gotchas
### Postponed annotations
With the introduction of [PEP 563](https://www.python.org/dev/peps/pep-0563/) in Python 3.10 (or using `from __future__ import annotations`) types are no longer evaluated at the time they are declared. This can sometimes break the type inferrence, if you for example declare your routes as closures inside of other functions.


## TODO
### Major
* More generic api support for other frameworks than Flask (starlette, fastapi?)
* Support for non-json-standard datatypes serde - e.g. date/datetime data types

### Minor
* Support for typed/casted url arguments in api routes
* dict/object data types
