# GameBargain Makefile
# 開発・デプロイ作業を簡略化するためのMakefile

.PHONY: help install dev test clean docker-build docker-up docker-down lint format

# デフォルトターゲット
help:
	@echo "GameBargain - ゲーム価格比較サービス"
	@echo "使用可能なコマンド:"
	@echo "  make install     - 依存関係をインストール"
	@echo "  make dev        - 開発サーバーを起動"
	@echo "  make test       - テストを実行"
	@echo "  make lint       - コード品質チェック"
	@echo "  make format     - コード整形"
	@echo "  make docker-build - Dockerイメージをビルド"
	@echo "  make docker-up   - Docker環境を起動"
	@echo "  make docker-down - Docker環境を停止"
	@echo "  make clean      - 一時ファイルを削除"

# 依存関係のインストール
install:
	@echo "依存関係をインストール中..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	@echo "インストール完了!"

# 開発環境のセットアップ
setup-dev: install
	@echo "開発環境をセットアップ中..."
	cp -n .env.example .env || true
	@echo "開発環境セットアップ完了!"
	@echo ".envファイルを編集して必要な設定値を入力してください"

# データベースの初期化
init-db:
	@echo "データベースを初期化中..."
	flask db init || true
	flask db migrate -m "Initial migration" || true
	flask db upgrade
	@echo "データベース初期化完了!"

# 開発サーバーの起動
dev:
	@echo "開発サーバーを起動中..."
	FLASK_ENV=development FLASK_APP=app.py flask run --host=0.0.0.0 --port=5000

# テストの実行
test:
	@echo "テストを実行中..."
	python -m pytest tests/ -v --cov=./ --cov-report=term-missing

# テスト（カバレッジレポート付き）
test-cov:
	@echo "カバレッジレポート付きでテストを実行中..."
	python -m pytest tests/ -v --cov=./ --cov-report=html --cov-report=term-missing
	@echo "HTMLレポートは htmlcov/index.html で確認できます"

# コード品質チェック
lint:
	@echo "コード品質をチェック中..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# コード整形
format:
	@echo "コードを整形中..."
	black . --line-length=100
	@echo "コード整形完了!"

# Dockerイメージのビルド
docker-build:
	@echo "Dockerイメージをビルド中..."
	docker build -t gamebargain:latest .
	@echo "Dockerイメージビルド完了!"

# Docker環境の起動
docker-up:
	@echo "Docker環境を起動中..."
	docker-compose up -d
	@echo "Docker環境起動完了!"
	@echo "アプリケーションは http://localhost:5000 で利用できます"

# Docker環境の停止
docker-down:
	@echo "Docker環境を停止中..."
	docker-compose down
	@echo "Docker環境停止完了!"

# ログの確認
docker-logs:
	@echo "Dockerコンテナのログを表示中..."
	docker-compose logs -f

# 一時ファイルの削除
clean:
	@echo "一時ファイルを削除中..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	@echo "一時ファイル削除完了!"

# 本番デプロイ（環境に応じて設定）
deploy:
	@echo "本番環境にデプロイ中..."
	# デプロイコマンドをここに追加
	@echo "デプロイ完了!"

# データベースマイグレーション
migrate:
	@echo "データベースマイグレーションを実行中..."
	flask db migrate
	flask db upgrade
	@echo "マイグレーション完了!"

# 開発用データの投入
seed:
	@echo "開発用データを投入中..."
	python scripts/seed_data.py
	@echo "データ投入完了!"
