# Source - https://stackoverflow.com/a
# Posted by Freifrau von Bleifrei, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-11, License - CC BY-SA 4.0

from functools import wraps
from importlib.util import find_spec
from types import FunctionType


def requires(module_name: str):
    def decorator(obj):
        spec = find_spec(module_name)
        if spec is None:
            raise ImportError(f"Optional dependency {module_name} required, install it with `pip install mamma-mia[{module_name}]`")

        # If it's a function, wrap it
        if isinstance(obj, FunctionType):
            @wraps(obj)
            def wrapper(*args, **kwargs):
                return obj(*args, **kwargs)

            return wrapper

        # Otherwise, assume it's a class and return it unchanged
        return obj

    return decorator

