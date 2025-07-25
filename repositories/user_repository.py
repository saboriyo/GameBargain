from typing import Optional, List
from sqlalchemy.orm import Session
from models import db, User

class UserRepository:
    """ユーザー情報のリポジトリクラス"""
    def __init__(self, session: Session = None):
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

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback() 