import argparse
import logging
import os
import typing
from functools import wraps

import sanic

from tsgen.apis import prepare_function, get_prepared_info, ClientBuilder, has_prepared_info, PreparedCallableType


logger = logging.getLogger(__name__)


def typed(localns=None):
    """Decorator to mark sanic view function for typescript client support

    * Mark a view for typescript client code generation
    * Inject an attached json body as a typed argument
    * Allow for custom data <-> json conversions in injected and returned data
    * Always return json for return-value-annotated views
    """
    def generator(func: typing.Callable):
        prepare_function(func, localns=localns, ignore_args=1)  # skip the request argument even if it's type annotated
        info = get_prepared_info(func)

        @wraps(func)
        async def new_f(request: sanic.Request, **kwargs):
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


def collect_endpoints(app: sanic.Sanic) -> ClientBuilder:
    """Generate typescript clients and types for a sanic app

    :param app: Sanic app with @typed()-decorated api routes
    """
    client_builder = ClientBuilder()

    router = app.router
    if not router.finalized:
        router.finalize()

    for path, route in router.routes_all.items():
        func: PreparedCallableType = route.handler

        if has_prepared_info(func):
            method = "GET"
            if "POST" in route.methods:
                method = "POST"
            elif "PUT" in route.methods:
                method = "PUT"
            url_pattern = '/'.join(path)

            # TODO/MAYBE: use param.label to also inject types for url params on the client side
            url_args = [param.name for param in route.params.values()]
            client_builder.add_endpoint(func, url_pattern, url_args, method)

    return client_builder


def build_and_save_api(app: sanic.Sanic, root_dir: str):
    logger.info(f"Writing client code to {root_dir}")
    client_builder = collect_endpoints(app)
    client_builder.save_to_disk(root_dir)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#
#     parser.add_argument("module")
#
#     if root_dir is None:
#         root_dir = os.environ.get("TSGEN_OUTPUT_DIR")
