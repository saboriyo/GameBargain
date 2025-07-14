"""
Favorite Model

お気に入り情報を管理するモデル
"""

from datetime import datetime

def create_favorite_model(db):
    """SQLAlchemyのdbインスタンスを使ってFavoriteモデルを作成"""
    
    class Favorite(db.Model):
        __tablename__ = 'user_favorites'
        
        favorite_id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
        game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        # ユニークインデックス（同じユーザーが同じゲームを複数回お気に入りできないように）
        __table_args__ = (db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_favorite'),)
        
        def __repr__(self):
            return f'<Favorite {self.user.username} - {self.game.title}>'
    
    return Favorite
