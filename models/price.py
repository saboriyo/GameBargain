"""
Price Model

価格情報を管理するモデル
"""

from datetime import datetime

def create_price_model(db):
    """SQLAlchemyのdbインスタンスを使ってPriceモデルを作成"""
    
    class Price(db.Model):
        __tablename__ = 'prices'
        
        price_id = db.Column(db.Integer, primary_key=True)
        game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'), nullable=False)
        store = db.Column(db.String(20), nullable=False, default='steam')
        regular_price = db.Column(db.Numeric(10, 2))
        sale_price = db.Column(db.Numeric(10, 2))
        discount_rate = db.Column(db.Integer, default=0)
        is_on_sale = db.Column(db.Boolean, default=False)
        currency = db.Column(db.String(3), default='JPY')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<Price {self.game.title} - {self.store}: ¥{self.current_price}>'
        
        @property
        def current_price(self):
            """現在の価格（セール価格があればセール価格、なければ通常価格）"""
            return self.sale_price if self.is_on_sale and self.sale_price else self.regular_price
        
        @property
        def formatted_price(self):
            """フォーマットされた価格文字列"""
            price = self.current_price
            if price is None:
                return "価格情報なし"
            return f"¥{int(price):,}"
    
    return Price
