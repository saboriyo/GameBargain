"""
Authentication Routes

認証関連のルーティング
Discord OAuth認証、ログイン・ログアウト機能を提供します。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlencode
import requests
from typing import Optional, Dict, Any
from os import getenv

# ブループリントの作成
auth_bp = Blueprint('auth', __name__)

# グローバル変数として定義
REDIRECT_URI = getenv('DISCORD_REDIRECT_URI', 'http://localhost:8000/auth/discord/callback')


@auth_bp.route('/login')
def login():
    """
    ログインページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    # 既にログイン済みの場合はトップページにリダイレクト
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html', page_title='ログイン')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    ログアウト処理
    
    Returns:
        Response: リダイレクトレスポンス
    """
    username = current_user.username if hasattr(current_user, 'username') else 'ユーザー'
    logout_user()
    flash(f'{username}さん、ログアウトしました。', 'info')
    current_app.logger.info(f"ユーザーがログアウトしました: {username}")
    return redirect(url_for('main.index'))


@auth_bp.route('/discord')
def discord_login():
    """
    Discord OAuth認証開始
    
    Returns:
        Response: Discord認証ページへのリダイレクト
    """
    # Discord OAuth2設定の確認
    client_id = current_app.config.get('DISCORD_CLIENT_ID')
    
    if not client_id or not REDIRECT_URI:
        flash('Discord認証の設定が完了していません。管理者にお問い合わせください。', 'error')
        return redirect(url_for('auth.login'))
    
    # Discord OAuth2パラメータ
    discord_oauth_url = 'https://discord.com/api/oauth2/authorize'
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify email connections guilds guilds.join',
        'state': 'gamebargain_auth'  # CSRF保護
    }
    
    # セッションに状態を保存（CSRF対策）
    session['oauth_state'] = params['state']
    
    oauth_url = f"{discord_oauth_url}?{urlencode(params)}"
    current_app.logger.info(f"Generated OAuth URL: {oauth_url}")
    
    return redirect(oauth_url)


@auth_bp.route('/discord/callback')
def discord_callback():
    """
    Discord OAuth認証コールバック
    
    Returns:
        Response: 認証後のリダイレクト
    """
    # エラーチェック
    error = request.args.get('error')
    if error:
        flash(f'Discord認証がキャンセルされました: {error}', 'warning')
        return redirect(url_for('auth.login'))
    
    # 認証コード取得
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        flash('認証コードが取得できませんでした。', 'error')
        return redirect(url_for('auth.login'))
    
    # CSRF保護: stateパラメータの検証
    if state != session.get('oauth_state'):
        flash('無効な認証状態です。再度ログインしてください。', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # アクセストークンの取得
        token_data = get_discord_token(code)
        if not token_data:
            flash('Discord認証に失敗しました。', 'error')
            return redirect(url_for('auth.login'))
        
        # ユーザー情報の取得
        user_info = get_discord_user_info(token_data['access_token'])
        if not user_info:
            flash('ユーザー情報の取得に失敗しました。', 'error')
            return redirect(url_for('auth.login'))
        
        # ユーザーの作成またはログイン
        user = handle_discord_user(user_info, token_data)
        if user:
            login_user(user, remember=True)
            flash(f'{user.username}さん、ログインしました！', 'success')
            current_app.logger.info(f"Discord認証ログイン成功: {user.username}")
            
            # リダイレクト先の決定
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('ユーザー情報の処理に失敗しました。', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Discord認証エラー: {e}")
        flash('認証処理中にエラーが発生しました。', 'error')
    
    return redirect(url_for('auth.login'))


def get_discord_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Discord認証コードからアクセストークンを取得
    
    Args:
        code: Discord認証コード
        
    Returns:
        Optional[Dict[str, Any]]: トークンデータ、失敗時はNone
    """
    token_url = 'https://discord.com/api/oauth2/token'
    
    data = {
        'client_id': current_app.config.get('DISCORD_CLIENT_ID'),
        'client_secret': current_app.config.get('DISCORD_CLIENT_SECRET'),
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(token_url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Discordトークン取得エラー: {e}")
        return None


def get_discord_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Discordアクセストークンからユーザー情報を取得
    
    Args:
        access_token: Discordアクセストークン
        
    Returns:
        Optional[Dict[str, Any]]: ユーザー情報、失敗時はNone
    """
    user_url = 'https://discord.com/api/users/@me'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(user_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Discordユーザー情報取得エラー: {e}")
        return None


def handle_discord_user(user_info: Dict[str, Any], token_data: Dict[str, Any]):
    """
    Discordユーザー情報を処理してUser インスタンスを作成/更新
    
    Args:
        user_info: Discordユーザー情報
        token_data: Discordトークンデータ
        
    Returns:
        User: ユーザーインスタンス、失敗時はNone
    """
    try:
        # TODO: 実際のデータベース操作を実装
        # ここではダミーユーザーを返す
        from models.user import create_user_model
        from models import User
        from app import db
        
        
        # Discord IDでユーザーを検索
        discord_id = user_info.get('id')
        user = User.query.filter_by(discord_id=discord_id).first()
        
        if not user:
            # 新規ユーザー作成
            username = user_info.get('username', '')
            if discord_id and username:
                user = User(
                    discord_id=str(discord_id),
                    username=username
                )
                db.session.add(user)
        
        # ユーザー情報の更新（setattrを使用）
        if user:
            setattr(user, 'username', user_info.get('username', ''))
            setattr(user, 'discriminator', user_info.get('discriminator'))
            setattr(user, 'email', user_info.get('email'))
            setattr(user, 'avatar_url', get_discord_avatar_url(user_info))
            setattr(user, 'access_token', token_data.get('access_token'))
            setattr(user, 'refresh_token', token_data.get('refresh_token'))
            
            # トークン有効期限の設定
            from datetime import datetime, timedelta, timezone
            expires_in = token_data.get('expires_in', 3600)
            setattr(user, 'token_expires_at', datetime.now(timezone.utc) + timedelta(seconds=expires_in))
            
            user.update_last_login()
        
        db.session.commit()
        return user
        
    except Exception as e:
        current_app.logger.error(f"Discordユーザー処理エラー: {e}")
        if 'db' in locals():
            db.session.rollback()
        return None


def get_discord_avatar_url(user_info: Dict[str, Any]) -> Optional[str]:
    """
    Discordアバター画像URLを生成
    
    Args:
        user_info: Discordユーザー情報
        
    Returns:
        Optional[str]: アバター画像URL
    """
    user_id = user_info.get('id')
    avatar_hash = user_info.get('avatar')
    
    if not user_id:
        return None
    
    if avatar_hash:
        # カスタムアバター
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    else:
        # デフォルトアバター
        discriminator = user_info.get('discriminator', '0001')
        default_avatar = int(discriminator) % 5
        return f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"


def is_safe_url(target: str) -> bool:
    """
    安全なリダイレクト先URLかチェック
    
    Args:
        target: チェック対象URL
        
    Returns:
        bool: 安全な場合True
    """
    # 相対URLのみ許可（オープンリダイレクト対策）
    return target.startswith('/') and not target.startswith('//')


@auth_bp.route('/profile')
@login_required
def profile():
    """
    ユーザープロフィールページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    return render_template('auth/profile.html', 
                         user=current_user,
                         page_title='プロフィール')


@auth_bp.route('/settings')
@login_required
def settings():
    """
    ユーザー設定ページ
    
    Returns:
        str: レンダリングされたHTMLテンプレート
    """
    return render_template('auth/settings.html', 
                         user=current_user,
                         page_title='設定')
