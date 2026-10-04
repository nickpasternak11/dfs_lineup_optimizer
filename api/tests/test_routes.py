import inspect

from fastapi.routing import APIRoute

from app.application import application


def test_route_handlers_are_not_async():
    # Handlers run blocking work (SQLAlchemy queries, the PuLP solve). As
    # `async def` that work runs on the event loop and stalls every other
    # request; as plain `def`, FastAPI runs each one in its thread pool.
    async_routes = [
        route.path
        for route in application.routes
        if isinstance(route, APIRoute) and inspect.iscoroutinefunction(route.endpoint)
    ]
    assert async_routes == []
