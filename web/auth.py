"""
Authentication Routes

認証関連のルーティング
"""

from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """ログインページ"""
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """ログアウト"""
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/discord')
def discord_login():
    """Discord OAuth認証開始"""
    # TODO: Discord OAuth2の実装
    # 今は簡易的にダミーログインを実装
    flash('Discord認証機能は開発中です。', 'warning')
    return redirect(url_for('main.index'))

@auth_bp.route('/discord/callback')
def discord_callback():
    """Discord OAuth認証コールバック"""
    # TODO: Discord OAuth2コールバックの実装
    flash('Discord認証機能は開発中です。', 'warning')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """ユーザープロフィールページ"""
    return render_template('user.html', user=current_user)
