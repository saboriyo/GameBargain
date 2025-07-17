"""
Base Model

GameBargainアプリケーションの共通ベースモデル
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime


class BaseModel:
    """
    全モデル共通のベースクラス
    
    Attributes:
        id: プライマリキー
        created_at: 作成日時
        updated_at: 更新日時
    """
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    def to_dict(self) -> dict:
        """
        モデルインスタンスを辞書形式に変換
        
        Returns:
            dict: モデルの辞書表現
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """
        文字列表現
        
        Returns:
            str: モデルの文字列表現
        """
        class_name = self.__class__.__name__
        return f'<{class_name} id={getattr(self, "id", None)}>'
