#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Initialization Script

データベースを初期化するための単独スクリプト
"""

import os
import sys

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def init_database():
    """データベースを初期化"""
    print('データベース初期化開始...')
    
    try:
        # Flaskアプリケーションを作成
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from models import db
            from sqlalchemy import inspect
            
            print('既存テーブルを削除中...')
            db.drop_all()
            
            print('新しいテーブルを作成中...')
            db.create_all()
            
            print('データベース初期化完了!')
            
            # 初期化後の状態確認
            print('\n初期化後の状態:')
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f'作成されたテーブル: {tables}')
            
            # 各テーブルの詳細確認
            for table_name in tables:
                print(f'\n{table_name}テーブルの構造:')
                columns = inspector.get_columns(table_name)
                for col in columns:
                    print(f'  - {col["name"]}: {col["type"]} (nullable: {col["nullable"]})')
                    
    except Exception as e:
        print(f'データベース初期化エラー: {e}')
        import traceback
        traceback.print_exc()
        return False
        
    return True

def debug_database():
    """データベースの状態をデバッグ"""
    print('データベースデバッグ情報:')
    print('=' * 60)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from models import db
            from models.game import Game
            from sqlalchemy import inspect, text
            
            # データベース接続の確認
            print('1. データベース接続テスト')
            try:
                result = db.session.execute(text('SELECT 1')).scalar()
                print(f'   ✓ データベース接続: 成功 (結果: {result})')
            except Exception as e:
                print(f'   ✗ データベース接続: 失敗 - {e}')
                return False
            
            # テーブル存在確認
            print('\n2. テーブル存在確認')
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f'   存在するテーブル: {tables}')
            
            if 'games' in tables:
                print('   ✓ gamesテーブル: 存在')
                
                # カラム情報の確認
                columns = inspector.get_columns('games')
                print('   カラム情報:')
                for col in columns:
                    print(f'     - {col["name"]}: {col["type"]} (nullable: {col["nullable"]})')
            else:
                print('   ✗ gamesテーブル: 存在しない')
                return False
            
            # データ数確認
            print('\n3. データ数確認')
            try:
                count = db.session.query(Game).count()
                print(f'   gamesテーブルのレコード数: {count}')
            except Exception as e:
                print(f'   ✗ データ数取得エラー: {e}')
                return False
            
            # モデル定義確認
            print('\n4. モデル定義確認')
            print(f'   Gameモデルのテーブル名: {Game.__tablename__}')
            print(f'   Gameモデルのカラム:')
            for col_name, col in Game.__table__.columns.items():
                print(f'     - {col_name}: {col.type} (primary_key: {col.primary_key})')
            
            # サンプルクエリテスト
            print('\n5. サンプルクエリテスト')
            try:
                # 最初の5件を取得してみる
                games = db.session.query(Game).limit(5).all()
                print(f'   ✓ クエリテスト成功: {len(games)}件取得')
                for i, game in enumerate(games, 1):
                    print(f'     {i}. {getattr(game, "title", "タイトル不明")} (id: {getattr(game, "id", "不明")})')
            except Exception as e:
                print(f'   ✗ クエリテストエラー: {e}')
                return False
                
            return True
            
    except Exception as e:
        print(f'デバッグエラー: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        debug_database()
    else:
        if init_database():
            print('\n=== 初期化後のデバッグ情報 ===')
            debug_database()
