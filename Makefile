##############################################################################
# Career Navigator — Developer Makefile
#
# Usage:
#   make dev           — start local dev (SQLite v1 backend + Next.js frontend)
#   make dev-v2        — start full v2 stack via Docker Compose
#   make test          — run all tests
#   make test-unit     — run unit tests only (fast, no DB/network)
#   make lint          — ruff lint + format check
#   make build         — build Docker images
#   make prod          — start production stack (v2 + Nginx)
#   make migrate       — run Alembic migrations
#   make migrate-make  — auto-generate a new migration
#   make logs          — tail Docker Compose logs
#   make down          — stop all Docker containers
#   make clean         — remove build artifacts and __pycache__
##############################################################################

.PHONY: help dev dev-v2 test test-unit test-integration lint format \
        build prod migrate migrate-make logs down clean seed \
        load-test monitor monitor-down backup terraform-plan terraform-apply

# ── Help ──────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Career Navigator — Make Commands"
	@echo "================================="
	@echo "  make dev            Start v1 SQLite backend (port 8001) + Next.js (port 3000)"
	@echo "  make dev-v2         Start full v2 Docker stack (Postgres + Redis + API + Worker)"
	@echo "  make test           Run full test suite"
	@echo "  make test-unit      Run unit tests only (fast)"
	@echo "  make lint           Lint Python with ruff"
	@echo "  make format         Auto-format Python with ruff"
	@echo "  make build          Build Docker images"
	@echo "  make prod           Start production Docker stack (with Nginx)"
	@echo "  make migrate        Apply Alembic migrations to DB"
	@echo "  make migrate-make   Auto-generate new Alembic migration (MSG= required)"
	@echo "  make logs           Tail Docker Compose logs"
	@echo "  make down           Stop all Docker containers"
	@echo "  make clean          Remove __pycache__, .pytest_cache, build artifacts"
	@echo ""

# ── Development ───────────────────────────────────────────────────────────
dev:
	@echo "[make dev] Starting v1 SQLite backend on port 8001..."
	@echo "  Backend: uvicorn src.backend.main:app --reload --port 8001"
	@echo "  Frontend: cd frontend && npm run dev"
	@echo "  Open: http://localhost:3000"
	@echo ""
	@echo "Run in separate terminals:"
	@echo "  Terminal 1: uvicorn src.backend.main:app --reload --port 8001"
	@echo "  Terminal 2: cd frontend && npm run dev"

dev-backend:
	uvicorn src.backend.main:app --reload --port 8001

dev-frontend:
	cd frontend && npm run dev

dev-v2:
	@echo "[make dev-v2] Starting full v2 Docker stack..."
	docker compose up --build

dev-v2-detached:
	docker compose up --build -d
	@echo "Services running:"
	@echo "  API:      http://localhost:8001"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Flower:   http://localhost:5555"
	@echo "  Postgres: localhost:5432"
	@echo ""
	@echo "  Logs:     make logs"
	@echo "  Stop:     make down"

# ── Testing ───────────────────────────────────────────────────────────────
test: test-unit test-integration

test-unit:
	@echo "[make test-unit] Running unit tests..."
	python -m pytest tests/unit/ -v --tb=short --no-header \
		-p no:warnings 2>&1 | head -100

test-integration:
	@echo "[make test-integration] Running integration tests..."
	python -m pytest tests/integration/ -v --tb=short --no-header 2>&1 | head -100

test-coverage:
	python -m pytest tests/ --cov=src/backend --cov=backend/app \
		--cov-report=term-missing --cov-report=html -q

test-watch:
	@echo "[make test-watch] Watching for changes..."
	python -m pytest tests/unit/ -v -f --tb=short

# ── Lint / Format ─────────────────────────────────────────────────────────
lint:
	@echo "[make lint] Running ruff..."
	ruff check src/backend/ backend/app/ tests/ --select E,W,F,I --ignore E501

format:
	@echo "[make format] Auto-formatting with ruff..."
	ruff format src/backend/ backend/app/ tests/

lint-fix:
	ruff check src/backend/ backend/app/ tests/ --fix --select E,W,F,I --ignore E501

# ── Docker ────────────────────────────────────────────────────────────────
build:
	@echo "[make build] Building Docker images..."
	docker compose build

build-no-cache:
	docker compose build --no-cache

prod:
	@echo "[make prod] Starting PRODUCTION stack (Nginx + resource limits)..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

logs:
	docker compose logs -f --tail=100

logs-api:
	docker compose logs -f api --tail=100

logs-worker:
	docker compose logs -f worker --tail=100

down:
	docker compose down

down-volumes:
	@echo "[WARNING] This will delete all PostgreSQL and Redis data!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v

# ── Database ──────────────────────────────────────────────────────────────
migrate:
	@echo "[make migrate] Applying Alembic migrations..."
	alembic upgrade head

migrate-make:
	@[ -n "$(MSG)" ] || (echo "Usage: make migrate-make MSG='describe change'" && exit 1)
	alembic revision --autogenerate -m "$(MSG)"

migrate-history:
	alembic history --verbose

migrate-current:
	alembic current

migrate-down:
	@echo "[make migrate-down] Rolling back one migration..."
	alembic downgrade -1

# ── Seed / Demo data ──────────────────────────────────────────────────────
seed:
	@echo "[make seed] Creating demo user dj@careernavigator.ai / Demo1234..."
	python -c "
import sys; sys.path.insert(0, '.')
from src.backend.user_management import SessionLocal, UserModel
import bcrypt, json
db = SessionLocal()
existing = db.query(UserModel).filter_by(email='dj@careernavigator.ai').first()
if existing:
    print('Demo user already exists.')
else:
    pw = bcrypt.hashpw(b'Demo1234', bcrypt.gensalt()).decode()
    user = UserModel(email='dj@careernavigator.ai', hashed_password=pw, full_name='DJ Jha')
    db.add(user); db.commit()
    print('Demo user created: dj@careernavigator.ai / Demo1234')
db.close()
"

# ── Cleanup ───────────────────────────────────────────────────────────────
clean:
	find . -type d -name '__pycache__' -not -path './career_env/*' | xargs rm -rf
	find . -type f -name '*.pyc' -not -path './career_env/*' | xargs rm -f
	find . -type d -name '.pytest_cache' | xargs rm -rf
	find . -type d -name '.ruff_cache' | xargs rm -rf
	find . -type d -name 'htmlcov' | xargs rm -rf
	find . -name '.coverage' -delete
	@echo "Clean complete."

clean-frontend:
	rm -rf frontend/.next frontend/out

# ── Security ──────────────────────────────────────────────────────────────
secret:
	@python -c "import secrets; print(secrets.token_hex(32))"
	@echo "(copy this to SECRET_KEY in .env)"

check-secrets:
	@echo "[make check-secrets] Checking for exposed secrets in codebase..."
	@grep -rn "change-me\|your-api-key\|password123\|PLACEHOLDER" \
		--include="*.py" --include="*.js" --include="*.ts" \
		--exclude-dir=career_env --exclude-dir=node_modules \
		. || echo "No obvious placeholder secrets found."

# ── Load Testing (Phase 7) ────────────────────────────────────────────────
load-test:
	@echo "[make load-test] Running Locust load test (50 users × 5 min)..."
	@echo "  Install: pip install locust"
	@echo "  Ensure backend is running: make dev-backend"
	locust -f tests/load/locustfile.py \
		--host=http://localhost:8001 \
		--users=50 --spawn-rate=5 --run-time=5m \
		--headless \
		--html=tests/load/report.html \
		--csv=tests/load/results

load-test-smoke:
	@echo "[make load-test-smoke] Quick smoke test (5 users × 60s)..."
	locust -f tests/load/locustfile.py \
		--host=http://localhost:8001 \
		--users=5 --spawn-rate=1 --run-time=60s \
		--headless

load-test-ui:
	@echo "[make load-test-ui] Starting Locust web UI at http://localhost:8089 ..."
	locust -f tests/load/locustfile.py --host=http://localhost:8001

# ── Monitoring (Phase 7) ──────────────────────────────────────────────────
monitor:
	@echo "[make monitor] Starting Prometheus + Grafana monitoring stack..."
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
	@echo ""
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001  (admin/admin)"
	@echo ""
	@echo "  Tail logs:  docker compose -f docker-compose.monitoring.yml logs -f"

monitor-down:
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml down

# ── Database Backup (Phase 7) ─────────────────────────────────────────────
backup:
	@echo "[make backup] Creating database backup..."
	bash scripts/db_backup_restore.sh backup

backup-list:
	bash scripts/db_backup_restore.sh list

# ── Terraform (Phase 7 — AWS deployment) ──────────────────────────────────
terraform-init:
	cd terraform && terraform init

terraform-plan:
	@[ -f terraform/prod.tfvars ] || (echo "Edit terraform/prod.tfvars first" && exit 1)
	cd terraform && terraform plan -var-file=prod.tfvars

terraform-apply:
	@echo "[WARNING] This will modify AWS infrastructure."
	@read -p "Type 'yes' to continue: " c && [ "$$c" = "yes" ] || exit 1
	cd terraform && terraform apply -var-file=prod.tfvars
