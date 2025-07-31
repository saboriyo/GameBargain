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
from repositories.price_repository import PriceRepository
from repositories.user_repository import UserRepository

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
        price_repository = PriceRepository()
        
        # データベースから注目ゲームを取得
        featured_games_db = game_repository.get_recent_games(6)
        current_app.logger.info(f"データベースから取得したゲーム数: {len(featured_games_db)}件")
        
        # データベースに十分なゲームがない場合、Steam APIから最近のゲームを取得
        if len(featured_games_db) < 3:
            current_app.logger.info("データベースにゲームが少ないため、Steam APIから最近のゲームを取得中...")
            try:
                steam_service = SteamAPIService()
                recent_games = steam_service.get_recent_games(10)
                
                # Steam APIの結果をデータベースに保存（リポジトリ層を使用）
                if recent_games:
                    game_repository.save_steam_games_from_api(recent_games)
                
                current_app.logger.info(f"Steam APIから取得したゲーム数: {len(recent_games)}件")
                
                # 再度データベースから取得
                featured_games_db = game_repository.get_recent_games(6)
                current_app.logger.info(f"最終的な注目ゲーム数: {len(featured_games_db)}件")
            except Exception as steam_error:
                current_app.logger.error(f"Steam API取得エラー: {steam_error}")
                # Steam APIが失敗しても、既存のデータで続行
        
        # セール中のゲームを取得（リポジトリ層に追加予定、現在は空のリスト）
        sale_games_db = []
        
        # レスポンス用に整形（エラーハンドリング付き）
        featured_games = []
        for game in featured_games_db:
            try:
                formatted_game = game_repository.format_game_for_web_template(game, price_repository)
                featured_games.append(formatted_game)
            except Exception as format_error:
                current_app.logger.error(f"ゲーム整形エラー (ID: {game.id}): {format_error}")
                # エラーが発生したゲームはスキップ
                continue
        
        sale_games = []
        for game in sale_games_db:
            try:
                formatted_game = game_repository.format_game_for_web_template(game, price_repository)
                sale_games.append(formatted_game)
            except Exception as format_error:
                current_app.logger.error(f"セールゲーム整形エラー (ID: {game.id}): {format_error}")
                continue
        
        current_app.logger.info(f"トップページ表示: 注目ゲーム={len(featured_games)}件, セール={len(sale_games)}件")
        
        return render_template('index.html', 
                             recent_games=featured_games,
                             sale_games=sale_games,
                             page_title='ホーム')
                             
    except Exception as e:
        current_app.logger.error(f"トップページ取得エラー: {e}")
        current_app.logger.exception("詳細なエラー情報:")
        # エラー時はサンプルデータで表示
        return render_template('index.html', 
                             recent_games=[],
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
            game_repository = GameRepository()
            price_repository = PriceRepository()
            search_service = GameSearchService()
            recent_games_data = search_service.get_recent_games(4)
            recent_games = [game_repository.format_game_for_web_template(game, price_repository) for game in recent_games_data]
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
        
        game_repository = GameRepository()
        price_repository = PriceRepository()
        search_results = [game_repository.format_game_for_web_template(game, price_repository) for game in games]
        
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
        # リポジトリを初期化
        game_repository = GameRepository()
        price_repository = PriceRepository()
        
        # データベースからゲーム情報を取得
        game = game_repository.get_by_id(game_id)
        if not game:
            flash('指定されたゲームが見つかりません。', 'error')
            return redirect(url_for('main.index'))
        
        # ゲーム情報を整形（価格情報も含む）
        game_data = game_repository.format_game_for_web_template(game, price_repository)
        current_app.logger.debug(f"ゲーム情報: id={game_data['id']}, "
                               f"title={game_data['title']}, "
                               f"current_price={game_data.get('current_price')}")

        # PriceRepositoryから価格情報を取得
        formatted_prices = price_repository.get_formatted_prices_for_game(game_id)
        current_app.logger.debug(f"取得した価格情報数: {len(formatted_prices)}")
        
        for formatted_price in formatted_prices:
            current_app.logger.debug(f"整形後の価格情報: {formatted_price}")

        # 最安値を特定
        lowest_price = price_repository.get_lowest_price_for_game(game_id)
        if lowest_price:
            current_app.logger.debug(f"最安値: store={lowest_price['store']}, "
                                   f"price={lowest_price['price']}, "
                                   f"discount={lowest_price['discount_percent']}%")

        # 最安値情報をゲームデータに追加
        if lowest_price:
            game_data['lowest_price'] = lowest_price
            current_app.logger.debug("ゲームデータに最安値情報を追加済み")

        current_app.logger.info(f"ゲーム詳細表示: game_id={game_id}, "
                               f"title={game.title}, "
                               f"価格数={len(formatted_prices)}")

        # お気に入り状態をチェック
        is_favorited = False
        if current_user.is_authenticated:
            user_repository = UserRepository()
            is_favorited = user_repository.is_game_favorited(current_user.user_id, game_id)

        return render_template('game_detail.html', 
                             game=game_data,
                             prices=formatted_prices,
                             lowest_price=lowest_price,
                             is_favorited=is_favorited,
                             page_title=game.title)

    except Exception as e:
        current_app.logger.error(f"ゲーム詳細取得エラー: {e}")
        current_app.logger.exception("詳細なエラー情報:")
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
        # UserRepositoryを使用してお気に入りを取得
        user_repository = UserRepository()
        game_repository = GameRepository()
        price_repository = PriceRepository()
        
        favorite_games_db = user_repository.get_user_favorites(current_user.user_id)
        favorite_games = [game_repository.format_game_for_web_template(game, price_repository) for game in favorite_games_db]
        
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
        # リポジトリを初期化
        game_repository = GameRepository()
        user_repository = UserRepository()
        
        # ゲームの存在確認
        game = game_repository.get_by_id(game_id)
        if not game:
            return jsonify({
                'success': False,
                'message': 'ゲームが見つかりません'
            }), 404
        
        # お気に入りに追加
        favorite = user_repository.add_favorite(current_user.user_id, game_id)
        
        if favorite is None:
            return jsonify({
                'success': False,
                'message': '既にお気に入りに追加されています'
            }), 400
        
        user_repository.commit()
        
        current_app.logger.info(f"お気に入り追加: user_id={current_user.user_id}, game_id={game_id}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りに追加しました'
        })
        
    except Exception as e:
        if 'user_repository' in locals():
            user_repository.rollback()
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
        # リポジトリを初期化
        user_repository = UserRepository()
        
        # お気に入りから削除
        success = user_repository.remove_favorite(current_user.user_id, game_id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'お気に入りに登録されていません'
            }), 404
        
        user_repository.commit()
        
        current_app.logger.info(f"お気に入り削除: user_id={current_user.user_id}, game_id={game_id}")
        
        return jsonify({
            'success': True,
            'message': 'お気に入りから削除しました'
        })
        
    except Exception as e:
        if 'user_repository' in locals():
            user_repository.rollback()
        current_app.logger.error(f"お気に入り削除エラー: {e}")
        return jsonify({
            'success': False,
            'message': 'お気に入りの削除に失敗しました'
        }), 500


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
        'app_version': '1.0.0',
        'current_user': current_user
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
