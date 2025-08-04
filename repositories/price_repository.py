
DEFAULT_MAX_AGE_HOURS = 1

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from models import db, Price, User, Game

class PriceRepository:
    """
    価格情報のリポジトリクラス
    """
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session
        # 外部APIサービスの遅延インポート（循環参照回避）
        self._steam_service = None
        self._epic_service = None

    @property
    def steam_service(self):
        """Steam APIサービスを遅延初期化"""
        if self._steam_service is None:
            from services.steam_service import SteamAPIService
            self._steam_service = SteamAPIService()
        return self._steam_service

    @property
    def epic_service(self):
        """Epic Games Store APIサービスを遅延初期化"""
        if self._epic_service is None:
            from services.epic_service import EpicGamesStoreService
            self._epic_service = EpicGamesStoreService()
        return self._epic_service

    def is_price_data_stale(self, price: Price, max_age_hours: int = 1) -> bool:
        """
        価格データが古いかチェック
        
        Args:
            price: 価格データ
            max_age_hours: 最大経過時間（時間）
            
        Returns:
            bool: 古い場合はTrue
        """
        if not price:
            return True
            
        updated_at = getattr(price, 'updated_at', None)
        if not updated_at:
            return True
            
        now = datetime.now(timezone.utc)
        
        # updated_atがタイムゾーンナイーブの場合はUTCとして扱う
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        
        time_diff = now - updated_at
        return time_diff > timedelta(hours=max_age_hours)

    def get_latest_prices_with_refresh(self, game_id: int, max_age_hours: Optional[int] = None) -> List[Price]:
        """
        ゲームの最新価格情報を取得（古い場合は自動更新）
        
        Args:
            game_id: ゲームID
            max_age_hours: 価格データの最大経過時間（時間）、Noneの場合は設定ファイルから取得
            
        Returns:
            List[Price]: 価格情報のリスト
        """
        # 設定ファイルからデフォルト値を取得
        if max_age_hours is None:
            try:
                from flask import current_app
                config_value = current_app.config.get('PRICE_CACHE_MAX_AGE_HOURS', DEFAULT_MAX_AGE_HOURS)
                max_age_hours = int(config_value) if config_value is not None else DEFAULT_MAX_AGE_HOURS
            except RuntimeError:
                # Flask context外の場合のデフォルト値
                max_age_hours = DEFAULT_MAX_AGE_HOURS
        else:
            max_age_hours = int(max_age_hours)
        # 既存の価格データを取得
        existing_prices = self.get_latest_prices(game_id)
        
        # Steam価格データの確認と更新
        steam_price = next((p for p in existing_prices if getattr(p, 'store', '') == 'steam'), None)
        
        if not steam_price or self.is_price_data_stale(steam_price, max_age_hours):
            print(f"[DEBUG] 価格データが古いまたは存在しません。Steam APIから最新価格を取得します: game_id={game_id}")
            
            # ゲーム情報を取得してSteam App IDを確認
            game = self.session.query(Game).filter_by(id=game_id).first()
            if game and getattr(game, 'steam_appid', None):
                steam_appid = getattr(game, 'steam_appid')
                
                try:
                    # Steam APIから最新価格を取得
                    price_data = self.steam_service.get_game_price(steam_appid)
                    
                    if price_data and price_data.get('price') is not None:
                        if steam_price:
                            # 既存データを更新
                            setattr(steam_price, 'regular_price', Decimal(str(price_data.get('original_price', price_data.get('price', 0)))))
                            setattr(steam_price, 'sale_price', Decimal(str(price_data.get('price', 0))) if price_data.get('discount_percent', 0) > 0 else None)
                            setattr(steam_price, 'discount_rate', price_data.get('discount_percent', 0))
                            setattr(steam_price, 'is_on_sale', price_data.get('discount_percent', 0) > 0)
                            setattr(steam_price, 'updated_at', datetime.now(timezone.utc))
                            print(f"[DEBUG] Steam価格データ更新: game_id={game_id}, price=¥{price_data.get('price')}")
                        else:
                            # 新規データを作成
                            new_price = Price()
                            setattr(new_price, 'game_id', game_id)
                            setattr(new_price, 'store', 'steam')
                            setattr(new_price, 'regular_price', Decimal(str(price_data.get('original_price', price_data.get('price', 0)))))
                            setattr(new_price, 'sale_price', Decimal(str(price_data.get('price', 0))) if price_data.get('discount_percent', 0) > 0 else None)
                            setattr(new_price, 'discount_rate', price_data.get('discount_percent', 0))
                            setattr(new_price, 'currency', 'JPY')
                            setattr(new_price, 'is_on_sale', price_data.get('discount_percent', 0) > 0)
                            
                            self.session.add(new_price)
                            existing_prices.append(new_price)
                            print(f"[DEBUG] Steam価格データ新規作成: game_id={game_id}, price=¥{price_data.get('price')}")
                        
                        # 変更をコミット
                        self.session.commit()
                        
                    else:
                        print(f"[DEBUG] Steam APIから有効な価格データを取得できませんでした: game_id={game_id}")
                        
                except Exception as e:
                    print(f"[DEBUG] Steam価格取得エラー: game_id={game_id}, error={e}")
                    self.session.rollback()
            else:
                print(f"[DEBUG] Steam App IDが設定されていません: game_id={game_id}")
        
        # Epic Games Store価格データの確認と更新
        epic_price = next((p for p in existing_prices if getattr(p, 'store', '') == 'epic'), None)
        
        if not epic_price or self.is_price_data_stale(epic_price, max_age_hours):
            print(f"[DEBUG] Epic Games Store価格データが古いまたは存在しません。APIから最新価格を取得します: game_id={game_id}")
            
            # ゲーム情報を取得してEpic Games Store namespaceを確認
            game = self.session.query(Game).filter_by(id=game_id).first()
            epic_namespace = getattr(game, 'epic_namespace', None) if game else None
            
            # namespaceが未設定の場合、ゲーム名で検索して取得を試行
            if game and not epic_namespace:
                game_title = getattr(game, 'title', '')
                print(f"[DEBUG] Epic namespaceが未設定です。ゲーム名で検索します: {game_title}")
                # 一時的にEpic検索を無効化（検索機能の問題により）
                print(f"[DEBUG] Epic検索機能は現在無効化されています")
                epic_namespace = None
                # epic_namespace = self._search_and_save_epic_namespace(game, game_title)
            
            if epic_namespace:
                try:
                    # Epic Games Store APIから最新価格を取得
                    price_data = self.epic_service.get_game_price(epic_namespace)
                    
                    if price_data and price_data.get('price') is not None:
                        if epic_price:
                            # 既存データを更新
                            setattr(epic_price, 'regular_price', Decimal(str(price_data.get('original_price', price_data.get('price', 0)))))
                            setattr(epic_price, 'sale_price', Decimal(str(price_data.get('price', 0))) if price_data.get('discount_percent', 0) > 0 else None)
                            setattr(epic_price, 'discount_rate', price_data.get('discount_percent', 0))
                            setattr(epic_price, 'is_on_sale', price_data.get('discount_percent', 0) > 0)
                            setattr(epic_price, 'updated_at', datetime.now(timezone.utc))
                            print(f"[DEBUG] Epic Games Store価格データ更新: game_id={game_id}, price=¥{price_data.get('price')}")
                        else:
                            # 新規データを作成
                            new_price = Price()
                            setattr(new_price, 'game_id', game_id)
                            setattr(new_price, 'store', 'epic')
                            setattr(new_price, 'regular_price', Decimal(str(price_data.get('original_price', price_data.get('price', 0)))))
                            setattr(new_price, 'sale_price', Decimal(str(price_data.get('price', 0))) if price_data.get('discount_percent', 0) > 0 else None)
                            setattr(new_price, 'discount_rate', price_data.get('discount_percent', 0))
                            setattr(new_price, 'currency', 'JPY')
                            setattr(new_price, 'is_on_sale', price_data.get('discount_percent', 0) > 0)
                            
                            self.session.add(new_price)
                            existing_prices.append(new_price)
                            print(f"[DEBUG] Epic Games Store価格データ新規作成: game_id={game_id}, price=¥{price_data.get('price')}")
                        
                        # 変更をコミット
                        self.session.commit()
                        
                    else:
                        print(f"[DEBUG] Epic Games Store APIから有効な価格データを取得できませんでした: game_id={game_id}")
                        
                except Exception as e:
                    print(f"[DEBUG] Epic Games Store価格取得エラー: game_id={game_id}, error={e}")
                    self.session.rollback()
            else:
                print(f"[DEBUG] Epic Games Store namespaceが取得できませんでした: game_id={game_id}")
        else:
            print(f"[DEBUG] Epic Games Store価格データは最新です: game_id={game_id}, updated_at={getattr(epic_price, 'updated_at', None)}")
        
        # 最新の価格データを再取得して返す
        return self.get_latest_prices(game_id)

    def _search_and_save_epic_namespace(self, game: Game, game_title: str) -> Optional[str]:
        """
        ゲーム名でEpic Games Storeを検索してnamespaceを取得し、Gameモデルに保存
        
        Args:
            game: ゲームモデル
            game_title: ゲームタイトル
            
        Returns:
            Optional[str]: 見つかったnamespace（見つからない場合はNone）
        """
        try:
            print(f"[DEBUG] Epic Games Storeでゲーム検索: '{game_title}'")
            
            # タイムアウトと例外処理を追加
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Epic Games Store 検索がタイムアウトしました")
            
            # 10秒でタイムアウト
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                search_results = self.epic_service.search_games(game_title, limit=5)
            finally:
                signal.alarm(0)  # タイムアウトをクリア
            
            if not search_results:
                print(f"[DEBUG] Epic Games Storeで検索結果が見つかりませんでした: '{game_title}'")
                return None
            
            # 最初の結果を使用（通常は最も関連度の高い結果）
            first_result = search_results[0]
            epic_namespace = first_result.get('namespace')
            
            if epic_namespace:
                # Gameモデルにnamespaceを保存
                setattr(game, 'epic_namespace', epic_namespace)
                
                self.session.commit()
                print(f"[DEBUG] Epic namespace保存成功: game_id={getattr(game, 'id')}, namespace={epic_namespace}")
                return epic_namespace
            else:
                print(f"[DEBUG] 検索結果にnamespaceが含まれていませんでした: '{game_title}'")
                return None
                
        except TimeoutError as e:
            print(f"[DEBUG] Epic namespace検索タイムアウト: {e}")
            return None
        except Exception as e:
            print(f"[DEBUG] Epic namespace検索エラー: {e}")
            self.session.rollback()
            return None

    def get_latest_prices(self, game_id: int) -> List[Price]:
        """
        ゲームの最新価格情報を取得
        
        Args:
            game_id: ゲームID
            
        Returns:
            List[Price]: 価格情報のリスト
        """
        prices = self.session.query(Price).filter_by(game_id=game_id).order_by(Price.created_at.desc()).all()
        print(f"[DEBUG] get_latest_prices: game_id={game_id}, count={len(prices)}")
        for p in prices:
            print(f"[DEBUG]  store={p.store}, price={p.get_current_price()}, sale={p.is_on_sale}, updated={p.updated_at}")
        return prices

    def get_formatted_prices_for_game(self, game_id: int, max_age_hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        ゲームの価格情報をフォーマットして取得（古い場合は自動更新）
        
        Args:
            game_id: ゲームID
            max_age_hours: 価格データの最大経過時間（時間）、Noneの場合は設定ファイルから取得
            
        Returns:
            List[Dict[str, Any]]: フォーマットされた価格情報のリスト
        """
        prices = self.get_latest_prices_with_refresh(game_id, max_age_hours)
        formatted_prices = []
        
        for price in prices:
            current_price = price.get_current_price()
            if current_price is None:
                continue
                
            regular_price = getattr(price, 'regular_price', None)
            discount_rate = getattr(price, 'discount_rate', 0)
            
            formatted_price = {
                'store': price.store,
                'price': float(current_price),
                'original_price': float(regular_price) if regular_price else float(current_price),
                'discount_percent': discount_rate or 0,
                'store_url': price.get_store_url(),
                'updated_at': price.updated_at,
                'is_on_sale': price.is_on_sale
            }
            formatted_prices.append(formatted_price)
        
        return formatted_prices

    def get_lowest_price_for_game(self, game_id: int, max_age_hours: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        ゲームの最安値情報を取得（古い場合は自動更新）
        
        Args:
            game_id: ゲームID
            max_age_hours: 価格データの最大経過時間（時間）、Noneの場合は設定ファイルから取得
            
        Returns:
            Optional[Dict[str, Any]]: 最安値情報（見つからない場合はNone）
        """
        formatted_prices = self.get_formatted_prices_for_game(game_id, max_age_hours)
        
        if not formatted_prices:
            return None
        
        lowest_price = min(formatted_prices, key=lambda p: p['price'])
        return lowest_price

    def save(self, price: Price) -> Price:
        self.session.add(price)
        self.session.flush()
        print(f"[DEBUG] save: store={price.store}, price={price.get_current_price()}, game_id={price.game_id}")
        return price

    def get_users_for_notification(self, game_id: int) -> List[User]:
        from models.favorite import Favorite
        users = self.session.query(User).join(Favorite).filter(
            Favorite.game_id == game_id,
            Favorite.notification_enabled == True
        ).all()
        print(f"[DEBUG] get_users_for_notification: game_id={game_id}, user_count={len(users)}")
        return users

    def commit(self):
        self.session.commit()
        print("[DEBUG] commit: transaction committed")

    def rollback(self):
        self.session.rollback()
        print("[DEBUG] rollback: transaction rolled back") 