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
    
    def __init__(self, session: Session = None):
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
        # 価格フィルター
        if filters.get('min_price'):
            try:
                min_price = float(filters['min_price'])
                query = query.filter(Game.current_price >= min_price)
            except (ValueError, TypeError):
                pass
        
        if filters.get('max_price'):
            try:
                max_price = float(filters['max_price'])
                query = query.filter(Game.current_price <= max_price)
            except (ValueError, TypeError):
                pass
        
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
        if sort == 'price_asc':
            return query.order_by(asc(Game.current_price))
        elif sort == 'price_desc':
            return query.order_by(desc(Game.current_price))
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
                price_info = steam_game.get('price_info', {})
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
                
                # 価格情報の更新（有効な値のみ）
                if price_info and price_info.get('current_price') is not None:
                    update_data.update({
                        'current_price': price_info.get('current_price'),
                        'original_price': price_info.get('original_price'),
                        'discount_percent': price_info.get('discount_percent', 0)
                    })
                
                return self.update(existing_game, **update_data)
            else:
                # 新規ゲームの作成
                genres = steam_game.get('genres', [])
                genres_str = ','.join(genres) if isinstance(genres, list) else str(genres) if genres else ''
                
                # 価格情報の取得
                price_info = steam_game.get('price_info', {})
                
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
                    'current_price': price_info.get('current_price') if price_info.get('current_price') is not None else None,
                    'original_price': price_info.get('original_price') if price_info.get('original_price') is not None else None,
                    'discount_percent': price_info.get('discount_percent', 0),
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
