from uuid import UUID

import typer

from src.contexts.auth.application.use_cases.revoke_api_key import RevokeApiKeyDTO
from src.contexts.auth.domain.errors import ApiKeyNotFoundError, UserNotFoundError
from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.cli import cli_async_command, console
from src.contexts.shared.infrastructure.container import SharedContainer


def register_deactivate_api_key_command(app: typer.Typer) -> None:
    @app.command("deactivate-api-key", help="Deactivate an API key for a user")
    @cli_async_command
    async def deactivate_api_key(
        user_id: str = typer.Option(
            ..., "--user-id", "-u", help="User ID that owns the API key"
        ),
        api_key: str = typer.Option(
            ..., "--api-key", "-k", help="API key to deactivate"
        ),
    ) -> None:
        container = AuthContainer(shared=SharedContainer())
        use_case = container.revoke_api_key_use_case()
        try:
            await use_case.execute(
                RevokeApiKeyDTO(user_id=UUID(user_id), api_key=api_key)
            )
        except UserNotFoundError as exc:
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except ApiKeyNotFoundError as exc:
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print("[green]✓[/green] API key deactivated successfully:")
        console.print(f"  • User ID: {user_id}")
        console.print(f"  • API Key: {api_key}")
