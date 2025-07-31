from typing import Optional, List
from sqlalchemy.orm import Session
from models import db, User, Favorite, Game

class UserRepository:
    """ユーザー情報のリポジトリクラス"""
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.query(User).filter_by(id=user_id).first()

    def get_by_discord_id(self, discord_id: str) -> Optional[User]:
        return self.session.query(User).filter_by(discord_id=discord_id).first()

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.session.flush()
        return user

    def get_all(self) -> List[User]:
        return self.session.query(User).all()

    def get_user_favorites(self, user_id: int) -> List[Game]:
        """
        ユーザーのお気に入りゲーム一覧を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            List[Game]: お気に入りゲーム一覧
        """
        return self.session.query(Game).join(Favorite).filter(
            Favorite.user_id == user_id
        ).order_by(db.desc(Favorite.created_at)).all()

    def is_game_favorited(self, user_id: int, game_id: int) -> bool:
        """
        ゲームがユーザーのお気に入りに追加されているかチェック
        
        Args:
            user_id: ユーザーID
            game_id: ゲームID
            
        Returns:
            bool: お気に入りに追加されている場合True
        """
        favorite = self.session.query(Favorite).filter_by(
            user_id=user_id,
            game_id=game_id
        ).first()
        return favorite is not None

    def add_favorite(self, user_id: int, game_id: int) -> Optional[Favorite]:
        """
        お気に入りを追加
        
        Args:
            user_id: ユーザーID
            game_id: ゲームID
            
        Returns:
            Optional[Favorite]: 追加されたお気に入り（既に存在する場合はNone）
        """
        # 既存チェック
        if self.is_game_favorited(user_id, game_id):
            return None
        
        favorite = Favorite(
            user_id=user_id,
            game_id=game_id
        )
        self.session.add(favorite)
        self.session.flush()
        return favorite

    def remove_favorite(self, user_id: int, game_id: int) -> bool:
        """
        お気に入りを削除
        
        Args:
            user_id: ユーザーID
            game_id: ゲームID
            
        Returns:
            bool: 削除に成功した場合True
        """
        favorite = self.session.query(Favorite).filter_by(
            user_id=user_id,
            game_id=game_id
        ).first()
        
        if favorite:
            self.session.delete(favorite)
            self.session.flush()
            return True
        return False

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()