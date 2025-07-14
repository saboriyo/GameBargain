# GameBargain

**ゲーム価格比較・監視サービス**

![GameBargain](docs/ワイヤーフレーム.drawio.png)

## 📋 概要

GameBargainは、Steam、Epic Games Store、Origin、Ubisoft Connectなど複数のゲームプラットフォームの価格を比較し、ユーザーが最安値でゲームを購入できるよう支援するWebアプリケーションです。Discord Botと連携した価格通知機能も提供します。

### 🎯 主な機能

- **🔍 ゲーム検索・価格比較**: 複数プラットフォームの価格を一括比較
- **📈 価格履歴・トレンド表示**: 価格推移をグラフで視覚化
- **🤖 Discord Bot連携**: リアルタイム価格通知とBot検索
- **⭐ お気に入り管理**: 気になるゲームを保存・管理
- **🔔 価格監視・通知**: 希望価格到達時の自動通知
- **🏪 ストアリンク**: 各プラットフォームへの直接リンク

## 🚀 開発背景

多くのゲーマーは複数のプラットフォームでゲームの価格を比較する必要がありますが、手動での価格調査は時間がかかります。特に学生などの予算が限られたユーザーにとって、最安値での購入は重要です。GameBargainは、この問題を解決し、ユーザーが効率的に最安値を見つけられるようサポートします。

## 🏗️ プロジェクト構成

```
GameBargain/
├── README.md                 # プロジェクト概要
├── docs/                     # 設計書・図表
│   ├── 要件定義.md
│   ├── 基本設計書.md
│   ├── 詳細設計書.md
│   ├── ER図.drawio.png
│   ├── クラス図.drawio.png
│   ├── システム構成図.drawio.png
│   ├── ワイヤーフレーム.drawio.png
│   └── [シーケンス図など]
├── discord_bot/              # Discord Bot関連
├── web/                      # Webアプリケーション
├── services/                 # ビジネスロジック
├── models/                   # データモデル
├── templates/                # HTMLテンプレート
├── static/                   # CSS/JavaScript/画像
└── data/                     # データファイル
```

## 🛠️ 技術スタック

### Backend
- **Python 3.11+**
- **Flask**: Webフレームワーク
- **SQLAlchemy**: ORM
- **Celery**: 非同期タスク処理
- **Redis**: キャッシュ・メッセージブローカー

### Frontend
- **HTML5/CSS3/JavaScript**
- **Bootstrap 5**: UIフレームワーク
- **Chart.js**: グラフ表示

### Database
- **PostgreSQL**: メインデータベース

### External APIs
- **Steam Web API**: Steam価格データ
- **Epic Games Store API**: Epic価格データ
- **Discord API**: Bot機能

### Infrastructure
- **Docker**: コンテナ化
- **GitHub Actions**: CI/CD

## 📖 ドキュメント

### 設計書
- [要件定義書](docs/要件定義.md)
- [基本設計書](docs/基本設計書.md)
- [詳細設計書](docs/詳細設計書.md)

### 図表
- [システム構成図](docs/システム構成図.drawio.png)
- [ER図](docs/ER図.drawio.png)
- [クラス図](docs/クラス図.drawio.png)
- [ワイヤーフレーム](docs/ワイヤーフレーム.drawio.png)

## 🔧 セットアップ

### 前提条件
- Python 3.11以上
- PostgreSQL 14以上
- Redis 6以上
- Node.js 18以上（フロントエンド開発用）

### 環境構築

1. **リポジトリのクローン**
```bash
git clone https://github.com/saboriyo/GameBargain.git
cd GameBargain
```

2. **仮想環境の作成・有効化**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **依存関係のインストール**
```bash
pip install -r requirements.txt
```

4. **環境変数の設定**
```bash
cp .env.example .env
# .envファイルを編集して必要な設定値を入力
```

5. **データベースの初期化**
```bash
flask db upgrade
flask db-seed  # 初期データの投入
```

6. **Redis・Celeryの起動**
```bash
# ターミナル1: Redis
redis-server

# ターミナル2: Celery Worker
celery -A app.celery worker --loglevel=info

# ターミナル3: Celery Beat（スケジューラー）
celery -A app.celery beat --loglevel=info
```

7. **アプリケーションの起動**
```bash
flask run
```

### Docker利用の場合

```bash
docker-compose up -d
```

## 🎮 使用方法

### Webアプリケーション
1. ブラウザで `http://localhost:5000` にアクセス
2. ゲーム名を検索して価格比較
3. お気に入り登録・価格監視設定
4. Discord連携でリアルタイム通知

### Discord Bot
1. BotをDiscordサーバーに招待
2. `/search [ゲーム名]` でゲーム検索
3. `/favorite` でお気に入り管理
4. `/notify` で価格通知設定

## 🧪 テスト

```bash
# 単体テスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# 全テスト
pytest
```

## 📈 監視・メトリクス

### ダッシュボード
- アプリケーションメトリクス: `/metrics`
- ヘルスチェック: `/health`
- API使用状況: `/api/stats`

### ログ
- アプリケーションログ: `logs/app.log`
- エラーログ: `logs/error.log`
- API呼び出しログ: `logs/api.log`

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 👥 開発チーム

- [@saboriyo](https://github.com/saboriyo) - メイン開発者

## 📞 サポート

- Issues: [GitHub Issues](https://github.com/saboriyo/GameBargain/issues)
- Discord: GameBargain公式サーバー
- Email: support@gamebargain.dev

---

**GameBargain** - あなたのゲーム購入をもっとお得に 🎮💰
