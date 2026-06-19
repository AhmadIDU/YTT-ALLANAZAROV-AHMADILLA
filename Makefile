# ============================================================
# PossKassa — Make buyruqlari
# ============================================================

.PHONY: help dev build migrate seed test lint k8s-deploy clean

help: ## Barcha buyruqlarni ko'rsatish
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Ishlab chiqish ─────────────────────────────────────
dev: ## Barcha xizmatlarni ishlab chiqish rejimida ishga tushirish
	docker compose up -d postgres redis rabbitmq minio keycloak
	@echo "⏳ Infratuzilma tayyor bo'lishi kutilmoqda..."
	sleep 10
	$(MAKE) migrate
	docker compose up -d

dev-infra: ## Faqat infratuzilmani ishga tushirish
	docker compose up -d postgres redis rabbitmq minio keycloak clickhouse

dev-services: ## Faqat backend xizmatlarni ishga tushirish
	docker compose up -d gateway sales-service inventory-service compliance-service intake-service analytics-service notifications-service

# ─── Ma'lumotlar bazasi ─────────────────────────────────
migrate: ## DB migratsiyalarini ishga tushirish
	docker compose exec postgres psql -U posskassa -d posskassa -f /docker-entrypoint-initdb.d/01-init.sql
	@echo "✅ Migratsiya bajarildi"

seed: ## Demo ma'lumotlarni yuklash
	docker compose exec postgres psql -U posskassa -d posskassa -f /scripts/seed.sql
	@echo "✅ Demo ma'lumotlar yuklandi"

# ─── Build ──────────────────────────────────────────────
build: ## Barcha Docker imaglarini build qilish
	docker compose build

build-push: ## Build qilib Docker registrga yuborish
	docker compose build
	docker compose push

# ─── Test ───────────────────────────────────────────────
test: ## Barcha testlarni ishga tushirish
	cd apps/pos-terminal && npm run test -- --run
	cd apps/backoffice   && npm run test -- --run
	docker compose exec sales-service pytest services/sales/tests/ -v
	docker compose exec inventory-service pytest services/inventory/tests/ -v

# ─── Lint ───────────────────────────────────────────────
lint: ## Kod sifatini tekshirish
	cd apps/pos-terminal && npm run lint
	cd apps/backoffice   && npm run lint
	docker compose exec sales-service ruff check services/sales/
	docker compose exec inventory-service ruff check services/inventory/

# ─── Kubernetes ─────────────────────────────────────────
k8s-deploy: ## Kubernetes ga deploy qilish
	kubectl apply -f infra/k8s/base/namespace.yaml
	kubectl apply -f infra/k8s/base/configmap.yaml
	kubectl apply -f infra/k8s/base/secrets.yaml
	kubectl apply -f infra/k8s/base/services.yaml
	kubectl apply -f infra/k8s/base/deployments.yaml
	kubectl apply -f infra/k8s/base/ingress.yaml
	kubectl apply -f infra/k8s/base/hpa.yaml
	@echo "✅ Kubernetes deployments amalga oshirildi"

k8s-status: ## Kubernetes pod holati
	kubectl get pods -n posskassa
	kubectl get services -n posskassa

k8s-logs: ## Gateway loglarini ko'rish
	kubectl logs -n posskassa -l app=gateway -f --tail=100

# ─── Tozalash ───────────────────────────────────────────
clean: ## Barcha konteyner va hajmlarni to'xtatish va o'chirish
	docker compose down -v --remove-orphans
	@echo "✅ Hamma narsa tozalandi"

stop: ## Xizmatlarni to'xtatish (hajmlarni saqlab)
	docker compose down

# ─── S3 bucket yaratish ─────────────────────────────────
minio-init: ## MinIO da posskassa bucket yaratish
	docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
	docker compose exec minio mc mb local/posskassa --ignore-existing
	@echo "✅ MinIO bucket yaratildi"

# ─── Holat tekshiruvi ────────────────────────────────────
health: ## Barcha xizmatlar sog'ligini tekshirish
	@for port in 8000 8001 8002 8003 8004 8005 8006; do \
		status=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$$port/health); \
		if [ "$$status" = "200" ]; then \
			echo "✅ :$$port — OK"; \
		else \
			echo "❌ :$$port — XATO ($$status)"; \
		fi; \
	done
