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
            plain_key = await use_case.execute(CreateApiKeyDTO(user_id=UUID(user_id)))
        except UserNotFoundError as exc:
            console.print(f"[red]x[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print("[green]v[/green] API key created successfully:")
        console.print(f"  - User ID: {user_id}")
        console.print(f"  - API Key: {plain_key}")
        console.print(
            "  [yellow]Save this key — it cannot be retrieved later.[/yellow]"
        )
