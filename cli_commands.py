# -*- coding: utf-8 -*-
"""CLI Commands

Flask CLIコマンドの定義
"""

import click
from flask import current_app
from flask.cli import with_appcontext

from services.game_search_service import GameSearchService
from repositories.game_repository import GameRepository
from services.price_change_detector import PriceChangeDetector



@click.command()
@click.option('--query', '-q', required=True, help='検索クエリ（必須）')
@click.option('--page', '-p', default=1, help='ページ番号 (デフォルト: 1)')
@click.option('--per-page', default=10, help='1ページあたりの表示件数 (デフォルト: 10)')
@click.option('--min-price', type=float, help='最低価格')
@click.option('--max-price', type=float, help='最高価格')
@click.option('--genre', help='ジャンル')
@click.option('--sort', type=click.Choice(['price_asc', 'price_desc', 'rating_desc', 'name_asc']), help='ソート順')
@with_appcontext
def search_db(query, page, per_page, min_price, max_price, genre, sort):
    """データベースからゲーム検索"""
    click.echo(f'データベース検索: "{query}" (ページ {page})')
    
    # フィルター条件の構築
    filters = {}
    if min_price is not None:
        filters['min_price'] = str(min_price)
    if max_price is not None:
        filters['max_price'] = str(max_price)
    if genre:
        filters['genre'] = genre
    if sort:
        filters['sort'] = sort
    
    try:
        # ゲーム検索サービスを使用（Steam APIは使わない）
        from repositories.game_repository import GameRepository
        game_repository = GameRepository()
        
        games, total_count = game_repository.search_games(
            query=query,
            filters=filters if filters else None,
            page=page,
            per_page=per_page
        )
        
        # 結果の表示
        click.echo(f'\nデータベース検索結果: {total_count}件')
        click.echo(f'ページ: {page}')
        click.echo('-' * 80)
        
        if not games:
            click.echo('該当するゲームが見つかりませんでした。')
            return
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {getattr(game, "title", "タイトル不明")}')
            
            if getattr(game, 'developer', None):
                click.echo(f'   開発者: {getattr(game, "developer")}')
            
            if getattr(game, 'genres', None):
                click.echo(f'   ジャンル: {getattr(game, "genres")}')
            
            # 価格情報の表示
            current_price = getattr(game, 'current_price', None)
            if current_price:
                click.echo(f'   価格: ¥{float(current_price):,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            if getattr(game, 'steam_rating', None):
                click.echo(f'   Steam評価: {getattr(game, "steam_rating")}%')
            
            if getattr(game, 'description', None):
                # 説明文を100文字で切り詰め
                description = getattr(game, 'description')
                if len(description) > 100:
                    description = description[:100] + '...'
                click.echo(f'   説明: {description}')
            
            click.echo()
        
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--query', '-q', required=True, help='検索クエリ（必須）')
@click.option('--limit', '-l', default=20, help='取得件数 (デフォルト: 20)')
@click.option('--save-to-db', is_flag=True, help='検索結果をデータベースに保存')
@with_appcontext
def search_steam(query, limit, save_to_db):
    """Steam APIからゲーム検索"""
    click.echo(f'Steam API検索: "{query}" (最大{limit}件)')
    
    try:
        from services.steam_service import SteamAPIService
        steam_service = SteamAPIService()
        
        # Steam APIから検索
        games = steam_service.search_games(query, limit)
        
        # 結果の表示
        click.echo(f'\nSteam API検索結果: {len(games)}件')
        click.echo('-' * 80)
        
        if not games:
            click.echo('該当するゲームが見つかりませんでした。')
            return
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            if game.get('genres'):
                genres = ', '.join(game['genres']) if isinstance(game['genres'], list) else game['genres']
                click.echo(f'   ジャンル: {genres}')
            
            # 価格情報の表示
            price_info = game.get('price_info', {})
            if price_info.get('current_price'):
                price = price_info['current_price']
                original_price = price_info.get('original_price')
                discount = price_info.get('discount_percent', 0)
                
                if original_price and discount > 0:
                    click.echo(f'   価格: ¥{price:,.0f} (元価格: ¥{original_price:,.0f}, {discount}%OFF)')
                else:
                    click.echo(f'   価格: ¥{price:,.0f}')
            elif price_info.get('is_free'):
                click.echo('   価格: 無料')
            else:
                click.echo('   価格: 価格情報なし')
            
            if game.get('steam_rating'):
                click.echo(f'   Steam評価: {game["steam_rating"]}%')
            
            if game.get('description'):
                # 説明文を100文字で切り詰め
                description = game['description']
                if len(description) > 100:
                    description = description[:100] + '...'
                click.echo(f'   説明: {description}')
            
            if game.get('steam_url'):
                click.echo(f'   Steam URL: {game["steam_url"]}')
            
            click.echo()
        
        # データベースに保存するオプション
        if save_to_db:
            click.echo('検索結果をデータベースに保存中...')
            from services.game_search_service import GameSearchService
            search_service = GameSearchService()
            game_repository = GameRepository()
            
            
            saved_game = game_repository.save_steam_games_from_api(games)

            
            search_service.game_repository.commit()
            click.echo(f'{len(saved_game)}件のゲームをデータベースに保存しました。')
        
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--query', '-q', help='検索クエリ')
@click.option('--page', '-p', default=1, help='ページ番号 (デフォルト: 1)')
@click.option('--per-page', default=10, help='1ページあたりの表示件数 (デフォルト: 10)')
@click.option('--min-price', type=float, help='最低価格')
@click.option('--max-price', type=float, help='最高価格')
@click.option('--genre', help='ジャンル')
@click.option('--sort', type=click.Choice(['price_asc', 'price_desc', 'rating_desc', 'name_asc']), help='ソート順')
@with_appcontext
def search_games(query, page, per_page, min_price, max_price, genre, sort):
    """ゲーム検索（データベース + Steam API自動切り替え）"""
    click.echo(f'ゲーム検索: "{query}" (ページ {page})')
    
    # フィルター条件の構築
    filters = {}
    if min_price is not None:
        filters['min_price'] = str(min_price)
    if max_price is not None:
        filters['max_price'] = str(max_price)
    if genre:
        filters['genre'] = genre
    if sort:
        filters['sort'] = sort
    
    try:
        # ゲーム検索サービスを使用
        search_service = GameSearchService()
        result = search_service.search_games(
            query=query,
            filters=filters if filters else None,
            page=page,
            per_page=per_page
        )
        
        # 結果の表示
        games = result.get('games', [])
        total_count = result.get('total_count', 0)
        pagination = result.get('pagination', {})
        
        click.echo(f'\n検索結果: {total_count}件')
        click.echo(f'ページ: {pagination.get("page", 1)} / {pagination.get("pages", 1)}')
        click.echo('-' * 80)
        
        if not games:
            click.echo('該当するゲームが見つかりませんでした。')
            return
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            if game.get('genres'):
                click.echo(f'   ジャンル: {game["genres"]}')
            
            # 価格情報の表示
            lowest_price = game.get('lowest_price')
            if lowest_price and lowest_price.get('price'):
                price = lowest_price['price']
                original_price = lowest_price.get('original_price')
                discount = lowest_price.get('discount_percent', 0)
                
                if original_price and discount > 0:
                    click.echo(f'   価格: ¥{price:,.0f} (元価格: ¥{original_price:,.0f}, {discount}%OFF)')
                else:
                    click.echo(f'   価格: ¥{price:,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            if game.get('steam_rating'):
                click.echo(f'   Steam評価: {game["steam_rating"]}%')
            
            if game.get('description'):
                # 説明文を100文字で切り詰め
                description = game['description']
                if len(description) > 100:
                    description = description[:100] + '...'
                click.echo(f'   説明: {description}')
            
            click.echo()
        
        # ページネーション情報
        if pagination.get('has_prev') or pagination.get('has_next'):
            nav_info = []
            if pagination.get('has_prev'):
                nav_info.append(f'前のページ: --page {pagination.get("prev_num")}')
            if pagination.get('has_next'):
                nav_info.append(f'次のページ: --page {pagination.get("next_num")}')
            click.echo('ナビゲーション: ' + ' | '.join(nav_info))
        
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def recent_games_db(limit):
    """データベースから最近追加されたゲーム一覧"""
    click.echo(f'データベース: 最近追加されたゲーム (上位{limit}件)')
    
    try:
        from repositories.game_repository import GameRepository
        game_repository = GameRepository()
        games = game_repository.get_recent_games(limit)
        
        if not games:
            click.echo('最近追加されたゲームがありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {getattr(game, "title", "タイトル不明")}')
            
            if getattr(game, 'developer', None):
                click.echo(f'   開発者: {getattr(game, "developer")}')
            
            # 価格情報の表示
            current_price = getattr(game, 'current_price', None)
            if current_price:
                click.echo(f'   価格: ¥{float(current_price):,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def recent_games_steam(limit):
    """Steam APIから最近追加されたゲーム一覧"""
    click.echo(f'Steam API: 最近追加されたゲーム (上位{limit}件)')
    
    try:
        from services.steam_service import SteamAPIService
        steam_service = SteamAPIService()
        games = steam_service.get_recent_games(limit)  # Steam APIでは人気ゲーム=最近のゲーム
        
        if not games:
            click.echo('最近追加されたゲームがありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            # 価格情報の表示
            price_info = game.get('price_info', {})
            if price_info.get('current_price'):
                click.echo(f'   価格: ¥{price_info["current_price"]:,.0f}')
            elif price_info.get('is_free'):
                click.echo('   価格: 無料')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def popular_games_db(limit):
    """データベースから人気ゲーム一覧"""
    click.echo(f'データベース: 人気ゲーム (上位{limit}件)')
    
    try:
        from repositories.game_repository import GameRepository
        game_repository = GameRepository()
        games = game_repository.get_popular_games(limit)
        
        if not games:
            click.echo('人気ゲームの情報がありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {getattr(game, "title", "タイトル不明")}')
            
            if getattr(game, 'developer', None):
                click.echo(f'   開発者: {getattr(game, "developer")}')
            
            if getattr(game, 'steam_rating', None):
                click.echo(f'   Steam評価: {getattr(game, "steam_rating")}%')
            
            # 価格情報の表示
            current_price = getattr(game, 'current_price', None)
            if current_price:
                click.echo(f'   価格: ¥{float(current_price):,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def popular_games_steam(limit):
    """Steam APIから人気ゲーム一覧"""
    click.echo(f'Steam API: 人気ゲーム (上位{limit}件)')
    
    try:
        from services.steam_service import SteamAPIService
        steam_service = SteamAPIService()
        games = steam_service.get_popular_games(limit)
        
        if not games:
            click.echo('人気ゲームの情報がありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            if game.get('steam_rating'):
                click.echo(f'   Steam評価: {game["steam_rating"]}%')
            
            # 価格情報の表示
            price_info = game.get('price_info', {})
            if price_info.get('current_price'):
                click.echo(f'   価格: ¥{price_info["current_price"]:,.0f}')
            elif price_info.get('is_free'):
                click.echo('   価格: 無料')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


# 統合版（既存のGameSearchServiceを使用）
@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def recent_games(limit):
    """最近追加されたゲーム一覧（データベース優先、自動Steam API補完）"""
    click.echo(f'最近追加されたゲーム (上位{limit}件)')
    
    try:
        search_service = GameSearchService()
        games = search_service.get_recent_games(limit)
        
        if not games:
            click.echo('最近追加されたゲームがありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            # 価格情報の表示
            lowest_price = game.get('lowest_price')
            if lowest_price and lowest_price.get('price'):
                click.echo(f'   価格: ¥{lowest_price["price"]:,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@click.option('--limit', '-l', default=10, help='表示件数 (デフォルト: 10)')
@with_appcontext
def popular_games(limit):
    """人気ゲーム一覧（データベース優先、自動Steam API補完）"""
    click.echo(f'人気ゲーム (上位{limit}件)')
    
    try:
        search_service = GameSearchService()
        games = search_service.get_popular_games(limit)
        
        if not games:
            click.echo('人気ゲームの情報がありません。')
            return
        
        click.echo('-' * 80)
        
        for i, game in enumerate(games, 1):
            click.echo(f'{i}. {game.get("title", "タイトル不明")}')
            
            if game.get('developer'):
                click.echo(f'   開発者: {game["developer"]}')
            
            if game.get('steam_rating'):
                click.echo(f'   Steam評価: {game["steam_rating"]}%')
            
            # 価格情報の表示
            lowest_price = game.get('lowest_price')
            if lowest_price and lowest_price.get('price'):
                click.echo(f'   価格: ¥{lowest_price["price"]:,.0f}')
            else:
                click.echo('   価格: 価格情報なし')
            
            click.echo()
            
    except Exception as e:
        click.echo(f'エラーが発生しました: {e}', err=True)


@click.command()
@with_appcontext
def db_debug():
    """データベースの状態をデバッグ"""
    click.echo('データベースデバッグ情報:')
    click.echo('=' * 60)
    
    try:
        from models import db
        from models.game import Game
        from sqlalchemy import inspect, text
        
        # データベース接続の確認
        click.echo('1. データベース接続テスト')
        try:
            result = db.session.execute(text('SELECT 1')).scalar()
            click.echo(f'   ✓ データベース接続: 成功 (結果: {result})')
        except Exception as e:
            click.echo(f'   ✗ データベース接続: 失敗 - {e}')
            return
        
        # テーブル存在確認
        click.echo('\n2. テーブル存在確認')
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        click.echo(f'   存在するテーブル: {tables}')
        
        if 'games' in tables:
            click.echo('   ✓ gamesテーブル: 存在')
            
            # カラム情報の確認
            columns = inspector.get_columns('games')
            click.echo('   カラム情報:')
            for col in columns:
                click.echo(f'     - {col["name"]}: {col["type"]} (nullable: {col["nullable"]})')
        else:
            click.echo('   ✗ gamesテーブル: 存在しない')
        
        # データ数確認
        click.echo('\n3. データ数確認')
        try:
            count = db.session.query(Game).count()
            click.echo(f'   gamesテーブルのレコード数: {count}')
        except Exception as e:
            click.echo(f'   ✗ データ数取得エラー: {e}')
        
        # モデル定義確認
        click.echo('\n4. モデル定義確認')
        click.echo(f'   Gameモデルのテーブル名: {Game.__tablename__}')
        click.echo(f'   Gameモデルのカラム:')
        for col_name, col in Game.__table__.columns.items():
            click.echo(f'     - {col_name}: {col.type} (primary_key: {col.primary_key})')
        
        # サンプルクエリテスト
        click.echo('\n5. サンプルクエリテスト')
        try:
            # 最初の5件を取得してみる
            games = db.session.query(Game).limit(5).all()
            click.echo(f'   ✓ クエリテスト成功: {len(games)}件取得')
            for i, game in enumerate(games, 1):
                click.echo(f'     {i}. {getattr(game, "title", "タイトル不明")} (id: {getattr(game, "id", "不明")})')
        except Exception as e:
            click.echo(f'   ✗ クエリテストエラー: {e}')
        
    except Exception as e:
        click.echo(f'デバッグエラー: {e}')
        import traceback
        click.echo(traceback.format_exc())


@click.command()
@with_appcontext
def db_init():
    """データベースを初期化（テーブル作成）"""
    click.echo('データベース初期化開始...')
    
    try:
        from models import db
        
        # 全テーブルを削除
        click.echo('既存テーブルを削除中...')
        db.drop_all()
        
        # 全テーブルを作成
        click.echo('新しいテーブルを作成中...')
        db.create_all()
        
        click.echo('データベース初期化完了!')
        
        # 初期化後の状態確認
        click.echo('\n初期化後の状態:')
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        click.echo(f'作成されたテーブル: {tables}')
        
    except Exception as e:
        click.echo(f'データベース初期化エラー: {e}')
        import traceback
        click.echo(traceback.format_exc())


@click.command()
@click.option('--dry-run', is_flag=True, help='実際の更新は行わず、検出のみ実行')
@click.option('--verbose', '-v', is_flag=True, help='詳細ログを表示')
@with_appcontext
def detect_price_changes(dry_run, verbose):
    """価格変動を検出し、価格データを更新"""
    click.echo('価格変動検出を開始...')
    
    # ログレベル設定
    if verbose:
        import logging
        logging.getLogger('services.steam_service').setLevel(logging.DEBUG)
        logging.getLogger('services.price_change_detector').setLevel(logging.DEBUG)
        click.echo('[VERBOSE] 詳細ログを有効にしました')
    
    try:
        detector = PriceChangeDetector()
        
        if dry_run:
            click.echo('[DRY RUN] 検出のみ実行します（データベースは更新されません）')
            price_changes = detector.detect_price_changes()
            
            if price_changes:
                click.echo(f'検出された価格変動: {len(price_changes)}件')
                for change in price_changes[:10]:  # 最初の10件のみ表示
                    click.echo(f'  - {change.game_title} ({change.store}): {change.change_type}')
                    if change.old_price:
                        click.echo(f'    {change.old_price} -> {change.new_price}')
                    else:
                        click.echo(f'    新規価格: ¥{change.new_price}')
                
                if len(price_changes) > 10:
                    click.echo(f'  ... 他 {len(price_changes) - 10}件')
            else:
                click.echo('価格変動は検出されませんでした')
        else:
            detector.process_price_changes()
            click.echo('価格変動検出・処理が完了しました')
        
    except Exception as e:
        click.echo(f'価格変動検出エラー: {e}')
        import traceback
        click.echo(traceback.format_exc())


def register_commands(app):
    """CLIコマンドを登録"""
    # ゲーム検索 - 統合版（自動切り替え）
    app.cli.add_command(search_games)
    app.cli.add_command(recent_games)
    app.cli.add_command(popular_games)
    
    # ゲーム検索 - データベース専用
    app.cli.add_command(search_db)
    app.cli.add_command(recent_games_db)
    app.cli.add_command(popular_games_db)
    
    # ゲーム検索 - Steam API専用
    app.cli.add_command(search_steam)
    app.cli.add_command(recent_games_steam)
    app.cli.add_command(popular_games_steam)
    
    # データベースデバッグと初期化
    app.cli.add_command(db_debug)
    app.cli.add_command(db_init)
    
    # 価格変動検出
    app.cli.add_command(detect_price_changes)
