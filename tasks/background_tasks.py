# -*- coding: utf-8 -*-
"""Background Tasks

バックグラウンドで実行されるタスク（定期的なデータ更新など）
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from flask import current_app
from models import db
from models import Game, Price, User, Favorite, Notification
from decimal import Decimal
from typing import Optional
from services.steam_service import SteamAPIService

logger = logging.getLogger(__name__)


def update_recent_searched_games_task():
    """
    最近検索されたゲームの定期更新タスク
    
    Steam APIから最近検索されたゲームを取得してデータベースを更新します。
    """
    try:
        logger.info("最近検索されたゲーム更新タスク開始")
        
        # Steam APIサービスをインスタンス化
        steam_service = SteamAPIService()
        
        # Steam APIから最近検索されたゲームを取得
        recent_games = steam_service.get_popular_games(30)
        logger.info(f"Steam APIから {len(recent_games)} 件の最近検索されたゲームを取得")
        
        updated_count = 0
        for steam_game in recent_games:
            if _save_game_from_steam_task(steam_game):
                updated_count += 1
            
            # API制限を考慮して短い間隔を置く
            time.sleep(0.5)
        
        logger.info(f"最近検索されたゲーム更新タスク完了: {updated_count}/{len(recent_games)} 件更新")
        
    except Exception as e:
        logger.error(f"人気ゲーム更新タスクエラー: {e}")


def update_game_prices_task():
    """
    ゲーム価格の定期更新タスク
    
    既存ゲームの価格情報をSteam APIから更新します。
    """
    try:
        logger.info("ゲーム価格更新タスク開始")
        
        # 最近更新されていないゲームを取得（過去24時間以内に更新されていないもの）
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        games_to_update = Game.query.filter(
            Game.steam_appid.isnot(None),
            Game.updated_at < cutoff_time
        ).order_by(Game.updated_at).limit(50).all()
        
        logger.info(f"{len(games_to_update)} 件のゲーム価格を更新予定")
        
        updated_count = 0
        for game in games_to_update:
            if _update_game_price(game):
                updated_count += 1
            
            # API制限を考慮
            time.sleep(1.0)
        
        logger.info(f"ゲーム価格更新タスク完了: {updated_count}/{len(games_to_update)} 件更新")
        
    except Exception as e:
        logger.error(f"ゲーム価格更新タスクエラー: {e}")


def cleanup_old_prices_task():
    """
    古い価格データのクリーンアップタスク
    
    90日以上古い価格データを削除します。
    """
    try:
        logger.info("古い価格データクリーンアップタスク開始")
        
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        deleted_count = Price.query.filter(
            Price.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        logger.info(f"古い価格データクリーンアップ完了: {deleted_count} 件削除")
        
    except Exception as e:
        logger.error(f"価格データクリーンアップエラー: {e}")
        db.session.rollback()


def _save_game_from_steam_task(steam_game: Dict[str, Any]) -> bool:
    """
    Steam APIのデータからゲームをデータベースに保存（タスク用）
    
    Args:
        steam_game: Steam APIから取得したゲームデータ
        
    Returns:
        bool: 保存が成功したかどうか
    """
    try:
        with current_app.app_context():
            # 既存ゲームをチェック
            existing_game = Game.query.filter_by(
                steam_appid=steam_game['steam_appid']
            ).first()
            price_info = steam_game.get('price_info', {})
            
            if existing_game:
                # 既存ゲームの更新（setattrを使用して型安全に）
                setattr(existing_game, 'title', steam_game['title'])
                setattr(existing_game, 'description', steam_game.get('description'))
                setattr(existing_game, 'developer', steam_game.get('developer'))
                setattr(existing_game, 'publisher', steam_game.get('publisher'))
                setattr(existing_game, 'image_url', steam_game.get('image_url'))
                setattr(existing_game, 'current_price', price_info.get('current_price'))
                setattr(existing_game, 'original_price', price_info.get('original_price'))
                setattr(existing_game, 'discount_percent', price_info.get('discount_percent', 0))
                setattr(existing_game, 'steam_rating', steam_game.get('steam_rating'))
                setattr(existing_game, 'metacritic_score', steam_game.get('metacritic_score'))
                setattr(existing_game, 'updated_at', datetime.utcnow())
                
                # ジャンルの設定
                if steam_game.get('genres'):
                    existing_game.set_genres(steam_game['genres'])
                
                game = existing_game
                db.session.add(game)
            else:
                # 新しいゲームを作成
                game = Game(
                    title=steam_game['title'],
                    steam_appid=steam_game['steam_appid'],
                    description=steam_game.get('description'),
                    developer=steam_game.get('developer'),
                    publisher=steam_game.get('publisher'),
                    image_url=steam_game.get('image_url'),
                    current_price=price_info.get('current_price'),
                    original_price=price_info.get('original_price'),
                    discount_percent=price_info.get('discount_percent', 0),
                    steam_rating=steam_game.get('steam_rating'),
                    metacritic_score=steam_game.get('metacritic_score')
                )
                if steam_game.get('genres'):
                    game.set_genres(steam_game['genres'])
                
                db.session.add(game)
            
            # 価格履歴の保存
            if price_info.get('current_price'):
                db.session.flush()  # game.idを取得するため
                
                # 同じ日に同じ価格の記録があるかチェック
                today = datetime.utcnow().date()
                game_id = getattr(game, 'id', None)
                if game_id:
                    existing_price = Price.query.filter(
                        Price.game_id == int(game_id),
                        Price.store == 'steam',
                        db.func.date(Price.created_at) == today,
                        Price.sale_price == price_info['current_price']
                    ).first()
                
                if not existing_price:
                    # 新しい価格記録を作成
                    game_id = getattr(game, 'id', None)
                    if game_id:
                        price_record = Price(
                            game_id=int(game_id),
                            store='steam',
                            regular_price=price_info.get('original_price', price_info['current_price']),
                            sale_price=price_info['current_price'],
                            discount_rate=price_info.get('discount_percent', 0),
                            is_on_sale=price_info.get('discount_percent', 0) > 0,
                            store_url=steam_game.get('steam_url')
                        )
                        db.session.add(price_record)

            db.session.commit()
            return True
        
    except Exception as e:
        logger.error(f"ゲーム保存エラー（タスク）: {e}")
        db.session.rollback()
        return False


def _update_game_price(game) -> bool:
    """
    単一ゲームの価格を更新
    
    Args:
        game: Gameオブジェクト
        
    Returns:
        bool: 更新が成功したかどうか
    """
    try:
        if not game.steam_appid:
            return False
        
        # Steam APIサービスをインスタンス化
        steam_service = SteamAPIService()
        
        # Steam APIから最新情報を取得
        app_detail = steam_service.get_app_details(game.steam_appid)
        
        if not app_detail or not app_detail.get('success'):
            return False
        
        game_data = app_detail.get('data', {})
        price_info = steam_service._extract_price_info(game_data)
        
        # 価格情報を更新
        if price_info.get('current_price') is not None:
            setattr(game, 'current_price', price_info['current_price'])
            setattr(game, 'original_price', price_info.get('original_price'))
            setattr(game, 'discount_percent', price_info.get('discount_percent', 0))
            setattr(game, 'updated_at', datetime.utcnow())
            
            # 価格履歴を追加
            today = datetime.utcnow().date()
            game_id = getattr(game, 'id', None)
            if game_id:
                existing_price = Price.query.filter(
                    Price.game_id == int(game_id),
                    Price.store == 'steam',
                    db.func.date(Price.created_at) == today,
                    Price.sale_price == price_info['current_price']
                ).first()
            
            if not existing_price:
                # 新しい価格記録を作成
                game_id = getattr(game, 'id', None)
                if game_id:
                    price_record = Price(
                        game_id=int(game_id),
                        store='steam',
                        regular_price=price_info.get('original_price', price_info['current_price']),
                        sale_price=price_info['current_price'],
                        discount_rate=price_info.get('discount_percent', 0),
                        is_on_sale=price_info.get('discount_percent', 0) > 0
                    )
                    db.session.add(price_record)

            db.session.commit()
            return True
        
        return False
        
    except Exception as e:
        game_id = getattr(game, 'id', 'Unknown')
        logger.error(f"ゲーム価格更新エラー (game_id: {game_id}): {e}")
        db.session.rollback()
        return False


def run_maintenance_tasks():
    """
    メンテナンスタスクを順次実行
    """
    logger.info("メンテナンスタスク開始")
    
    # 最近検索されたゲーム更新
    update_recent_searched_games_task()
    
    # 価格更新
    update_game_prices_task()
    
    # 古いデータクリーンアップ
    cleanup_old_prices_task()
    
    logger.info("メンテナンスタスク完了")
