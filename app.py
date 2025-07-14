"""
GameBargain Main Application

ゲーム価格比較・監視サービスのメインアプリケーション
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from celery import Celery

from config import config

# Extensionのインスタンス化
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def make_celery(app):
    """Celeryインスタンスの作成"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Flask application contextでタスクを実行"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(config_name=None):
    """Application Factory Pattern"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Extensionの初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # ログイン設定
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    
    # Blueprintの登録
    from web.routes import main_bp
    from web.auth import auth_bp
    from web.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app


# アプリケーションインスタンスの作成
app = create_app()
celery = make_celery(app)

# Modelsのインポート（テーブル作成のため）
from models import User, Game, Store, Price, Favorite, Notification


@login_manager.user_loader
def load_user(user_id):
    """ユーザーローダー"""
    return User.query.get(int(user_id))


if __name__ == '__main__':
    with app.app_context():
        # テーブル作成
        db.create_all()
    
    # アプリケーション起動
    app.run(debug=True, host='0.0.0.0', port=5000)
