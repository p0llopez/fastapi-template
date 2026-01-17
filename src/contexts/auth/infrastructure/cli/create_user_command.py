import typer

from src.contexts.auth.application.use_cases.create_user import CreateUserDTO
from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.cli import cli_async_command, console
from src.contexts.shared.infrastructure.container import SharedContainer


def register_create_user_command(app: typer.Typer) -> None:
    @app.command("create-user", help="Create a new user")
    @cli_async_command
    async def create_user(
        username: str = typer.Option(..., "--username", "-u", help="Username"),
        password: str = typer.Option(
            ...,
            "--password",
            "-p",
            help="Password (will be bcrypt-hashed)",
            prompt=True,
            hide_input=True,
        ),
        email: str | None = typer.Option(None, "--email", "-e", help="User email"),
    ) -> None:
        container = AuthContainer(shared=SharedContainer())
        use_case = container.create_user_use_case()
        user = await use_case.execute(
            CreateUserDTO(username=username, password=password, email=email)
        )

        console.print("[green]✓[/green] User created successfully:")
        console.print(f"  • ID: {user.user_id}")
        console.print(f"  • Username: {user.username}")
        console.print(f"  • Email: {user.email or 'N/A'}")
        console.print(f"  • Created: {user.created_at}")
