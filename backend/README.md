# 🛒 Product Price Tracker

A robust price monitoring system that automatically tracks product prices across multiple Brazilian e-commerce platforms (OLX, Mercado Livre, Enjoei, Estante Virtual). Built with FastAPI, Celery, and Clean Architecture principles.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![CI](https://github.com/pattersonrptr/product-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/pattersonrptr/product-tracker/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [First Run](#first-run)
- [API Documentation](#-api-documentation)
- [Running Tests](#-running-tests)
- [CI/CD](#-cicd)
- [Code Quality Tools](#-code-quality-tools)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Environment Variables](#-environment-variables)

---

## ✨ Features

### Core Functionality
- **🔍 Multi-Platform Scraping**: Automated data collection from 4 major Brazilian e-commerce sites
- **📊 Price History Tracking**: Monitor price changes over time (append-only records per product)
- **🔐 User Management**: Complete authentication and authorization system (JWT)
- **🌐 Source Websites**: Manage and configure e-commerce platforms to scrape
- **⚙️ Search Configurations**: Define custom search parameters, schedules, and target platforms (M2M with source websites)
- **📝 Search Execution Logs**: Audit trail of scraper runs (status, results count, error messages) — created by Celery workers via the API
- **�🔄 Async Task Processing**: Background jobs with Celery for efficient scraping
- **📝 JSON:API Compliant**: RESTful API following JSON:API specification

### Technical Features
- **Clean Architecture**: Well-organized layers (Domain, Use Cases, Infrastructure, Interfaces)
- **Repository Pattern**: Database abstraction for easy testing and maintenance
- **Comprehensive Testing**: Unit, integration, and E2E tests with pytest
- **Docker Support**: Fully containerized for consistent environments
- **Database Migrations**: Managed with Alembic
- **Structured Logging**: JSON logs for production, colored console for development

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                     │
│  Controllers → Presenters → Validators → Use Cases          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                   Domain Layer                              │
│  Entities • Validators • Business Logic                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│               Infrastructure Layer                          │
│  Repositories • Database • External Services                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Scrapers Module                            │
│  OLX • Mercado Livre • Enjoei • Estante Virtual            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | FastAPI, SQLAlchemy, Alembic |
| **Database** | PostgreSQL 13+ |
| **Task Queue** | Celery, Redis |
| **Authentication** | JWT (python-jose), bcrypt |
| **Scraping** | BeautifulSoup4, requests, cloudscraper |
| **Testing** | pytest, pytest-cov, pytest-asyncio |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Code Quality** | Ruff, MyPy, Pre-commit, Bandit |
| **Dependency Management** | Poetry |

---

## 🚀 Getting Started

### Prerequisites

- **Docker** and **Docker Compose** installed ([Installation Guide](https://docs.docker.com/engine/install/))
- **Git** for cloning the repository
- **8GB RAM** minimum (for running all services)
- **Poetry** ≥ 2.0 for local development ([Installation Guide](https://python-poetry.org/docs/#installation))

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/pattersonrptr/product-tracker.git
cd product-tracker
```

2. **Configure environment variables** (optional)

```bash
cp .env.example .env
# Edit .env with your custom values if needed
```

Default values work out-of-the-box for development.

3. **Build and start the containers**

```bash
docker compose up --build
```

This will:
- ✅ Build all Docker images
- ✅ Start PostgreSQL database
- ✅ Start Redis (message broker)
- ✅ Run database migrations
- ✅ Create default admin user
- ✅ Start the FastAPI server (`web`)
- ✅ Start Celery workers (`scraper`)
- ✅ Start Celery Beat scheduler (`celery-beat`)
- ✅ Start Flower monitoring UI (`flower`) — [http://localhost:5555](http://localhost:5555)

### First Run

After the containers are up, you'll see:

```
✓ Database migrations applied
✓ Superuser created: admin (ID: 1)
  Username: admin
  Password: admin
  Email: admin@example.com

INFO:     Uvicorn running on http://0.0.0.0:8000
```

**🎉 Your API is ready at [http://localhost:8000](http://localhost:8000)**

| Service | URL | Description |
|---------|-----|-------------|
| FastAPI | [http://localhost:8000](http://localhost:8000) | REST API |
| Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API docs |
| Flower | [http://localhost:5555](http://localhost:5555) | Celery task monitoring |
| PostgreSQL | `localhost:5432` | Database |
| Redis | `localhost:6379` | Message broker |

---

## 📚 API Documentation

### Interactive Documentation

Once the server is running, access:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Authentication

1. **Login** to get an access token:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

2. **Use the token** in subsequent requests:

```bash
curl -X GET "http://localhost:8000/users/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Or use the **Authorize** button in Swagger UI.

### Main Endpoints

#### Authentication
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/auth/register` | POST | Public user registration | ❌ |
| `/auth/login` | POST | Get access token | ❌ |
| `/auth/validate` | POST | Validate token | ✅ |

#### Users
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/users/` | GET | List all users | ✅ (Staff) |
| `/users/{id}` | GET | Get user by ID | ✅ (Staff) |
| `/users/` | POST | Create new user | ✅ (Superuser) |
| `/users/{id}` | PATCH | Update user | ✅ (Superuser) |
| `/users/{id}` | DELETE | Delete user | ✅ (Superuser) |

#### Products
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/products/` | GET | List products (paginated) | ✅ (Staff) |
| `/products/{id}` | GET | Get product by ID | ✅ (Staff) |
| `/products/url` | GET | Get product by URL | ✅ (Staff) |
| `/products/` | POST | Create new product | ✅ (Staff) |
| `/products/{id}` | PUT | Update product | ✅ (Staff) |
| `/products/{id}` | DELETE | Delete product | ✅ (Staff) |

#### Source Websites
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/source-websites/` | GET | List source websites (paginated) | ✅ (Staff) |
| `/source-websites/{id}` | GET | Get source website by ID | ✅ (Staff) |
| `/source-websites/name/{name}` | GET | Get source website by name | ✅ (Staff) |
| `/source-websites/` | POST | Create new source website | ✅ (Staff) |
| `/source-websites/{id}` | PUT | Update source website | ✅ (Staff) |
| `/source-websites/{id}` | DELETE | Delete source website | ✅ (Staff) |

#### Price Histories
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/price-histories/` | GET | List all price records (paginated) | ✅ (Staff) |
| `/price-histories/{id}` | GET | Get price record by ID | ✅ (Staff) |
| `/price-histories/product/{product_id}` | GET | Get all prices for a product | ✅ (Staff) |
| `/price-histories/product/{product_id}/latest` | GET | Get latest price for a product | ✅ (Staff) |
| `/price-histories/` | POST | Record new price for a product | ✅ (Staff) |
| `/price-histories/{id}` | DELETE | Delete price record | ✅ (Staff) |

#### Search Configurations
| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/search-configs/` | GET | List all search configs (paginated) | ✅ (Staff) |
| `/search-configs/{id}` | GET | Get search config by ID | ✅ (Staff) |
| `/search-configs/user/{user_id}` | GET | Get all search configs for a user | ✅ (Staff) |
| `/search-configs/` | POST | Create new search config | ✅ (Staff) |
| `/search-configs/{id}` | PUT | Update search config | ✅ (Staff) |
| `/search-configs/{id}` | DELETE | Delete search config | ✅ (Staff) |

#### Search Execution Logs

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/search-execution-logs/` | GET | List all execution logs (paginated) | ✅ (Staff) |
| `/search-execution-logs/` | POST | Create new execution log | ✅ (Staff) |
| `/search-execution-logs/{id}` | GET | Get execution log by ID | ✅ (Staff) |
| `/search-execution-logs/search-config/{id}` | GET | Get all logs for a search config | ✅ (Staff) |

---

## 🧪 Running Tests

### Local (without Docker)

> **Requirements**: [Poetry](https://python-poetry.org/docs/#installation) installed (`pipx install poetry` or see official docs).

```bash
# Install all dependencies (including dev: pytest, ruff, mypy, etc.)
poetry install

# Activate the virtual environment
poetry shell

# Run all tests
pytest src/tests/

# Run with verbose output
pytest -v src/tests/

# Run with coverage report
pytest --cov=src --cov-report=term-missing src/tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html src/tests/
# Open htmlcov/index.html in browser
```

### Via Docker

```bash
# Run all tests
docker exec -it web pytest src/tests/

# Run with verbose output
docker exec -it web pytest -vv src/tests/

# Run specific test file
docker exec -it web pytest src/tests/unit/use_cases/test_user_use_cases.py

# Run specific test function
docker exec -it web pytest src/tests/unit/use_cases/test_user_use_cases.py::TestCreateUserUseCase::test_execute_should_create_user_successfully

# Run with coverage report
docker exec -it web pytest --cov=src --cov-report=term-missing src/tests/

# Generate HTML coverage report
docker exec -it web pytest --cov=src --cov-report=html src/tests/
# Open htmlcov/index.html in browser
```

### Test Structure

```
src/tests/
├── unit/                    # Fast, isolated tests (with mocks)
│   ├── domain/
│   │   └── validators/      # Business rule validation
│   └── use_cases/           # Business logic tests
├── integration/             # Tests with real database
│   └── repositories/        # Data access layer tests
└── e2e/                     # End-to-end API tests
    └── controllers/         # Full HTTP request/response cycle
```

### Test Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Critical paths covered
- **E2E Tests**: Happy paths + error scenarios

### Bash API Tests (Manual Testing)

For manual testing with real HTTP requests while the API is running:

```bash
# Run all bash tests in order (auth → users → products → source_websites → price_histories → search_configs → search_execution_logs)
./src/scripts/api_tests/run_all_tests.sh

# Or with custom API URL
API_BASE_URL=http://localhost:8000 ./src/scripts/api_tests/run_all_tests.sh

# Run individual test scripts
./src/scripts/api_tests/auth/login.sh
./src/scripts/api_tests/users/list_users.sh
./src/scripts/api_tests/products/create_product.sh
./src/scripts/api_tests/source_websites/create_source_website.sh
./src/scripts/api_tests/price_histories/get_latest_price_by_product_id.sh
./src/scripts/api_tests/search_configs/list_search_configs.sh
./src/scripts/api_tests/search_execution_logs/list_search_execution_logs.sh
```

Scripts are organized by domain:

| Domain | Scripts | Coverage |
|--------|---------|----------|
| `auth/` | login, verify_token, refresh_token | POST /auth/login, verify, refresh |
| `users/` | list, get by id/username/email, create, update, delete | Full CRUD |
| `products/` | list, get by id/url, create, update, delete | Full CRUD |
| `source_websites/` | list, get by id, create, update, delete | Full CRUD |
| `price_histories/` | list, get by id, get by product, latest by product, create, delete | Append-only |
| `search_configs/` | list, get by id, get by user, create, update, delete | Full CRUD |
| `search_execution_logs/` | list, get by id, get by search config, create | Staff only |

**Features:**
- ✅ Validates API is reachable before running
- ✅ Runs tests in correct dependency order
- ✅ Colorful output with pass/fail summary
- ✅ Exit code for CI/CD integration (0 = success)

---

## ⚙️ CI/CD

This project uses **GitHub Actions** for continuous integration. The pipeline runs automatically on every push and on pull requests to `main`.

### Pipeline (`.github/workflows/ci.yml`)

| Step | Tool | Blocks merge? |
|------|------|---------------|
| **Lint** | `ruff check src/` | ✅ Yes |
| **Format check** | `ruff format --check src/` | ✅ Yes |
| **Type check** | `mypy src/` | ⚠️ No (informational) |
| **Tests + Coverage** | `pytest --cov-fail-under=60` | ✅ Yes |

### Triggers

- **Push** to any branch → runs full pipeline
- **Pull Request** to `main` → runs full pipeline (must pass to merge)

### Coverage Threshold

The pipeline enforces a minimum of **60% test coverage**. Current coverage: **~79%**.

### Test Count

| Domain | Unit (validators) | Unit (use cases) | Unit (presenters) | Integration | E2E | Total |
|--------|:-----------------:|:----------------:|:-----------------:|:-----------:|:---:|------:|
| User | ✅ | ✅ | ✅ | ✅ | ✅ | ~80 |
| Product | ✅ | ✅ | ✅ | ✅ | ✅ | ~57 |
| SourceWebsite | ✅ | ✅ | ✅ | ✅ | ✅ | ~77 |
| PriceHistory | ✅ | ✅ | ✅ | ✅ | ✅ | ~71 |
| SearchConfig | ✅ | ✅ | ✅ | ✅ | ✅ | ~85 |
| SearchExecutionLog | ✅ | ✅ | ✅ | ✅ | ✅ | ~65 |
| Auth | — | — | ✅ | — | ✅ | ~25 |
| **Total** | | | | | | **486** |

### Artifacts

The XML coverage report is uploaded as a GitHub Actions artifact (retained for 7 days) after each run.

---

## � Code Quality Tools

This project uses modern Python tools to maintain high code quality standards:

### Ruff - Fast Linter & Formatter

[Ruff](https://docs.astral.sh/ruff/) is an extremely fast Python linter and formatter, written in Rust. It replaces Black, isort, flake8, and more.

```bash
# Check code (linting)
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

**Configured rules:** pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-comprehensions, flake8-simplify

### MyPy - Static Type Checker

[MyPy](http://mypy-lang.org/) performs static type checking to catch type-related bugs before runtime.

```bash
# Check types
mypy src/

# Check specific module
mypy src/app/use_cases/
```

**Current strategy:** Gradual adoption with permissive settings. Core modules (use_cases, domain, entities) have stricter checking enabled.

### Pre-commit - Git Hooks

[Pre-commit](https://pre-commit.com/) automatically runs code quality checks before each commit.

```bash
# Install hooks (one-time setup)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

**Configured hooks:**
- ✅ **Ruff** (linter + formatter) - Blocks commits if issues found
- ⚠️ **MyPy** (type checker) - Manual stage (run with `--hook-stage manual`)
- ⚠️ **Bandit** (security scanner) - Manual stage
- ✅ Standard checks (trailing whitespace, EOF, YAML/JSON/TOML validation)

### Bandit - Security Scanner

[Bandit](https://bandit.readthedocs.io/) finds common security issues in Python code.

```bash
# Scan for security issues
bandit -r src/

# Generate detailed report
bandit -r src/ -f json -o bandit-report.json
```

### Poetry - Dependency Management

[Poetry](https://python-poetry.org/) provides modern dependency management with bette⚙️ Search Configurations: Define custom search parameters and schedules
🔄 Async Task Processing: Background jobs with r dependency resolution and reproducible builds via `poetry.lock`.

```bash
# Install dependencies (production + dev)
poetry install

# Install only production dependencies
poetry install --only main

# Add new dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Run commands in virtual environment
poetry run pytest
poetry run python -m src.main

# Export production requirements (used by Docker — do not edit manually)
poetry export --without dev --without-hashes -f requirements.txt -o requirements.txt
```

> **Note:** `pyproject.toml` / `poetry.lock` are the **source of truth** for all dependencies.
> `requirements.txt` contains **only production deps** and is auto-generated from the lock file — never edit it by hand.

### Running Quality Checks

```bash
# Complete quality check pipeline
ruff check . && ruff format --check . && mypy src/ && bandit -r src/

# Or use pre-commit for everything
pre-commit run --all-files --hook-stage manual
```

**Note:** These tools are integrated into the development workflow via pre-commit hooks, ensuring code quality is maintained automatically.

---

## �📁 Project Structure

```
product-tracker/
├── src/
│   ├── app/                           # Main application
│   │   ├── entities/                  # Domain entities (User, Product, SourceWebsite, PriceHistory, SearchConfig)
│   │   ├── fixtures/                  # Development fixtures (seed data)
│   │   ├── use_cases/                 # Business logic (one file per domain)
│   │   ├── domain/
│   │   │   └── validators/            # Domain validation rules (one file per domain)
│   │   ├── infrastructure/
│   │   │   ├── database/
│   │   │   │   └── models/            # SQLAlchemy ORM models + association tables
│   │   │   └── repositories/          # Data access implementations
│   │   ├── interfaces/
│   │   │   ├── http/                  # Web layer
│   │   │   │   ├── controllers/       # Request handlers (one router per domain)
│   │   │   │   ├── schemas/           # Pydantic request/response models
│   │   │   │   ├── presenters/        # Response formatters (JSON:API)
│   │   │   │   ├── middleware/        # HTTP middleware (CORS, logging, JSON:API)
│   │   │   │   └── setup/             # Application setup (middleware, routers, handlers)
│   │   │   └── repositories/          # Repository interfaces (ABCs)
│   │   └── security/                  # Authentication & authorization
│   ├── product_scrapers/              # Scraping module
│   │   ├── scrapers/
│   │   │   ├── olx.py
│   │   │   ├── mercado_livre.py
│   │   │   ├── enjoei.py
│   │   │   └── estante_virtual.py
│   │   ├── api/                       # API client for scrapers
│   │   └── celery/                    # Async tasks
│   ├── config/                        # Application configuration
│   │   ├── settings.py
│   │   └── logging_config.py
│   ├── common/                        # Shared utilities (JSON:API helpers)
│   ├── scripts/                       # Utility scripts
│   │   ├── create_superuser.py
│   │   ├── init_dev_db.py
│   │   └── api_tests/                 # Bash test scripts
│   ├── tests/                         # All tests
│   │   ├── unit/
│   │   │   ├── domain/validators/     # Validator unit tests
│   │   │   └── use_cases/             # Use case unit tests
│   │   ├── integration/
│   │   │   └── repositories/          # Repository integration tests
│   │   └── e2e/                       # End-to-end controller tests
│   └── main.py                        # Application entry point
├── alembic/                           # Database migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 👨‍💻 Development

### Running in Development Mode

The application runs with **auto-reload** enabled:

```bash
docker compose up
# Edit code → server reloads automatically
```

### Database Migrations

Migrations are versioned in `alembic/versions/` and applied by `start.sh` on
every boot (`alembic upgrade head`). Commit each new migration together with the
model change that needs it.

```bash
# Generate migration after model changes
docker exec -it web alembic revision --autogenerate -m "Add new field"

# Apply migrations
docker exec -it web alembic upgrade head

# Rollback one migration
docker exec -it web alembic downgrade -1
```

### Creating Additional Users

```bash
# Interactive mode (prompts for input)
docker exec -it web python3 src/scripts/create_superuser.py

# Non-interactive mode (with parameters)
docker exec -it web python3 src/scripts/create_superuser.py \
    --username newuser \
    --email newuser@example.com \
    --password secure123

# Create multiple users with bash script
docker exec -it web bash src/scripts/create_multiple_users.sh

# Programmatic usage (skip if exists)
docker exec -it web python3 src/scripts/create_superuser.py \
    --username developer \
    --email dev@example.com \
    --password dev123 \
    --skip-if-exists \
    --quiet
```

**Available options:**
- `--username` - Username for the superuser
- `--email` - Email address
- `--password` - Password (will be hashed)
- `--skip-if-exists` - Don't fail if user already exists (idempotent)
- `--quiet` - Suppress output messages

**Note:** The default `admin` user is automatically created every time the container starts (via `start.sh` → `init_dev_db.py`). This is idempotent and safe to run multiple times.

### Accessing Database

```bash
# PostgreSQL
docker exec -it db psql -U user -d price_monitor

# Common queries
\dt                           # List tables
SELECT * FROM users;          # View users
\q                            # Quit
```

### Logs

```bash
# API logs
docker logs -f web

# Database logs
docker logs -f db

# All services
docker compose logs -f
```

### Stopping Services

```bash
# Stop containers (keep data)
docker compose down

# Stop and remove volumes (⚠️ deletes database)
docker compose down -v
```

---

## 🔐 Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Security
SECRET_KEY=your_secret_key_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
ENVIRONMENT=development           # development | production
ENABLE_JSON_LOGS=false            # true for JSON format (production)

# Database (Docker handles this by default)
# DATABASE_URL=postgresql://user:password@localhost:5432/price_monitor
```

### Important for Production

⚠️ **Change these before deploying:**

1. Generate a strong `SECRET_KEY`:
   ```bash
   openssl rand -hex 32
   ```

2. Update default admin credentials immediately

3. Set `ENABLE_JSON_LOGS=true` for structured logging

4. Use environment-specific database credentials

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

This project uses automated tools to enforce code quality:

- **Ruff** for linting and formatting (auto-runs on commit)
- **MyPy** for static type checking
- **Pre-commit hooks** ensure code quality before commits
- Use **type hints** for function signatures
- Write **docstrings** for classes and methods
- Maintain **test coverage** above 80%

All code quality checks run automatically via pre-commit hooks. See the [Code Quality Tools](#-code-quality-tools) section for details.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- FastAPI for the amazing web framework
- SQLAlchemy for robust ORM
- Celery for distributed task processing
- The Python community for excellent libraries

---

## 📧 Contact

**Patterson** - [@pattersonrptr](https://github.com/pattersonrptr)

Project Link: [https://github.com/pattersonrptr/product_tracker_backend](https://github.com/pattersonrptr/product_tracker_backend)

---

**Made with ❤️ and ☕ in Brazil**
