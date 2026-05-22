.PHONY: up down logs build rebuild backend frontend test fmt

up:           ## Start the full stack
	docker compose up -d --build

down:         ## Stop the full stack
	docker compose down

logs:         ## Tail backend logs
	docker compose logs -f backend

rebuild:      ## Force rebuild
	docker compose build --no-cache

backend:      ## Run backend locally (requires Postgres already up)
	cd backend && uvicorn app.main:app --reload

frontend:     ## Run frontend dev server
	cd frontend && npm install && npm run dev

test:         ## Run backend tests
	cd backend && pytest -q

fmt:          ## Format Python with ruff
	cd backend && ruff check --fix . && ruff format .
