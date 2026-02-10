# GitHub Actions CI/CD Workflows

This directory contains the CI/CD configuration for the TG Flowers Bot project.

## Workflows

### 1. CI (`ci.yml`)
**Triggers:** Push to `main` or Pull Requests targeting `main`

**Jobs:**
- **Lint** - Runs `ruff` linter on all Python services
  - Checks for syntax errors and critical issues
  - Services: catalog-service, order-service, analytics-service, main-bot, admin-bot

- **Test** - Runs pytest test suites
  - Services with tests: catalog-service, order-service
  - Runs all unit tests with verbose output

### 2. Docker Build (`docker-build.yml`)
**Triggers:** Push to `main` or Pull Requests targeting `main`

**Jobs:**
- **Build** - Validates Docker image builds for all microservices
  - Uses Docker Buildx for efficient building
  - Enables layer caching with GitHub Actions cache
  - Services: catalog-service, order-service, analytics-service, main-bot, admin-bot

### 3. Docker Compose Validation (`docker-compose.yml`)
**Triggers:** Push to `main` or Pull Requests targeting `main`

**Jobs:**
- **Validate** - End-to-end validation of the entire stack
  - Validates docker-compose configuration
  - Builds all services
  - Starts the full stack with all dependencies (PostgreSQL, Kafka, etc.)
  - Checks service health
  - Tests API endpoints
  - Shows logs on failure

## Running Locally

### Linting
```bash
cd services/catalog-service
pip install ruff
ruff check --select=E9,F63,F7,F82 --target-version=py311 .
```

### Testing
```bash
cd services/catalog-service
pip install -r requirements.txt -r requirements-test.txt
pytest -v
```

### Docker Build
```bash
docker build -t flowers-catalog-service ./services/catalog-service
```

### Full Stack
```bash
cp .env.example .env
# Edit .env with your bot tokens
docker compose up --build
```
