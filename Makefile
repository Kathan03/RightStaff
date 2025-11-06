.PHONY: help setup start stop restart logs clean test install

help:
	@echo "RightStaff AI Backend - Available Commands:"
	@echo "  make setup     - Initial project setup"
	@echo "  make start     - Start all Docker services"
	@echo "  make stop      - Stop Docker services (keep data)"
	@echo "  make restart   - Restart Docker services"
	@echo "  make logs      - View Docker logs"
	@echo "  make clean     - Remove all data (WARNING: destructive)"
	@echo "  make install   - Install Python dependencies"
	@echo "  make test      - Run pytest suite"

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
