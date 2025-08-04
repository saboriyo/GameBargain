# Epic Games Store API調査結果

## 概要

Epic Games Storeから価格情報を取得する方法を調査し、[SD4RK/epicstore_api](https://github.com/SD4RK/epicstore_api)リポジトリを参考にして改善されたEpic Games Storeサービスを実装しました。

## 調査結果

### 1. 利用可能なAPI

#### 1.1 epicstore_apiライブラリ
- **状態**: ✅ 正常動作
- **機能**: プロダクトマッピング、オファー情報、価格情報の取得
- **取得可能データ**: 1271件のプロダクトマッピング
- **価格情報**: 正常に取得可能

#### 1.2 Epic Games Store GraphQL API
- **状態**: ❌ 404エラー
- **エンドポイント**: `https://graphql.epicgames.com/graphql`
- **問題**: 現在はアクセス不可

#### 1.3 Epic Games Store Web API（無料ゲーム）
- **状態**: ✅ 正常動作
- **エンドポイント**: `https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions`
- **機能**: 無料ゲーム情報、価格情報の取得

### 2. 実装された改善

#### 2.1 ハイブリッドアプローチ
```python
# epicstore_apiライブラリを優先使用
if self.epicstore_api:
    # epicstore_apiライブラリでデータ取得
    mapping = self.epicstore_api.get_product_mapping()
else:
    # フォールバック: 独自実装
    mapping = self._get_mapping_from_free_games()
```

#### 2.2 価格取得機能
- **epicstore_apiライブラリ**: 詳細な価格情報を取得
- **フォールバック**: 無料ゲームAPIから価格情報を取得
- **価格情報**: 現在価格、割引価格、割引率、セール情報

#### 2.3 ゲーム検索機能
- **epicstore_apiライブラリ**: プロダクトマッピングから検索
- **フォールバック**: 無料ゲームAPIから検索
- **検索結果**: タイトル、開発者、価格、画像URL

### 3. 取得可能なデータ

#### 3.1 ゲーム情報
```python
{
    'epic_namespace': 'game_id',
    'title': 'ゲームタイトル',
    'description': 'ゲーム説明',
    'developer': '開発者名',
    'publisher': 'パブリッシャー名',
    'release_date': 'リリース日',
    'image_url': '画像URL',
    'epic_url': 'Epic Games Store URL',
    'price_info': {
        'is_free': True/False,
        'current_price': 価格,
        'original_price': 原価,
        'discount_percent': 割引率,
        'formatted_price': '¥1,000',
        'is_on_sale': True/False
    }
}
```

#### 3.2 価格情報
```python
{
    'price': 現在価格,
    'original_price': 原価,
    'discount_percent': 割引率,
    'currency': 'JPY',
    'is_on_sale': True/False,
    'namespace': 'game_id',
    'title': 'ゲームタイトル',
    'image_url': '画像URL'
}
```

### 4. 使用方法

#### 4.1 サービスの初期化
```python
from services.epic_service import EpicGamesStoreAPI

epic_service = EpicGamesStoreAPI()
```

#### 4.2 ゲーム検索
```python
# ゲーム検索
games = epic_service.search_games("fortnite", limit=10)

# 最近のゲーム
recent_games = epic_service.get_recent_games(limit=20)

# 無料ゲーム
free_games = epic_service.get_free_games()
```

#### 4.3 価格取得
```python
# 価格情報取得
price_info = epic_service.get_game_price("game_namespace", "game_slug")
```

### 5. エラーハンドリング

#### 5.1 フォールバック機能
- epicstore_apiライブラリが失敗した場合、独自実装にフォールバック
- 無料ゲームAPIが失敗した場合、エラーログを出力

#### 5.2 ログ出力
```python
logger.info("epicstore_apiライブラリでプロダクトマッピング取得成功")
logger.warning("epicstore_apiライブラリでの取得に失敗")
logger.error("Epic Games Store API取得エラー")
```

### 6. パフォーマンス

#### 6.1 キャッシュ機能
- プロダクトマッピング: 1時間キャッシュ
- 価格情報: リアルタイム取得

#### 6.2 リクエスト制限
- タイムアウト: 30秒
- リトライ: なし（フォールバック機能で対応）

### 7. 制限事項

#### 7.1 epicstore_apiライブラリ
- プロダクトマッピングは正常に取得可能
- 一部のゲームで価格情報が取得できない場合がある

#### 7.2 無料ゲームAPI
- 無料ゲームとセール中のゲームのみ取得可能
- 全ゲームの価格情報は取得不可

### 8. 今後の改善案

#### 8.1 価格監視機能
- 定期的な価格チェック
- 価格変動通知

#### 8.2 データベース統合
- Epic Games Storeデータの永続化
- 価格履歴の管理

#### 8.3 エラー回復機能
- 自動リトライ機能
- 複数APIエンドポイントの並行使用

## 結論

epicstore_apiライブラリと独自実装を組み合わせることで、Epic Games Storeから価格情報を安定して取得できるようになりました。GraphQL APIは現在利用できませんが、代替手段により十分な機能を提供できています。

### 推奨事項

1. **epicstore_apiライブラリの継続使用**: 最も安定したデータ取得方法
2. **フォールバック機能の維持**: API障害時の冗長性確保
3. **定期的な監視**: APIの状態確認とエラー検出
4. **データベース統合**: 価格履歴の管理と分析機能の追加 