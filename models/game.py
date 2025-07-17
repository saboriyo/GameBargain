"""
Game Model

ゲーム情報を管理するモデル
Flask-SQLAlchemyパターン
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, Boolean, DECIMAL, Integer
from sqlalchemy.orm import relationship
from models import db


class Game(db.Model):
    """
    ゲーム情報モデル
    
    複数のプラットフォーム（Steam、Epic Games Store等）からの
    ゲーム情報を統合して管理
    """
    
    __tablename__ = 'games'
    
    # プライマリキー
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本情報
    title = Column(String(200), nullable=False, index=True, comment='ゲームタイトル')
    normalized_title = Column(String(200), nullable=True, index=True, comment='正規化されたタイトル（検索用）')
    developer = Column(String(100), nullable=True, comment='開発者')
    publisher = Column(String(100), nullable=True, comment='パブリッシャー')
    
    # プラットフォーム固有ID
    steam_appid = Column(String(20), nullable=True, unique=True, index=True, comment='Steam App ID')
    epic_game_id = Column(String(50), nullable=True, unique=True, index=True, comment='Epic Games Store ID')
    
    # メディア情報
    image_url = Column(String(255), nullable=True, comment='ゲーム画像URL')
    steam_url = Column(String(500), nullable=True, comment='Steam商品ページURL')
    
    # 詳細情報
    description = Column(Text, nullable=True, comment='ゲーム説明')
    genres = Column(Text, nullable=True, comment='ジャンル（JSON文字列）')
    release_date = Column(Date, nullable=True, comment='リリース日')
    platforms = Column(Text, nullable=True, comment='対応プラットフォーム（カンマ区切り）')
    
    # 評価情報
    steam_rating = Column(DECIMAL(3, 2), nullable=True, comment='Steam評価（0-100）')
    metacritic_score = Column(Integer, nullable=True, comment='Metacriticスコア')
    
    # 価格情報（最新の価格を保持）
    current_price = Column(DECIMAL(10, 2), nullable=True, comment='現在価格')
    original_price = Column(DECIMAL(10, 2), nullable=True, comment='元価格')
    discount_percent = Column(Integer, nullable=True, comment='割引率')
    
    # ステータス
    is_active = Column(Boolean, default=True, nullable=False, comment='アクティブ状態')
    
    # タイムスタンプ
    created_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # リレーションシップ
    prices = relationship('Price', back_populates='game', cascade='all, delete-orphan')
    favorites = relationship('Favorite', back_populates='game', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Game {self.title}>'
    
    def to_dict(self):
        """辞書形式に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'normalized_title': self.normalized_title,
            'developer': self.developer,
            'publisher': self.publisher,
            'steam_appid': self.steam_appid,
            'epic_game_id': self.epic_game_id,
            'image_url': self.image_url,
            'steam_url': self.steam_url,
            'description': self.description,
            'genres': getattr(self, 'genres', None),
            'release_date': getattr(self, 'release_date').isoformat() if getattr(self, 'release_date') else None,
            'steam_rating': float(getattr(self, 'steam_rating')) if getattr(self, 'steam_rating') is not None else None,
            'metacritic_score': self.metacritic_score,
            'current_price': float(getattr(self, 'current_price')) if getattr(self, 'current_price') is not None else None,
            'original_price': float(getattr(self, 'original_price')) if getattr(self, 'original_price') is not None else None,
            'discount_percent': self.discount_percent,
            'is_active': self.is_active,
            'created_at': getattr(self, 'created_at').isoformat() if getattr(self, 'created_at') else None,
            'updated_at': getattr(self, 'updated_at').isoformat() if getattr(self, 'updated_at') else None
        }
