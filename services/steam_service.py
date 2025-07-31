# -*- coding: utf-8 -*-
"""Steam API Service

Steam Web APIを使用してゲーム情報を取得するサービス。
APIキーなしで利用可能なエンドポイントを使用します。
"""

import requests
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class SteamAPIService:
    """Steam API サービスクラス
    
    Steam Web APIからゲーム情報を取得します。
    """
    
    # Steam API エンドポイント
    BASE_URL = "https://api.steampowered.com"
    STORE_BASE_URL = "https://store.steampowered.com/api"
    
    def __init__(self):
        """Steam API サービスの初期化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GameBargain/1.0'
        })
        self._app_list_cache = None
        self._cache_timestamp = None
        
    def get_app_list(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        全Steamアプリケーション一覧を取得
        
        Args:
            force_refresh: キャッシュを無視して強制取得
            
        Returns:
            List[Dict]: アプリケーション一覧
        """
        try:
            # キャッシュチェック（1時間有効）
            if (not force_refresh and 
                self._app_list_cache and 
                self._cache_timestamp and 
                (datetime.now() - self._cache_timestamp).seconds < 3600):
                return self._app_list_cache
            
            logger.info("Steam API からアプリケーション一覧を取得中...")
            
            url = f"{self.BASE_URL}/ISteamApps/GetAppList/v2/"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            app_list = data.get('applist', {}).get('apps', [])

            # ゲームのみをフィルタリング (DLCやツールを除外 )
            game_apps = []
            for app in app_list:
                name = app.get('name', '').lower()
                if not name or len(name) < 3:
                    continue
                # DLC、サウンドトラック、ツールなどを除外
                if any(keyword in name for keyword in [
                    'dlc', 'soundtrack', 'demo', 'beta', 'test', 
                    'dedicated server', 'tool', 'benchmark', 'trailer', 
                    'mod', 'asset', 'pack', 'bundle', 'collection', '追加'
                ]):
                    continue
                game_apps.append(app)
            
            # キャッシュ更新
            self._app_list_cache = app_list
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Steam アプリケーション {len(app_list)} 件を取得しました")
            return app_list
            
        except Exception as e:
            logger.error(f"Steam API アプリ一覧取得エラー: {e}")
            return self._app_list_cache or []
    
    def search_games(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        ゲーム検索
        
        Args:
            query: 検索クエリ
            limit: 結果数制限
            
        Returns:
            List[Dict]: 検索結果
        """
        try:
            logger.info(f"Steam でゲーム検索: '{query}'")
            
            # アプリ一覧から検索
            app_list = self.get_app_list()
            if not app_list:
                return []
            
            # 名前で検索（大文字小文字を無視）
            query_lower = query.lower()
            matches = []
            
            for app in app_list:
                name = app.get('name', '').lower()
                if query_lower in name:
                    matches.append(app)
                    if len(matches) >= limit * 2:  # 詳細取得で失敗する可能性があるので多めに取得
                        break
            
            # 詳細情報を取得
            detailed_games = []
            for app in matches[:limit * 2]:
                detail = self.get_app_details(app['appid'])
                if detail and detail.get('success'):
                    game_data = detail.get('data', {})
                    
                    # ゲームタイプのみ（DLC等を除外）
                    if game_data.get('type') == 'game':
                        detailed_games.append({
                            'steam_appid': app['appid'],
                            'title': game_data.get('name', app['name']),
                            'description': game_data.get('short_description', ''),
                            'developer': ', '.join(game_data.get('developers', [])),
                            'publisher': ', '.join(game_data.get('publishers', [])),
                            'release_date': self._parse_release_date(game_data.get('release_date', {})),
                            'genres': [genre['description'] for genre in game_data.get('genres', [])],
                            'image_url': game_data.get('header_image'),
                            'steam_url': f"https://store.steampowered.com/app/{app['appid']}/",
                            'price_info': self._extract_price_info(game_data),
                            'metacritic_score': game_data.get('metacritic', {}).get('score'),
                            'steam_rating': self._calculate_steam_rating(game_data)
                        })
                        
                        if len(detailed_games) >= limit:
                            break
                
                # API制限を考慮して短い間隔を置く
                time.sleep(0.2)
            
            logger.info(f"Steam 検索結果: {len(detailed_games)} 件")
            return detailed_games
            
        except Exception as e:
            logger.error(f"Steam ゲーム検索エラー: {e}")
            return []
    
    def get_app_details(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Steamアプリの詳細情報を取得
        
        Args:
            appid: Steam アプリID
            
        Returns:
            Optional[Dict]: アプリ詳細情報
            success: True/False
            data: 詳細情報辞書
                name: アプリ名
                steam_appid: アプリID
                required_age: 年齢制限
                is_free: 無料かどうか
                detailed_description: 詳細説明
                short_description: 簡易説明
                fullgame: appid,name
                supported_languages: 対応言語
                header_image: ヘッダー画像URL
                capsule_image: カプセル画像URL
                capsule_imagev5: カプセル画像URL (新)
                website: 公式サイトURL
                pc_requirements: PC要件
                mac_requirements: Mac要件
                linux_requirements: Linux要件
                developers: 開発者リスト
                price_overview: 価格情報
                    currency,initial,final,discount_percent,initial_formatted,final_formatted
                packages: パッケージ情報
                package_groups: パッケージグループ情報
                screenshots: スクリーンショットリスト
                path_full: 完全なパス
                release_date: リリース日
                support_info: サポート情報
                background: 背景画像URL
                background_raw: 背景画像URL (新)
                content_descriptors: コンテンツ記述子
                ratings: 制限のやつ
                    dejus:
                        rating_generated
                        rating: 14,lなど
                        required_age: 年齢制限
                        banned: 
                steam_germany

        """
        try:
            url = f"{self.STORE_BASE_URL}/appdetails"
            params = {
                'appids': appid,
                'cc': 'jp',  # 日本の価格情報
                'l': 'japanese'  # 日本語
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            app_data = data.get(str(appid))
            
            return app_data
            
        except Exception as e:
            logger.error(f"Steam アプリ詳細取得エラー (appid: {appid}): {e}")
            return None
    
    def get_recent_games(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        適当なゲーム一覧を取得（詳細情報を含む）

        Steam APIから適当にゲーム情報を取得します。
        価格が0より大きいゲームのみを取得します。
        
        Args:
            limit: 取得数制限
            
        Returns:
            List[Dict]: ゲーム一覧
        """
        try:
            logger.info(f"Steam API から適当なゲーム {limit} 件を取得中...")

            # アプリ一覧を取得
            game_apps = self.get_app_list()
            if not game_apps:
                logger.warning("Steam アプリ一覧の取得に失敗しました")
                return []
            
            

            # 適当に選択（AppIDが大きいものから順番に）
            selected_apps = sorted(game_apps, key=lambda x: x.get('appid', 0), reverse=True)[:limit * 2]

            recent_games: List[Dict[str, Any]] = []

            for app in selected_apps:
                if len(recent_games) >= limit:
                    break

                # 詳細情報を取得
                detail = self.get_app_details(app['appid'])
                if detail and detail.get('success'):
                    game_data = detail.get('data', {})

                    # ゲームタイプのみ（DLC等を除外）
                    if game_data.get('type') == 'game':
                            detailed_game = {
                                'steam_appid': app['appid'],
                                'title': game_data.get('name', app['name']),
                                'description': game_data.get('short_description', ''),
                                'developer': ', '.join(game_data.get('developers', [])),
                                'publisher': ', '.join(game_data.get('publishers', [])),
                                'release_date': self._parse_release_date(game_data.get('release_date', {})),
                                'genres': [genre['description'] for genre in game_data.get('genres', [])],
                                'image_url': game_data.get('header_image'),
                                'steam_url': f"https://store.steampowered.com/app/{app['appid']}/",
                                'price_info': self._extract_price_info(game_data),
                                'metacritic_score': game_data.get('metacritic', {}).get('score'),
                                'steam_rating': self._calculate_steam_rating(game_data)
                            }

                            recent_games.append(detailed_game)

                # API制限を考慮して短い間隔を置く
                time.sleep(0.2)

            logger.info(f"適当なゲーム {len(recent_games)} 件を取得しました")
            return recent_games

        except Exception as e:
            logger.error(f"適当なゲーム取得エラー: {e}")
            return []
    
    def _parse_release_date(self, release_data: Dict) -> Optional[str]:
        """
        リリース日をパース
        
        Args:
            release_data: Steam APIのリリース日データ
            
        Returns:
            Optional[str]: ISO形式の日付文字列
        """
        try:
            if not release_data or not release_data.get('date'):
                return None
            
            date_str = release_data['date']
            
            # 様々な日付フォーマットに対応
            formats = [
                '%d %b, %Y',    # 10 Dec, 2020
                '%b %d, %Y',    # Dec 10, 2020
                '%b %Y',        # Dec 2020
                '%Y'            # 2020
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _extract_price_info(self, game_data: Dict) -> Dict[str, Any]:
        """
        価格情報を抽出
        
        Args:
            game_data: Steam APIのゲームデータ
            
        Returns:
            Dict: 価格情報
        """
        try:
            price_info = {
                'is_free': game_data.get('is_free', False),
                'current_price': None,
                'original_price': None,
                'discount_percent': 0,
                'formatted_price': 'Free to Play' if game_data.get('is_free') else None
            }
            
            price_overview = game_data.get('price_overview')
            if price_overview:
                price_info.update({
                    'current_price': price_overview.get('final') / 100 if price_overview.get('final') else None,
                    'original_price': price_overview.get('initial') / 100 if price_overview.get('initial') else None,
                    'discount_percent': price_overview.get('discount_percent', 0),
                    'formatted_price': price_overview.get('final_formatted')
                })
            
            return price_info
            
        except Exception:
            return {
                'is_free': False,
                'current_price': None,
                'original_price': None,
                'discount_percent': 0,
                'formatted_price': None
            }
    
    def _calculate_steam_rating(self, game_data: Dict) -> Optional[int]:
        """
        Steam レビュー評価を計算
        
        Args:
            game_data: Steam APIのゲームデータ
            
        Returns:
            Optional[int]: 評価スコア (0-100)
        """
        try:
            recommendations = game_data.get('recommendations')
            if recommendations and recommendations.get('total'):
                # 簡易的な評価計算（実際のSteamの計算式とは異なる）
                total = recommendations['total']
                if total > 10:  # 最小レビュー数
                    # Steam の "Very Positive" などの評価を数値化
                    rating_text = game_data.get('steam_rating', {}).get('rating_generated_internally')
                    if rating_text:
                        rating_map = {
                            'overwhelmingly positive': 95,
                            'very positive': 85,
                            'positive': 75,
                            'mostly positive': 70,
                            'mixed': 60,
                            'mostly negative': 40,
                            'negative': 30,
                            'very negative': 20,
                            'overwhelmingly negative': 10
                        }
                        return rating_map.get(rating_text.lower(), 60)
                    
                    # レビュー数から推定
                    if total > 1000:
                        return 80
                    elif total > 100:
                        return 70
                    else:
                        return 60
            
            return None
            
        except Exception:
            return None

    def get_game_price(self, app_id: str) -> Optional[Dict[str, Any]]:
        """
        指定されたゲームの価格情報を取得
        
        Args:
            app_id: Steam App ID
            
        Returns:
            Optional[Dict[str, Any]]: 価格情報（見つからない場合はNone）
        """
        try:
            # Steam Store API を使用して価格情報を取得
            url = f"{self.STORE_BASE_URL}/appdetails"
            params = {
                'appids': app_id,
                'filters': 'price_overview',
                'cc': 'jp'  # 日本の価格
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Steam API response for {app_id}: {type(data)} - {data}")
            
            # データが辞書でない場合の対処
            if not isinstance(data, dict):
                logger.warning(f"Steam APIから予期しないデータ形式: {type(data)} (App ID: {app_id})")
                return None
            
            app_data = data.get(str(app_id))
            
            # app_dataがNoneまたは辞書でない場合の対処
            if not app_data or not isinstance(app_data, dict):
                logger.warning(f"App data not found or invalid format for App ID {app_id}: {app_data}")
                return None
            
            if not app_data.get('success'):
                logger.warning(f"Steam価格取得失敗: App ID {app_id} - {app_data}")
                return None
            
            # dataフィールドの確認
            app_detail_data = app_data.get('data')
            if not app_detail_data or not isinstance(app_detail_data, dict):
                logger.debug(f"App detail data not found for App ID {app_id}")
                # 無料ゲームまたは価格情報がない場合
                return {
                    'price': 0,
                    'original_price': 0,
                    'discount_percent': 0,
                    'currency': 'JPY',
                    'is_on_sale': False
                }
            
            price_overview = app_detail_data.get('price_overview')
            
            if not price_overview or not isinstance(price_overview, dict):
                # 無料ゲームの場合
                logger.debug(f"No price overview for App ID {app_id} - likely free game")
                return {
                    'price': 0,
                    'original_price': 0,
                    'discount_percent': 0,
                    'currency': 'JPY',
                    'is_on_sale': False
                }
            
            # 価格情報を整形
            current_price = price_overview.get('final', 0) / 100  # セント単位から円に変換
            initial_price = price_overview.get('initial', current_price) / 100
            discount_percent = price_overview.get('discount_percent', 0)
            
            logger.debug(f"Parsed price for App ID {app_id}: {current_price} JPY")
            
            return {
                'price': current_price,
                'original_price': initial_price,
                'discount_percent': discount_percent,
                'currency': price_overview.get('currency', 'JPY'),
                'is_on_sale': discount_percent > 0
            }
            
        except Exception as e:
            logger.error(f"Steam価格取得エラー (App ID: {app_id}): {e}")
            return None
