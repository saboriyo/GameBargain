"""
Main Routes

メインページのルーティング
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """トップページ"""
    return render_template('index.html')

@main_bp.route('/search')
def search():
    """ゲーム検索ページ"""
    query = request.args.get('q', '')
    
    if not query:
        return render_template('search.html', games=[], query='')
    
    # TODO: 実際のゲーム検索ロジックを実装
    # ダミーデータを返す
    games = [
        {
            'id': 1,
            'title': 'Cyberpunk 2077',
            'developer': 'CD PROJEKT RED',
            'image_url': '/static/images/game_placeholder.jpg',
            'prices': {
                'steam': {'price': 3000, 'discount': 50, 'on_sale': True},
                'epic': {'price': 6000, 'discount': 0, 'on_sale': False}
            }
        },
        {
            'id': 2,
            'title': 'The Witcher 3',
            'developer': 'CD PROJEKT RED',
            'image_url': '/static/images/game_placeholder.jpg',
            'prices': {
                'steam': {'price': 1500, 'discount': 75, 'on_sale': True},
                'epic': {'price': 2000, 'discount': 50, 'on_sale': True}
            }
        }
    ]
    
    return render_template('search.html', games=games, query=query)

@main_bp.route('/game/<int:game_id>')
def game_detail(game_id):
    """ゲーム詳細ページ"""
    # TODO: データベースから実際のゲーム情報を取得
    # ダミーデータを返す
    game = {
        'id': game_id,
        'title': 'Cyberpunk 2077',
        'developer': 'CD PROJEKT RED',
        'image_url': '/static/images/game_placeholder.jpg',
        'description': '2077年のナイトシティを舞台にしたオープンワールドRPG',
        'prices': {
            'steam': {'price': 3000, 'regular_price': 6000, 'discount': 50, 'on_sale': True},
            'epic': {'price': 6000, 'regular_price': 6000, 'discount': 0, 'on_sale': False}
        },
        'price_history': [
            {'date': '2024-01-01', 'steam': 6000, 'epic': 6000},
            {'date': '2024-02-01', 'steam': 4500, 'epic': 6000},
            {'date': '2024-03-01', 'steam': 3000, 'epic': 5000},
        ]
    }
    
    return render_template('game_detail.html', game=game)

@main_bp.route('/api/games/search')
def api_search_games():
    """ゲーム検索API"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'games': []})
    
    # TODO: 実際の検索ロジック
    games = [
        {
            'id': 1,
            'title': 'Cyberpunk 2077',
            'developer': 'CD PROJEKT RED',
            'image_url': '/static/images/game_placeholder.jpg'
        }
    ]
    
    return jsonify({'games': games})
