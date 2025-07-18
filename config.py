"""
GameBargain Configuration Module

アプリケーションの設定を管理するモジュール
各環境（開発、本番、テスト）に応じた設定を提供します。
"""

import os
from dotenv import load_dotenv
from datetime import timedelta

# .envファイルを読み込み
load_dotenv()


class Config:
    """
    基本設定クラス
    
    全環境で共通する設定項目を定義します。
    機密情報は環境変数から取得し、デフォルト値を設定します。
    """
    
    # Flask基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # データベース設定
    DATABASE_URL_RAW = os.environ.get('DATABASE_URL') or 'sqlite:///gamebargain.db'
    
    # SQLiteの場合は絶対パスに変換
    if DATABASE_URL_RAW.startswith('sqlite:///'):
        db_path = DATABASE_URL_RAW.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            # プロジェクトルートからの相対パスを絶対パスに変換
            project_root = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(project_root, db_path)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL_RAW
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'check_same_thread': False} if SQLALCHEMY_DATABASE_URI.startswith('sqlite') else {}
    }
    
    # セッション設定
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_SECURE = False  # 開発環境ではFalse
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Redis設定（本番環境用）
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery設定（本番環境用）
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # API Key設定
    STEAM_API_KEY = os.environ.get('STEAM_API_KEY')
    EPIC_GAMES_API_KEY = os.environ.get('EPIC_GAMES_API_KEY')
    RAPID_API_KEY = os.environ.get('RAPID_API_KEY')
    
    # Discord設定
    DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
    DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
    DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI') or 'http://localhost:8000/auth/discord/callback'
    
    # メール設定
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # アプリケーション固有設定
    PRICE_UPDATE_INTERVAL = int(os.environ.get('PRICE_UPDATE_INTERVAL', 3600))  # 1時間
    MAX_FAVORITES_PER_USER = int(os.environ.get('MAX_FAVORITES_PER_USER', 100))
    NOTIFICATION_BATCH_SIZE = int(os.environ.get('NOTIFICATION_BATCH_SIZE', 50))
    
    # ログ設定
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # レート制限設定
    STEAM_API_RATE_LIMIT = int(os.environ.get('STEAM_API_RATE_LIMIT', 10))  # requests per second
    EPIC_API_RATE_LIMIT = int(os.environ.get('EPIC_API_RATE_LIMIT', 5))
    
    # キャッシュ設定
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5分


class DevelopmentConfig(Config):
    """
    開発環境設定
    
    デバッグモードを有効にし、開発に便利な設定を行います。
    """
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    
    # 開発環境用のより短いキャッシュ時間
    CACHE_DEFAULT_TIMEOUT = 60  # 1分


class ProductionConfig(Config):
    """
    本番環境設定
    
    セキュリティを重視した設定を行います。
    """
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # より長いキャッシュ時間
    CACHE_DEFAULT_TIMEOUT = 600  # 10分


class TestingConfig(Config):
    """
    テスト環境設定
    
    テスト実行時に使用する設定です。
    インメモリデータベースを使用し、CSRF保護を無効にします。
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'null'  # キャッシュを無効化


# 設定選択
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
