# tsgen 0.1.0

tsgen builds typescript interfaces and api boilerplate based on python types and flask route definitions

## Features
### Currently supported type translations

| Python type   | Typescript type | Note   |
| ------------- | --------------- | ------ |
| dataclass     | interface       |        |
| int           | number          |        |
| float         | number          |        |
| bool          | boolean         |        |
| list          | Array           |*type*[]|

### Flask integration

The flask integration relies on typing hints in the flask endpoint declarations to generate typescript source code for accessing the endpoints.

To prepare an endpoint for source generation, make sure it has a python return type annotation and decorate your flask route with the `@tsgen.flask.typed` decorator:

```python
@app.route("/api/foo/<my_id>")
@typed()
def get_foo(my_id) -> Foo:
    return Foo(...)
```
__IMPORTANT__: The `typed` decorator must currently be applied before to the flask endpoint registration. This means it must be written after the `route` decorator in source code order.

To generate the typescript source files, run the following command in the context of your flask app:

```bash
flask tsgen build
```

For the above example, the following function is generated:
```typescript
export const getFoo = async (myId: string): Promise<Foo> => {
  const resp = await fetch(`/api/foo/${myId}`, {
    method: 'GET'
  });
  const data: Foo = await resp.json();
  return data;
}
```

### Name formatting
tsgen translates python *snake_case* field names and function names into *camelCase* variables and functions in typescript to conform with standard linting rules in each context.


## TODO
-[ ] More generic api support for other frameworks than Flask
-[ ] Support for typed/casted url arguments in api routes
-[ ] Support for pydantic validation in flask payload injection (would help solving the following two as well)
    -[ ] Unpack nested json structures in injected payloads
    -[ ] Automated data validation for injected payloads
