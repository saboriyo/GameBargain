"""
Web Package

GameBargain Webアプリケーションの実装パッケージ
Flask blueprintとルーティングを管理します。
"""

from .routes import main_bp
from .auth import auth_bp
from .api import api_bp

__all__ = [
    'main_bp',
    'auth_bp', 
    'api_bp'
]
