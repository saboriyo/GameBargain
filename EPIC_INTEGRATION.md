# 🎮 Epic Games Store API 統合

## 📋 概要

GameBargainにEpic Games Store APIを統合し、SteamとEpic Games Storeの両方からゲーム情報と価格を取得できるようになりました。

## 🆕 新機能

### Epic Games Store API サービス
- **`services/epic_service.py`**: Epic Games Store APIとの通信を担当
- GraphQLエンドポイントを使用した効率的なデータ取得
- 日本語対応（ロケール: ja, 国: JP）
- 価格情報の自動更新機能

### 主要機能

#### 1. ゲーム検索
```python
from services.epic_service import EpicGamesStoreAPI

epic_service = EpicGamesStoreAPI()
results = epic_service.search_games("cyberpunk", limit=10)
```

#### 2. 価格取得
```python
price_data = epic_service.get_game_price("epic_namespace")
# 戻り値: {
#   'price': 1500.0,
#   'original_price': 3000.0,
#   'discount_percent': 50,
#   'currency': 'JPY',
#   'is_on_sale': True
# }
```

#### 3. 最近のゲーム取得
```python
recent_games = epic_service.get_recent_games(limit=20)
```

#### 4. 無料ゲーム取得
```python
free_games = epic_service.get_free_games()
```

## 🏗️ アーキテクチャ変更

### データベースモデル更新
- **`models/game.py`**: Epic Games Store用フィールド追加
  - `epic_namespace`: Epic Games Storeのnamespace
  - `epic_url`: Epic Games Store商品ページURL

### リポジトリ層更新
- **`repositories/game_repository.py`**: Epic Games Storeデータ保存機能追加
- **`repositories/price_repository.py`**: Epic Games Store価格取得機能追加

### サービス層更新
- **`services/game_search_service.py`**: Epic Games Store検索統合
- マルチプラットフォーム検索対応

## 🔧 技術仕様

### API エンドポイント
- **GraphQL**: `https://graphql.epicgames.com/graphql`
- **無料ゲーム**: `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions`
- **カタログ**: `https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/epic/items`

### データ形式
```python
{
    'epic_namespace': 'epic_namespace',
    'title': 'ゲームタイトル',
    'description': 'ゲーム説明',
    'developer': '開発者名',
    'publisher': 'パブリッシャー名',
    'image_url': '画像URL',
    'epic_url': 'Epic Games Store URL',
    'price_info': {
        'is_free': False,
        'current_price': 1500.0,
        'original_price': 3000.0,
        'discount_percent': 50,
        'formatted_price': '¥1,500',
        'is_on_sale': True
    },
    'tags': ['アクション', 'RPG']
}
```

## 🚀 使用方法

### 1. 基本的な使用
```python
from services.epic_service import EpicGamesStoreAPI

# サービス初期化
epic_service = EpicGamesStoreAPI()

# ゲーム検索
games = epic_service.search_games("cyberpunk")

# 価格取得
price = epic_service.get_game_price("epic_namespace")
```

### 2. ゲーム検索サービスでの使用
```python
from services.game_search_service import GameSearchService

# 自動的にSteamとEpic Games Storeの両方から検索
search_service = GameSearchService()
results = search_service.search_games("cyberpunk")
```

### 3. 価格リポジトリでの使用
```python
from repositories.price_repository import PriceRepository

# 自動的にEpic Games Storeの価格も取得・更新
price_repo = PriceRepository()
prices = price_repo.get_latest_prices_with_refresh(game_id)
```

## 🧪 テスト

### テストスクリプト実行
```bash
python test_epic_service.py
```

### テスト内容
1. **最近のゲーム取得テスト**
2. **ゲーム検索テスト**
3. **無料ゲーム取得テスト**
4. **価格取得テスト**
5. **GraphQLクエリテスト**

## 📊 パフォーマンス

### キャッシュ機能
- プロダクトマッピング: 1時間キャッシュ
- 価格データ: 設定可能なキャッシュ時間（デフォルト1時間）

### レート制限対応
- API呼び出し間隔: 0.2秒
- エラーハンドリング: 自動リトライ機能

## 🔒 セキュリティ

### 認証
- APIキー不要（公開API使用）
- User-Agent設定: `GameBargain/1.0`

### エラーハンドリング
- ネットワークエラー対応
- タイムアウト設定: 30秒
- 例外処理とログ出力

## 📈 今後の拡張

### 予定機能
- [ ] セール情報の詳細取得
- [ ] レビュー・評価情報取得
- [ ] システム要件情報取得
- [ ] 多言語対応拡張

### 最適化予定
- [ ] バッチ処理による価格更新
- [ ] Redisキャッシュ導入
- [ ] 非同期処理対応

## 🐛 トラブルシューティング

### よくある問題

#### 1. 価格取得エラー
```python
# ログ確認
print(f"[DEBUG] Epic Games Store価格取得エラー: {e}")
```

#### 2. GraphQLクエリエラー
```python
# レスポンス確認
response = epic_service.session.post(graphql_url, json=query_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

#### 3. データベースエラー
```bash
# マイグレーション実行
python -m alembic upgrade head
```

## 📚 参考資料

- [Epic Games Store GraphQL API](https://graphql.epicgames.com/graphql)
- [Epic Games Store Web API](https://github.com/SD4RK/epicstore_api)
- [Epic Games Store 無料ゲームAPI](https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions)

## 🤝 貢献

Epic Games Store API統合の改善にご協力いただける場合は、以下の点をご確認ください：

1. テストの追加・改善
2. エラーハンドリングの強化
3. パフォーマンス最適化
4. 新機能の提案

---

**作成日**: 2024年12月  
**バージョン**: 1.0.0  
**対応プラットフォーム**: Epic Games Store 