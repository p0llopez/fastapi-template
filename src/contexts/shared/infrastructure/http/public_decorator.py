from collections.abc import Callable


def public[F: Callable[..., object]](func: F) -> F:
    func.is_public = True
    return func
