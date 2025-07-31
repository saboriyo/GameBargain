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
from services.epic_service import EpicGamesStoreAPI


class GameSearchService:
    """ゲーム検索サービス"""
    
    def __init__(self, game_repository: Optional[GameRepository] = None, 
                 steam_service: Optional[SteamAPIService] = None,
                 epic_service: Optional[EpicGamesStoreAPI] = None):
        """
        初期化
        
        Args:
            game_repository: ゲームリポジトリ
            steam_service: Steam APIサービス
            epic_service: Epic Games Store APIサービス
        """
        self.game_repository = game_repository or GameRepository()
        self.steam_service = steam_service or SteamAPIService()
        self.epic_service = epic_service or EpicGamesStoreAPI()
    
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
            Dict[str, Any]: 検索結果（gamesはGameModelオブジェクトのリスト）
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
            
            current_app.logger.info(f"データベース検索結果: {len(games)}件（総数: {total_count}）")
            if games:
                for i, game in enumerate(games[:3]):
                    current_app.logger.info(f"  検索結果{i+1}: {game.title} (ID: {game.id}, Steam: {game.steam_appid})")
            
            # データベースに十分な結果がない場合、外部APIから検索
            # 初回検索（page=1）で結果が少ない場合のみ外部APIを呼び出し
            if query and len(games) < 3 and page == 1:
                current_app.logger.info(f"外部APIから追加検索: '{query}'")
                
                # Steam APIから検索（個別デバッグ）
                try:
                    current_app.logger.info("=== Steam API検索開始 ===")
                    steam_games = self._search_from_steam_api(query)
                    current_app.logger.info(f"Steam API検索完了: {len(steam_games)}件")
                except Exception as steam_error:
                    current_app.logger.error(f"Steam API検索エラー: {steam_error}")
                    steam_games = []
                
                # Epic Games Store APIから検索（個別デバッグ）
                try:
                    current_app.logger.info("=== Epic Games Store API検索開始 ===")
                    epic_games = self._search_from_epic_api(query)
                    current_app.logger.info(f"Epic Games Store API検索完了: {len(epic_games)}件")
                except Exception as epic_error:
                    current_app.logger.error(f"Epic Games Store API検索エラー: {epic_error}")
                    epic_games = []
                
                # SteamとEpicの結果を別々に保存
                saved_count = 0
                
                # Steam APIの結果を保存
                if steam_games:
                    current_app.logger.info(f"Steam API結果をデータベースに保存開始: {len(steam_games)}件")
                    try:
                        self.game_repository.save_steam_games_from_api(steam_games)
                        current_app.logger.info("Steam API結果のデータベース保存完了")
                        saved_count += len(steam_games)
                    except Exception as steam_save_error:
                        current_app.logger.error(f"Steam API結果の保存エラー: {steam_save_error}")
                
                # Epic Games Store APIの結果を保存
                if epic_games:
                    current_app.logger.info(f"Epic Games Store API結果をデータベースに保存開始: {len(epic_games)}件")
                    try:
                        self.game_repository.save_external_games_from_api(epic_games)
                        current_app.logger.info("Epic Games Store API結果のデータベース保存完了")
                        saved_count += len(epic_games)
                    except Exception as epic_save_error:
                        current_app.logger.error(f"Epic Games Store API結果の保存エラー: {epic_save_error}")
                
                if saved_count > 0:
                    current_app.logger.info(f"外部API結果保存完了: 合計{saved_count}件")
                    
                    # データベースから再検索
                    current_app.logger.info("外部API結果保存後の再検索開始")
                    games, total_count = self.game_repository.search_games(
                        query=query, 
                        filters=filters, 
                        page=page, 
                        per_page=per_page
                    )
                    current_app.logger.info(f"再検索完了: {len(games)}件（総数: {total_count}）")
                else:
                    current_app.logger.info("外部APIから結果が取得できませんでした")
            
            # レスポンス用に整形（Noneオブジェクトをフィルタリング）
            formatted_games = [self._format_game_for_response(game) for game in games if game is not None]
            
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
            if not self.steam_service:
                current_app.logger.warning("Steam APIサービスが初期化されていません")
                return []
            
            current_app.logger.info(f"Steam API検索開始: query='{query}', limit={limit}")
            steam_games = self.steam_service.search_games(query, limit)
            current_app.logger.info(f"Steam API検索完了: {len(steam_games)}件")
            
            # デバッグ用：最初の3件をログ出力
            if steam_games:
                for i, game in enumerate(steam_games[:3]):
                    current_app.logger.info(f"  Steam結果{i+1}: {game.get('title', 'N/A')} (ID: {game.get('steam_appid', 'N/A')})")
            else:
                current_app.logger.warning("Steam APIから結果が取得できませんでした")
            
            return steam_games
        except Exception as e:
            current_app.logger.error(f"Steam API検索エラー: {e}")
            current_app.logger.exception("Steam API検索エラーの詳細:")
            return []
    
    def _search_from_epic_api(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Epic Games Store APIから検索
        
        Args:
            query: 検索クエリ
            limit: 取得件数
            
        Returns:
            List[Dict[str, Any]]: Epic Games Store APIからの検索結果
        """
        try:
            if not self.epic_service:
                current_app.logger.warning("Epic Games Store APIサービスが初期化されていません")
                return []
            
            current_app.logger.info(f"Epic Games Store API検索開始: query='{query}', limit={limit}")
            epic_games = self.epic_service.search_games(query, limit)
            current_app.logger.info(f"Epic Games Store API検索完了: {len(epic_games)}件")
            
            # デバッグ用：最初の3件をログ出力
            if epic_games:
                for i, game in enumerate(epic_games[:3]):
                    current_app.logger.info(f"  Epic結果{i+1}: {game.get('title', 'N/A')} (ID: {game.get('epic_namespace', 'N/A')})")
            else:
                current_app.logger.warning("Epic Games Store APIから結果が取得できませんでした")
            
            return epic_games
        except Exception as e:
            current_app.logger.error(f"Epic Games Store API検索エラー: {e}")
            current_app.logger.exception("Epic Games Store API検索エラーの詳細:")
            return []
    
    def _format_game_for_response(self, game: GameModel) -> GameModel:
        """
        ゲーム情報をレスポンス用に整形（モデルオブジェクトをそのまま返す）
        
        Args:
            game: ゲーム情報
            
        Returns:
            GameModel: ゲームモデルオブジェクト
        """
        # Noneオブジェクトの場合はNoneを返す
        if game is None:
            return None
            
        # モデルオブジェクトをそのまま返す
        return game
    
    def _get_lowest_price_info(self, game: GameModel) -> Optional[Dict[str, Any]]:
        """
        最安値情報を取得
        
        Args:
            game: ゲーム情報
            
        Returns:
            Optional[Dict[str, Any]]: 最安値情報
        """
        # Noneオブジェクトの場合はNoneを返す
        if game is None:
            return None
            
        try:
            # Priceモデルから最新の価格情報を取得
            from models.price import Price
            from models import db
            
            # ゲームに関連する最新の価格情報を取得
            latest_price = db.session.query(Price).filter(
                Price.game_id == game.id
            ).order_by(Price.updated_at.desc()).first()
            
            if latest_price:
                current_price = latest_price.get_current_price()
                if current_price:
                    return {
                        'price': float(current_price),
                        'original_price': float(latest_price.regular_price) if latest_price.regular_price else None,
                        'discount_percent': latest_price.discount_rate or 0,
                        'store': latest_price.store or 'steam'
                    }
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"価格情報取得エラー: {e}")
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
    
    def get_recent_games(self, limit: int = 4) -> List[GameModel]:
        """
        最近追加されたゲーム一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[GameModel]: ゲーム一覧（モデルオブジェクト）
        """
        try:
            games = self.game_repository.get_recent_games(limit)
            return [self._format_game_for_response(game) for game in games if game is not None]
        except Exception as e:
            current_app.logger.error(f"最近のゲーム取得エラー: {e}")
            return []
    
    def get_popular_games(self, limit: int = 6) -> List[GameModel]:
        """
        人気ゲーム一覧を取得
        
        Args:
            limit: 取得件数
            
        Returns:
            List[GameModel]: ゲーム一覧（モデルオブジェクト）
        """
        try:
            games = self.game_repository.get_popular_games(limit)
            return [self._format_game_for_response(game) for game in games if game is not None]
        except Exception as e:
            current_app.logger.error(f"人気ゲーム取得エラー: {e}")
            return []
    
    def debug_steam_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Steam API検索のデバッグ用メソッド
        
        Args:
            query: 検索クエリ
            limit: 取得件数
            
        Returns:
            Dict[str, Any]: デバッグ情報
        """
        try:
            current_app.logger.info(f"=== Steam API検索デバッグ開始: '{query}' ===")
            
            if not self.steam_service:
                current_app.logger.error("Steam APIサービスが初期化されていません")
                return {
                    'query': query,
                    'limit': limit,
                    'total_results': 0,
                    'games': [],
                    'success': False,
                    'error': 'Steam APIサービスが初期化されていません'
                }
            
            steam_games = self._search_from_steam_api(query, limit)
            
            debug_info = {
                'query': query,
                'limit': limit,
                'total_results': len(steam_games),
                'games': steam_games[:limit],
                'success': True
            }
            
            current_app.logger.info(f"Steam API検索デバッグ完了: {len(steam_games)}件")
            return debug_info
            
        except Exception as e:
            current_app.logger.error(f"Steam API検索デバッグエラー: {e}")
            current_app.logger.exception("Steam API検索デバッグエラーの詳細:")
            return {
                'query': query,
                'limit': limit,
                'total_results': 0,
                'games': [],
                'success': False,
                'error': str(e)
            }
    
    def debug_epic_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Epic Games Store API検索のデバッグ用メソッド
        
        Args:
            query: 検索クエリ
            limit: 取得件数
            
        Returns:
            Dict[str, Any]: デバッグ情報
        """
        try:
            current_app.logger.info(f"=== Epic Games Store API検索デバッグ開始: '{query}' ===")
            
            if not self.epic_service:
                current_app.logger.error("Epic Games Store APIサービスが初期化されていません")
                return {
                    'query': query,
                    'limit': limit,
                    'total_results': 0,
                    'games': [],
                    'success': False,
                    'error': 'Epic Games Store APIサービスが初期化されていません'
                }
            
            epic_games = self._search_from_epic_api(query, limit)
            
            debug_info = {
                'query': query,
                'limit': limit,
                'total_results': len(epic_games),
                'games': epic_games[:limit],
                'success': True
            }
            
            current_app.logger.info(f"Epic Games Store API検索デバッグ完了: {len(epic_games)}件")
            return debug_info
            
        except Exception as e:
            current_app.logger.error(f"Epic Games Store API検索デバッグエラー: {e}")
            current_app.logger.exception("Epic Games Store API検索デバッグエラーの詳細:")
            return {
                'query': query,
                'limit': limit,
                'total_results': 0,
                'games': [],
                'success': False,
                'error': str(e)
            }
    
    def debug_external_apis(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        外部API検索の総合デバッグ用メソッド
        
        Args:
            query: 検索クエリ
            limit: 取得件数
            
        Returns:
            Dict[str, Any]: デバッグ情報
        """
        try:
            current_app.logger.info(f"=== 外部API総合デバッグ開始: '{query}' ===")
            
            # Steam API検索
            steam_debug = self.debug_steam_search(query, limit)
            
            # Epic Games Store API検索
            epic_debug = self.debug_epic_search(query, limit)
            
            # 結果をマージ
            all_external_games = steam_debug['games'] + epic_debug['games']
            
            debug_info = {
                'query': query,
                'limit': limit,
                'steam': steam_debug,
                'epic': epic_debug,
                'merged_results': {
                    'total_games': len(all_external_games),
                    'games': all_external_games
                },
                'success': steam_debug['success'] or epic_debug['success']
            }
            
            current_app.logger.info(f"外部API総合デバッグ完了: Steam={len(steam_debug['games'])}件, Epic={len(epic_debug['games'])}件, 合計={len(all_external_games)}件")
            return debug_info
            
        except Exception as e:
            current_app.logger.error(f"外部API総合デバッグエラー: {e}")
            return {
                'query': query,
                'limit': limit,
                'steam': {'success': False, 'error': str(e)},
                'epic': {'success': False, 'error': str(e)},
                'merged_results': {'total_games': 0, 'games': []},
                'success': False,
                'error': str(e)
            }
