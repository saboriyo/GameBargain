"""
Game Repository

ゲーム情報のデータアクセス層
データベースへの直接アクセスを抽象化します。
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import and_, or_, asc, desc, func
from sqlalchemy.orm import Session

from models import db, Game, Price
from models.game import Game as GameModel


class GameRepository:
    """ゲーム情報のリポジトリクラス"""
    
    def __init__(self, session: Optional[Session] = None):
        """
        初期化
        
        Args:
            session: SQLAlchemyセッション（指定しない場合はdb.sessionを使用）
        """
        self.session = session or db.session
    
    def search_games(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, 
                    page: int = 1, per_page: int = 20) -> Tuple[List[GameModel], int]:
        """
        ゲーム検索
        
        Args:
            query: 検索クエリ
            filters: フィルター条件
            page: ページ番号
            per_page: 1ページあたりの件数
            
        Returns:
            Tuple[List[GameModel], int]: (ゲーム一覧, 総件数)
        """
        # ベースクエリの作成
        base_query = self.session.query(Game)
        
        # テキスト検索
        if query:
            search_conditions = [
                Game.title.ilike(f'%{query}%'),
                Game.normalized_title.ilike(f'%{query}%'),
                Game.developer.ilike(f'%{query}%'),
                Game.publisher.ilike(f'%{query}%')
            ]
            base_query = base_query.filter(or_(*search_conditions))
        
        # フィルター適用
        if filters:
            base_query = self._apply_filters(base_query, filters)
        
        # ソート処理
        sort = filters.get('sort', 'relevance') if filters else 'relevance'
        base_query = self._apply_sort(base_query, sort)
        
        # 総件数を取得
        total_count = base_query.count()
        
        # ページネーション
        offset = (page - 1) * per_page
        games = base_query.offset(offset).limit(per_page).all()
        
        return games, total_count
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        フィルター条件をクエリに適用
        
        Args:
            query: SQLAlchemyクエリ
            filters: フィルター条件
            
        Returns:
            フィルター適用後のクエリ
        """
        # 価格フィルターは現在のところ無効化（Priceテーブルとの結合が必要）
        # TODO: 価格フィルターを実装する場合はPriceテーブルとの結合を追加
        
        # ジャンルフィルター
        if filters.get('genre'):
            query = query.filter(Game.genres.ilike(f'%{filters["genre"]}%'))
        
        # プラットフォームフィルター（必要に応じて実装）
        if filters.get('platform'):
            # プラットフォーム情報が追加されたら実装
            pass
        
        return query
    
    def _apply_sort(self, query, sort: str):
        """
        ソート条件をクエリに適用
        
        Args:
            query: SQLAlchemyクエリ
            sort: ソート条件
            
        Returns:
            ソート適用後のクエリ
        """
        # 価格ソートは現在のところ無効化（Priceテーブルとの結合が必要）
        # TODO: 価格ソートを実装する場合はPriceテーブルとの結合を追加
        if sort == 'price_asc' or sort == 'price_desc':
            # 価格ソートは無効化し、関連度順にフォールバック
            return query.order_by(
                desc(Game.steam_rating),
                desc(Game.updated_at)
            )
        elif sort == 'release_date':
            return query.order_by(desc(Game.release_date))
        elif sort == 'title':
            return query.order_by(asc(Game.title))
        else:  # relevance (default)
            return query.order_by(
                desc(Game.steam_rating),
                desc(Game.updated_at)
            )
    
    def get_by_id(self, game_id: int) -> Optional[GameModel]:
        """
        IDでゲームを取得
        
        Args:
            game_id: ゲームID
            
        Returns:
            Optional[GameModel]: ゲーム情報（見つからない場合はNone）
        """
        return self.session.query(Game).filter_by(id=game_id).first()
    
    def get_by_steam_appid(self, steam_appid: str) -> Optional[GameModel]:
        """
        Steam App IDでゲームを取得
        
        Args:
            steam_appid: Steam App ID
            
        Returns:
            Optional[GameModel]: ゲーム情報（見つからない場合はNone）
        """
        return self.session.query(Game).filter_by(steam_appid=steam_appid).first()
    
    def save(self, game: GameModel) -> GameModel:
        """
        ゲーム情報を保存
        
        Args:
            game: ゲーム情報
            
        Returns:
            GameModel: 保存されたゲーム情報
        """
        # バリデーション実行
        game.validate()
        
        # NULL IDチェック
        if game.id is None:
            # 新規保存の場合
            self.session.add(game)
            self.session.flush()  # IDを取得するため
            
            # IDが正しく設定されたか確認
            if game.id is None:
                raise ValueError("ゲームの保存に失敗しました: IDがNULLです")
        else:
            # 更新の場合
            self.session.merge(game)
            self.session.flush()
        
        return game
    
    def update(self, game: GameModel, **kwargs) -> GameModel:
        """
        ゲーム情報を更新
        
        Args:
            game: 更新対象のゲーム
            **kwargs: 更新データ
            
        Returns:
            GameModel: 更新されたゲーム情報
        """
        for key, value in kwargs.items():
            if hasattr(game, key):
                setattr(game, key, value)
        
        self.session.flush()
        return game
    
    def get_recent_games(self, limit: int = 10) -> List[GameModel]:
        """
        最近追加されたゲーム一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[GameModel]: ゲーム一覧
        """
        return self.session.query(Game).order_by(
            desc(Game.created_at)
        ).limit(limit).all()
    

    def save_steam_games_from_api(self, steam_games: List[Dict[str, Any]]) -> List[GameModel]:
        """
        Steam APIから取得したゲーム情報を一括保存
        
        Args:
            steam_games: Steam APIからのゲーム情報リスト
            
        Returns:
            List[GameModel]: 保存されたゲーム一覧
        """
        saved_games = []
        
        try:
            for steam_game in steam_games:
                saved_game = self._save_single_steam_game(steam_game)
                if saved_game:
                    saved_games.append(saved_game)
            
            # 一括でコミット
            self.session.commit()
            return saved_games
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def save_external_games_from_api(self, external_games: List[Dict[str, Any]]) -> List[GameModel]:
        """
        外部APIから取得したゲーム情報を一括保存
        
        Args:
            external_games: 外部APIからのゲーム情報リスト
            
        Returns:
            List[GameModel]: 保存されたゲーム一覧
        """
        saved_games = []
        
        try:
            for game_data in external_games:
                # Steam APIのデータかEpic Games Store APIのデータかを判定
                if 'steam_appid' in game_data:
                    saved_game = self._save_single_steam_game(game_data)
                elif 'epic_namespace' in game_data:
                    saved_game = self._save_single_epic_game(game_data)
                else:
                    # 不明なデータ形式はスキップ
                    continue
                
                if saved_game:
                    saved_games.append(saved_game)
            
            # 一括でコミット
            self.session.commit()
            return saved_games
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def _save_single_steam_game(self, steam_game: Dict[str, Any]) -> Optional[GameModel]:
        """
        単一のSteam ゲームをデータベースに保存
        
        Args:
            steam_game: Steam APIからのゲーム情報
            
        Returns:
            Optional[GameModel]: 保存されたゲーム（失敗時はNone）
        """
        try:
            steam_appid = steam_game.get('steam_appid')
            if not steam_appid:
                return None
            
            # steam_appidを文字列に変換
            steam_appid = str(steam_appid)
            
            # 既存チェック（デバッグログ追加）
            existing_game = self.get_by_steam_appid(steam_appid)
            
            if existing_game:
                # 既存ゲームの更新
                print(f"既存ゲームを更新: {existing_game.title} (ID: {existing_game.id})")
                update_data = {
                    'title': steam_game.get('title') or existing_game.title,
                    'description': steam_game.get('description') or existing_game.description,
                    'developer': steam_game.get('developer') or existing_game.developer,
                    'publisher': steam_game.get('publisher') or existing_game.publisher,
                    'image_url': steam_game.get('image_url') or existing_game.image_url,
                    'steam_url': steam_game.get('steam_url') or f"https://store.steampowered.com/app/{steam_appid}/",
                    'steam_rating': steam_game.get('steam_rating') or existing_game.steam_rating,
                    'metacritic_score': steam_game.get('metacritic_score') or existing_game.metacritic_score,
                    'updated_at': datetime.now(timezone.utc)
                }
                
                return self.update(existing_game, **update_data)
            else:
                # 新規ゲームの作成
                print(f"新規ゲームを作成: {steam_game.get('title')} (Steam App ID: {steam_appid})")
                genres = steam_game.get('genres', [])
                genres_str = ','.join(genres) if isinstance(genres, list) else str(genres) if genres else ''
                
                # 必須フィールドのデフォルト値設定
                title = steam_game.get('title')
                if not title:
                    return None
                
                # Gameインスタンスを辞書で作成
                game_data = {
                    'steam_appid': steam_appid,
                    'title': title,
                    'normalized_title': self._normalize_title(title),
                    'description': steam_game.get('description') or f"Steam App ID: {steam_appid}",
                    'developer': steam_game.get('developer') or '不明',
                    'publisher': steam_game.get('publisher') or '不明',
                    'genres': genres_str,
                    'image_url': steam_game.get('image_url') or f"https://cdn.akamai.steamstatic.com/steam/apps/{steam_appid}/header.jpg",
                    'steam_url': steam_game.get('steam_url') or f"https://store.steampowered.com/app/{steam_appid}/",
                    'steam_rating': steam_game.get('steam_rating'),
                    'metacritic_score': steam_game.get('metacritic_score'),
                    'is_active': True
                }
                
                game = GameModel(**game_data)
                return self.save(game)
                
        except Exception as e:
            print(f"Steamゲーム保存エラー: {e}")
            return None
    
    def _save_single_epic_game(self, epic_game: Dict[str, Any]) -> Optional[GameModel]:
        """
        単一のEpic Games Store ゲームをデータベースに保存
        
        Args:
            epic_game: Epic Games Store APIからのゲーム情報
            
        Returns:
            Optional[GameModel]: 保存されたゲーム（失敗時はNone）
        """
        try:
            epic_namespace = epic_game.get('epic_namespace')
            if not epic_namespace:
                return None
            
            # 既存チェック（Epic Games Storeのnamespaceで検索）
            existing_game = self.session.query(Game).filter(
                Game.epic_namespace == epic_namespace
            ).first()
            
            if existing_game:
                # 既存ゲームの更新
                update_data = {
                    'title': epic_game.get('title') or existing_game.title,
                    'description': epic_game.get('description') or existing_game.description,
                    'developer': epic_game.get('developer') or existing_game.developer,
                    'publisher': epic_game.get('publisher') or existing_game.publisher,
                    'image_url': epic_game.get('image_url') or existing_game.image_url,
                    'epic_url': epic_game.get('epic_url') or f"https://store.epicgames.com/ja/p/{epic_game.get('productSlug', '')}",
                    'updated_at': datetime.now(timezone.utc)
                }
                
                return self.update(existing_game, **update_data)
            else:
                # 新規ゲームの作成
                tags = epic_game.get('tags', [])
                tags_str = ','.join(tags) if isinstance(tags, list) else str(tags) if tags else ''
                
                # 必須フィールドのデフォルト値設定
                title = epic_game.get('title')
                if not title:
                    return None
                
                # Gameインスタンスを辞書で作成
                game_data = {
                    'epic_namespace': epic_namespace,
                    'title': title,
                    'normalized_title': self._normalize_title(title),
                    'description': epic_game.get('description') or f"Epic Games Store: {epic_namespace}",
                    'developer': epic_game.get('developer') or '不明',
                    'publisher': epic_game.get('publisher') or '不明',
                    'genres': tags_str,  # Epic Games Storeではtagsをgenresとして使用
                    'image_url': epic_game.get('image_url') or '',
                    'epic_url': epic_game.get('epic_url') or f"https://store.epicgames.com/ja/p/{epic_game.get('productSlug', '')}",
                    'is_active': True
                }
                
                game = GameModel(**game_data)
                return self.save(game)
                
        except Exception:
            return None
    
    def _normalize_title(self, title: str) -> str:
        """
        タイトルを正規化（検索用）
        
        Args:
            title: 元のタイトル
            
        Returns:
            str: 正規化されたタイトル
        """
        import re
        # 英数字以外を除去し、小文字に変換
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        return ' '.join(normalized.split())
    
    def _parse_genres(self, genres_data) -> List[str]:
        """
        ジャンルデータをパース
        
        Args:
            genres_data: ジャンルデータ（文字列、リスト、None）
            
        Returns:
            List[str]: ジャンルのリスト
        """
        if genres_data is None:
            return []
        
        if isinstance(genres_data, list):
            return genres_data
        
        if isinstance(genres_data, str):
            if genres_data.strip():
                return [genre.strip() for genre in genres_data.split(',') if genre.strip()]
            return []
        
        return []
    
    def _parse_platforms(self, platforms_data) -> List[str]:
        """
        プラットフォームデータをパース
        
        Args:
            platforms_data: プラットフォームデータ（文字列、リスト、None）
            
        Returns:
            List[str]: プラットフォームのリスト
        """
        if platforms_data is None:
            return []
        
        if isinstance(platforms_data, list):
            return platforms_data
        
        if isinstance(platforms_data, str):
            if platforms_data.strip():
                return [platform.strip() for platform in platforms_data.split(',') if platform.strip()]
            return []
        
        return []

    def commit(self):
        """トランザクションをコミット"""
        self.session.commit()
    
    def rollback(self):
        """トランザクションをロールバック"""
        self.session.rollback()
    
    def cleanup_null_id_records(self) -> int:
        """
        NULL IDレコードを削除
        
        Returns:
            int: 削除されたレコード数
        """
        try:
            from sqlalchemy import text
            result = self.session.execute(text("DELETE FROM games WHERE id IS NULL"))
            deleted_count = result.rowcount
            self.session.commit()
            return deleted_count
        except Exception as e:
            self.session.rollback()
            raise e
    
    def validate_database_integrity(self) -> Dict[str, Any]:
        """
        データベースの整合性をチェック
        
        Returns:
            Dict[str, Any]: 整合性チェック結果
        """
        try:
            from sqlalchemy import text
            
            # NULL IDレコード数を確認
            result = self.session.execute(text("SELECT COUNT(*) as count FROM games WHERE id IS NULL"))
            null_id_count = result.fetchone()[0]
            
            # 重複steam_appid数を確認
            result = self.session.execute(text("""
                SELECT COUNT(*) as count FROM (
                    SELECT steam_appid, COUNT(*) as cnt 
                    FROM games 
                    WHERE steam_appid IS NOT NULL 
                    GROUP BY steam_appid 
                    HAVING COUNT(*) > 1
                )
            """))
            duplicate_steam_count = result.fetchone()[0]
            
            # 重複epic_namespace数を確認
            result = self.session.execute(text("""
                SELECT COUNT(*) as count FROM (
                    SELECT epic_namespace, COUNT(*) as cnt 
                    FROM games 
                    WHERE epic_namespace IS NOT NULL 
                    GROUP BY epic_namespace 
                    HAVING COUNT(*) > 1
                )
            """))
            duplicate_epic_count = result.fetchone()[0]
            
            return {
                'null_id_count': null_id_count,
                'duplicate_steam_count': duplicate_steam_count,
                'duplicate_epic_count': duplicate_epic_count,
                'is_valid': null_id_count == 0 and duplicate_steam_count == 0 and duplicate_epic_count == 0
            }
        except Exception as e:
            return {
                'error': str(e),
                'is_valid': False
            }

    def format_game_for_web_template(self, game_data, price_repository=None) -> Dict[str, Any]:
        """
        ゲームデータをWebテンプレート用に整形
        Gameモデルオブジェクトを辞書形式に変換
        
        Args:
            game_data: Gameモデルオブジェクト
            price_repository: PriceRepositoryインスタンス（価格情報取得用）
            
        Returns:
            Dict: 整形されたゲームデータ
        """
        # Noneチェック
        if game_data is None:
            return {
                'id': None,
                'title': '不明なゲーム',
                'description': '',
                'developer': '',
                'publisher': '',
                'release_date': '',
                'genres': [],
                'platforms': [],
                'image_url': 'https://via.placeholder.com/300x400',
                'steam_url': '',
                'steam_rating': None,
                'metacritic_score': None,
                'current_price': 0.0,
                'original_price': 0.0,
                'discount_percent': 0,
                'is_on_sale': False,
                'lowest_price': {
                    'price': 0.0,
                    'store': 'steam',
                    'discount_percent': 0,
                    'original_price': 0.0
                },
                'lowest_store': 'steam',
                'prices': {}
            }

        # Gameモデルオブジェクトを辞書形式に変換
        formatted_game = {
            'id': game_data.id,
            'title': game_data.title,
            'description': game_data.description,
            'developer': game_data.developer,
            'publisher': game_data.publisher,
            'release_date': game_data.release_date.strftime('%Y-%m-%d') if game_data.release_date else '',
            'genres': self._parse_genres(game_data.genres),
            'platforms': self._parse_platforms(game_data.platforms),
            'image_url': game_data.image_url or 'https://via.placeholder.com/300x400',
            'steam_url': game_data.steam_url,
            'epic_url': game_data.epic_url,
            'steam_rating': game_data.steam_rating,
            'metacritic_score': game_data.metacritic_score,
            'current_price': 0.0,
            'original_price': 0.0,
            'discount_percent': 0,
            'is_on_sale': False,
            'lowest_price': {
                'price': 0.0,
                'store': 'steam',
                'discount_percent': 0,
                'original_price': 0.0
            },
            'lowest_store': 'steam',
            'prices': {}
        }

        # 価格情報を取得してマージ
        if price_repository and game_data.id:
            try:
                formatted_prices = price_repository.get_formatted_prices_for_game(game_data.id)
                if formatted_prices:
                    # 最初の価格を現在価格として設定
                    first_price = formatted_prices[0]
                    formatted_game.update({
                        'current_price': first_price['price'],
                        'original_price': first_price['original_price'],
                        'discount_percent': first_price['discount_percent'],
                        'is_on_sale': first_price['is_on_sale']
                    })

                    # 最安値を計算
                    lowest_price_info = min(formatted_prices, key=lambda p: p['price'])
                    formatted_game.update({
                        'lowest_price': {
                            'price': lowest_price_info['price'],
                            'store': lowest_price_info['store'],
                            'discount_percent': lowest_price_info['discount_percent'],
                            'original_price': lowest_price_info['original_price']
                        },
                        'lowest_store': lowest_price_info['store']
                    })

                    # prices辞書を構築
                    prices_dict = {}
                    for price_info in formatted_prices:
                        prices_dict[price_info['store']] = {
                            'current': price_info['price'],
                            'original': price_info['original_price'],
                            'discount': price_info['discount_percent'],
                            'url': price_info.get('store_url')
                        }
                    formatted_game['prices'] = prices_dict
            except Exception as e:
                # 価格情報の取得に失敗した場合はデフォルト値のまま
                print(f"価格情報取得エラー (Game ID: {game_data.id}): {e}")
                pass

        return formatted_game
