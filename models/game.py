"""
Game Model

ゲーム情報を管理するモデル
"""

from datetime import datetime

def create_game_model(db):
    """SQLAlchemyのdbインスタンスを使ってGameモデルを作成"""
    
    class Game(db.Model):
        __tablename__ = 'games'
        
        game_id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        developer = db.Column(db.String(100))
        steam_app_id = db.Column(db.String(20), unique=True)
        image_url = db.Column(db.String(255))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        # リレーションシップ
        prices = db.relationship('Price', backref='game', lazy=True)
        favorites = db.relationship('Favorite', backref='game', lazy=True)
        
        def __repr__(self):
            return f'<Game {self.title}>'
        
        def get_latest_price(self, store='steam'):
            """指定ストアの最新価格を取得"""
            latest_price = self.prices.filter_by(store=store).order_by(
                self.prices.created_at.desc()
            ).first()
            return latest_price
    
    return Game
