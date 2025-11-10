.PHONY: help setup start stop restart logs clean test install db-dummy db-reset db-connect

help:
	@echo "RightStaff AI Backend - Available Commands:"
	@echo "  make setup       - Initial project setup"
	@echo "  make start       - Start all Docker services"
	@echo "  make stop        - Stop Docker services (keep data)"
	@echo "  make restart     - Restart Docker services"
	@echo "  make logs        - View Docker logs"
	@echo "  make clean       - Remove all data (WARNING: destructive)"
	@echo "  make install     - Install Python dependencies"
	@echo "  make test        - Run pytest suite"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-dummy    - Load 10 dummy candidates into database"
	@echo "  make db-reset    - Reset database and load all scripts"
	@echo "  make db-connect  - Connect to PostgreSQL database"

venv:
	@echo "🐍 Creating virtual environment..."
	python -m venv venv
	@echo "✅ Virtual environment created!"
	@echo "👉 Activate with: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)"

setup:
	@echo "🚀 Setting up RightStaff AI Backend..."
	@if [ ! -d "venv" ]; then \
		echo "⚠️  No virtual environment detected!"; \
		echo "👉 Run 'make venv' first, then activate it."; \
		exit 1; \
	fi
	cd docker && docker-compose up -d
	@echo "⏳ Waiting for services to be healthy..."
	sleep 10
	cd backend && pip install -r requirements.txt
	python -m spacy download en_core_web_sm
	@echo "✅ Setup complete!"

start:
	cd docker && docker-compose up -d

stop:
	cd docker && docker-compose down

restart:
	cd docker && docker-compose restart

logs:
	cd docker && docker-compose logs -f

clean:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd docker && docker-compose down -v; \
		rm -rf data/*; \
		echo "✅ All data deleted"; \
	fi

install:
	@if [ ! -d "venv" ]; then \
		echo "⚠️  Please create and activate virtual environment first"; \
		echo "   make venv"; \
		echo "   source venv/bin/activate"; \
		exit 1; \
	fi
	cd backend && pip install -r requirements.txt
	python -m spacy download en_core_web_sm

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=html

db-dummy:
	@echo "📊 Loading dummy data into database..."
	@docker exec -i rightstaff-postgres psql -U right_staff -d rightstaff < database/scripts/05_dummy_data.sql
	@echo "✅ Dummy data loaded! (10 candidates, 5 jobs, 7 applications)"

db-reset:
	@echo "⚠️  WARNING: This will reset the database with fresh data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd docker && docker-compose down -v; \
		cd docker && docker-compose up -d postgres; \
		echo "⏳ Waiting for PostgreSQL to initialize..."; \
		sleep 15; \
		echo "✅ Database reset complete with dummy data!"; \
	fi

db-connect:
	@echo "🔌 Connecting to PostgreSQL database..."
	@echo "💡 Tip: Use 'SET search_path = rightstaff, public;' once connected"
	@docker exec -it rightstaff-postgres psql -U right_staff -d rightstaff
