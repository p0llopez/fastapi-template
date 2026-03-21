import typer
from rich.table import Table

from src.contexts.auth.application.use_cases.list_users import ListUsersDTO
from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.cli import cli_async_command, console
from src.contexts.shared.infrastructure.container import SharedContainer


def register_list_users_command(app: typer.Typer) -> None:
    @app.command("list-users", help="List all registered users")
    @cli_async_command
    async def list_users() -> None:
        container = AuthContainer(shared=SharedContainer())
        use_case = container.list_users_use_case()
        result = await use_case.execute(ListUsersDTO())

        if not result.items:
            console.print("[yellow]No users registered.[/yellow]")
            return

        table = Table(title=f"Users ({len(result.items)})")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Username", style="green")
        table.add_column("Email", style="blue")
        table.add_column("API Keys", justify="right", style="magenta")
        table.add_column("Active", justify="center")
        table.add_column("Created", style="dim")

        for user in result.items:
            active_keys = len(user.get_active_api_keys())
            table.add_row(
                str(user.user_id),
                user.username,
                user.email or "N/A",
                str(active_keys),
                "✓" if user.is_active else "✗",
                user.created_at.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)
