"""
Test Configuration

テスト用の設定とフィクスチャ
"""

import pytest
import os
from app import create_app, db
from config import TestingConfig


@pytest.fixture
def app():
    """テスト用Flaskアプリケーションフィクスチャ"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """テスト用クライアントフィクスチャ"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """テスト用CLIランナーフィクスチャ"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """認証ヘッダーフィクスチャ"""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }
