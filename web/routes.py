"""
Main Routes

メインWebアプリケーションのルーティング
トップページ、ゲーム検索、詳細表示などの主要機能を提供します。
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user  # type: ignore
from datetime import datetime
from typing import Dict, List, Any, Optional

from models import db, Game, Price, Favorite, User, Notification

from services.steam_service import SteamAPIService
from services.game_search_service import GameSearchService
from repositories.game_repository import GameRepository

# ブループリントの作成
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    トップページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    try:
        # GameRepositoryを使用してデータ取得
        game_repository = GameRepository()
        
        # データベースから注目ゲームを取得
        featured_games_db = game_repository.get_recent_games(6)
        
        # データベースに十分なゲームがない場合、Steam APIから最近のゲームを取得
        if len(featured_games_db) < 3:
            current_app.logger.info("データベースにゲームが少ないため、Steam APIから最近のゲームを取得中...")
            steam_service = SteamAPIService()
            recent_games = steam_service.get_recent_games(10)
            
            # Steam APIの結果をデータベースに保存（リポジトリ層を使用）
            if recent_games:
                game_repository.save_steam_games_from_api(recent_games)
            
            current_app.logger.info(f"Steam APIから取得したゲーム数: {len(recent_games)}件")
            
            # 再度データベースから取得
            featured_games_db = game_repository.get_recent_games(6)
            current_app.logger.info(f"最終的な注目ゲーム数: {len(featured_games_db)}件")
        
        # セール中のゲームを取得（リポジトリ層に追加予定、現在は空のリスト）
        sale_games_db = []
        
        # レスポンス用に整形
        featured_games = [_format_game_for_web_template(game) for game in featured_games_db]
        sale_games = [_format_game_for_web_template(game) for game in sale_games_db]
        
        current_app.logger.info(f"トップページ表示: 注目ゲーム={len(featured_games)}件, セール={len(sale_games)}件")
        
        return render_template('index.html', 
                             featured_games=featured_games,
                             sale_games=sale_games,
                             page_title='ホーム')
                             
    except Exception as e:
        current_app.logger.error(f"トップページ取得エラー: {e}")
        # エラー時はサンプルデータで表示
        return render_template('index.html', 
                             featured_games=[],
                             sale_games=[],
                             page_title='ホーム')


@main_bp.route('/search')
def search():
    """
    ゲーム検索ページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    
    # フィルター情報の取得
    filters = {}
    if request.args.get('min_price'):
        filters['min_price'] = request.args.get('min_price')
    if request.args.get('max_price'):
        filters['max_price'] = request.args.get('max_price')
    if request.args.get('genre'):
        filters['genre'] = request.args.get('genre')
    if request.args.get('platform'):
        filters['platform'] = request.args.get('platform')
    if request.args.get('sort'):
        filters['sort'] = request.args.get('sort')
    
    # フィルターが設定されているかチェック
    has_filters = bool(filters)
    
    # アクティブフィルターの生成
    active_filters = {k: v for k, v in filters.items() if v}
    
    # 人気のキーワード（サンプル）
    popular_keywords = ['Cyberpunk 2077', 'The Witcher 3', 'Elden Ring', 'GTA V', 'Minecraft']
    
    # 最近のゲーム（初期表示用）
    recent_games = []
    
    if not query and not has_filters:
        # 初期状態（検索前）- GameSearchServiceから最近追加されたゲームを取得
        try:
            search_service = GameSearchService()
            recent_games_data = search_service.get_recent_games(4)
            recent_games = [_format_game_for_web_template(game) for game in recent_games_data]
        except Exception as e:
            current_app.logger.error(f"最近のゲーム取得エラー: {e}")
            recent_games = []
        
        return render_template('search.html', 
                             games=[], 
                             query=query,
                             filters={'min_price': '', 'max_price': '', 'genre': '', 'platform': '', 'sort': 'relevance'},
                             has_filters=has_filters,
                             active_filters=active_filters,
                             popular_keywords=popular_keywords,
                             recent_games=recent_games,
                             page_title='ゲーム検索')
    
    try:
        current_app.logger.info(f"ゲーム検索開始: '{query}'")
        
        # GameSearchServiceを使用
        search_service = GameSearchService()
        search_result = search_service.search_games(
            query=query,
            filters=filters,
            page=page,
            per_page=20
        )
        
        # 検索結果をWeb用に整形
        games = search_result.get('games', [])
        pagination_data = search_result.get('pagination', {})
        total_count = search_result.get('total_count', 0)
        
        search_results = [_format_game_for_web_template(game) for game in games]
        
        # ページネーション情報をWeb用に変換
        pagination = {
            'page': pagination_data.get('page', 1),
            'pages': pagination_data.get('pages', 1),
            'total': total_count,
            'per_page': pagination_data.get('per_page', 20),
            'has_prev': pagination_data.get('has_prev', False),
            'has_next': pagination_data.get('has_next', False),
            'prev_num': pagination_data.get('prev_num'),
            'next_num': pagination_data.get('next_num'),
            'start_index': pagination_data.get('start_index', 0),
            'end_index': pagination_data.get('end_index', 0),
            'iter_pages': lambda: _iter_pages(pagination_data.get('page', 1), pagination_data.get('pages', 1))
        }
        
        current_app.logger.info(f"検索完了: クエリ='{query}', 結果数={len(search_results)}")
        
        # フィルター用のデフォルト値を設定
        display_filters = {
            'min_price': filters.get('min_price', ''),
            'max_price': filters.get('max_price', ''),
            'genre': filters.get('genre', ''),
            'platform': filters.get('platform', ''),
            'sort': filters.get('sort', 'relevance')
        }
        
        return render_template('search.html', 
                             games=search_results, 
                             query=query,
                             filters=display_filters,
                             has_filters=has_filters,
                             active_filters=active_filters,
                             pagination=pagination,
                             popular_keywords=popular_keywords,
                             recent_games=recent_games,
                             page_title=f'検索結果: {query}' if query else 'ゲーム検索')
                             
    except Exception as e:
        current_app.logger.error(f"ゲーム検索エラー: {e}")
        
        # エラー時も最低限の変数を渡す
        pagination = {
            'page': 1,
            'pages': 0,
            'total': 0,
            'per_page': 20,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None,
            'start_index': 0,
            'end_index': 0,
            'iter_pages': lambda: []
        }
        
        display_filters = {
            'min_price': '',
            'max_price': '',
            'genre': '',
            'platform': '',
            'sort': 'relevance'
        }
        
        return render_template('search.html', 
                             games=[], 
                             query=query,
                             filters=display_filters,
                             has_filters=has_filters,
                             active_filters=active_filters,
                             pagination=pagination,
                             popular_keywords=popular_keywords,
                             recent_games=recent_games,
                             page_title=f'検索結果: {query}' if query else 'ゲーム検索',
                             error='検索中にエラーが発生しました')


@main_bp.route('/game/<int:game_id>')
def game_detail(game_id: int):
    """
    ゲーム詳細ページ
    
    Args:
        game_id: ゲームID
        
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    try:
        # データベースからゲーム情報を取得
        game = db.session.get(Game, game_id)
        if not game:
            flash('指定されたゲームが見つかりません。', 'error')
            return redirect(url_for('main.index'))
        
        # 価格履歴を取得
        price_history = db.session.query(Price).filter_by(
            game_id=game_id
        ).order_by(Price.created_at).limit(30).all()
        
        # 最新の価格情報を取得
        prices = db.session.query(Price).filter_by(
            game_id=game_id
        ).order_by(Price.updated_at.desc()).limit(5).all()
        
        # 最安値を特定
        lowest_price = None
        if prices:
            lowest_price = min(prices, key=lambda p: getattr(p, 'sale_price') or getattr(p, 'regular_price', float('inf')))
        
        # お気に入り状態をチェック（ログイン時のみ）
        is_favorited = False
        if current_user.is_authenticated:
            favorite = db.session.query(Favorite).filter_by(
                user_id=current_user.user_id,
                game_id=game_id
            ).first()
            is_favorited = favorite is not None
        
        # レスポンス用に整形
        game_data = _format_game_for_web_template(game)
        
        # 価格履歴を整形
        price_history_data = [
            {
                'date': getattr(price, 'created_at', datetime.now()).strftime('%Y-%m-%d'),
                'price': float(getattr(price, 'sale_price') or getattr(price, 'regular_price', 0))
            }
            for price in price_history
        ]
        
        current_app.logger.info(f"ゲーム詳細表示: game_id={game_id}, title={game.title}")
        
        return render_template('game_detail.html', 
                             game=game_data,
                             prices=prices,
                             lowest_price=lowest_price,
                             price_history=price_history_data,
                             is_favorited=is_favorited,
                             page_title=game.title)
                             
    except Exception as e:
        current_app.logger.error(f"ゲーム詳細取得エラー: {e}")
        flash('ゲーム情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/favorites')
@login_required
def favorites():
    """
    お気に入り一覧ページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    try:
        # データベースからユーザーのお気に入りを取得
        favorites_query = db.session.query(Game).join(Favorite).filter(
            Favorite.user_id == current_user.user_id
        ).order_by(db.desc(Favorite.created_at))
        
        favorite_games_db = favorites_query.all()
        favorite_games = [_format_game_for_web_template(game) for game in favorite_games_db]
        
        current_app.logger.info(f"お気に入り一覧表示: user_id={current_user.user_id}, count={len(favorite_games)}")
        
        return render_template('favorites.html', 
                             games=favorite_games,
                             page_title='お気に入り')
                             
    except Exception as e:
        current_app.logger.error(f"お気に入り取得エラー: {e}")
        return render_template('favorites.html', 
                             games=[],
                             page_title='お気に入り',
                             error='お気に入りの取得中にエラーが発生しました')


@main_bp.route('/add_favorite/<int:game_id>', methods=['POST'])
@login_required
def add_favorite(game_id: int):
    """
    お気に入り追加
    
    Args:
        game_id: ゲームID
        
    Returns:
        dict: JSON レスポンス
    """
    try:
        # ゲームの存在確認
        game = db.session.get(Game, game_id)
        if not game:
            return jsonify({
                'success': False,
                'message': 'ゲームが見つかりません'
            }), 404
        
        # 既にお気に入りに追加済みかチェック
        existing_favorite = db.session.query(Favorite).filter_by(
            user_id=current_user.user_id,
            game_id=game_id
        ).first()
        
        if existing_favorite:
            return jsonify({
                'success': False,
                'message': '既にお気に入りに追加されています'
            }), 400
        
        # お気に入りに追加
        favorite = Favorite(
            user_id=current_user.user_id,
            game_id=game_id
        )
        db.session.add(favorite)
        db.session.commit()
        
        current_app.logger.info(f"お気に入り追加: user_id={current_user.user_id}, game_id={game_id}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りに追加しました'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"お気に入り追加エラー: {e}")
        return jsonify({
            'success': False,
            'message': 'お気に入りの追加に失敗しました'
        }), 500


@main_bp.route('/remove_favorite/<int:game_id>', methods=['POST'])
@login_required
def remove_favorite(game_id: int):
    """
    お気に入り削除
    
    Args:
        game_id: ゲームID
        
    Returns:
        dict: JSON レスポンス
    """
    try:
        # お気に入りを検索
        favorite = db.session.query(Favorite).filter_by(
            user_id=current_user.user_id,
            game_id=game_id
        ).first()
        
        if not favorite:
            return jsonify({
                'success': False,
                'message': 'お気に入りに登録されていません'
            }), 404
        
        # お気に入りから削除
        db.session.delete(favorite)
        db.session.commit()
        
        current_app.logger.info(f"お気に入り削除: user_id={current_user.user_id}, game_id={game_id}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りから削除しました'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"お気に入り削除エラー: {e}")
        return jsonify({
            'success': False,
            'message': 'お気に入りの削除に失敗しました'
        }), 500


# ヘルパー関数
def _format_game_for_web_template(game_data) -> Dict[str, Any]:
    """
    ゲームデータをWebテンプレート用に整形
    GameSearchServiceからのデータとGameモデルの両方に対応
    
    Args:
        game_data: GameSearchServiceからの辞書データまたはGameモデルオブジェクト
        
    Returns:
        Dict: 整形されたゲームデータ
    """
    # GameSearchServiceからの辞書データの場合
    if isinstance(game_data, dict):
        return {
            'id': game_data.get('id'),
            'title': game_data.get('title'),
            'description': game_data.get('description'),
            'developer': game_data.get('developer'),
            'publisher': game_data.get('publisher'),
            'release_date': game_data.get('release_date') or '',
            'genres': game_data.get('genres', []),
            'platforms': game_data.get('platforms', []),
            'image_url': game_data.get('image_url') or 'https://via.placeholder.com/300x400',
            'steam_url': game_data.get('steam_url'),
            'steam_rating': game_data.get('steam_rating'),
            'metacritic_score': game_data.get('metacritic_score'),
            'current_price': game_data.get('current_price') or 0.0,
            'original_price': game_data.get('original_price') or 0.0,
            'discount_percent': game_data.get('discount_percent', 0),
            'is_on_sale': game_data.get('discount_percent', 0) > 0,
            'lowest_price': game_data.get('current_price') or 0.0,
            'lowest_store': 'steam',
            'prices': game_data.get('prices', {})
        }

    # Gameモデルオブジェクトの場合
    return {
        'id': game_data.id,
        'title': game_data.title,
        'description': game_data.description,
        'developer': game_data.developer,
        'publisher': game_data.publisher,
        'release_date': game_data.release_date.strftime('%Y-%m-%d') if game_data.release_date else '',
        'genres': game_data.genres.split(',') if isinstance(game_data.genres, str) and game_data.genres else (game_data.genres if isinstance(game_data.genres, list) else []),
        'platforms': game_data.platforms.split(',') if isinstance(game_data.platforms, str) and game_data.platforms else (game_data.platforms if isinstance(game_data.platforms, list) else []),
        'image_url': game_data.image_url or 'https://via.placeholder.com/300x400',
        'steam_url': game_data.steam_url,
        'steam_rating': game_data.steam_rating,
        'metacritic_score': game_data.metacritic_score,
        'current_price': float(game_data.current_price) if game_data.current_price else 0.0,
        'original_price': float(game_data.original_price) if game_data.original_price else 0.0,
        'discount_percent': game_data.discount_percent or 0,
        'is_on_sale': (game_data.discount_percent or 0) > 0,
        'lowest_price': float(game_data.current_price) if game_data.current_price else 0.0,
        'lowest_store': 'steam',
        'prices': {
            'steam': {
                'current': float(game_data.current_price) if game_data.current_price else 0.0,
                'original': float(game_data.original_price) if game_data.original_price else 0.0,
                'discount': game_data.discount_percent or 0,
                'url': game_data.steam_url
            }
        }
    }


@main_bp.route('/about')
def about():
    """
    アバウトページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    return render_template('about.html', page_title='GameBargainについて')


@main_bp.route('/help')
def help_page():
    """
    ヘルプページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    return render_template('help.html', page_title='ヘルプ')


@main_bp.route('/contact')
def contact():
    """
    お問い合わせページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    return render_template('contact.html', page_title='お問い合わせ')


# コンテキストプロセッサ：全テンプレートで使用可能な変数
@main_bp.app_context_processor
def inject_template_vars():
    """
    テンプレート用のグローバル変数を注入
    
    Returns:
        dict: テンプレート変数
    """
    return {
        'current_year': datetime.now().year,
        'app_name': 'GameBargain',
        'app_version': '1.0.0'
    }


def _iter_pages(current_page: int, total_pages: int, left_edge: int = 2, left_current: int = 2, right_current: int = 3, right_edge: int = 2):
    """
    ページネーション用のページ番号生成
    
    Args:
        current_page: 現在のページ番号
        total_pages: 総ページ数
        left_edge: 左端に表示するページ数
        left_current: 現在ページの左側に表示するページ数
        right_current: 現在ページの右側に表示するページ数
        right_edge: 右端に表示するページ数
        
    Yields:
        int | None: ページ番号（Noneは省略記号を表す）
    """
    for num in range(1, total_pages + 1):
        if num <= left_edge or \
           (current_page - left_current - 1 < num < current_page + right_current) or \
           num > total_pages - right_edge:
            yield num
    
    # 省略記号は実装を簡略化（必要に応じて後で追加）
