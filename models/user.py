"""
User Model

ユーザー情報を管理するモデル
Discord認証とユーザー設定を統合管理します。
"""

from datetime import datetime
from flask_login import UserMixin
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from models import db

# 型チェック時のみインポート（循環参照回避）
if TYPE_CHECKING:
    from .favorite import Favorite
    from .notification import Notification


class User(UserMixin, db.Model):
    """
    ユーザーモデル (設計書 3.3.1 準拠)
    
    Discord認証を使用したユーザー情報の管理を行います。
    OAuth2トークンやプリファレンス設定を含みます。
    """
    __tablename__ = 'users'
    
    # プライマリキー
    id = Column(Integer, primary_key=True, index=True)
    
    # Discord認証情報
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    discriminator = Column(String(4))  # Discord#0000形式のタグ
    avatar_url = Column(String(255))
    email = Column(String(255))
    access_token = Column(Text)  # 暗号化推奨
    refresh_token = Column(Text)  # 暗号化推奨
    token_expires_at = Column(DateTime)
    guild_ids = Column(Text)  # JSON文字列として保存
    is_active = Column(Boolean, default=True, index=True)
    last_login_at = Column(DateTime, index=True)
    preferences = Column(Text)  # JSON文字列として保存
    
    # タイムスタンプ
    created_at = Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # リレーションシップ（型チェック時のみ型注釈）
    if TYPE_CHECKING:
        favorites: List['Favorite']
        notifications: List['Notification']
    else:
        favorites = relationship('Favorite', back_populates='user', cascade='all, delete-orphan')
        notifications = relationship('Notification', back_populates='user')
    
    def get_id(self) -> str:
        """
        Flask-Login required method
        
        Returns:
            str: ユーザーID文字列
        """
        return str(getattr(self, 'id', ''))
    
    def get_guild_ids(self) -> List[str]:
        """
        ギルドIDリストを取得
        
        Returns:
            List[str]: DiscordギルドIDのリスト
        """
        guild_ids = getattr(self, 'guild_ids', None)
        if not guild_ids:
            return []
        try:
            return json.loads(guild_ids)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_guild_ids(self, guild_list: List[str]) -> None:
        """
        ギルドIDリストを設定
        
        Args:
            guild_list: DiscordギルドIDのリスト
        """
        setattr(self, 'guild_ids', json.dumps(guild_list))
    
    def get_preferences(self) -> Dict[str, Any]:
        """
        プリファレンスを取得
        
        Returns:
            Dict[str, Any]: ユーザープリファレンス辞書
        """
        preferences = getattr(self, 'preferences', None)
        if not preferences:
            return {}
        try:
            return json.loads(preferences)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_preferences(self, prefs_dict: Dict[str, Any]) -> None:
        """
        プリファレンスを設定
        
        Args:
            prefs_dict: ユーザープリファレンス辞書
        """
        setattr(self, 'preferences', json.dumps(prefs_dict))
    
    def update_last_login(self) -> None:
        """
        最終ログイン時刻を更新
        """
        setattr(self, 'last_login_at', datetime.utcnow())
    
    def is_token_expired(self) -> bool:
        """
        アクセストークンが期限切れかチェック
        
        Returns:
            bool: 期限切れの場合True
        """
        token_expires_at = getattr(self, 'token_expires_at', None)
        if not token_expires_at:
            return True
        return datetime.utcnow() > token_expires_at
    
    def __repr__(self) -> str:
        """
        文字列表現
        
        Returns:
            str: ユーザーの文字列表現
        """
        username = getattr(self, 'username', 'Unknown')
        discriminator = getattr(self, 'discriminator', None)
        discriminator_str = f"#{discriminator}" if discriminator else ""
        return f'<User {username}{discriminator_str}>'


# 後方互換性のためのファクトリー関数
def create_user_model(db):
    """
    後方互換性のためのファクトリー関数
    
    Args:
        db: SQLAlchemyインスタンス（使用されない）
        
    Returns:
        class: Userモデルクラス
    """
    return User  # type: ignore 

# 型安全のためColumn属性への代入は避け、setattrを使用
