"""
Store Model

ゲームストア情報を管理するモデル
"""

from datetime import datetime

def create_store_model(db):
    """SQLAlchemyのdbインスタンスを使ってStoreモデルを作成"""
    
    class Store(db.Model):
        __tablename__ = 'stores'
        
        store_id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), unique=True, nullable=False)
        display_name = db.Column(db.String(100), nullable=False)
        base_url = db.Column(db.String(255))
        api_endpoint = db.Column(db.String(255))
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        # リレーションシップ
        prices = db.relationship('Price', backref='store_info', lazy=True)
        
        def __repr__(self):
            return f'<Store {self.display_name}>'
    
    return Store
