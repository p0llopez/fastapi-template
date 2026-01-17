# FastAPI Template

A production-ready FastAPI template implementing Domain-Driven Design (DDD) and Clean Architecture principles with Dependency Injection, featuring authentication, database migrations, and Docker deployment.

## 🚀 Features

- **Clean Architecture**: Organized by contexts following DDD principles
- **Dependency Injection**: Using `dependency-injector` for better testability and modularity
- **Authentication**: API Key middleware (global dependency) with public-route decorator
- **CLI Commands**: Typer-based administrative CLI for user management and more
- **Database Management**:
  - PostgreSQL with async SQLAlchemy
  - Alembic for database migrations
  - Connection pooling and health checks
- **Docker Support**: Complete Docker Compose setup for development and production
- **Code Quality**:
  - Ruff for linting and formatting (configured with extensive rule sets)
  - Pre-commit hooks
  - Type hints targeting Python 3.13
- **Structured Logging**: Loguru integration with request/response middleware
- **Settings Management**: Pydantic Settings with environment-based configuration
- **Production Ready**:
  - Multi-stage Docker builds
  - Health check endpoints
  - Non-root user execution
  - Hot reload in development

## 📋 Requirements

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer (used locally and in Docker)
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL 16+ (handled by Docker Compose)

## 🏗️ Project Structure

```
fastapi-template/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── settings.py                # Application settings & configuration
│   ├── container.py               # Dependency injection container
│   └── contexts/                  # DDD contexts
│       ├── auth/                  # Authentication context
│       │   ├── domain/           # Domain models & repositories
│       │   ├── application/      # Use cases
│       │   └── infrastructure/   # Persistence, HTTP middleware, CLI
│       └── shared/               # Shared kernel
│           ├── domain/
│           └── infrastructure/   # Database, cache, logging
├── migrations/                    # Alembic database migrations
├── scripts/                       # Utility scripts (init_db, etc.)
├── secrets/                       # Environment variables (.env)
├── docker-compose.yaml           # Docker services definition
├── Dockerfile                    # Multi-stage Docker build
├── Makefile                      # Development commands
└── pyproject.toml               # Project dependencies & config
```

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/p0llopez/fastapi-template.git
cd fastapi-template
```

### 2. Set Up Environment Variables

Create a `.env` file in the `secrets/` directory (used by the app and Docker Compose):

```bash
cp secrets/.env.example secrets/.env
```

### 3. Start with Docker Compose (Recommended)

```bash
# Build and start all services
make build && make start

# Or manually:
docker compose up --build
```

The API will be available at `http://localhost:8080`

### 4. Local Development (without Docker)

```bash
# Install dependencies with uv
make install

# Or manually:
uv sync

# Run database migrations (requires DATABASE_URL)
make migration-upgrade

# Start the application
uv run uvicorn src.main:app --reload
```

## 🛠️ Development Commands

The project includes a comprehensive Makefile for common tasks:

### Docker Operations

```bash
make start           # Start all services
make stop            # Stop all services
make build           # Build Docker images
make restart         # Restart all services
make logs            # Follow application logs
make shell           # Open bash in app container
make db-shell        # Open psql in database container
```

If your environment file lives in `secrets/.env`, run:

```bash
ENV_FILE=secrets/.env make db-shell
```

### Database Migrations

```bash
make migration-create              # Create auto-generated migration
make migration-create-empty        # Create empty migration template
make migration-upgrade             # Apply all pending migrations
make migration-downgrade           # Rollback last migration
make migration-history             # Show migration history
make migration-current             # Show current migration version
make migration-show                # Show current head revision
make migration-sql                 # Generate SQL for upgrade head
```

### Code Quality

```bash
make fmt             # Format code with ruff
make lint            # Run linter with auto-fix
make test            # Run tests with pytest
make all             # Run install, format, lint, and test
make clean           # Remove __pycache__ and .pyc files
```

### CLI Commands

```bash
# Make sure services are running first
make start

# Show CLI help
make cli

# Run CLI commands (pass args explicitly):
make cli args="auth list-users"
make cli args="auth create-user --username admin --email admin@example.com"
make cli args="auth create-api-key --user-id <uuid>"
make cli args="auth deactivate-api-key --user-id <uuid> --api-key <key>"

# For local development (without Docker):
uv run cli auth create-user --username admin --email admin@example.com
uv run cli auth list-users
```

## 📚 Architecture Overview

### Domain-Driven Design (DDD)

The project is organized into **contexts** (bounded contexts in DDD terminology):

- **Auth Context**: Handles authentication, users, and API keys
- **Shared Context**: Common infrastructure (database, logging, caching)

Each context follows a layered architecture:

1. **Domain Layer**: Business logic, entities, and repository interfaces
1. **Application Layer**: Use cases and business workflows
1. **Infrastructure Layer**: Database models, external services, and implementations

### Dependency Injection

The application uses `dependency-injector` for managing dependencies:

- `ApplicationContainer`: Root container
- Context-specific containers (e.g., `AuthContainer`, `SharedContainer`)
- Providers for repositories, use cases, and services

### Example: Adding a New Feature

To add a new feature (e.g., a "Products" context):

1. Create the context structure:

   ```
   src/contexts/products/
   ├── domain/
   │   ├── aggregates.py      # Product entity
   │   └── repositories.py    # Repository interface
   ├── application/
   │   └── use_cases/         # Business logic
   └── infrastructure/
       ├── container.py       # DI container
       └── persistence/       # Database models
   ```

1. Register in the main container (`src/container.py`)

1. Create database models and migrations

1. Implement use cases and endpoints

## 🔐 Authentication & Users

The template includes an API Key authentication system and user management:

- **User Management**: Create and list users via CLI (passwords are bcrypt-hashed)
- **API Keys**: Generate and validate API keys for authentication
- **HTTP**: All routes require `X-API-Key` unless explicitly marked public

### CLI User Management

```bash
# Create user (interactive prompt for password)
make cli args="auth create-user"

# List users
make cli args="auth list-users"
```

### API Key Authentication

```python
from src.contexts.auth.application.use_cases import AuthenticateWithApiKeyUseCase

# In your endpoint:
is_valid = await authenticate_use_case.execute(api_key="user-api-key")
```

### HTTP Authentication Behavior

- Global dependency: all routes require the `X-API-Key` header.
- Public routes: decorate handlers with `@public` to bypass auth.
- Health endpoints:
  - `GET /health` is public.
  - `GET /health-protected` requires `X-API-Key`.

> Note: The auth HTTP endpoints are not exposed yet. Use the CLI for now or add a router under `src/contexts/auth/infrastructure/http/` and include it in `src/main.py`.

````

## 🗄️ Database

### Migrations

The project uses Alembic for database migrations:

```bash
# Create a new migration after modifying models
make migration-create

# Apply migrations
make migration-upgrade

# Rollback last migration
make migration-downgrade
````

### Database Initialization

Run the initialization script to set up the database and apply migrations:

```bash
docker compose exec app python -m scripts.init_db
```

## 🐳 Docker Deployment

### Multi-Stage Build

The Dockerfile uses a multi-stage build for optimized images:

1. **Base**: Python 3.13 slim image
1. **Builder**: Installs dependencies using uv
1. **Runner**: Final image with only runtime dependencies

### Production Considerations

- Non-root user execution for security
- Compiled bytecode for faster startup
- Health checks for container orchestration
- Volume mounts for hot reload in development

### Environment Variables

Control build behavior:

```bash
# Build with dev dependencies
docker compose build --build-arg INSTALL_DEV=true

# Production build
docker compose build --build-arg INSTALL_DEV=false
```

## ⚙️ Configuration

Configuration is managed through `src/settings.py` using Pydantic Settings:

```python
from src.settings import settings

# Access configuration
if settings.is_production:
    # Production-specific code
    pass

# Database URL
db_url = settings.database_url

# Feature flags
log_level = settings.log_level
```

### Available Settings

- **Application**: `environment`, `log_level`
- **Security**: `secret_key`, `allowed_origins`
- **Database**: `database_url`

## 📝 Logging

Structured logging with Loguru:

- Request/response logging middleware
- Configurable log levels
- JSON formatting for production
- Console formatting for development

## 🤝 Contributing

1. Fork the repository
1. Create a feature branch (`git checkout -b feature/amazing-feature`)
1. Commit your changes using conventional commits
1. Push to the branch (`git push origin feature/amazing-feature`)
1. Open a Pull Request

### Code Style

This project uses:

- **Ruff** for linting and formatting
- **Pre-commit hooks** for automated checks
- **Conventional commits** with gitmoji

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**Pol López Cano**

- Email: pol.lopez.cano@gmail.com
- GitHub: [@p0llopez](https://github.com/p0llopez)

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- Astral's uv for blazing-fast package management
- The Python community for amazing tools and libraries

______________________________________________________________________

**Happy Coding! 🎉**
