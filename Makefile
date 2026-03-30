SHELL := /bin/bash

.PHONY: help venv install test lint fmt serve docker-build docker-up docker-down docker-test

help:
	@echo "Targets:"
	@echo "  venv         - create local venv"
	@echo "  install      - editable install agent+collector"
	@echo "  test         - run pytest"
	@echo "  lint         - run ruff"
	@echo "  fmt          - format code with ruff"
	@echo "  serve        - run collector on 127.0.0.1:8080"
	@echo "  docker-build - build Docker images (collector + UI)"
	@echo "  docker-up    - start Docker services (collector + UI)"
	@echo "  docker-down  - stop Docker services (docker-compose down)"
	@echo "  docker-test  - test Docker setup (build + run + health check)"

venv:
	python -m venv .venv

install:
	. .venv/bin/activate && pip install -U pip && \
	pip install -e packages/qobserva_agent -e packages/qobserva_collector && \
	pip install pytest httpx ruff

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && ruff check packages tests

fmt:
	. .venv/bin/activate && ruff format packages tests

serve:
	. .venv/bin/activate && qobserva-collector serve --host 127.0.0.1 --port 8080

docker-build:
	cd docker && docker-compose build

docker-up:
	cd docker && docker-compose up -d

docker-down:
	cd docker && docker-compose down

docker-test: docker-build
	@echo "Testing Docker setup..."
	cd docker && docker-compose up -d
	@echo "Waiting for containers to start..."
	@sleep 10
	@echo "Checking container status..."
	@cd docker && docker-compose ps
	@echo "Waiting for services to be ready..."
	@for i in 1 2 3 4 5 6 7 8; do \
		echo "Attempt $$i/8: Testing collector health endpoint..."; \
		response=$$(curl -s -w "\n%{http_code}" http://localhost:8080/v1/health 2>&1); \
		http_code=$$(echo "$$response" | tail -n1); \
		body=$$(echo "$$response" | head -n-1); \
		if [ "$$http_code" = "200" ]; then \
			echo "Collector health check passed! Response: $$body"; \
			echo "Testing UI endpoint..."; \
			ui_response=$$(curl -s -w "\n%{http_code}" http://localhost:3000 2>&1); \
			ui_code=$$(echo "$$ui_response" | tail -n1); \
			if [ "$$ui_code" = "200" ] || [ "$$ui_code" = "000" ]; then \
				echo "UI is accessible (HTTP $$ui_code)"; \
				echo "Docker test passed!"; \
				echo "Collector: http://localhost:8080"; \
				echo "UI: http://localhost:3000"; \
				cd docker && docker-compose down; \
				exit 0; \
			fi; \
		fi; \
		echo "  HTTP $$http_code - Waiting..."; \
		sleep 3; \
		if [ $$i -eq 8 ]; then \
			echo "Health check failed after 8 attempts!"; \
			echo "Last response: $$response"; \
			echo "Container logs:"; \
			cd docker && docker-compose logs; \
			cd docker && docker-compose down; \
			exit 1; \
		fi; \
	done
