"""
Notification Model

通知情報を管理するモデル
Discord通知やメール通知の履歴と状態を管理します。
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Text, Index
from sqlalchemy.orm import relationship
from models import db

# 型チェック時のみインポート（循環参照回避）
if TYPE_CHECKING:
    from .user import User
    from .game import Game


class NotificationType(Enum):
    """通知タイプの列挙"""
    PRICE_DROP = "price_drop"
    SALE_START = "sale_start" 
    SALE_END = "sale_end"
    FREE_GAME = "free_game"
    THRESHOLD_MET = "threshold_met"
    RECOMMENDATION = "recommendation"


class Notification(db.Model):
    """
    通知モデル (設計書 3.3.6 準拠)
    
    Discord通知やメール通知の履歴と送信状態を管理します。
    ユーザーごとの通知設定に基づいて通知を制御します。
    """
    __tablename__ = 'notifications'
    
    # プライマリキー
    id = Column(Integer, primary_key=True, index=True)
    
    # 外部キー
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=True)
    notification_type = Column(String(50))  # NotificationType enum values
    title = Column(String(200))
    message = Column(Text)
    discord_channel_id = Column(String(20))
    is_sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime)
    priority = Column(Integer, default=1)  # 1=低, 2=通常, 3=高
    
    # タイムスタンプ
    created_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index('idx_notifications_user_type', 'user_id', 'notification_type'),
        Index('idx_notifications_sent_priority', 'is_sent', 'priority'),
    )
    
    # リレーションシップ（型チェック時のみ型注釈）
    if TYPE_CHECKING:
        user: Optional['User']
        game: Optional['Game']
    else:
        user = relationship('User', back_populates='notifications')
        game = relationship('Game')  # Gameモデルには通知のリレーションシップは不要
    
    def __init__(self, notification_type: str, title: str, message: str, **kwargs: Any) -> None:
        """
        コンストラクタ
        
        Args:
            notification_type: 通知タイプ
            title: 通知タイトル
            message: 通知メッセージ
            **kwargs: その他の属性
        """
        super().__init__()
        setattr(self, 'notification_type', notification_type)
        setattr(self, 'title', title)
        setattr(self, 'message', message)
        
        # その他の属性を設定
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def mark_as_sent(self) -> None:
        """
        通知を送信済みとしてマーク
        """
        setattr(self, 'is_sent', True)
        setattr(self, 'sent_at', datetime.now(timezone.utc))
    
    def increment_retry(self) -> None:
        """
        リトライ回数を増加
        """
        retry_count = getattr(self, 'retry_count', 0)
        setattr(self, 'retry_count', retry_count + 1)
        setattr(self, 'last_retry_at', datetime.now(timezone.utc))
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """
        リトライ可能かチェック
        
        Args:
            max_retries: 最大リトライ回数
            
        Returns:
            bool: リトライ可能な場合True
        """
        is_sent = getattr(self, 'is_sent', False)
        retry_count = getattr(self, 'retry_count', 0)
        return not is_sent and retry_count < max_retries
    
    def get_priority_label(self) -> str:
        """
        優先度ラベルを取得
        
        Returns:
            str: 優先度ラベル
        """
        priority = getattr(self, 'priority', 1)
        priority_map = {1: "低", 2: "通常", 3: "高"}
        return priority_map.get(priority, "不明")
    
    def to_discord_embed(self) -> Dict[str, Any]:
        """
        Discord Embed形式に変換
        
        Returns:
            Dict[str, Any]: Discord Embed辞書
        """
        title = getattr(self, 'title', '')
        message = getattr(self, 'message', '')
        notification_type = getattr(self, 'notification_type', '')
        
        # 通知タイプに応じた色設定
        color_map = {
            NotificationType.PRICE_DROP.value: 0x00ff00,  # 緑
            NotificationType.SALE_START.value: 0xff9900,  # オレンジ
            NotificationType.SALE_END.value: 0xff0000,    # 赤
            NotificationType.FREE_GAME.value: 0x9900ff,   # 紫
            NotificationType.THRESHOLD_MET.value: 0x00ff00, # 緑
            NotificationType.RECOMMENDATION.value: 0x0099ff, # 青
        }
        
        embed = {
            "title": title,
            "description": message,
            "color": color_map.get(notification_type, 0x808080),  # デフォルトグレー
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # ゲーム情報があれば追加
        if hasattr(self, 'game') and self.game:
            game_title = getattr(self.game, 'title', 'Unknown Game')
            embed["footer"] = {"text": f"ゲーム: {game_title}"}
            
            image_url = getattr(self.game, 'image_url', None)
            if image_url:
                embed["thumbnail"] = {"url": image_url}
        
        return embed
    
    def __repr__(self) -> str:
        """
        文字列表現
        
        Returns:
            str: 通知の文字列表現
        """
        title = getattr(self, 'title', 'Unknown')
        notification_type = getattr(self, 'notification_type', 'Unknown')
        is_sent = getattr(self, 'is_sent', False)
        status = "送信済み" if is_sent else "未送信"
        return f'<Notification {notification_type}: {title} ({status})>'

