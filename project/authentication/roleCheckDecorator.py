import json
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import Request, Response

def roleCheck(role):
    def innerRole(function):
        @wraps(function)
        def decorator(*args, **kwargs):
            # Move the JWT verification inside this inner function
            verify_jwt_in_request()
            claims = get_jwt()
            if ("roles" in claims) and (role in claims["roles"]):
                return function(*args, **kwargs)
            else:
                responseData = {}
                responseData["msg"] = "Missing Authorization Header"  # Update this error message
                return Response(json.dumps(responseData), status=401)
        return decorator
    return innerRole
