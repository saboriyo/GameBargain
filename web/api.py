"""
API Routes

APIエンドポイント
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'message': 'GameBargain API is running'
    })

@api_bp.route('/games')
def games():
    """ゲーム一覧API"""
    # TODO: データベースから実際のゲーム一覧を取得
    games_data = [
        {
            'id': 1,
            'title': 'Cyberpunk 2077',
            'developer': 'CD PROJEKT RED',
            'current_price': 3000,
            'stores': ['steam', 'epic']
        },
        {
            'id': 2,
            'title': 'The Witcher 3',
            'developer': 'CD PROJEKT RED',
            'current_price': 1500,
            'stores': ['steam', 'epic']
        }
    ]
    
    return jsonify({'games': games_data})

@api_bp.route('/games/<int:game_id>')
def game_detail(game_id):
    """ゲーム詳細API"""
    # TODO: データベースから実際のゲーム詳細を取得
    game_data = {
        'id': game_id,
        'title': 'Cyberpunk 2077',
        'developer': 'CD PROJEKT RED',
        'description': '2077年のナイトシティを舞台にしたオープンワールドRPG',
        'prices': {
            'steam': 3000,
            'epic': 6000
        },
        'lowest_price': 3000,
        'lowest_price_store': 'steam'
    }
    
    return jsonify(game_data)

@api_bp.route('/favorites', methods=['GET', 'POST', 'DELETE'])
@login_required
def favorites():
    """お気に入りAPI"""
    if request.method == 'GET':
        # TODO: ユーザーのお気に入り一覧を取得
        favorites_data = [
            {
                'id': 1,
                'title': 'Cyberpunk 2077',
                'current_price': 3000,
                'added_at': '2024-01-01T00:00:00Z'
            }
        ]
        return jsonify({'favorites': favorites_data})
    
    elif request.method == 'POST':
        # TODO: お気に入りに追加
        game_id = request.json.get('game_id')
        return jsonify({
            'success': True,
            'message': f'ゲームID {game_id} をお気に入りに追加しました'
        })
    
    elif request.method == 'DELETE':
        # TODO: お気に入りから削除
        game_id = request.json.get('game_id')
        return jsonify({
            'success': True,
            'message': f'ゲームID {game_id} をお気に入りから削除しました'
        })

@api_bp.route('/stats')
def stats():
    """統計情報API"""
    return jsonify({
        'total_games': 150,
        'total_users': 50,
        'price_updates_today': 1200,
        'notifications_sent_today': 45
    })
