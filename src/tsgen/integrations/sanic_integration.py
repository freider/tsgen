import functools
import typing
from functools import wraps

import sanic

from tsgen.apis import prepare_function, get_prepared_info


def typed(localns=None):
    """Decorator to mark sanic view function for typescript client support

    * Mark a view for typescript client code generation
    * Inject an attached json body as a typed argument
    * Allow for custom data <-> json conversions in injected and returned data
    * Always return json for return-value-annotated views
    """
    def generator(func: typing.Callable):
        prepare_function(func, localns=localns)
        info = get_prepared_info(func)

        @wraps(func)
        async def new_f(request: sanic.Request, **kwargs):
            # if dataclass arg has been specified, build one and add it as an arg
            new_kwargs = kwargs.copy()
            payload_args = set(info.arg_type_trees.keys()) - set(kwargs.keys())
            if payload_args:
                payload_name = list(payload_args)[0]
                payload_tree = info.arg_type_trees[payload_name]
                new_kwargs[payload_name] = payload_tree.parse_dto(request.json)

            response = await func(request, **new_kwargs)
            if info.return_type_tree is None:
                return response  # unannotated return value returns raw response
            return sanic.response.json(info.return_type_tree.create_dto(response))

        return new_f

    return generator
