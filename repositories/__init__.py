"""
Repositories Package

データアクセス層のパッケージ
モデルとサービス層の間の抽象化を提供します。
"""

from .game_repository import GameRepository

__all__ = [
    'GameRepository'
]
