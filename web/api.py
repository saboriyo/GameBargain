"""
API Routes

APIエンドポイント
ゲーム情報、価格データ、お気に入り管理などのAPIを提供します。
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from sqlalchemy import desc, asc, func
from sqlalchemy.orm import joinedload

from models import db, Game, User, Favorite, Price, Notification

# ブループリントの作成
api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health_check():
    """
    ヘルスチェックAPI
    
    Returns:
        dict: システム状態情報
    """
    return jsonify({
        'status': 'ok',
        'message': 'GameBargain API is running',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


@api_bp.route('/games')
def games():
    """
    ゲーム一覧API
    
    Query Parameters:
        q: 検索クエリ
        page: ページ番号（デフォルト: 1）
        limit: 1ページあたりの件数（デフォルト: 20）
        sort: ソート順（price_asc, price_desc, name_asc, name_desc）
        
    Returns:
        dict: ゲーム一覧データ
    """
    # クエリパラメータの取得
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 20)), 100)  # 最大100件
    sort = request.args.get('sort', 'name_asc')
    
    try:
        # ベースクエリの作成
        base_query = db.session.query(Game)
        
        # 検索フィルタリング
        if query:
            base_query = base_query.filter(
                (Game.title.ilike(f'%{query}%')) |
                (Game.developer.ilike(f'%{query}%')) |
                (Game.normalized_title.ilike(f'%{query}%'))
            )
        
        # ソート処理
        if sort == 'price_asc':
            base_query = base_query.order_by(asc(Game.current_price))
        elif sort == 'price_desc':
            base_query = base_query.order_by(desc(Game.current_price))
        elif sort == 'name_desc':
            base_query = base_query.order_by(desc(Game.title))
        else:  # name_asc (default)
            base_query = base_query.order_by(asc(Game.title))
        
        # ページネーション
        total_count = base_query.count()
        page_games = base_query.offset((page - 1) * limit).limit(limit).all()
        
        # レスポンス用にデータを変換
        games_data = []
        for game in page_games:
            # 価格情報の取得
            prices = {}
            lowest_price = None
            lowest_store = None
            
            game_prices = getattr(game, 'prices', [])
            for price in game_prices:
                current_price = price.get_current_price()
                regular_price = getattr(price, 'regular_price', None)
                discount_rate = getattr(price, 'discount_rate', 0)
                store = getattr(price, 'store', '')
                
                store_price = {
                    'current': float(current_price) if current_price else None,
                    'original': float(regular_price) if regular_price else None,
                    'discount': discount_rate or 0,
                    'currency': 'JPY'
                }
                prices[store] = store_price
                
                # 最安値の計算
                if current_price and (lowest_price is None or current_price < lowest_price):
                    lowest_price = current_price
                    lowest_store = store
            
            release_date = getattr(game, 'release_date', None)
            steam_rating = getattr(game, 'steam_rating', None)
            
            game_data = {
                'id': getattr(game, 'id', None),
                'title': getattr(game, 'title', ''),
                'developer': getattr(game, 'developer', ''),
                'publisher': getattr(game, 'publisher', ''),
                'image_url': getattr(game, 'image_url', ''),
                'genres': game.get_genres(),
                'release_date': release_date.isoformat() if release_date else None,
                'steam_rating': float(steam_rating) if steam_rating else None,
                'prices': prices,
                'lowest_price': float(lowest_price) if lowest_price else None,
                'lowest_store': lowest_store
            }
            games_data.append(game_data)
        
        current_app.logger.info(f"ゲーム一覧API: query='{query}', page={page}, total={total_count}")
        
        return jsonify({
            'games': games_data,
            'pagination': {
                'current_page': page,
                'total_pages': (total_count + limit - 1) // limit,
                'total_count': total_count,
                'per_page': limit
            },
            'filters': {
                'query': query,
                'sort': sort
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"ゲーム一覧API エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/games/<int:game_id>')
def game_detail(game_id: int):
    """
    ゲーム詳細API
    
    Args:
        game_id: ゲームID
        
    Returns:
        dict: ゲーム詳細データ
    """
    try:
        # データベースからゲーム詳細を取得
        game = db.session.query(Game).filter_by(id=game_id).first()
        
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        # 価格情報の取得
        prices = {}
        lowest_price = None
        lowest_store = None
        
        game_prices = getattr(game, 'prices', [])
        for price in game_prices:
            current_price = price.get_current_price()
            regular_price = getattr(price, 'regular_price', None)
            discount_rate = getattr(price, 'discount_rate', 0)
            store = getattr(price, 'store', '')
            store_url = getattr(price, 'store_url', '')
            created_at = getattr(price, 'created_at', None)
            
            store_data = {
                'current': float(current_price) if current_price else None,
                'original': float(regular_price) if regular_price else None,
                'discount': discount_rate or 0,
                'currency': 'JPY',
                'url': store_url,
                'last_updated': created_at.isoformat() if created_at else None
            }
            prices[store] = store_data
            
            # 最安値の計算
            if current_price and (lowest_price is None or current_price < lowest_price):
                lowest_price = current_price
                lowest_store = store
        
        # TODO: 価格履歴の取得（実装時に追加）
        price_history = []
        
        release_date = getattr(game, 'release_date', None)
        steam_rating = getattr(game, 'steam_rating', None)
        metacritic_score = getattr(game, 'metacritic_score', None)
        
        game_data = {
            'id': getattr(game, 'id', None),
            'title': getattr(game, 'title', ''),
            'developer': getattr(game, 'developer', ''),
            'publisher': getattr(game, 'publisher', ''),
            'description': getattr(game, 'description', ''),
            'image_url': getattr(game, 'image_url', ''),
            'genres': game.get_genres(),
            'release_date': release_date.isoformat() if release_date else None,
            'steam_app_id': getattr(game, 'steam_appid', ''),
            'steam_rating': float(steam_rating) if steam_rating else None,
            'metacritic_score': int(metacritic_score) if metacritic_score else None,
            'prices': prices,
            'lowest_price': float(lowest_price) if lowest_price else None,
            'lowest_store': lowest_store,
            'price_history': price_history
        }
        
        return jsonify(game_data)
        
    except Exception as e:
        current_app.logger.error(f"ゲーム詳細API エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/favorites', methods=['GET', 'POST', 'DELETE'])
@login_required
def favorites():
    """
    お気に入りAPI
    
    GET: お気に入り一覧取得
    POST: お気に入り追加
    DELETE: お気に入り削除
    
    Returns:
        dict: お気に入りデータ
    """
    user_id = current_user.get_id()
    
    if request.method == 'GET':
        # お気に入り一覧取得
        try:
            favorites = db.session.query(Favorite).filter_by(user_id=user_id).all()
            
            favorite_games = []
            for favorite in favorites:
                game = getattr(favorite, 'game', None)
                if game:
                    # 価格情報の取得
                    game_prices = getattr(game, 'prices', [])
                    lowest_price = None
                    lowest_store = None
                    
                    for price in game_prices:
                        current_price = price.get_current_price()
                        store = getattr(price, 'store', '')
                        
                        if current_price and (lowest_price is None or current_price < lowest_price):
                            lowest_price = current_price
                            lowest_store = store
                    
                    favorite_data = {
                        'favorite_id': getattr(favorite, 'id', None),
                        'game_id': getattr(game, 'id', None),
                        'title': getattr(game, 'title', ''),
                        'developer': getattr(game, 'developer', ''),
                        'image_url': getattr(game, 'image_url', ''),
                        'genres': game.get_genres(),
                        'lowest_price': float(lowest_price) if lowest_price else None,
                        'lowest_store': lowest_store,
                        'price_threshold': float(getattr(favorite, 'price_threshold')) if getattr(favorite, 'price_threshold', None) else None,
                        'notification_enabled': getattr(favorite, 'notification_enabled', True),
                        'created_at': getattr(favorite, 'created_at', None).isoformat() if getattr(favorite, 'created_at', None) and hasattr(getattr(favorite, 'created_at', None), 'isoformat') else None
                    }
                    favorite_games.append(favorite_data)
            
            return jsonify({
                'favorites': favorite_games,
                'count': len(favorite_games)
            })
            
        except Exception as e:
            current_app.logger.error(f"お気に入り一覧取得エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    elif request.method == 'POST':
        # お気に入り追加
        data = request.get_json()
        game_id = data.get('game_id')
        price_threshold = data.get('price_threshold')
        
        if not game_id:
            return jsonify({'error': 'game_id is required'}), 400
        
        try:
            # ゲームが存在するかチェック
            game = db.session.query(Game).filter_by(id=game_id).first()
            if not game:
                return jsonify({'error': 'Game not found'}), 404
            
            # 既にお気に入りに追加されているかチェック
            existing_favorite = db.session.query(Favorite).filter_by(
                user_id=user_id, game_id=game_id
            ).first()
            
            if existing_favorite:
                return jsonify({'error': 'Game already in favorites'}), 400
            
            # お気に入りを追加
            favorite = Favorite(user_id=int(user_id), game_id=game_id)
            if price_threshold:
                setattr(favorite, 'price_threshold', price_threshold)
            
            db.session.add(favorite)
            db.session.commit()
            
            current_app.logger.info(f"お気に入り追加: user_id={user_id}, game_id={game_id}")
            
            return jsonify({
                'success': True,
                'message': 'お気に入りに追加しました',
                'game_id': game_id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"お気に入り追加エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    elif request.method == 'DELETE':
        # お気に入り削除
        data = request.get_json()
        game_id = data.get('game_id')
        
        if not game_id:
            return jsonify({'error': 'game_id is required'}), 400
        
        try:
            # お気に入りを削除
            favorite = db.session.query(Favorite).filter_by(
                user_id=user_id, game_id=game_id
            ).first()
            
            if not favorite:
                return jsonify({'error': 'Favorite not found'}), 404
            
            db.session.delete(favorite)
            db.session.commit()
            
            current_app.logger.info(f"お気に入り削除: user_id={user_id}, game_id={game_id}")
            
            return jsonify({
                'success': True,
                'message': 'お気に入りから削除しました',
                'game_id': game_id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"お気に入り削除エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # すべての分岐でreturnされなかった場合は405 Method Not Allowedを返す
    return jsonify({'error': 'Method Not Allowed'}), 405


@api_bp.route('/price-alerts', methods=['GET', 'POST', 'DELETE'])
@login_required
def price_alerts():
    """
    価格アラートAPI
    
    GET: アラート一覧取得
    POST: アラート設定
    DELETE: アラート削除
    
    Returns:
        dict: アラートデータ
    """
    user_id = current_user.get_id()
    
    if request.method == 'GET':
        # アラート一覧取得
        try:
            # お気に入りテーブルから価格アラート設定を取得
            favorites_with_alerts = db.session.query(Favorite).filter(
                Favorite.user_id == user_id,
                Favorite.price_threshold.isnot(None)
            ).all()
            
            alerts = []
            for favorite in favorites_with_alerts:
                game = getattr(favorite, 'game', None)
                if game:
                    # 現在の最安値を取得
                    game_prices = getattr(game, 'prices', [])
                    current_lowest = None
                    
                    for price in game_prices:
                        current_price = price.get_current_price()
                        if current_price and (current_lowest is None or current_price < current_lowest):
                            current_lowest = current_price
                    
                    price_threshold = getattr(favorite, 'price_threshold', None)
                    alert_data = {
                        'alert_id': getattr(favorite, 'id', None),
                        'game_id': getattr(game, 'id', None),
                        'title': getattr(game, 'title', ''),
                        'image_url': getattr(game, 'image_url', ''),
                        'threshold_price': float(price_threshold) if price_threshold else None,
                        'current_lowest_price': float(current_lowest) if current_lowest else None,
                        'is_triggered': bool(current_lowest and price_threshold and current_lowest <= price_threshold),
                        'notification_enabled': getattr(favorite, 'notification_enabled', True)
                    }
                    alerts.append(alert_data)
            
            return jsonify({
                'alerts': alerts,
                'count': len(alerts)
            })
            
        except Exception as e:
            current_app.logger.error(f"アラート一覧取得エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    elif request.method == 'POST':
        # アラート設定
        data = request.get_json()
        game_id = data.get('game_id')
        threshold_price = data.get('threshold_price')
        
        if not game_id or not threshold_price:
            return jsonify({'error': 'game_id and threshold_price are required'}), 400
        
        try:
            # お気に入りの価格しきい値を更新（既存のお気に入りがない場合は作成）
            favorite = db.session.query(Favorite).filter_by(
                user_id=user_id, game_id=game_id
            ).first()
            
            if not favorite:
                # ゲームが存在するかチェック
                game = db.session.query(Game).filter_by(id=game_id).first()
                if not game:
                    return jsonify({'error': 'Game not found'}), 404
                
                # 新しいお気に入りを作成
                favorite = Favorite(user_id=int(user_id), game_id=game_id)
                db.session.add(favorite)
            
            # 価格しきい値を設定
            setattr(favorite, 'price_threshold', threshold_price)
            setattr(favorite, 'notification_enabled', True)
            
            db.session.commit()
            
            current_app.logger.info(f"価格アラート設定: user_id={user_id}, game_id={game_id}, threshold={threshold_price}")
            
            return jsonify({
                'success': True,
                'message': '価格アラートを設定しました',
                'game_id': game_id,
                'threshold_price': threshold_price
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"価格アラート設定エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    elif request.method == 'DELETE':
        # アラート削除
        data = request.get_json()
        game_id = data.get('game_id')
        
        if not game_id:
            return jsonify({'error': 'game_id is required'}), 400
        
        try:
            # お気に入りの価格しきい値をクリア
            favorite = db.session.query(Favorite).filter_by(
                user_id=user_id, game_id=game_id
            ).first()
            
            if not favorite:
                return jsonify({'error': 'Alert not found'}), 404
            
            setattr(favorite, 'price_threshold', None)
            setattr(favorite, 'notification_enabled', False)
            
            db.session.commit()
            
            current_app.logger.info(f"価格アラート削除: user_id={user_id}, game_id={game_id}")
            
            return jsonify({
                'success': True,
                'message': '価格アラートを削除しました',
                'game_id': game_id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"価格アラート削除エラー: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # すべての分岐でreturnされなかった場合は405 Method Not Allowedを返す
    return jsonify({'error': 'Method Not Allowed'}), 405


@api_bp.route('/stats')
def stats():
    """
    統計情報API
    
    Returns:
        dict: システム統計情報
    """
    try:
        # 実際の統計データを取得
        total_games = db.session.query(Game).count()
        total_users = db.session.query(User).count()
        total_favorites = db.session.query(Favorite).count()
        
        # セール中のゲーム数
        active_sales = db.session.query(Price).filter(Price.is_on_sale == True).count()
        
        # 今日の通知送信数
        today = datetime.utcnow().date()
        notifications_sent_today = db.session.query(Notification).filter(
            Notification.sent_at >= today,
            Notification.is_sent == True
        ).count()
        
        # 人気ゲーム（お気に入り数順）
        popular_games = db.session.query(
            Game, func.count(Favorite.id).label('favorite_count')
        ).join(Favorite).group_by(Game.id).order_by(
            func.count(Favorite.id).desc()
        ).limit(3).all()
        
        top_games = []
        for game, count in popular_games:
            top_games.append({
                'title': getattr(game, 'title', ''),
                'favorite_count': count
            })
        
        # 最近のセール情報
        recent_sales = db.session.query(Price).filter(
            Price.is_on_sale == True,
            Price.discount_rate > 0
        ).order_by(desc(Price.created_at)).limit(5).all()
        
        recent_sales_data = []
        for price in recent_sales:
            game = getattr(price, 'game', None)
            if game:
                recent_sales_data.append({
                    'title': getattr(game, 'title', ''),
                    'discount': getattr(price, 'discount_rate', 0),
                    'store': getattr(price, 'store', '')
                })
        
        stats_data = {
            'total_games': total_games,
            'total_users': total_users,
            'total_favorites': total_favorites,
            'active_sales': active_sales,
            'price_updates_today': 0,  # TODO: 価格更新履歴テーブルが実装されたら更新
            'notifications_sent_today': notifications_sent_today,
            'top_games': top_games,
            'recent_sales': recent_sales_data[:2]  # 最大2件
        }
        
        return jsonify(stats_data)
        
    except Exception as e:
        current_app.logger.error(f"統計情報API エラー: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/search/suggestions')
def search_suggestions():
    """
    検索候補API
    
    Query Parameters:
        q: 検索クエリ
        limit: 候補数（デフォルト: 5）
        
    Returns:
        dict: 検索候補リスト
    """
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 5)), 20)
    
    if len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        # データベースから検索候補を取得
        suggestions_query = db.session.query(Game.title).filter(
            (Game.title.ilike(f'%{query}%')) |
            (Game.normalized_title.ilike(f'%{query}%'))
        ).order_by(asc(Game.title)).limit(limit)
        
        suggestions = [title for (title,) in suggestions_query.all()]
        
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        current_app.logger.error(f"検索候補API エラー: {e}")
        return jsonify({'suggestions': []})


# エラーハンドラー
@api_bp.errorhandler(400)
def bad_request(error):
    """400エラーハンドラー"""
    return jsonify({'error': 'Bad request'}), 400


@api_bp.errorhandler(401)
def unauthorized(error):
    """401エラーハンドラー"""
    return jsonify({'error': 'Unauthorized'}), 401


@api_bp.errorhandler(404)
def not_found(error):
    """404エラーハンドラー"""
    return jsonify({'error': 'Not found'}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    """500エラーハンドラー"""
    return jsonify({'error': 'Internal server error'}), 500
