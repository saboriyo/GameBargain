"""
Models Package

GameBargainアプリケーションのデータモデルパッケージ
Flask-SQLAlchemyパターンを使用したデータベースモデルを提供します。
"""

# Flask-SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# ベースモデル（dbインスタンスを共有）
from .base import BaseModel

# 各モデル
from .user import User
from .game import Game
from .price import Price
from .favorite import Favorite
from .notification import Notification, NotificationType
from typing import Any, List, Optional, TYPE_CHECKING


__all__ = [
    # Flask-SQLAlchemy
    'db',
    # ベースモデル
    'BaseModel',
    # 各モデル
    'User',
    'Game', 
    'Price',
    'Favorite',
    'Notification',
    'NotificationType',
]
