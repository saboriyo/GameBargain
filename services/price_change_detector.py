"""
Price Change Detector Service

価格変動を検出し、通知を送信するサービス
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
import logging

from models import db, Game, Price, User
from repositories.game_repository import GameRepository
from repositories.price_repository import PriceRepository
from repositories.user_repository import UserRepository
from services.steam_service import SteamAPIService


logger = logging.getLogger(__name__)


class PriceChange:
    """価格変動情報を表すクラス"""
    
    def __init__(self, game_id: int, game_title: str, store: str, 
                 old_price: Optional[Decimal], new_price: Decimal, 
                 change_type: str, change_percent: float = 0.0):
        self.game_id = game_id
        self.game_title = game_title
        self.store = store
        self.old_price = old_price
        self.new_price = new_price
        self.change_type = change_type  # 'increase', 'decrease', 'new', 'sale_start', 'sale_end'
        self.change_percent = change_percent
        self.detected_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f'<PriceChange {self.game_title} ({self.store}): {self.old_price} -> {self.new_price} ({self.change_type})>'


class PriceChangeDetector:
    """価格変動検出サービス"""
    
    def __init__(self):
        self.game_repository = GameRepository()
        self.price_repository = PriceRepository()
        self.user_repository = UserRepository()
        self.steam_service = SteamAPIService()
        
    def detect_price_changes(self) -> List[PriceChange]:
        """
        価格変動を検出
        
        Returns:
            List[PriceChange]: 検出された価格変動のリスト
        """
        price_changes = []
        
        try:
            # 1. 価格データが存在しないゲームを検出
            games_without_prices = self._get_games_without_prices()
            logger.info(f"価格データが存在しないゲーム数: {len(games_without_prices)}")
            
            # 2. 価格データが存在しないゲームの価格を取得
            for game in games_without_prices:
                new_prices = self._fetch_game_prices(game)
                for price_data in new_prices:
                    price_change = PriceChange(
                        game_id=getattr(game, 'id'),
                        game_title=getattr(game, 'title'),
                        store=price_data['store'],
                        old_price=None,
                        new_price=price_data['price'],
                        change_type='new'
                    )
                    price_changes.append(price_change)
            
            # 3. 既存の価格データとの比較（将来的に実装）
            # TODO: 既存価格との比較機能を追加
            
            logger.info(f"検出された価格変動数: {len(price_changes)}")
            return price_changes
            
        except Exception as e:
            logger.error(f"価格変動検出エラー: {e}")
            return []
    
    def process_price_changes(self) -> None:
        """
        価格変動を処理（価格更新と通知送信）
        """
        try:
            price_changes = self.detect_price_changes()
            
            if not price_changes:
                logger.info("処理する価格変動がありません")
                return
            
            # 価格データを更新
            self.update_prices(price_changes)
            
            # 通知送信（将来的に実装）
            # TODO: NotificationServiceを使用した通知機能を追加
            
            logger.info(f"価格変動処理完了: {len(price_changes)}件")
            
        except Exception as e:
            logger.error(f"価格変動処理エラー: {e}")
    
    def update_prices(self, price_changes: List[PriceChange]) -> None:
        """
        価格データを更新
        
        Args:
            price_changes: 価格変動のリスト
        """
        try:
            for change in price_changes:
                if change.change_type == 'new':
                    # 新しい価格データを作成
                    price = Price()
                    setattr(price, 'game_id', change.game_id)
                    setattr(price, 'store', change.store)
                    setattr(price, 'regular_price', change.new_price)
                    setattr(price, 'sale_price', None)
                    setattr(price, 'discount_rate', 0)
                    setattr(price, 'currency', 'JPY')
                    setattr(price, 'is_on_sale', False)
                    
                    self.price_repository.save(price)
                    logger.debug(f"新規価格データ保存: {change}")
                
                # TODO: 他の変動タイプの処理を追加
            
            self.price_repository.commit()
            logger.info(f"価格データ更新完了: {len(price_changes)}件")
            
        except Exception as e:
            self.price_repository.rollback()
            logger.error(f"価格データ更新エラー: {e}")
            raise
    
    def _get_games_without_prices(self) -> List[Game]:
        """
        価格データが存在しないゲームを取得
        
        Returns:
            List[Game]: 価格データが存在しないゲームのリスト（最大10件）
        """
        try:
            # GameテーブルとPriceテーブルを結合して、価格データが存在しないゲームを取得
            games_with_prices_subquery = db.session.query(Price.game_id).distinct()
            games_without_prices = db.session.query(Game).filter(
                ~Game.id.in_(games_with_prices_subquery),
                Game.is_active == True
            ).filter(Game.steam_appid.isnot(None)).limit(10).all()  # Steam App IDが存在するもののみ、最大10件
            
            return games_without_prices
            
        except Exception as e:
            logger.error(f"価格データなしゲーム取得エラー: {e}")
            return []
    
    def _fetch_game_prices(self, game: Game) -> List[Dict[str, Any]]:
        """
        ゲームの価格情報を外部APIから取得
        
        Args:
            game: ゲーム情報
            
        Returns:
            List[Dict[str, Any]]: 価格情報のリスト
        """
        prices = []
        game_title = getattr(game, 'title', 'Unknown')
        
        try:
            # Steam価格を取得
            steam_appid = getattr(game, 'steam_appid', None)
            if steam_appid:
                logger.debug(f"Steam価格取得開始: {game_title} (App ID: {steam_appid})")
                steam_price = self.steam_service.get_game_price(steam_appid)
                
                if steam_price and steam_price.get('price') is not None:
                    price_data = {
                        'store': 'steam',
                        'price': Decimal(str(steam_price.get('price', 0))),
                        'original_price': Decimal(str(steam_price.get('original_price', steam_price.get('price', 0)))),
                        'discount_rate': steam_price.get('discount_percent', 0),
                        'is_on_sale': steam_price.get('discount_percent', 0) > 0
                    }
                    prices.append(price_data)
                    logger.info(f"Steam価格取得成功: {game_title} - ¥{price_data['price']}")
                else:
                    logger.warning(f"Steam価格取得失敗: {game_title} (App ID: {steam_appid}) - APIからの応答が無効")
            else:
                logger.warning(f"Steam App ID未設定: {game_title}")
            
            # TODO: 他のストア（Epic Games Store等）の価格取得を追加
            
            logger.debug(f"取得した価格情報: {game_title} - {len(prices)}件")
            return prices
            
        except Exception as e:
            logger.error(f"価格取得エラー ({game_title}): {e}")
            return []
    
    def _determine_change_type(self, old_price: Optional[Decimal], new_price: Decimal, 
                             old_sale: bool = False, new_sale: bool = False) -> str:
        """
        価格変動タイプを判定
        
        Args:
            old_price: 旧価格
            new_price: 新価格
            old_sale: 旧セール状態
            new_sale: 新セール状態
            
        Returns:
            str: 変動タイプ
        """
        if old_price is None:
            return 'new'
        
        if not old_sale and new_sale:
            return 'sale_start'
        elif old_sale and not new_sale:
            return 'sale_end'
        elif new_price > old_price:
            return 'increase'
        elif new_price < old_price:
            return 'decrease'
        else:
            return 'no_change'
    
    def _get_users_to_notify(self, game_id: int) -> List[User]:
        """
        通知対象のユーザーを取得
        
        Args:
            game_id: ゲームID
            
        Returns:
            List[User]: 通知対象ユーザーのリスト
        """
        try:
            users = self.price_repository.get_users_for_notification(game_id)
            return users
        except Exception as e:
            logger.error(f"通知対象ユーザー取得エラー: {e}")
            return []
