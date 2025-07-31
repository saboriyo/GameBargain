# -*- coding: utf-8 -*-
"""Epic Games Store API Service

Epic Games Store Web APIを使用してゲーム情報と価格を取得するサービス。
epicstore_apiライブラリと非公式APIを使用します。
"""

import requests
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

try:
    from epicstore_api import EpicGamesStoreAPI, OfferData
    EPICSTORE_AVAILABLE = True
except ImportError:
    EPICSTORE_AVAILABLE = False
    logger.warning("epicstore_apiライブラリが利用できません。基本的なAPIのみ使用します。")


class EpicGamesStoreService:
    """Epic Games Store API サービスクラス
    
    Epic Games Storeからゲーム情報と価格を取得します。
    epicstore_apiライブラリと独自のAPI実装を組み合わせて使用します。
    """
    
    # Epic Games Store API エンドポイント
    GRAPHQL_URL = "https://graphql.epicgames.com/graphql"
    STORE_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    CATALOG_URL = "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/epic/items"
    SEARCH_GRAPHQL_URL = "https://www.epicgames.com/graphql"
    
    def __init__(self):
        """Epic Games Store API サービスの初期化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GameBargain/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self._product_mapping_cache = None
        self._cache_timestamp = None
        
        # epicstore_apiライブラリのインスタンス
        self.epicstore_api = None
        if EPICSTORE_AVAILABLE:
            try:
                # epicstore_apiライブラリからEpicGamesStoreAPIクラスをインポート
                from epicstore_api import EpicGamesStoreAPI as EpicStoreAPI
                self.epicstore_api = EpicStoreAPI()
                logger.info("epicstore_apiライブラリを初期化しました")
            except Exception as e:
                logger.error(f"epicstore_apiライブラリの初期化に失敗: {e}")
                self.epicstore_api = None
        else:
            logger.warning("epicstore_apiライブラリが利用できません")
    
    def search_games_graphql(self, query: str, limit: int = 20, namespace: str = "epic") -> List[Dict[str, Any]]:
        """
        GraphQL APIを使用してゲーム検索
        
        Args:
            query: 検索クエリ
            limit: 結果数制限
            namespace: Epic Games Store namespace (デフォルト: "epic")
            
        Returns:
            List[Dict]: 検索結果
        """
        try:
            logger.info(f"Epic Games Store GraphQL APIでゲーム検索: '{query}' (namespace: {namespace})")
            
            # GraphQLクエリ
            graphql_query = {
                "query": """
                query searchStore($namespace: String!, $start: Int!, $count: Int!) {
                    Catalog {
                        searchStore(namespace: $namespace, start: $start, count: $count) {
                            paging {
                                count
                                total
                            }
                            elements {
                                id
                                namespace
                                title
                                productSlug
                                items {
                                    id
                                }
                            }
                        }
                    }
                }
                """,
                "variables": {
                    "namespace": namespace,
                    "start": 0,
                    "count": limit
                }
            }
            
            # GraphQL APIにリクエスト
            response = self.session.post(
                self.SEARCH_GRAPHQL_URL,
                json=graphql_query,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"GraphQL APIレスポンス: {json.dumps(data, indent=2)}")
            
            # レスポンスからゲームデータを抽出
            search_store = data.get('data', {}).get('Catalog', {}).get('searchStore', {})
            elements = search_store.get('elements', [])
            paging = search_store.get('paging', {})
            
            logger.info(f"GraphQL API検索結果: {len(elements)}件 (総数: {paging.get('total', 0)})")
            
            # 検索クエリでフィルタリング
            filtered_results = []
            query_lower = query.lower()
            
            for element in elements:
                title = element.get('title', '').lower()
                if query_lower in title:
                    game_data = self._format_game_data_from_graphql(element)
                    if game_data:
                        # 価格情報を取得
                        namespace = element.get('id', '')
                        product_slug = element.get('productSlug', '')
                        if namespace and product_slug:
                            try:
                                price_info = self.get_game_price(namespace, product_slug)
                                if price_info:
                                    game_data['price_info'] = {
                                        'is_free': price_info.get('price', 0) == 0,
                                        'current_price': price_info.get('price', 0),
                                        'original_price': price_info.get('original_price', 0),
                                        'discount_percent': price_info.get('discount_percent', 0),
                                        'formatted_price': f"¥{int(price_info.get('price', 0)):,}" if price_info.get('price', 0) > 0 else "無料",
                                        'is_on_sale': price_info.get('is_on_sale', False)
                                    }
                                    # 追加情報も更新
                                    if price_info.get('title'):
                                        game_data['title'] = price_info['title']
                                    if price_info.get('image_url'):
                                        game_data['image_url'] = price_info['image_url']
                            except Exception as e:
                                logger.debug(f"価格情報取得エラー (namespace: {namespace}): {e}")
                        
                        filtered_results.append(game_data)
                        
                        if len(filtered_results) >= limit:
                            break
            
            logger.info(f"GraphQL API検索完了: フィルタリング後 {len(filtered_results)}件")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Epic Games Store GraphQL API検索エラー: {e}")
            logger.exception("詳細エラー:")
            return []
    
    def search_games_catalog(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Epic Games Store カタログAPIを使用してゲーム検索
        
        Args:
            query: 検索クエリ
            limit: 結果数制限
            
        Returns:
            List[Dict]: 検索結果
        """
        try:
            logger.info(f"Epic Games Store カタログAPIでゲーム検索: '{query}'")
            
            # カタログAPIのエンドポイント
            catalog_url = "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/epic/items"
            
            # 検索パラメータ
            params = {
                'category': 'games/edition/base|bundles/games|editors',
                'count': limit,
                'country': 'JP',
                'keywords': query,
                'locale': 'ja',
                'sortBy': 'relevancy',
                'sortDir': 'DESC'
            }
            
            # カタログAPIにリクエスト
            response = self.session.get(catalog_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"カタログAPIレスポンス: {json.dumps(data, indent=2)}")
            
            # レスポンスからゲームデータを抽出
            elements = data.get('elements', [])
            
            logger.info(f"カタログAPI検索結果: {len(elements)}件")
            
            # 結果を整形
            results = []
            for element in elements:
                game_data = self._format_game_data_from_catalog(element)
                if game_data:
                    results.append(game_data)
                    
                    if len(results) >= limit:
                        break
            
            logger.info(f"カタログAPI検索完了: {len(results)}件")
            return results
            
        except Exception as e:
            logger.error(f"Epic Games Store カタログAPI検索エラー: {e}")
            logger.exception("詳細エラー:")
            return []
    
    def get_product_mapping(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Epic Games Storeのプロダクトマッピングを取得
        
        Args:
            force_refresh: キャッシュを無視して強制取得
            
        Returns:
            Dict[str, str]: namespace -> slug のマッピング
        """
        try:
            # キャッシュチェック（1時間有効）
            if (not force_refresh and 
                self._product_mapping_cache and 
                self._cache_timestamp and 
                (datetime.now() - self._cache_timestamp).seconds < 3600):
                return self._product_mapping_cache
            
            logger.info("Epic Games Store からプロダクトマッピングを取得中...")
            
            # epicstore_apiライブラリを使用
            if self.epicstore_api:
                try:
                    mapping = self.epicstore_api.get_product_mapping()
                    logger.info(f"epicstore_apiライブラリでプロダクトマッピング {len(mapping)} 件を取得しました")
                    
                    # キャッシュ更新
                    self._product_mapping_cache = mapping
                    self._cache_timestamp = datetime.now()
                    return mapping
                    
                except Exception as e:
                    logger.warning(f"epicstore_apiライブラリでの取得に失敗: {e}")
            
            # フォールバック: 独自実装
            logger.info("独自実装でプロダクトマッピングを取得中...")
            
            # 無料ゲームAPIから情報を取得
            response = self.session.get(self.STORE_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # namespace -> slug のマッピングを作成
            mapping = {}
            for element in elements:
                namespace = element.get('id')  # IDをnamespaceとして使用
                title = element.get('title', '')
                if namespace and title:
                    # slugを生成（タイトルから）
                    slug = self._generate_slug(title)
                    mapping[namespace] = slug
            
            # キャッシュ更新
            self._product_mapping_cache = mapping
            self._cache_timestamp = datetime.now()
            
            logger.info(f"独自実装でプロダクトマッピング {len(mapping)} 件を取得しました")
            return mapping
            
        except Exception as e:
            logger.error(f"Epic Games Store プロダクトマッピング取得エラー: {e}")
            return self._product_mapping_cache or {}
    
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
            logger.info(f"Epic Games Store でゲーム検索: '{query}'")
            
            # まず無料ゲームAPIを試行（認証不要で動作する）
            try:
                free_games_results = self._search_games_from_free_games(query, limit)
                if free_games_results:
                    logger.info(f"無料ゲームAPIで検索結果 {len(free_games_results)} 件を取得しました")
                    return free_games_results
            except Exception as e:
                logger.warning(f"無料ゲームAPI検索に失敗: {e}")
            
            # epicstore_apiライブラリを使用
            if self.epicstore_api:
                try:
                    # プロダクトマッピングから検索
                    mapping = self.get_product_mapping()
                    results = []
                    
                    for namespace, slug in mapping.items():
                        if query.lower() in slug.lower():
                            try:
                                product = self.epicstore_api.get_product(slug)
                                if product:
                                    game_data = self._format_game_data_from_epicstore(product, namespace)
                                    if game_data:
                                        results.append(game_data)
                                        
                                        if len(results) >= limit:
                                            break
                            except Exception as e:
                                logger.debug(f"プロダクト取得エラー (slug: {slug}): {e}")
                                continue
                    
                    logger.info(f"epicstore_apiライブラリで検索結果 {len(results)} 件を取得しました")
                    return results
                    
                except Exception as e:
                    logger.warning(f"epicstore_apiライブラリでの検索に失敗: {e}")
            
            # カタログAPIを試行（認証が必要な場合がある）
            try:
                catalog_results = self.search_games_catalog(query, limit)
                if catalog_results:
                    logger.info(f"カタログAPIで検索結果 {len(catalog_results)} 件を取得しました")
                    return catalog_results
            except Exception as e:
                logger.warning(f"カタログAPI検索に失敗: {e}")
            
            # GraphQL APIを試行（認証が必要な場合がある）
            try:
                graphql_results = self.search_games_graphql(query, limit)
                if graphql_results:
                    logger.info(f"GraphQL APIで検索結果 {len(graphql_results)} 件を取得しました")
                    return graphql_results
            except Exception as e:
                logger.warning(f"GraphQL API検索に失敗: {e}")
            
            logger.info("すべてのAPIで検索結果が取得できませんでした")
            return []
            
        except Exception as e:
            logger.error(f"Epic Games Store ゲーム検索エラー: {e}")
            return []
    
    def get_recent_games(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        最近のゲーム一覧を取得
        
        Args:
            limit: 取得数制限
            
        Returns:
            List[Dict]: ゲーム一覧
        """
        try:
            logger.info(f"Epic Games Store から最近のゲーム {limit} 件を取得中...")
            
            # 無料ゲームAPIから最新のゲームを取得
            response = self.session.get(self.STORE_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # 結果を整形
            games = []
            for element in elements[:limit]:
                game_data = self._format_game_data(element)
                if game_data:
                    games.append(game_data)
            
            logger.info(f"Epic Games Store 最近のゲーム {len(games)} 件を取得しました")
            return games
            
        except Exception as e:
            logger.error(f"Epic Games Store 最近のゲーム取得エラー: {e}")
            return []
    
    def get_game_price(self, namespace: str, slug: str = None) -> Optional[Dict[str, Any]]:
        """
        指定されたゲームの価格情報を取得
        
        Args:
            namespace: Epic Games Store namespace
            slug: ゲームスラッグ（オプション）
            
        Returns:
            Optional[Dict[str, Any]]: 価格情報（見つからない場合はNone）
        """
        try:
            logger.info(f"Epic Games Store 価格取得: namespace={namespace}, slug={slug}")
            
            # epicstore_apiライブラリを使用
            if self.epicstore_api and slug:
                try:
                    logger.debug(f"epicstore_apiライブラリでプロダクト取得: slug={slug}")
                    product = self.epicstore_api.get_product(slug)
                    if product:
                        logger.debug(f"プロダクト取得成功: {product.get('title', 'Unknown')}")
                        
                        # オファー情報を取得
                        offers = []
                        for page in product.get('pages', []):
                            if page.get('offer') and 'id' in page['offer']:
                                offer_data = OfferData(page['namespace'], page['offer']['id'])
                                offers.append(offer_data)
                        
                        if offers:
                            logger.debug(f"オファー {len(offers)} 件を取得中...")
                            offers_data = self.epicstore_api.get_offers_data(*offers)
                            if offers_data:
                                # 最初のオファーの価格情報を取得
                                offer_data = offers_data[0]
                                data = offer_data['data']['Catalog']['catalogOffer']
                                
                                price_info = data.get('price', {})
                                total_price = price_info.get('totalPrice', {})
                                
                                original_price = total_price.get('originalPrice', 0) / 100
                                discount_price = total_price.get('discountPrice', original_price) / 100
                                discount_percent = total_price.get('discount', 0)
                                
                                logger.info(f"epicstore_apiライブラリで価格取得: {discount_price} JPY")
                                
                                return {
                                    'price': discount_price,
                                    'original_price': original_price,
                                    'discount_percent': discount_percent,
                                    'currency': total_price.get('currencyCode', 'JPY'),
                                    'is_on_sale': discount_percent > 0,
                                    'namespace': namespace,
                                    'title': data.get('title', ''),
                                    'image_url': self._get_image_url(data.get('keyImages', []))
                                }
                            else:
                                logger.warning("オファーデータの取得に失敗しました")
                        else:
                            logger.warning("オファー情報が見つかりませんでした")
                    else:
                        logger.warning(f"プロダクトが見つかりませんでした: slug={slug}")
                    
                except Exception as e:
                    logger.warning(f"epicstore_apiライブラリでの価格取得に失敗: {e}")
                    logger.exception("詳細エラー:")
            
            # フォールバック: 無料ゲームAPIから価格情報を取得
            logger.info("無料ゲームAPIから価格情報を取得中...")
            return self._get_price_from_free_games(namespace)
            
        except Exception as e:
            logger.error(f"Epic Games Store 価格取得エラー (namespace: {namespace}): {e}")
            return None
    
    def get_free_games(self) -> List[Dict[str, Any]]:
        """
        無料ゲーム一覧を取得
        
        Returns:
            List[Dict]: 無料ゲーム一覧
        """
        try:
            logger.info("Epic Games Store から無料ゲームを取得中...")
            
            response = self.session.get(self.STORE_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            free_games = []
            
            # 現在の無料ゲーム
            current_games = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            for game in current_games:
                if game.get('promotions'):
                    game_data = self._format_game_data(game)
                    if game_data:
                        game_data['is_free'] = True
                        free_games.append(game_data)
            
            logger.info(f"Epic Games Store 無料ゲーム {len(free_games)} 件を取得しました")
            return free_games
            
        except Exception as e:
            logger.error(f"Epic Games Store 無料ゲーム取得エラー: {e}")
            return []
    
    def _search_games_from_free_games(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        無料ゲームAPIから検索
        
        Args:
            query: 検索クエリ
            limit: 結果数制限
            
        Returns:
            List[Dict]: 検索結果
        """
        try:
            response = self.session.get(self.STORE_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            results = []
            query_lower = query.lower()
            
            # より柔軟な検索（部分一致、単語分割）
            query_words = query_lower.split()
            
            for element in elements:
                title = element.get('title', '').lower()
                description = element.get('description', '').lower()
                
                # 検索条件を緩和
                match_found = False
                
                # 完全一致
                if query_lower in title:
                    match_found = True
                # 単語の一部一致
                elif any(word in title for word in query_words if len(word) > 2):
                    match_found = True
                # 説明文での検索
                elif query_lower in description:
                    match_found = True
                # 単語の一部が説明文に含まれる
                elif any(word in description for word in query_words if len(word) > 2):
                    match_found = True
                
                if match_found:
                    game_data = self._format_game_data(element)
                    if game_data:
                        results.append(game_data)
                        
                        if len(results) >= limit:
                            break
            
            logger.info(f"無料ゲームAPI検索結果: {len(results)}件 (クエリ: '{query}')")
            return results
            
        except Exception as e:
            logger.error(f"無料ゲームAPI検索エラー: {e}")
            return []
    
    def _get_price_from_free_games(self, namespace: str) -> Optional[Dict[str, Any]]:
        """
        無料ゲームAPIから価格情報を取得
        
        Args:
            namespace: Epic Games Store namespace
            
        Returns:
            Optional[Dict[str, Any]]: 価格情報
        """
        try:
            response = self.session.get(self.STORE_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            for element in elements:
                if element.get('id') == namespace:
                    price_data = element.get('price', {})
                    total_price = price_data.get('totalPrice', {})
                    
                    original_price = total_price.get('originalPrice', 0) / 100
                    discount_price = total_price.get('discountPrice', original_price) / 100
                    discount_percent = total_price.get('discount', 0)
                    
                    return {
                        'price': discount_price,
                        'original_price': original_price,
                        'discount_percent': discount_percent,
                        'currency': total_price.get('currencyCode', 'JPY'),
                        'is_on_sale': discount_percent > 0,
                        'namespace': namespace,
                        'title': element.get('title', ''),
                        'image_url': self._get_image_url(element.get('keyImages', []))
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"無料ゲームAPI価格取得エラー: {e}")
            return None
    
    def _format_game_data_from_epicstore(self, product: Dict[str, Any], namespace: str) -> Optional[Dict[str, Any]]:
        """
        epicstore_apiライブラリのデータを整形
        
        Args:
            product: epicstore_apiライブラリのプロダクトデータ
            namespace: Epic Games Store namespace
            
        Returns:
            Optional[Dict]: 整形されたゲームデータ
        """
        try:
            title = product.get('title', '')
            if not title:
                return None
            
            # 価格情報を抽出（オファーから）
            price_info = {
                'is_free': True,
                'current_price': 0,
                'original_price': 0,
                'discount_percent': 0,
                'formatted_price': "無料",
                'is_on_sale': False
            }
            
            # オファー情報から価格を取得
            offers = []
            for page in product.get('pages', []):
                if page.get('offer') and 'id' in page['offer']:
                    offer_data = OfferData(page['namespace'], page['offer']['id'])
                    offers.append(offer_data)
            
            if offers:
                try:
                    logger.debug(f"オファー {len(offers)} 件の価格データを取得中...")
                    offers_data = self.epicstore_api.get_offers_data(*offers)
                    if offers_data:
                        data = offers_data[0]['data']['Catalog']['catalogOffer']
                        price_data = data.get('price', {})
                        total_price = price_data.get('totalPrice', {})
                        
                        original_price = total_price.get('originalPrice', 0) / 100
                        discount_price = total_price.get('discountPrice', original_price) / 100
                        discount_percent = total_price.get('discount', 0)
                        
                        price_info = {
                            'is_free': discount_price == 0,
                            'current_price': discount_price,
                            'original_price': original_price,
                            'discount_percent': discount_percent,
                            'formatted_price': f"¥{int(discount_price):,}" if discount_price > 0 else "無料",
                            'is_on_sale': discount_percent > 0
                        }
                        logger.debug(f"価格情報取得成功: {price_info['formatted_price']}")
                    else:
                        logger.warning("オファーデータの取得に失敗しました")
                except Exception as e:
                    logger.debug(f"オファー価格取得エラー: {e}")
                    logger.exception("詳細エラー:")
            
            return {
                'epic_namespace': namespace,
                'title': title,
                'description': product.get('description', ''),
                'developer': product.get('developer', ''),
                'publisher': product.get('seller', {}).get('name', ''),
                'release_date': product.get('releaseDate'),
                'image_url': self._get_image_url(product.get('keyImages', [])),
                'epic_url': self._generate_epic_url(product.get('productSlug', ''), namespace),
                'price_info': price_info,
                'tags': [tag.get('id', '') for tag in product.get('tags', [])]
            }
            
        except Exception as e:
            logger.error(f"epicstore_apiゲームデータ整形エラー: {e}")
            return None
    
    def _format_game_data(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ゲームデータを整形
        
        Args:
            element: Epic Games Store APIの要素データ
            
        Returns:
            Optional[Dict]: 整形されたゲームデータ
        """
        try:
            title = element.get('title', '')
            if not title:
                return None
            
            # 価格情報を抽出
            price_data = element.get('price', {})
            total_price = price_data.get('totalPrice', {})
            
            original_price = total_price.get('originalPrice', 0) / 100
            discount_price = total_price.get('discountPrice', original_price) / 100
            discount_percent = total_price.get('discount', 0)
            
            # セール情報を確認
            line_offers = price_data.get('lineOffers', [])
            is_on_sale = False
            for offer in line_offers:
                applied_rules = offer.get('appliedRules', [])
                for rule in applied_rules:
                    if rule.get('discountSetting', {}).get('discountPercentage', 0) > 0:
                        is_on_sale = True
                        break
            
            return {
                'epic_namespace': element.get('id', ''),
                'title': title,
                'description': element.get('description', ''),
                'developer': element.get('developer', ''),
                'publisher': element.get('seller', {}).get('name', ''),
                'release_date': element.get('releaseDate'),
                'image_url': self._get_image_url(element.get('keyImages', [])),
                'epic_url': self._generate_epic_url(element.get('productSlug', ''), element.get('id', '')),
                'price_info': {
                    'is_free': discount_price == 0,
                    'current_price': discount_price,
                    'original_price': original_price,
                    'discount_percent': discount_percent,
                    'formatted_price': f"¥{int(discount_price):,}" if discount_price > 0 else "無料",
                    'is_on_sale': is_on_sale
                },
                'tags': [tag.get('id', '') for tag in element.get('tags', [])]
            }
            
        except Exception as e:
            logger.error(f"ゲームデータ整形エラー: {e}")
            return None
    
    def _format_game_data_from_graphql(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        GraphQL APIから取得したゲームデータを整形
        
        Args:
            element: GraphQL APIの要素データ
            
        Returns:
            Optional[Dict]: 整形されたゲームデータ
        """
        try:
            title = element.get('title', '')
            if not title:
                return None
            
            # GraphQL APIは基本的な情報のみを返すため、価格情報は後で取得
            # 基本的なゲーム情報を返す
            return {
                'epic_namespace': element.get('id', ''),
                'title': title,
                'description': '',  # GraphQL APIでは取得できない
                'developer': '',    # GraphQL APIでは取得できない
                'publisher': '',    # GraphQL APIでは取得できない
                'release_date': None,  # GraphQL APIでは取得できない
                'image_url': None,     # GraphQL APIでは取得できない
                'epic_url': self._generate_epic_url(element.get('productSlug', ''), element.get('id', '')),
                'price_info': {
                    'is_free': False,  # 後で価格取得時に更新
                    'current_price': 0,
                    'original_price': 0,
                    'discount_percent': 0,
                    'formatted_price': "価格情報取得中...",
                    'is_on_sale': False
                },
                'tags': []  # GraphQL APIでは取得できない
            }
            
        except Exception as e:
            logger.error(f"GraphQL APIゲームデータ整形エラー: {e}")
            return None
    
    def _format_game_data_from_catalog(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        カタログAPIから取得したゲームデータを整形
        
        Args:
            element: カタログAPIの要素データ
            
        Returns:
            Optional[Dict]: 整形されたゲームデータ
        """
        try:
            title = element.get('title', '')
            if not title:
                return None
            
            # 価格情報を抽出
            price_data = element.get('price', {})
            total_price = price_data.get('totalPrice', {})
            
            original_price = total_price.get('originalPrice', 0) / 100
            discount_price = total_price.get('discountPrice', original_price) / 100
            discount_percent = total_price.get('discount', 0)
            
            # セール情報を確認
            line_offers = price_data.get('lineOffers', [])
            is_on_sale = False
            for offer in line_offers:
                applied_rules = offer.get('appliedRules', [])
                for rule in applied_rules:
                    if rule.get('discountSetting', {}).get('discountPercentage', 0) > 0:
                        is_on_sale = True
                        break
            
            return {
                'epic_namespace': element.get('id', ''),
                'title': title,
                'description': element.get('description', ''),
                'developer': element.get('developer', ''),
                'publisher': element.get('seller', {}).get('name', ''),
                'release_date': element.get('releaseDate'),
                'image_url': self._get_image_url(element.get('keyImages', [])),
                'epic_url': self._generate_epic_url(element.get('productSlug', ''), element.get('id', '')),
                'price_info': {
                    'is_free': discount_price == 0,
                    'current_price': discount_price,
                    'original_price': original_price,
                    'discount_percent': discount_percent,
                    'formatted_price': f"¥{int(discount_price):,}" if discount_price > 0 else "無料",
                    'is_on_sale': is_on_sale
                },
                'tags': [tag.get('id', '') for tag in element.get('tags', [])]
            }
            
        except Exception as e:
            logger.error(f"カタログAPIゲームデータ整形エラー: {e}")
            return None
    
    def _get_image_url(self, key_images: List[Dict[str, Any]]) -> Optional[str]:
        """
        画像URLを取得
        
        Args:
            key_images: Epic Games Store APIの画像データ
            
        Returns:
            Optional[str]: 画像URL
        """
        try:
            # 優先順位: OfferImageWide > OfferImageTall > Thumbnail
            image_types = ['OfferImageWide', 'OfferImageTall', 'Thumbnail']
            
            for image_type in image_types:
                for image in key_images:
                    if image.get('type') == image_type:
                        return image.get('url')
            
            # デフォルトで最初の画像を返す
            if key_images:
                return key_images[0].get('url')
            
            return None
            
        except Exception:
            return None
    
    def _generate_epic_url(self, product_slug: str, namespace: str) -> str:
        """
        Epic Games Store URLを生成
        
        Args:
            product_slug: プロダクトスラッグ
            namespace: Epic namespace
            
        Returns:
            str: Epic Games Store URL
        """
        try:
            if product_slug and product_slug.strip():
                return f"https://store.epicgames.com/ja/p/{product_slug}"
            elif namespace and namespace.strip():
                # namespaceを使用してURLを生成
                return f"https://store.epicgames.com/ja/p/{namespace}"
            else:
                return ""
        except Exception:
            return ""
    
    def _generate_slug(self, title: str) -> str:
        """
        タイトルからスラッグを生成
        
        Args:
            title: ゲームタイトル
            
        Returns:
            str: 生成されたスラッグ
        """
        try:
            # 特殊文字を除去し、スペースをハイフンに変換
            slug = re.sub(r'[^\w\s-]', '', title.lower())
            slug = re.sub(r'[-\s]+', '-', slug)
            return slug.strip('-')
            
        except Exception:
            return title.lower().replace(' ', '-') 