"""
Favorite Model

お気に入りゲーム管理モデル
ユーザーのお気に入りゲームと通知設定を管理します。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Any, TYPE_CHECKING, Union
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint, Index
from sqlalchemy.types import Integer, Boolean, Numeric
from sqlalchemy.orm import relationship
from models import db

# 型チェック時のみインポート（循環インポート回避）
if TYPE_CHECKING:
    from .user import User
    from .game import Game


class Favorite(db.Model):
    """
    お気に入りモデル (設計書 3.3.4 準拠)
    
    ユーザーがお気に入り登録したゲームの管理を行います。
    価格通知の閾値設定も含みます。
    """
    __tablename__ = 'user_favorites'
    
    # プライマリキー
    id = Column(Integer, primary_key=True, index=True)
    
    # 外部キー
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    notification_enabled = Column(Boolean, default=True, index=True)
    price_threshold = Column(Numeric(10, 2))  # 通知する価格閾値
    
    # タイムスタンプ
    created_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'game_id', name='unique_user_game_favorite'),
        Index('idx_user_favorites_user_id', 'user_id'),
    )
    
    # リレーションシップ（型注釈付き）
    if TYPE_CHECKING:
        user: 'User'
        game: 'Game'
    else:
        user = relationship('User', back_populates='favorites')
        game = relationship('Game', back_populates='favorites')
    
    def __init__(self, user_id: int, game_id: int, **kwargs):
        """
        お気に入りの初期化
        
        Args:
            user_id: ユーザーID
            game_id: ゲームID
            **kwargs: その他のオプション
        """
        # setattr を使用してColumn属性への代入エラーを回避
        setattr(self, 'user_id', user_id)
        setattr(self, 'game_id', game_id)
        setattr(self, 'notification_enabled', kwargs.get('notification_enabled', True))
        setattr(self, 'price_threshold', kwargs.get('price_threshold'))
        setattr(self, 'created_at', kwargs.get('created_at', datetime.now(timezone.utc)))
    
    def set_price_threshold(self, threshold: Optional[Decimal]) -> None:
        """
        価格通知閾値を設定
        
        Args:
            threshold: 通知する価格閾値
        """
        setattr(self, 'price_threshold', threshold)
        
        # 閾値が設定された場合は自動的に通知を有効化
        if threshold is not None:
            setattr(self, 'notification_enabled', True)
    
    def should_notify_price_drop(self, current_price: Decimal) -> bool:
        """
        価格下落通知が必要かチェック
        
        Args:
            current_price: 現在価格
            
        Returns:
            bool: 通知が必要な場合True
        """
        # 型安全な条件チェック
        if not bool(self.notification_enabled):
            return False
        
        if self.price_threshold is None:
            return False
        
        # Decimalと比較する際は適切にキャスト
        threshold_value = Decimal(str(self.price_threshold))
        return current_price <= threshold_value
    
    def toggle_notification(self) -> bool:
        """
        通知設定をトグル
        
        Returns:
            bool: 変更後の通知設定状態
        """
        current_value = bool(getattr(self, 'notification_enabled', False))
        new_value = not current_value
        setattr(self, 'notification_enabled', new_value)
        return new_value
    
    def update_threshold_from_current_price(self, discount_percentage: int = 10) -> None:
        """
        現在価格から指定割引率で閾値を自動設定
        
        Args:
            discount_percentage: 割引率（デフォルト10%）
        """
        # ゲームの現在最安値を取得
        if hasattr(self, 'game') and self.game:
            lowest_price = self.game.get_lowest_price()
            if lowest_price:
                discount_factor = (100 - discount_percentage) / 100
                self.price_threshold = lowest_price * Decimal(str(discount_factor))
    
    def get_threshold_status(self) -> dict:
        """
        閾値設定の状況を取得
        
        Returns:
            dict: 閾値設定情報
        """
        # 属性値を一時変数に格納して型安全にアクセス
        threshold = getattr(self, 'price_threshold', None)
        created = getattr(self, 'created_at', None)
        notification_enabled = getattr(self, 'notification_enabled', False)
        
        status = {
            'has_threshold': threshold is not None,
            'threshold_value': float(threshold) if threshold is not None else None,
            'notification_enabled': bool(notification_enabled),
            'created_at': created.isoformat() if created is not None else None
        }
        
        # ゲームの現在価格と比較
        if hasattr(self, 'game') and self.game and threshold is not None:
            current_lowest = self.game.get_lowest_price()
            if current_lowest:
                status['current_lowest_price'] = float(current_lowest)
                status['threshold_met'] = current_lowest <= threshold
                status['discount_needed'] = max(0, float(current_lowest - threshold))
        
        return status
    
    def is_recent(self, days: int = 7) -> bool:
        """
        最近追加されたお気に入りかチェック
        
        Args:
            days: 判定する日数
            
        Returns:
            bool: 指定日数以内に追加された場合True
        """
        created = getattr(self, 'created_at', None)
        if created is None:
            return False
        
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
        return bool(created > threshold_date)
    
    def get_formatted_threshold(self) -> str:
        """
        フォーマット済み閾値文字列を取得
        
        Returns:
            str: フォーマット済み閾値
        """
        threshold = getattr(self, 'price_threshold', None)
        if threshold is None:
            return "未設定"
        
        return f"¥{threshold:,.0f}" if threshold % 1 == 0 else f"¥{threshold:,.2f}"
    
    def __repr__(self) -> str:
        """
        文字列表現
        
        Returns:
            str: お気に入りの文字列表現
        """
        return f'<Favorite user_id={self.user_id} game_id={self.game_id} threshold={self.get_formatted_threshold()}>'
    
    @staticmethod
    def validate_threshold(threshold: Optional[Union[int, float, Decimal]]) -> Optional[Decimal]:
        """
        価格閾値のバリデーション
        
        Args:
            threshold: 閾値（None、数値）
            
        Returns:
            Optional[Decimal]: 正規化された閾値、無効な場合はNone
            
        Raises:
            ValueError: 無効な閾値の場合
        """
        from decimal import InvalidOperation
        
        if threshold is None:
            return None
        
        try:
            threshold_decimal = Decimal(str(threshold))
            if threshold_decimal < 0:
                raise ValueError("価格閾値は0以上である必要があります")
            if threshold_decimal > Decimal('999999'):
                raise ValueError("価格閾値は999,999円以下である必要があります")
            return threshold_decimal.quantize(Decimal('0.01'))
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"無効な価格閾値です: {e}")
    
    @classmethod
    def create_favorite(cls, user_id: int, game_id: int, 
                       price_threshold: Optional[Union[int, float, Decimal]] = None,
                       notification_enabled: bool = True) -> 'Favorite':
        """
        お気に入り作成のクラスメソッド
        
        Args:
            user_id: ユーザーID
            game_id: ゲームID
            price_threshold: 価格閾値
            notification_enabled: 通知設定
            
        Returns:
            Favorite: 作成されたお気に入りインスタンス
            
        Raises:
            ValueError: 無効なパラメータの場合
        """
        validated_threshold = cls.validate_threshold(price_threshold)
        
        return cls(
            user_id=user_id,
            game_id=game_id,
            price_threshold=validated_threshold,
            notification_enabled=notification_enabled,
            created_at=datetime.now(timezone.utc)
        )
