"""
User Model

ユーザー情報を管理するモデル
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# app.pyからimportするため、ここではdbを直接importしない
# from app import db の代わりに、必要に応じてdbを渡す形にする

class User(UserMixin):
    """ユーザーモデル"""
    
    def __init__(self, db):
        self.db = db
    
    # テーブル定義は後でSQLAlchemyのdeclarative_baseで行う

# SQLAlchemy使用時のテーブル定義用のクラス
def create_user_model(db):
    """SQLAlchemyのdbインスタンスを使ってUserモデルを作成"""
    
    class User(UserMixin, db.Model):
        __tablename__ = 'users'
        
        user_id = db.Column(db.Integer, primary_key=True)
        discord_id = db.Column(db.String(20), unique=True, nullable=False)
        username = db.Column(db.String(100), nullable=False)
        avatar_url = db.Column(db.String(255))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        # リレーションシップ
        favorites = db.relationship('Favorite', backref='user', lazy=True)
        notifications = db.relationship('Notification', backref='user', lazy=True)
        
        def get_id(self):
            """Flask-Login required method"""
            return str(self.user_id)
        
        def __repr__(self):
            return f'<User {self.username}>'
    
    return User
