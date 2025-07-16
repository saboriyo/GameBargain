"""
GameBargain サービス層の初期化モジュール

このモジュールはサービス層の基盤クラスとユーティリティを提供します。
全てのサービスクラスで共通的に使用される機能を含んでいます。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

# サービスクラス
from .game_search_service import GameSearchService
import logging
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError


class BaseService(ABC):
    """
    サービス層の基底クラス
    
    全てのサービスクラスが継承する基底クラスです。
    共通的な機能やエラーハンドリングを提供します。
    
    Attributes:
        logger (logging.Logger): ログ出力用のロガー
    """
    
    def __init__(self):
        """基底サービスクラスの初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _handle_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """
        エラーハンドリングの共通処理
        
        Args:
            error (Exception): 発生したエラー
            operation (str): 実行していた処理名
            
        Returns:
            Dict[str, Any]: エラー情報を含む辞書
        """
        error_message = f"{operation}でエラーが発生しました: {str(error)}"
        self.logger.error(error_message, exc_info=True)
        
        if isinstance(error, SQLAlchemyError):
            return {
                'success': False,
                'error': 'database_error',
                'message': 'データベースエラーが発生しました',
                'details': str(error) if current_app.debug else None
            }
        elif isinstance(error, ValueError):
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(error),
                'details': None
            }
        else:
            return {
                'success': False,
                'error': 'internal_error',
                'message': '内部エラーが発生しました',
                'details': str(error) if current_app.debug else None
            }
    
    def _create_success_response(self, data: Any = None, message: str = "処理が正常に完了しました") -> Dict[str, Any]:
        """
        成功レスポンスの作成
        
        Args:
            data (Any, optional): レスポンスデータ
            message (str): 成功メッセージ
            
        Returns:
            Dict[str, Any]: 成功レスポンス
        """
        response = {
            'success': True,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
            
        return response
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        必須フィールドのバリデーション
        
        Args:
            data (Dict[str, Any]): バリデーション対象のデータ
            required_fields (List[str]): 必須フィールドのリスト
            
        Raises:
            ValueError: 必須フィールドが不足している場合
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            raise ValueError(f"必須フィールドが不足しています: {', '.join(missing_fields)}")
    
    def _validate_positive_number(self, value: Any, field_name: str) -> float:
        """
        正の数値のバリデーション
        
        Args:
            value (Any): バリデーション対象の値
            field_name (str): フィールド名
            
        Returns:
            float: バリデーション済みの数値
            
        Raises:
            ValueError: 値が正の数値でない場合
        """
        try:
            num_value = float(value)
            if num_value <= 0:
                raise ValueError(f"{field_name}は正の数値である必要があります")
            return num_value
        except (TypeError, ValueError):
            raise ValueError(f"{field_name}は有効な数値である必要があります")
    
    def _validate_string_length(self, value: str, field_name: str, min_length: int = 1, max_length: int = 255) -> str:
        """
        文字列長のバリデーション
        
        Args:
            value (str): バリデーション対象の文字列
            field_name (str): フィールド名
            min_length (int): 最小長
            max_length (int): 最大長
            
        Returns:
            str: バリデーション済みの文字列
            
        Raises:
            ValueError: 文字列長が無効な場合
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name}は文字列である必要があります")
        
        if len(value) < min_length:
            raise ValueError(f"{field_name}は{min_length}文字以上である必要があります")
        
        if len(value) > max_length:
            raise ValueError(f"{field_name}は{max_length}文字以下である必要があります")
        
        return value.strip()


class ServiceError(Exception):
    """
    サービス層で発生する例外の基底クラス
    
    サービス層固有のエラーを表現するための例外クラスです。
    
    Attributes:
        error_code (str): エラーコード
        message (str): エラーメッセージ
        details (Dict[str, Any]): エラーの詳細情報
    """
    
    def __init__(self, message: str, error_code: str = "service_error", details: Dict[str, Any] = None):
        """
        サービスエラーの初期化
        
        Args:
            message (str): エラーメッセージ
            error_code (str): エラーコード
            details (Dict[str, Any], optional): エラーの詳細情報
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(ServiceError):
    """
    バリデーションエラー
    
    入力データのバリデーションで発生するエラーを表現します。
    """
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        """
        バリデーションエラーの初期化
        
        Args:
            message (str): エラーメッセージ
            field (str, optional): エラーが発生したフィールド名
            details (Dict[str, Any], optional): エラーの詳細情報
        """
        super().__init__(message, "validation_error", details)
        self.field = field


class BusinessLogicError(ServiceError):
    """
    ビジネスロジックエラー
    
    ビジネスルール違反で発生するエラーを表現します。
    """
    
    def __init__(self, message: str, rule: str = None, details: Dict[str, Any] = None):
        """
        ビジネスロジックエラーの初期化
        
        Args:
            message (str): エラーメッセージ
            rule (str, optional): 違反したビジネスルール名
            details (Dict[str, Any], optional): エラーの詳細情報
        """
        super().__init__(message, "business_logic_error", details)
        self.rule = rule


class ExternalServiceError(ServiceError):
    """
    外部サービスエラー
    
    外部APIやサービスとの連携で発生するエラーを表現します。
    """
    
    def __init__(self, message: str, service: str = None, status_code: int = None, details: Dict[str, Any] = None):
        """
        外部サービスエラーの初期化
        
        Args:
            message (str): エラーメッセージ
            service (str, optional): エラーが発生した外部サービス名
            status_code (int, optional): HTTPステータスコード
            details (Dict[str, Any], optional): エラーの詳細情報
        """
        super().__init__(message, "external_service_error", details)
        self.service = service
        self.status_code = status_code


def create_pagination_info(page: int, per_page: int, total: int) -> Dict[str, Any]:
    """
    ページネーション情報の作成
    
    Args:
        page (int): 現在のページ番号
        per_page (int): 1ページあたりのアイテム数
        total (int): 総アイテム数
        
    Returns:
        Dict[str, Any]: ページネーション情報
    """
    pages = (total - 1) // per_page + 1 if total > 0 else 1
    has_prev = page > 1
    has_next = page < pages
    
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_num': page - 1 if has_prev else None,
        'next_num': page + 1 if has_next else None,
        'start_index': (page - 1) * per_page + 1 if total > 0 else 0,
        'end_index': min(page * per_page, total)
    }


def format_currency(amount: float, currency: str = 'JPY') -> str:
    """
    通貨フォーマット
    
    Args:
        amount (float): 金額
        currency (str): 通貨コード
        
    Returns:
        str: フォーマット済みの金額文字列
    """
    if currency == 'JPY':
        return f"¥{int(amount):,}"
    elif currency == 'USD':
        return f"${amount:.2f}"
    elif currency == 'EUR':
        return f"€{amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def calculate_discount_percentage(original_price: float, discounted_price: float) -> float:
    """
    割引率の計算
    
    Args:
        original_price (float): 元の価格
        discounted_price (float): 割引後の価格
        
    Returns:
        float: 割引率（パーセント）
    """
    if original_price <= 0:
        return 0.0
    
    discount = ((original_price - discounted_price) / original_price) * 100
    return max(0.0, round(discount, 1))


def sanitize_string(text: str, max_length: int = None) -> str:
    """
    文字列のサニタイズ
    
    Args:
        text (str): サニタイズ対象の文字列
        max_length (int, optional): 最大長
        
    Returns:
        str: サニタイズ済みの文字列
    """
    if not isinstance(text, str):
        return ""
    
    # 基本的なサニタイズ
    sanitized = text.strip()
    
    # 最大長の制限
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized


__all__ = [
    'BaseService',
    'GameSearchService',
    'ServiceError',
    'ValidationError',
    'BusinessLogicError',
    'ExternalServiceError',
    'create_pagination_info',
    'format_currency',
    'calculate_discount_percentage',
    'sanitize_string'
]
