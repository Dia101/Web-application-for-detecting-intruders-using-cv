from functools import wraps
from flask import redirect
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError


def protected_route(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(locations=["cookies"])
            get_jwt_identity()
        except NoAuthorizationError:
            return redirect("/login")
        return view_func(*args, **kwargs)
    return wrapper
