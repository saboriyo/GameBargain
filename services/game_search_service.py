"""
Game Search Service

ゲーム検索のビジネスロジック層
検索、フィルタリング、外部API連携などの処理を行います。
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from flask import current_app

from models.game import Game as GameModel
from repositories.game_repository import GameRepository
from services.steam_service import SteamAPIService


class GameSearchService:
    """ゲーム検索サービス"""
    
    def __init__(self, game_repository: Optional[GameRepository] = None, steam_service: Optional[SteamAPIService] = None):
        """
        初期化
        
        Args:
            game_repository: ゲームリポジトリ
            steam_service: Steam APIサービス
        """
        self.game_repository = game_repository or GameRepository()
        self.steam_service = steam_service or SteamAPIService()
    
    def search_games(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, 
                    page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        ゲーム検索メイン処理
        
        Args:
            query: 検索クエリ
            filters: フィルター条件
            page: ページ番号
            per_page: 1ページあたりの件数
            
        Returns:
            Dict[str, Any]: 検索結果
        """
        try:
            current_app.logger.info(f"ゲーム検索開始: query='{query}', filters={filters}")
            
            # データベースから検索
            games, total_count = self.game_repository.search_games(
                query=query, 
                filters=filters, 
                page=page, 
                per_page=per_page
            )
            
            # データベースに十分な結果がない場合、Steam APIから検索
            if query and len(games) < 5 and page == 1:
                current_app.logger.info(f"Steam APIから追加検索: '{query}'")
                steam_games = self._search_from_steam_api(query)
                
                if steam_games:
                    # Steam APIの結果をデータベースに保存（リポジトリ層を使用）
                    self.game_repository.save_steam_games_from_api(steam_games)
                    
                    # データベースから再検索
                    games, total_count = self.game_repository.search_games(
                        query=query, 
                        filters=filters, 
                        page=page, 
                        per_page=per_page
                    )
            
            # レスポンス用に整形
            formatted_games = [self._format_game_for_response(game) for game in games]
            
            # ページネーション情報
            pagination = self._create_pagination_info(page, per_page, total_count)
            
            current_app.logger.info(f"検索完了: 結果数={len(formatted_games)}")
            
            return {
                'games': formatted_games,
                'pagination': pagination,
                'total_count': total_count
            }
            
        except Exception as e:
            current_app.logger.error(f"ゲーム検索エラー: {e}")
            raise
    
    def _search_from_steam_api(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Steam APIから検索
        
        Args:
            query: 検索クエリ
            limit: 取得件数
            
        Returns:
            List[Dict[str, Any]]: Steam APIからの検索結果
        """
        try:
            return self.steam_service.search_games(query, limit)
        except Exception as e:
            current_app.logger.error(f"Steam API検索エラー: {e}")
            return []
    
    def _format_game_for_response(self, game: GameModel) -> Dict[str, Any]:
        """
        ゲーム情報をレスポンス用に整形
        
        Args:
            game: ゲーム情報
            
        Returns:
            Dict[str, Any]: 整形されたゲーム情報
        """
        # 価格情報の取得
        lowest_price_info = self._get_lowest_price_info(game)
        
        return {
            'id': getattr(game, 'id', None),
            'title': getattr(game, 'title', ''),
            'description': getattr(game, 'description', ''),
            'developer': getattr(game, 'developer', ''),
            'publisher': getattr(game, 'publisher', ''),
            'image_url': getattr(game, 'image_url', ''),
            'genres': getattr(game, 'genres', ''),
            'steam_rating': getattr(game, 'steam_rating', None),
            'release_date': getattr(game, 'release_date', None),
            'lowest_price': lowest_price_info
        }
    
    def _get_lowest_price_info(self, game: GameModel) -> Optional[Dict[str, Any]]:
        """
        最安値情報を取得
        
        Args:
            game: ゲーム情報
            
        Returns:
            Optional[Dict[str, Any]]: 最安値情報
        """
        current_price = getattr(game, 'current_price', None)
        original_price = getattr(game, 'original_price', None)
        discount_percent = getattr(game, 'discount_percent', 0)
        
        if current_price:
            return {
                'price': float(current_price),
                'original_price': float(original_price) if original_price else None,
                'discount_percent': discount_percent or 0,
                'store': 'steam'  # デフォルト
            }
        
        return None
    
    def _create_pagination_info(self, page: int, per_page: int, total_count: int) -> Dict[str, Any]:
        """
        ページネーション情報を作成
        
        Args:
            page: 現在のページ
            per_page: 1ページあたりの件数
            total_count: 総件数
            
        Returns:
            Dict[str, Any]: ページネーション情報
        """
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return {
            'page': page,
            'pages': total_pages,
            'total': total_count,
            'per_page': per_page,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None,
            'start_index': (page - 1) * per_page + 1 if total_count > 0 else 0,
            'end_index': min(page * per_page, total_count),
            'iter_pages': lambda: self._iter_pages(page, total_pages)
        }
    
    def _iter_pages(self, current_page: int, total_pages: int) -> List[int]:
        """
        ページネーション用のページ番号生成
        
        Args:
            current_page: 現在のページ番号
            total_pages: 総ページ数
            
        Returns:
            List[int]: ページ番号のリスト
        """
        pages = []
        for num in range(1, total_pages + 1):
            if num <= 2 or \
               (current_page - 2 < num < current_page + 3) or \
               num > total_pages - 2:
                pages.append(num)
        return pages
    
    def get_recent_games(self, limit: int = 4) -> List[Dict[str, Any]]:
        """
        最近追加されたゲーム一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[Dict[str, Any]]: ゲーム一覧
        """
        try:
            games = self.game_repository.get_recent_games(limit)
            return [self._format_game_for_response(game) for game in games]
        except Exception as e:
            current_app.logger.error(f"最近のゲーム取得エラー: {e}")
            return []
    
    def get_popular_games(self, limit: int = 6) -> List[Dict[str, Any]]:
        """
        人気ゲーム一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[Dict[str, Any]]: ゲーム一覧
        """
        try:
            games = self.game_repository.get_popular_games(limit)
            return [self._format_game_for_response(game) for game in games]
        except Exception as e:
            current_app.logger.error(f"人気ゲーム取得エラー: {e}")
            return []
