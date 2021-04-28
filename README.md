# tsgen 0.3.2

tsgen is a lightweight library for building typescript interfaces and client side api accessor boilerplate based on Python types and (Flask) route definitions.

## Who is it for?
Mainly for myself ;) I built it because it was fun to build from scratch and learn a bit more about python type hint introspection and various aspects of typing syntax in both Python and TypeScript. 

However - It can definitely be useful for anyone who is setting up a new web project with a typescript frontend and a Python/Flask backend and want to build/prototype something quickly without having to write client code boilerplate or set up more complicated client code generation systems.

## Installation instructions
The package is currently not in pypi. You can install the package using a git reference, e.g.:
```shell
pip install git+git://github.com/freider/tsgen.git@v0.3.2
```

To enable the code generation cli tool, call `init_tsgen(app)`on your flask app:

```python
from flask import Flask
from tsgen.flask_integration import init_tsgen

app = Flask(__name__)
init_tsgen(app)
```
The extension doesn't add or modify any routes but adds the `tsgen` group of command line tools to your flask app (e.g. `flask tsgen build`)

## Features
* Generation of TypeScript interfaces based on Python type annotations, including dataclasses ([PEP 557](https://www.python.org/dev/peps/pep-0557/)).
* Generation of TypeScript client side api accessor functions using `fetch` to get/post typed data to/from flask routes.
* Provides payload data injection for flask views, to access http body payload data as typed data instead of untyped json-like structures (similar to FastAPI)

### Example

The flask integration relies on typing hints in the flask view definitions.

To prepare a flask view function for source generation, make sure it has a python return type annotation and decorate your flask route with the `@tsgen.flask.typed` decorator:

```python
from dataclasses import dataclass
from flask import Flask
from tsgen.flask_integration import init_tsgen, typed

app = Flask(__name__)
init_tsgen(app)


@dataclass
class Foo:
  one_field: str


@app.route("/foo/<foo_id>")
@typed()
def get_foo(foo_id) -> Foo:
  return Foo(one_field=f"hello {foo_id}")
```
__IMPORTANT__: The `typed` decorator must be applied before to the flask route decorator. This means it must be written *after* the `route` decorator in source code order:
```python
@app.route("/foo/<foo_id>")
@typed()
```

To generate typescript source files, run the following command in the context of your flask app:

```shell
flask tsgen build
```

Using the above route example, the following typescript interface and function is generated:
```typescript
export interface Foo {
  oneField: string;
}


export const getFoo = async (fooId: string): Promise<Foo> => {
  const response = await fetch(`/foo/${fooId}`, {
    method: 'GET'
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }
  return await response.json();
}
```

### Flask payload injection
The `typed()` decorator described above also adds typed *data injection* to your flask view functions on the python side. Add a type annotated argument to your flask view function and it will be automatically populated with data from the request payload (the contents of `flask.request.json`)

```python
@dataclass()
class Bar:
    something: str


@app.route("/bar/", methods=["POST"])
@typed()
def create_bar(bar: Bar) -> str:
    return f"hello {bar.something}"
```

The added argument also ensures that the generated typescript client function takes the same typed parameter as an argument:
```typescript
export interface Bar {
  something: string;
}


export const createBar = async (bar: Bar): Promise<string> => {
  const response = await fetch(`/bar/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(bar),
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }
  return await response.json();
}
```

In the end the effect is that you can effectively "call" your python 
functions from your frontend js code.


### Json translation
For datatypes that are not directly supported by the json standard, like dates and datetimes, `tsgen` supports custom data transfer objects (*DTO*s) and packing/unpacking of those.

```python
import datetime

@app.route("/some-dates/")
@typed()
def some_dates() -> list[datetime.datetime]:
    return [
        datetime.datetime.utcnow(),
        datetime.datetime.utcnow() + datetime.timedelta(1)
    ]
```

Generated typescript:
```typescript
export const someDates = async (): Promise<Date[]> => {
  const response = await fetch(`/some-dates/`, {
    method: 'GET'
  });
  if (!response.ok) {
    throw new ApiError("HTTP status code: " + response.status, response);
  }   
  const dto: string[] = await response.json();
  return dto.map(item => (new Date(item)));
}
```

### Current supported type translations

| Python type          | Typescript type      | Note                        |
| -------------        | ---------------      | -----------------------     |
| `dataclass`          | `interface`          |                             |
| `int`                | `number`             |                             |
| `float`              | `number`             |                             |
| `bool`               | `boolean`            |                             |
| `list[T]`            | `T[]`                |                             |
| `tuple[T...]`        | `[T...]`             |                             |
|` dict[str, T]`        | `{ [key: string]: T}`| Only `str` keys due to js constraints |
| `datetime.datetime`  | `Date`               | Using ISO 8601 string DTOs  |
| `datetime.date`      | `Date`               | same without time part    |
| `typing.Optional[T]` | `T \ null`           | (<-- pipe character) |


Additional types can be added by implementing a new subclass of the `tsgen.typetree.AbstractNode` and adding it to `tsgen.typetree.type_registry`.

### Name formatting
tsgen translates python *snake_case* field names and function names into *camelCase* variables and functions in typescript to conform with standard linting rules in each context. This renaming rule is currently non-optional.

### "Hot reloading"
Add a `dev_reload_hook` call at the bottom of your flask app file (at module level) to have the client code be automatically generated whenever you change your code in flask `development` mode.

```python
from flask import Flask
from tsgen.flask_integration import dev_reload_hook

app = Flask(__name__)

# ...
# After route definitions:
dev_reload_hook(app)
```

Together with HMR support on the bundler side (using parcel or webpack or similar) this can be extremely powerful as you can basically change stuff in your backend api and have the changes reflect in your browser without a hard page refresh.



## Dev/Testing instructions
The examples dir serves as a simple development environment for the library, as well as a "manual" integration test. To build and run it using docker-compose, run the following command:
```shell
docker-compose up --build
```
You can then inspect the test results by navigating to http://localhost:1234

The architecture of the simple example is similar to what you might have in production as well:
* A json api defined in flask
* A frontend in html + js/typescript, including the tsgen-generated api client code
* Node + Parcel to build a deliverable html bundle.

## Gotchas
### Postponed annotations
With the possible introduction of [PEP 563](https://www.python.org/dev/peps/pep-0563/) in Python 3.11 (or using `from __future__ import annotations`) types are no longer evaluated at the time they are declared. This can sometimes break the type inference, if you for example declare your routes as closures inside other functions. You can provide `localns=locals()` to the `typed()` decorator which can help.


## TODO
### Major
* More generic api support for other frameworks than Flask (starlette, fastapi?)
* Support for multiple input parameters (?)

### Minor
* Improved error messages when data doesn't conform to type declarations
* Support for typed/casted url arguments in api routes, and maybe query params?
* New types
  * Union types
  * Support for "*any*" untyped subtrees ?
