import typer

from src.contexts.auth.infrastructure.cli.create_api_key_command import (
    register_create_api_key_command,
)
from src.contexts.auth.infrastructure.cli.create_user_command import (
    register_create_user_command,
)
from src.contexts.auth.infrastructure.cli.deactivate_api_key_command import (
    register_deactivate_api_key_command,
)
from src.contexts.auth.infrastructure.cli.list_users_command import (
    register_list_users_command,
)
from src.contexts.shared.infrastructure.logger.setup import configure_loguru

# Setup
configure_loguru()

app = typer.Typer(
    name="fastapi-template-cli",
    help="Administrative CLI for FastAPI Template",
    no_args_is_help=True,
)

# Auth context commands
auth_app = typer.Typer(help="Auth management")
register_create_user_command(auth_app)
register_create_api_key_command(auth_app)
register_deactivate_api_key_command(auth_app)
register_list_users_command(auth_app)
app.add_typer(auth_app, name="auth")

if __name__ == "__main__":
    app()
