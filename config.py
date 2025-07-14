"""
GameBargain Configuration Module

アプリケーションの設定を管理するモジュール
"""

import os
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """基本設定クラス"""
    
    # Flask基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///data/gamebargain.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis設定
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery設定
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
    DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI') or 'http://localhost:5000/auth/discord/callback'
    
    # メール設定
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # アプリケーション固有設定
    PRICE_UPDATE_INTERVAL = int(os.environ.get('PRICE_UPDATE_INTERVAL', 3600))
    MAX_FAVORITES_PER_USER = int(os.environ.get('MAX_FAVORITES_PER_USER', 100))
    NOTIFICATION_BATCH_SIZE = int(os.environ.get('NOTIFICATION_BATCH_SIZE', 50))
    
    # ログ設定
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')


class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 設定選択
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
