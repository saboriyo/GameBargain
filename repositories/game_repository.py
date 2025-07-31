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
        self.session.add(game)
        self.session.flush()  # IDを取得するため
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
            
            # 既存チェック
            existing_game = self.get_by_steam_appid(steam_appid)
            
            if existing_game:
                # 既存ゲームの更新
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

    def commit(self):
        """トランザクションをコミット"""
        self.session.commit()
    
    def rollback(self):
        """トランザクションをロールバック"""
        self.session.rollback()

    def format_game_for_web_template(self, game_data, price_repository=None) -> Dict[str, Any]:
        """
        ゲームデータをWebテンプレート用に整形
        GameSearchServiceからのデータとGameモデルの両方に対応
        
        Args:
            game_data: GameSearchServiceからの辞書データまたはGameモデルオブジェクト
            price_repository: PriceRepositoryインスタンス（価格情報取得用）
            
        Returns:
            Dict: 整形されたゲームデータ
        """
        # GameSearchServiceからの辞書データの場合
        if isinstance(game_data, dict):
            return {
                'id': game_data.get('id'),
                'title': game_data.get('title'),
                'description': game_data.get('description'),
                'developer': game_data.get('developer'),
                'publisher': game_data.get('publisher'),
                'release_date': game_data.get('release_date') or '',
                'genres': game_data.get('genres', []),
                'platforms': game_data.get('platforms', []),
                'image_url': game_data.get('image_url') or 'https://via.placeholder.com/300x400',
                'steam_url': game_data.get('steam_url'),
                'steam_rating': game_data.get('steam_rating'),
                'metacritic_score': game_data.get('metacritic_score'),
                'current_price': game_data.get('current_price') or 0.0,
                'original_price': game_data.get('original_price') or 0.0,
                'discount_percent': game_data.get('discount_percent', 0),
                'is_on_sale': game_data.get('discount_percent', 0) > 0,
                'lowest_price': game_data.get('current_price') or 0.0,
                'lowest_store': 'steam',
                'prices': game_data.get('prices', {})
            }

        # Gameモデルオブジェクトの場合
        formatted_game = {
            'id': game_data.id,
            'title': game_data.title,
            'description': game_data.description,
            'developer': game_data.developer,
            'publisher': game_data.publisher,
            'release_date': game_data.release_date.strftime('%Y-%m-%d') if game_data.release_date else '',
            'genres': game_data.genres.split(',') if isinstance(game_data.genres, str) and game_data.genres else (game_data.genres if isinstance(game_data.genres, list) else []),
            'platforms': game_data.platforms.split(',') if isinstance(game_data.platforms, str) and game_data.platforms else (game_data.platforms if isinstance(game_data.platforms, list) else []),
            'image_url': game_data.image_url or 'https://via.placeholder.com/300x400',
            'steam_url': game_data.steam_url,
            'steam_rating': game_data.steam_rating,
            'metacritic_score': game_data.metacritic_score,
            'current_price': 0.0,
            'original_price': 0.0,
            'discount_percent': 0,
            'is_on_sale': False,
            'lowest_price': 0.0,
            'lowest_store': 'steam',
            'prices': {}
        }

        # 価格情報を取得してマージ
        if price_repository:
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
                        'lowest_price': lowest_price_info['price'],
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
            except Exception:
                # 価格情報の取得に失敗した場合はデフォルト値のまま
                pass

        return formatted_game
