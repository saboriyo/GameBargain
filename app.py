"""
GameBargain Main Application

ゲーム価格比較・監視サービスのメインアプリケーション
Discord Botと統合したFlaskアプリケーション
"""

import os
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from datetime import datetime
import logging
from typing import Optional
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# Configuration
from config import config
from models import db
from models import (
    User,
    Game,
    Price,
    Favorite,
    Notification
)

# Global extensions
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Application Factory Pattern
    
    Args:
        config_name: 設定名（development, production, testing）
        
    Returns:
        Flask: 設定済みFlaskアプリケーションインスタンス
    """
    app = Flask(__name__)
    
    # 設定の読み込み
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    config_name = str(config_name)
    app.config.from_object(config[config_name])
    
    # Extensions の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # ログイン設定
    login_manager.login_view = 'auth.login'  # type: ignore
    login_manager.login_message = 'ログインが必要です。'
    login_manager.login_message_category = 'info'
    
    # ログ設定
    setup_logging(app)
    
    # モデルの登録
    register_models(app)
    
    # ブループリントの登録
    register_blueprints(app)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    # データベースディレクトリの作成
    ensure_database_directory(app)
    
    with app.app_context():
        try:
            # データベースの初期化をスキップ（make create-dbを使用）
            database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if database_uri.startswith('sqlite:///'):
                db_path = database_uri.replace('sqlite:///', '')
                if not os.path.isabs(db_path):
                    db_path = os.path.join(app.root_path, db_path)
                
                # データベースファイルが存在しない場合は警告
                if not os.path.exists(db_path):
                    app.logger.warning(f"データベースファイルが見つかりません: {db_path}")
                    app.logger.warning("'make create-db' を実行してデータベースを作成してください")
                else:
                    app.logger.info(f"データベースファイルが見つかりました: {db_path}")
                    
                    # ファイルの権限とアクセス性をチェック
                    if os.access(db_path, os.R_OK | os.W_OK):
                        app.logger.info("データベースファイルへの読み書きアクセスが確認できました")
                    else:
                        app.logger.error("データベースファイルへのアクセス権限がありません")
                        
        except Exception as e:
            app.logger.error(f"データベース確認エラー: {e}")
            # アプリケーション起動は継続（データベースなしでも起動可能）
    
    # CLIコマンドの登録
    from cli_commands import register_commands
    register_commands(app)
    
    return app


def setup_logging(app: Flask) -> None:
    """
    ログ設定のセットアップ
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    if not app.debug:
        # ログディレクトリの作成
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # ファイルハンドラーの設定
        file_handler = logging.FileHandler('logs/gamebargain.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('GameBargain startup')


def ensure_database_directory(app: Flask) -> None:
    """
    データベースディレクトリの存在確認と作成
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    # SQLiteデータベースの場合のみ処理
    if database_uri.startswith('sqlite:///'):
        # sqlite:/// の後のパスを取得
        db_path = database_uri.replace('sqlite:///', '')
        
        # 絶対パスに変換
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, db_path)
        
        # データベースファイルのディレクトリを取得
        db_dir = os.path.dirname(db_path)
        
        # ディレクトリが存在しない場合は作成（空文字の場合も考慮）
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                app.logger.info(f"データベースディレクトリを作成しました: {db_dir}")
            except Exception as e:
                app.logger.error(f"データベースディレクトリ作成エラー: {e}")
                raise
        
        app.logger.info(f"データベースパス: {db_path}")
        app.logger.info(f"設定URI: {database_uri}")
        app.logger.info(f"ディレクトリ: {db_dir}")
        
        # ディレクトリが存在するか最終確認
        if db_dir and os.path.exists(db_dir):
            app.logger.info(f"データベースディレクトリが存在します: {db_dir}")
        elif not db_dir:
            app.logger.info("データベースファイルはカレントディレクトリに作成されます")


def register_models(app: Flask) -> None:
    """
    モデルの登録とグローバル変数の設定
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    # modelsパッケージから作成済みのモデルをインポート
    from models import User
    
    # ユーザーローダーの設定
    @login_manager.user_loader
    def load_user(user_id: str):
        """Flask-Login用ユーザーローダー"""
        return db.session.get(User, int(user_id))


def register_blueprints(app: Flask) -> None:
    """
    ブループリントの登録
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    # メインルート
    from web.routes import main_bp
    app.register_blueprint(main_bp)
    
    # 認証ルート
    from web.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # APIルート
    from web.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')


def register_error_handlers(app: Flask) -> None:
    """
    エラーハンドラーの登録
    
    Args:
        app: Flaskアプリケーションインスタンス
    """
    @app.errorhandler(404)
    def not_found_error(error):
        """404エラーハンドラー"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500エラーハンドラー"""
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """403エラーハンドラー"""
        return render_template('errors/403.html'), 403

# アプリケーションインスタンスの作成
app = create_app()


if __name__ == '__main__':
    """
    開発サーバーの起動
    
    プロダクション環境ではgunicornを使用することを推奨
    """
    app.logger.info("GameBargain development server starting...")
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=app.config.get('DEBUG', False)
    )
