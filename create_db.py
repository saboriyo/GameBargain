#!/usr/bin/env python3
"""
データベーステーブル作成スクリプト

このスクリプトを実行してデータベーステーブルを手動で作成します。
SQLite3を使用して確実にテーブルを作成します。
"""

import os
import sqlite3
from dotenv import load_dotenv

# 環境変数クリア（複数回実行）
for var in ['DATABASE_URL', 'SQLALCHEMY_DATABASE_URI']:
    os.environ.pop(var, None)

# .envファイル読み込み
load_dotenv()

def create_database():
    """SQLite3でデータベーステーブルを作成"""
    
    # データベースファイルパスを決定
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///gamebargain.db')
    if db_url.startswith('sqlite:///'):
        db_path = db_url.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
    else:
        db_path = 'gamebargain.db'
    
    print(f"データベースファイル: {db_path}")
    
    # ディレクトリ作成
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"ディレクトリを作成: {db_dir}")
    
    try:
        # SQLite接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("SQLiteデータベースに接続しました")
        
        # ユーザーテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id VARCHAR(20) UNIQUE NOT NULL,
            username VARCHAR(100) NOT NULL,
            display_name VARCHAR(100),
            avatar_url TEXT,
            email VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            notification_enabled BOOLEAN DEFAULT TRUE,
            price_threshold_percentage REAL DEFAULT 10.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # ゲームテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(200) NOT NULL,
            normalized_title VARCHAR(200),
            developer VARCHAR(100),
            publisher VARCHAR(100),
            steam_appid VARCHAR(20) UNIQUE,
            epic_game_id VARCHAR(50) UNIQUE,
            image_url VARCHAR(255),
            steam_url VARCHAR(500),
            description TEXT,
            genres TEXT,
            release_date DATE,
            platforms TEXT,
            steam_rating DECIMAL(3, 2),
            metacritic_score INTEGER,
            current_price DECIMAL(10, 2),
            original_price DECIMAL(10, 2),
            discount_percent INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 価格テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            platform VARCHAR(50) NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            discount_percentage REAL,
            currency VARCHAR(3) DEFAULT 'JPY',
            store_url TEXT,
            is_on_sale BOOLEAN DEFAULT FALSE,
            sale_ends_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE
        )
        ''')
        
        # お気に入りテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            price_threshold REAL,
            notification_enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE CASCADE,
            UNIQUE (user_id, game_id)
        )
        ''')
        
        # 通知テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_id INTEGER,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            sent_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (game_id) REFERENCES games (id) ON DELETE SET NULL
        )
        ''')
        
        # インデックス作成
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users (discord_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_title ON games (title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_normalized_title ON games (normalized_title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_steam_appid ON games (steam_appid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_epic_game_id ON games (epic_game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_game_platform ON prices (game_id, platform)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user_game ON user_favorites (user_id, game_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_favorites_notification_enabled ON user_favorites (notification_enabled)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id)')
        
        # コミット
        conn.commit()
        
        # テーブル一覧確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables if not table[0].startswith('sqlite_')]
        print(f"✅ 作成されたテーブル: {table_names}")
        
        # 各テーブルの詳細情報
        for table_name in table_names:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"  {table_name}: {column_names}")
        
        conn.close()
        print("✅ データベーステーブルが正常に作成されました")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    create_database()
