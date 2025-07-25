from typing import Optional, List
from sqlalchemy.orm import Session
from models import db, Price, User

class PriceRepository:
    """価格情報のリポジトリクラス"""
    def __init__(self, session: Session = None):
        self.session = session or db.session

    def get_latest_prices(self, game_id: int) -> List[Price]:
        return self.session.query(Price).filter_by(game_id=game_id).order_by(Price.created_at.desc()).all()

    def save(self, price: Price) -> Price:
        self.session.add(price)
        self.session.flush()
        return price

    def get_users_for_notification(self, game_id: int) -> List[User]:
        # 通知対象ユーザー取得（例: お気に入りかつ通知ONのユーザー）
        from models.favorite import Favorite
        return self.session.query(User).join(Favorite).filter(
            Favorite.game_id == game_id,
            Favorite.notification_enabled == True
        ).all()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback() 