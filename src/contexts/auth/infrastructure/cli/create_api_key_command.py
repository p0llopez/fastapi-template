from uuid import UUID

import typer

from src.contexts.auth.application.use_cases.create_api_key import CreateApiKeyDTO
from src.contexts.auth.domain.errors import UserNotFoundError
from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.cli import cli_async_command, console
from src.contexts.shared.infrastructure.container import SharedContainer


def register_create_api_key_command(app: typer.Typer) -> None:
    @app.command("create-api-key", help="Create a new API key for a user")
    @cli_async_command
    async def create_api_key(
        user_id: str = typer.Option(
            ..., "--user-id", "-u", help="User ID to create the API key for"
        ),
    ) -> None:
        container = AuthContainer(shared=SharedContainer())
        use_case = container.create_api_key_use_case()
        try:
            api_key = await use_case.execute(CreateApiKeyDTO(user_id=UUID(user_id)))
        except UserNotFoundError as exc:
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print("[green]✓[/green] API key created successfully:")
        console.print(f"  • ID: {api_key.api_key_id}")
        console.print(f"  • User ID: {api_key.user_id}")
        console.print(f"  • API Key: {api_key.api_key}")
        console.print(f"  • Active: {'yes' if api_key.is_active else 'no'}")
        console.print(f"  • Created: {api_key.created_at}")
