"""
GameBargain Models Package

このパッケージには、GameBargainアプリケーションのデータモデルが含まれています。
"""

def create_models(db):
    """dbインスタンスを使って全てのモデルクラスを作成"""
    from .user import create_user_model
    from .game import create_game_model
    from .store import create_store_model
    from .price import create_price_model
    from .favorite import create_favorite_model
    from .notification import create_notification_model
    
    # 各モデルクラスを作成
    User = create_user_model(db)
    Game = create_game_model(db)
    Store = create_store_model(db)
    Price = create_price_model(db)
    Favorite = create_favorite_model(db)
    Notification = create_notification_model(db)
    
    return {
        'User': User,
        'Game': Game,
        'Store': Store,
        'Price': Price,
        'Favorite': Favorite,
        'Notification': Notification
    }

# 後方互換性のため
User = None
Game = None
Store = None
Price = None
Favorite = None
Notification = None

__all__ = [
    'create_models',
    'User',
    'Game', 
    'Store',
    'Price',
    'Favorite',
    'Notification'
]
