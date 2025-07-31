"""
Price Model

価格情報を管理するモデル
現在価格と価格履歴を管理します。
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, TYPE_CHECKING, Any

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, DECIMAL, Index
from sqlalchemy.orm import relationship
from models import db

# 型チェック時のみインポート（循環参照回避）
if TYPE_CHECKING:
    from .game import Game


class Price(db.Model):
    """
    現在価格モデル (設計書 3.3.3 準拠)
    
    各ストアの最新価格情報を管理します。
    セール情報や割引率も含みます。
    """
    __tablename__ = 'prices'
    
    # プライマリキー
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    store = Column(String(20), nullable=False)  # 'steam', 'epic'
    regular_price = Column(DECIMAL(10, 2))
    sale_price = Column(DECIMAL(10, 2))
    discount_rate = Column(Integer, default=0)  # 割引率 (0-100)
    currency = Column(String(3), default='JPY')
    is_on_sale = Column(Boolean, default=False, index=True)
    sale_start_date = Column(DateTime)
    sale_end_date = Column(DateTime)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index('idx_prices_game_store', 'game_id', 'store'),
    )
    
    # リレーションシップ（型チェック時のみ型注釈）
    if TYPE_CHECKING:
        game: 'Game'
    else:
        game = relationship('Game', back_populates='prices')
    
    def get_current_price(self) -> Optional[Decimal]:
        """
        現在の有効価格を取得
        
        Returns:
            Optional[Decimal]: セール中の場合はセール価格、そうでなければ通常価格
        """
        is_on_sale = getattr(self, 'is_on_sale', False)
        if is_on_sale:
            sale_price = getattr(self, 'sale_price', None)
            if sale_price is not None:
                return Decimal(str(sale_price))
        
        regular_price = getattr(self, 'regular_price', None)
        if regular_price is not None:
            return Decimal(str(regular_price))
        
        return None
    
    def update_price(self, regular_price: Decimal, sale_price: Optional[Decimal] = None,
                    discount_rate: int = 0, is_on_sale: bool = False) -> None:
        """
        価格情報を更新
        
        Args:
            regular_price: 通常価格
            sale_price: セール価格
            discount_rate: 割引率
            is_on_sale: セール中フラグ
        """
        setattr(self, 'regular_price', regular_price)
        setattr(self, 'sale_price', sale_price)
        setattr(self, 'discount_rate', discount_rate)
        setattr(self, 'is_on_sale', is_on_sale)
        
        # セール期間の自動設定
        if is_on_sale:
            setattr(self, 'sale_start_date', datetime.now(timezone.utc))
        else:
            setattr(self, 'sale_end_date', datetime.now(timezone.utc))
    
    def calculate_savings(self) -> Decimal:
        """
        節約額を計算
        
        Returns:
            Decimal: 節約額（通常価格 - セール価格）
        """
        regular_price = getattr(self, 'regular_price', None)
        sale_price = getattr(self, 'sale_price', None)
        
        if regular_price and sale_price:
            return Decimal(str(regular_price)) - Decimal(str(sale_price))
        return Decimal('0')
    
    def is_sale_active(self) -> bool:
        """
        セールが有効かチェック
        
        Returns:
            bool: セールが有効な場合True
        """
        is_on_sale = getattr(self, 'is_on_sale', False)
        if not is_on_sale:
            return False
        
        now = datetime.now(timezone.utc)
        sale_start = getattr(self, 'sale_start_date', None)
        sale_end = getattr(self, 'sale_end_date', None)
        
        # 開始日のチェック
        if sale_start and now < sale_start:
            return False
        
        # 終了日のチェック
        if sale_end and now > sale_end:
            return False
        
        return True
    
    def get_store_url(self) -> Optional[str]:
        """
        ストアURLを動的に生成
        
        Returns:
            Optional[str]: ストアURL（生成できない場合はNone）
        """
        store = getattr(self, 'store', '')
        
        if store == 'steam' and hasattr(self, 'game'):
            game = getattr(self, 'game', None)
            if game:
                steam_appid = getattr(game, 'steam_appid', None)
                if steam_appid:
                    return f"https://store.steampowered.com/app/{steam_appid}/"
        
        # TODO: 他のストア（Epic Games Store等）のURL生成を追加
        
        return None
    
    def get_formatted_price(self) -> str:
        """
        フォーマット済み価格文字列を取得
        
        Returns:
            str: フォーマット済み価格
        """
        current_price = self.get_current_price()
        if current_price is None:
            return "価格不明"
        
        currency = getattr(self, 'currency', 'JPY')
        
        if currency == 'JPY':
            return f"¥{current_price:,.0f}" if current_price % 1 == 0 else f"¥{current_price:,.2f}"
        else:
            return f"{currency} {current_price:,.2f}"
    
    def __repr__(self) -> str:
        """
        文字列表現
        
        Returns:
            str: 価格の文字列表現
        """
        store = getattr(self, 'store', 'Unknown')
        formatted_price = self.get_formatted_price()
        return f'<Price {store}: {formatted_price}>'


