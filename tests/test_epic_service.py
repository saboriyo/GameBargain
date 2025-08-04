#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Epic Games Store API Service テストスクリプト

Epic Games Store APIサービスの動作をテストします。
"""

import sys
import os
import json
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.epic_service import EpicGamesStoreAPI


def test_epic_service():
    """Epic Games Store APIサービスのテスト"""
    
    print("🎮 Epic Games Store API Service テスト開始")
    print("=" * 50)
    
    # サービス初期化
    epic_service = EpicGamesStoreAPI()
    
    try:
        # 1. 最近のゲーム取得テスト
        print("\n1. 最近のゲーム取得テスト")
        print("-" * 30)
        
        recent_games = epic_service.get_recent_games(limit=5)
        print(f"取得件数: {len(recent_games)}")
        
        for i, game in enumerate(recent_games[:3], 1):
            print(f"\nゲーム {i}:")
            print(f"  タイトル: {game.get('title', 'N/A')}")
            print(f"  開発者: {game.get('developer', 'N/A')}")
            print(f"  価格: {game.get('price_info', {}).get('formatted_price', 'N/A')}")
            print(f"  割引: {game.get('price_info', {}).get('discount_percent', 0)}%")
            print(f"  画像URL: {game.get('image_url', 'N/A')[:50]}...")
        
        # 2. ゲーム検索テスト
        print("\n\n2. ゲーム検索テスト")
        print("-" * 30)
        
        search_query = "cyberpunk"
        search_results = epic_service.search_games(search_query, limit=3)
        print(f"検索クエリ: '{search_query}'")
        print(f"検索結果数: {len(search_results)}")
        
        for i, game in enumerate(search_results, 1):
            print(f"\n検索結果 {i}:")
            print(f"  タイトル: {game.get('title', 'N/A')}")
            print(f"  開発者: {game.get('developer', 'N/A')}")
            print(f"  価格: {game.get('price_info', {}).get('formatted_price', 'N/A')}")
            print(f"  Epic URL: {game.get('epic_url', 'N/A')}")
        
        # 3. 無料ゲーム取得テスト
        print("\n\n3. 無料ゲーム取得テスト")
        print("-" * 30)
        
        free_games = epic_service.get_free_games()
        print(f"無料ゲーム数: {len(free_games)}")
        
        for i, game in enumerate(free_games[:3], 1):
            print(f"\n無料ゲーム {i}:")
            print(f"  タイトル: {game.get('title', 'N/A')}")
            print(f"  開発者: {game.get('developer', 'N/A')}")
            print(f"  価格: {game.get('price_info', {}).get('formatted_price', 'N/A')}")
        
        # 4. 価格取得テスト（最初のゲームで）
        if recent_games:
            print("\n\n4. 価格取得テスト")
            print("-" * 30)
            
            first_game = recent_games[0]
            namespace = first_game.get('epic_namespace')
            title = first_game.get('title')
            
            if namespace:
                print(f"ゲーム: {title}")
                print(f"Namespace: {namespace}")
                
                price_data = epic_service.get_game_price(namespace)
                if price_data:
                    print(f"価格情報:")
                    print(f"  現在価格: ¥{price_data.get('price', 0):,}")
                    print(f"  原価: ¥{price_data.get('original_price', 0):,}")
                    print(f"  割引率: {price_data.get('discount_percent', 0)}%")
                    print(f"  セール中: {price_data.get('is_on_sale', False)}")
                    print(f"  通貨: {price_data.get('currency', 'N/A')}")
                else:
                    print("価格情報を取得できませんでした")
            else:
                print("Namespaceが取得できませんでした")
        
        print("\n\n✅ テスト完了")
        
    except Exception as e:
        print(f"\n❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


def test_graphql_query():
    """GraphQLクエリのテスト"""
    
    print("\n\n🔍 GraphQLクエリテスト")
    print("=" * 50)
    
    epic_service = EpicGamesStoreAPI()
    
    try:
        # プロダクトマッピング取得テスト
        print("\nプロダクトマッピング取得テスト")
        print("-" * 30)
        
        mapping = epic_service.get_product_mapping()
        print(f"マッピング数: {len(mapping)}")
        
        # 最初の5件を表示
        for i, (namespace, slug) in enumerate(list(mapping.items())[:5], 1):
            print(f"{i}. {namespace} -> {slug}")
        
        print("\n✅ GraphQLテスト完了")
        
    except Exception as e:
        print(f"\n❌ GraphQLテストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print(f"テスト開始時刻: {datetime.now()}")
    
    # メインテスト
    test_epic_service()
    
    # GraphQLテスト
    test_graphql_query()
    
    print(f"\nテスト終了時刻: {datetime.now()}")
    print("\n🎉 全テスト完了！") 