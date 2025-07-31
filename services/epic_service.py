# -*- coding: utf-8 -*-
"""Epic Games Store API Service

Epic Games Store Web APIを使用してゲーム情報と価格を取得するサービス。
非公式APIとGraphQLエンドポイントを使用します。
"""

import requests
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)


class EpicGamesStoreAPI:
    """Epic Games Store API サービスクラス
    
    Epic Games Storeからゲーム情報と価格を取得します。
    """
    
    # Epic Games Store API エンドポイント
    GRAPHQL_URL = "https://graphql.epicgames.com/graphql"
    STORE_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    CATALOG_URL = "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/namespace/epic/items"
    
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
            
            # GraphQLクエリでプロダクト一覧を取得
            query = """
            query searchStoreQuery($category: String, $count: Int, $country: String, $keywords: String, $locale: String, $sortBy: String, $sortDir: String, $start: Int, $tag: String, $withPrice: Boolean = true) {
                Catalog {
                    searchStore(category: $category, count: $count, country: $country, keywords: $keywords, locale: $locale, sortBy: $sortBy, sortDir: $sortDir, start: $start, tag: $tag) {
                        elements {
                            id
                            namespace
                            title
                            description
                            developer
                            seller {
                                name
                            }
                            price(country: $country) @include(if: $withPrice) {
                                totalPrice {
                                    originalPrice
                                    discountPrice
                                    discount
                                    currencyCode
                                }
                                lineOffers {
                                    appliedRules {
                                        id
                                        endDate
                                        discountSetting {
                                            discountType
                                            discountPercentage
                                        }
                                    }
                                }
                            }
                            tags {
                                id
                            }
                            catalogNs {
                                mappings(pageType: "productHome") {
                                    page
                                    pageType
                                }
                            }
                            keyImages {
                                type
                                url
                            }
                            releaseDate
                            lastModifiedDate
                        }
                        paging {
                            count
                            total
                            start
                        }
                    }
                }
            }
            """
            
            variables = {
                "category": "games/edition/base|bundles/games|editors",
                "count": 100,
                "country": "JP",
                "keywords": "",
                "locale": "ja",
                "sortBy": "effectiveDate",
                "sortDir": "DESC",
                "start": 0,
                "withPrice": True
            }
            
            response = self.session.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # namespace -> slug のマッピングを作成
            mapping = {}
            for element in elements:
                namespace = element.get('namespace')
                title = element.get('title', '')
                if namespace and title:
                    # slugを生成（タイトルから）
                    slug = self._generate_slug(title)
                    mapping[namespace] = slug
            
            # キャッシュ更新
            self._product_mapping_cache = mapping
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Epic Games Store プロダクトマッピング {len(mapping)} 件を取得しました")
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
            
            # GraphQLクエリで検索
            search_query = """
            query searchStoreQuery($category: String, $count: Int, $country: String, $keywords: String, $locale: String, $sortBy: String, $sortDir: String, $start: Int, $tag: String, $withPrice: Boolean = true) {
                Catalog {
                    searchStore(category: $category, count: $count, country: $country, keywords: $keywords, locale: $locale, sortBy: $sortBy, sortDir: $sortDir, start: $start, tag: $tag) {
                        elements {
                            id
                            namespace
                            title
                            description
                            developer
                            seller {
                                name
                            }
                            price(country: $country) @include(if: $withPrice) {
                                totalPrice {
                                    originalPrice
                                    discountPrice
                                    discount
                                    currencyCode
                                }
                                lineOffers {
                                    appliedRules {
                                        id
                                        endDate
                                        discountSetting {
                                            discountType
                                            discountPercentage
                                        }
                                    }
                                }
                            }
                            tags {
                                id
                            }
                            catalogNs {
                                mappings(pageType: "productHome") {
                                    page
                                    pageType
                                }
                            }
                            keyImages {
                                type
                                url
                            }
                            releaseDate
                            lastModifiedDate
                        }
                        paging {
                            count
                            total
                            start
                        }
                    }
                }
            }
            """
            
            variables = {
                "category": "games/edition/base|bundles/games|editors",
                "count": limit * 2,
                "country": "JP",
                "keywords": query,
                "locale": "ja",
                "sortBy": "relevancy",
                "sortDir": "DESC",
                "start": 0,
                "withPrice": True
            }
            
            response = self.session.post(
                self.GRAPHQL_URL,
                json={"query": search_query, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # 結果を整形
            games = []
            for element in elements[:limit]:
                game_data = self._format_game_data(element)
                if game_data:
                    games.append(game_data)
            
            logger.info(f"Epic Games Store 検索結果: {len(games)} 件")
            return games
            
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
            
            # GraphQLクエリで最近のゲームを取得
            query = """
            query searchStoreQuery($category: String, $count: Int, $country: String, $keywords: String, $locale: String, $sortBy: String, $sortDir: String, $start: Int, $tag: String, $withPrice: Boolean = true) {
                Catalog {
                    searchStore(category: $category, count: $count, country: $country, keywords: $keywords, locale: $locale, sortBy: $sortBy, sortDir: $sortDir, start: $start, tag: $tag) {
                        elements {
                            id
                            namespace
                            title
                            description
                            developer
                            seller {
                                name
                            }
                            price(country: $country) @include(if: $withPrice) {
                                totalPrice {
                                    originalPrice
                                    discountPrice
                                    discount
                                    currencyCode
                                }
                                lineOffers {
                                    appliedRules {
                                        id
                                        endDate
                                        discountSetting {
                                            discountType
                                            discountPercentage
                                        }
                                    }
                                }
                            }
                            tags {
                                id
                            }
                            catalogNs {
                                mappings(pageType: "productHome") {
                                    page
                                    pageType
                                }
                            }
                            keyImages {
                                type
                                url
                            }
                            releaseDate
                            lastModifiedDate
                        }
                        paging {
                            count
                            total
                            start
                        }
                    }
                }
            }
            """
            
            variables = {
                "category": "games/edition/base|bundles/games|editors",
                "count": limit,
                "country": "JP",
                "keywords": "",
                "locale": "ja",
                "sortBy": "effectiveDate",
                "sortDir": "DESC",
                "start": 0,
                "withPrice": True
            }
            
            response = self.session.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            elements = data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', [])
            
            # 結果を整形
            games = []
            for element in elements:
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
            
            # GraphQLクエリで価格情報を取得
            query = """
            query getCatalogOffer($country: String!, $locale: String!, $offerId: String!) {
                Catalog {
                    catalogOffer(offerId: $offerId, locale: $locale, country: $country) {
                        id
                        title
                        description
                        effectiveDate
                        expiryDate
                        status
                        isCodeRedemptionOnly
                        seller {
                            id
                            name
                        }
                        productSlug
                        urlSlug
                        price(country: $country) {
                            totalPrice {
                                originalPrice
                                discountPrice
                                discount
                                currencyCode
                            }
                            lineOffers {
                                appliedRules {
                                    id
                                    endDate
                                    discountSetting {
                                        discountType
                                        discountPercentage
                                    }
                                }
                            }
                        }
                        keyImages {
                            type
                            url
                        }
                        tags {
                            id
                        }
                    }
                }
            }
            """
            
            # offerIdを生成（namespaceを使用）
            offer_id = f"{namespace}::default"
            
            variables = {
                "country": "JP",
                "locale": "ja",
                "offerId": offer_id
            }
            
            response = self.session.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            catalog_offer = data.get('data', {}).get('Catalog', {}).get('catalogOffer')
            
            if not catalog_offer:
                logger.warning(f"Epic Games Store 価格情報が見つかりません: {namespace}")
                return None
            
            # 価格情報を抽出
            price_data = catalog_offer.get('price', {})
            total_price = price_data.get('totalPrice', {})
            
            original_price = total_price.get('originalPrice', 0) / 100  # セント単位から円に変換
            discount_price = total_price.get('discountPrice', original_price) / 100
            discount_percent = total_price.get('discount', 0)
            
            # セール情報を確認
            line_offers = price_data.get('lineOffers', [])
            is_on_sale = False
            sale_end_date = None
            
            for offer in line_offers:
                applied_rules = offer.get('appliedRules', [])
                for rule in applied_rules:
                    if rule.get('discountSetting', {}).get('discountPercentage', 0) > 0:
                        is_on_sale = True
                        end_date = rule.get('endDate')
                        if end_date:
                            sale_end_date = end_date
                        break
            
            logger.debug(f"Epic Games Store 価格解析: {discount_price} JPY (割引: {discount_percent}%)")
            
            return {
                'price': discount_price,
                'original_price': original_price,
                'discount_percent': discount_percent,
                'currency': total_price.get('currencyCode', 'JPY'),
                'is_on_sale': is_on_sale,
                'sale_end_date': sale_end_date,
                'namespace': namespace,
                'title': catalog_offer.get('title', ''),
                'image_url': self._get_image_url(catalog_offer.get('keyImages', []))
            }
            
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
                'epic_namespace': element.get('namespace', ''),
                'title': title,
                'description': element.get('description', ''),
                'developer': element.get('developer', ''),
                'publisher': element.get('seller', {}).get('name', ''),
                'release_date': element.get('releaseDate'),
                'image_url': self._get_image_url(element.get('keyImages', [])),
                'epic_url': f"https://store.epicgames.com/ja/p/{element.get('productSlug', '')}",
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