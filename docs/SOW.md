# GameBargain プロジェクト SOW（Statement of Work）

## 1. プロジェクト概要

### 1.1 プロジェクト名
GameBargain - ゲーム価格比較サービス

### 1.2 プロジェクト目的
複数のゲームストア（Steam、Epic Games Store等）の価格情報をリアルタイムで比較し、ユーザーが最安値でゲームを購入できるよう支援するWebサービスの開発

### 1.3 プロジェクト期間
- 開発期間: 2024年1月〜2024年6月（6ヶ月）
- フェーズ1（MVP）: 2024年1月〜2024年3月（3ヶ月）
- フェーズ2（機能拡張）: 2024年4月〜2024年6月（3ヶ月）

## 2. 技術仕様

### 2.1 技術スタック

#### バックエンド
- **Framework**: Flask 3.0+
- **Database ORM**: SQLAlchemy 2.0+
- **Database**: SQLite（開発）/ PostgreSQL（本番）
- **Authentication**: Flask-Login + Discord OAuth2
- **Migration**: Flask-Migrate
- **Testing**: pytest + pytest-flask

#### フロントエンド
- **Template Engine**: Jinja2
- **CSS Framework**: Bootstrap 5.3.2
- **JavaScript**: Vanilla JS（モジュール構成）
- **Icons**: Bootstrap Icons

#### 外部API連携
- **Discord Bot**: discord.py 2.3+
- **Steam API**: Steam Web API
- **Epic Games**: Epic Games Store API（調査中）

#### インフラ
- **Container**: Docker + Docker Compose
- **Web Server**: Gunicorn
- **Reverse Proxy**: Nginx（本番）
- **Deployment**: Cloud Platform（AWS/GCP）

### 2.2 アーキテクチャ

#### システム構成
```
[Users] -> [Nginx] -> [Flask App] -> [Database]
                  -> [Discord Bot] -> [Discord API]
                  -> [Price Crawler] -> [Store APIs]
```

#### アプリケーション構成
```
GameBargain/
├── app.py                 # アプリケーションファクトリ
├── config.py             # 設定管理
├── models/               # データモデル（Factory Pattern）
├── web/                  # Webルーティング（Blueprint）
├── services/             # ビジネスロジック
├── discord_bot/          # Discord Bot機能
├── templates/            # HTMLテンプレート
├── static/               # 静的ファイル
└── tests/               # テストコード
```

## 3. 機能仕様

### 3.1 Phase 1 - MVP機能

#### 3.1.1 ユーザー管理機能
- **認証方式**: Discord OAuth2認証
- **ユーザープロフィール**: Discord情報に基づく基本プロフィール
- **権限管理**: 一般ユーザーのみ（管理者機能は後フェーズ）

#### 3.1.2 ゲーム検索機能
- **全文検索**: タイトル、開発者、パブリッシャーでの検索
- **フィルタリング**: ジャンル、プラットフォーム、価格帯
- **ソート機能**: 価格順、タイトル順、リリース日順、関連度順
- **ページネーション**: 20件/ページ、無限スクロール対応

#### 3.1.3 価格比較機能
- **対応ストア**: Steam（必須）、Epic Games Store（調査中）
- **価格表示**: 現在価格、元価格、割引率、更新日時
- **最安値表示**: ストア横断での最安値ハイライト
- **価格履歴**: 過去30日間の価格推移グラフ

#### 3.1.4 お気に入り機能
- **追加/削除**: ワンクリックでお気に入り管理
- **一覧表示**: ユーザーのお気に入りゲーム一覧
- **価格変動通知**: お気に入りゲームの価格変動表示

#### 3.1.5 価格アラート機能
- **アラート設定**: 目標価格の設定
- **通知方法**: Discord DM、メール通知（設定可能）
- **アラート管理**: アクティブ/非アクティブ切り替え

#### 3.1.6 Discord Bot機能
- **ゲーム検索**: `/search [ゲーム名]` コマンド
- **価格確認**: `/price [ゲーム名]` コマンド
- **アラート通知**: 価格下落時の自動DM送信

### 3.2 Phase 2 - 拡張機能

#### 3.2.1 高度な検索機能
- **検索候補**: リアルタイム検索候補表示
- **詳細フィルター**: リリース年、ユーザースコア、言語対応
- **保存済み検索**: 検索条件の保存と再実行

#### 3.2.2 レコメンデーション機能
- **関連ゲーム**: 同ジャンル、同開発者のゲーム推薦
- **セール情報**: 期間限定セールの自動発見と通知
- **価格予測**: 機械学習による価格動向予測

#### 3.2.3 ソーシャル機能
- **ウィッシュリスト共有**: お気に入りリストの公開/共有
- **レビュー機能**: ユーザーレビューと評価
- **フォロー機能**: 他ユーザーのお気に入りをフォロー

#### 3.2.4 管理機能
- **管理者ダッシュボード**: システム統計、ユーザー管理
- **ゲーム管理**: ゲーム情報の手動追加/編集
- **価格データ管理**: 価格データの正規化と検証

## 4. データベース設計

### 4.1 主要テーブル

#### Users テーブル
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id VARCHAR(20) UNIQUE NOT NULL,
    discord_username VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(255),
    email_notifications BOOLEAN DEFAULT true,
    discord_notifications BOOLEAN DEFAULT true,
    weekly_digest BOOLEAN DEFAULT false,
    deal_alerts BOOLEAN DEFAULT true,
    profile_public BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Games テーブル
```sql
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    developer VARCHAR(100),
    publisher VARCHAR(100),
    release_date DATE,
    genres VARCHAR(200),
    platforms VARCHAR(200),
    steam_app_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Prices テーブル
```sql
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    store VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    discount_percent DECIMAL(5,2),
    store_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games (id)
);
```

#### Favorites テーブル
```sql
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, game_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (game_id) REFERENCES games (id)
);
```

#### Notifications テーブル
```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id INTEGER,
    notification_type VARCHAR(50) NOT NULL,
    threshold_price DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    last_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (game_id) REFERENCES games (id)
);
```

## 5. API仕様

### 5.1 認証API

#### Discord OAuth2 認証
```
GET  /auth/discord          # Discord認証開始
GET  /auth/discord/callback # Discord認証コールバック
POST /auth/logout           # ログアウト
```

### 5.2 ゲームAPI

#### ゲーム検索・取得
```
GET  /api/games                    # ゲーム検索
GET  /api/games/{id}               # ゲーム詳細取得
GET  /api/games/{id}/prices        # ゲーム価格一覧
GET  /api/games/{id}/price-history # 価格履歴取得
GET  /api/search/suggestions       # 検索候補取得
```

### 5.3 ユーザーAPI

#### お気に入り管理
```
GET    /api/favorites              # お気に入り一覧
POST   /api/favorites              # お気に入り追加
DELETE /api/favorites              # お気に入り削除
```

#### 価格アラート管理
```
GET    /api/price-alerts           # アラート一覧
POST   /api/price-alerts           # アラート作成
PUT    /api/price-alerts/{id}      # アラート更新
DELETE /api/price-alerts/{id}      # アラート削除
```

#### ユーザー設定
```
GET  /api/user/profile             # プロフィール取得
PUT  /api/user/profile             # プロフィール更新
PUT  /api/user/notifications       # 通知設定更新
```

### 5.4 Discord Bot API

#### Discord コマンド
```
/search [game_name]                # ゲーム検索
/price [game_name]                 # 価格確認
/favorite add [game_name]          # お気に入り追加
/favorite list                     # お気に入り一覧
/alert set [game_name] [price]     # 価格アラート設定
```

## 6. セキュリティ要件

### 6.1 認証・認可
- **Discord OAuth2**: 公式Discord認証による安全な認証
- **Session管理**: Flask-Sessionによるセッション管理
- **CSRF保護**: Flask-WTFによるCSRF攻撃対策

### 6.2 データ保護
- **個人情報**: 最小限の個人情報のみ保存（Discord ID、ユーザー名）
- **データ暗号化**: 本番環境でのデータベース暗号化
- **アクセスログ**: API アクセスログの記録と監視

### 6.3 API セキュリティ
- **Rate Limiting**: API呼び出し頻度制限
- **Input Validation**: 全入力データの検証とサニタイズ
- **SQL Injection対策**: SQLAlchemy ORMによる対策

## 7. パフォーマンス要件

### 7.1 レスポンス時間
- **ページ読み込み**: 2秒以内
- **API レスポンス**: 500ms以内
- **検索結果**: 1秒以内

### 7.2 同時接続数
- **Phase 1**: 100同時接続対応
- **Phase 2**: 1,000同時接続対応

### 7.3 データ更新頻度
- **価格情報**: 1時間に1回更新
- **ゲーム情報**: 1日に1回更新
- **セール情報**: 30分に1回更新

## 8. 運用・保守

### 8.1 監視項目
- **サーバー稼働率**: 99.5%以上
- **API エラー率**: 1%未満
- **データベース応答時間**: 100ms以内

### 8.2 バックアップ
- **データベース**: 日次フルバックアップ
- **ログファイル**: 週次アーカイブ
- **設定ファイル**: Git管理による版数管理

### 8.3 更新手順
- **アプリケーション**: Blue-Green デプロイメント
- **データベース**: マイグレーション スクリプト
- **設定変更**: 環境変数による動的設定

## 9. テスト戦略

### 9.1 テスト種別
- **単体テスト**: pytest による関数・クラス単位テスト
- **統合テスト**: API エンドポイント統合テスト
- **E2Eテスト**: ブラウザ自動化による画面テスト

### 9.2 テスト範囲
- **コードカバレッジ**: 80%以上
- **API テスト**: 全エンドポイント
- **ブラウザテスト**: Chrome、Firefox、Safari

### 9.3 テスト自動化
- **CI/CD**: GitHub Actions による自動テスト実行
- **品質ゲート**: テスト失敗時のデプロイ阻止
- **パフォーマンステスト**: 負荷テストの自動実行

## 10. 成果物

### 10.1 開発成果物
- **ソースコード**: GitHub リポジトリ
- **ドキュメント**: README、API仕様書、運用手順書
- **テストコード**: 単体テスト、統合テスト一式

### 10.2 設計書類
- **要件定義書**: 機能要件、非機能要件
- **基本設計書**: システム構成、画面設計
- **詳細設計書**: データベース設計、API設計

### 10.3 運用資料
- **デプロイ手順書**: 本番環境構築手順
- **運用監視手順書**: 監視項目、アラート設定
- **障害対応手順書**: 障害分析、復旧手順

## 11. プロジェクト体制

### 11.1 開発チーム
- **プロジェクトマネージャー**: 1名
- **バックエンドエンジニア**: 1名
- **フロントエンドエンジニア**: 1名
- **インフラエンジニア**: 1名（兼任）

### 11.2 品質管理
- **コードレビュー**: Pull Request による相互レビュー
- **設計レビュー**: 週次設計レビュー会議
- **テストレビュー**: テストケース妥当性確認

## 12. リスク管理

### 12.1 技術リスク
- **外部API制限**: Steam API利用制限への対応策
- **スケーラビリティ**: 急激なユーザー増加への対応
- **データ品質**: 価格データの正確性確保

### 12.2 運用リスク
- **サーバー障害**: 冗長化による可用性確保
- **セキュリティ**: 定期的な脆弱性診断
- **法的リスク**: 各ストアの利用規約遵守

### 12.3 対応策
- **監視体制**: 24時間監視システム
- **エスカレーション**: 障害レベル別対応フロー
- **事業継続**: 災害復旧計画（DRP）

## 13. 成功指標（KPI）

### 13.1 Phase 1 目標
- **ユーザー登録数**: 500名
- **月間アクティブユーザー**: 200名
- **お気に入り登録**: 1,000件
- **価格アラート設定**: 500件

### 13.2 Phase 2 目標
- **ユーザー登録数**: 2,000名
- **月間アクティブユーザー**: 1,000名
- **検索実行数**: 5,000回/月
- **Discord Bot利用**: 1,000回/月

### 13.3 品質指標
- **システム稼働率**: 99.5%以上
- **平均レスポンス時間**: 1秒以内
- **ユーザー満足度**: 4.0/5.0以上

---

**文書管理情報**
- 作成日: 2024年1月15日
- 最終更新: 2024年1月15日
- 版数: 1.0
- 作成者: GameBargain開発チーム
- 承認者: プロジェクトマネージャー
