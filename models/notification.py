"""
Notification Model

通知情報を管理するモデル
"""

from datetime import datetime

def create_notification_model(db):
    """SQLAlchemyのdbインスタンスを使ってNotificationモデルを作成"""
    
    class Notification(db.Model):
        __tablename__ = 'notifications'
        
        notification_id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
        game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'))
        notification_type = db.Column(db.String(50))
        title = db.Column(db.String(200))
        message = db.Column(db.Text)
        is_sent = db.Column(db.Boolean, default=False)
        sent_at = db.Column(db.DateTime)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<Notification {self.title}>'
        
        def mark_as_sent(self):
            """通知を送信済みとしてマーク"""
            self.is_sent = True
            self.sent_at = datetime.utcnow()
    
    return Notification
