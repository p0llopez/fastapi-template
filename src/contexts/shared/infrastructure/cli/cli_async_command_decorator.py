import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

import typer
from loguru import logger
from rich.console import Console

console = Console()


def cli_async_command[**P, R](
    fn: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        async def run() -> R:
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                name = getattr(fn, "__name__", repr(fn))
                logger.error(f"Error in {name}: {e}")
                console.print(f"[red]✗[/red] Error: {e}")
                raise typer.Exit(code=1) from e

        return asyncio.run(run())

    return wrapper
