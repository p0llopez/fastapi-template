import asyncio
import sys

from faker import Faker
from loguru import logger
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.table import Table

from src.contexts.auth.application.use_cases.create_api_key import CreateApiKeyDTO
from src.contexts.auth.application.use_cases.create_user import CreateUserDTO
from src.contexts.auth.domain.errors import UsernameAlreadyExistsError
from src.contexts.auth.infrastructure.container import AuthContainer
from src.contexts.shared.infrastructure.cli import console
from src.contexts.shared.infrastructure.container import SharedContainer

MAX_RETRIES = 3

fake = Faker()


async def seed_users(
    count: int,
    auth: AuthContainer,
) -> list[dict[str, str]]:
    create_user = auth.create_user_use_case()
    create_api_key = auth.create_api_key_use_case()
    results: list[dict[str, str]] = []

    for i in range(count):
        user = None
        for _ in range(MAX_RETRIES):
            try:
                user = await create_user.execute(
                    CreateUserDTO(
                        username=fake.user_name(),
                        password=fake.password(),
                        email=fake.email(),
                    )
                )
            except UsernameAlreadyExistsError:
                continue
            else:
                break

        if not user:
            logger.warning(
                "Skipped user {}/{} after {} retries", i + 1, count, MAX_RETRIES
            )
            continue

        plain_key = await create_api_key.execute(CreateApiKeyDTO(user_id=user.user_id))
        results.append(
            {
                "Username": user.username,
                "Email": user.email or "N/A",
                "API Key": plain_key,
            }
        )

    return results


def display_results(title: str, results: list[dict[str, str]]) -> None:
    if not results:
        console.print(f"  [yellow]No {title} created.[/yellow]")
        return

    table = Table(title=f"{title} ({len(results)})", show_lines=True)
    styles = {"Username": "green", "Email": "blue", "API Key": "cyan"}
    for col in results[0]:
        table.add_column(col, style=styles.get(col, ""))
    for row in results:
        table.add_row(*row.values())
    console.print(table)


async def main() -> None:
    console.print(
        Panel(
            "[bold]Database Seeder[/bold]\nGenerate random seed data for development",
            border_style="blue",
        )
    )

    count = IntPrompt.ask(
        "How many [green]users[/green] to create",
        default=5,
    )

    shared = SharedContainer()
    auth = AuthContainer(shared=shared)

    with console.status(f"Seeding {count} users..."):
        results = await seed_users(count, auth)

    console.print()
    display_results("Users", results)

    console.print(
        Panel("[bold green]Seed complete![/bold green]", border_style="green")
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(1)
    except Exception:
        logger.exception("Seed failed")
        sys.exit(1)
