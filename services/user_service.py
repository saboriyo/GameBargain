"""
ユーザー関連のビジネスロジックを担当するサービス

このモジュールはユーザーの認証、プロフィール管理、
お気に入り機能、通知設定などの機能を提供します。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import desc, func, and_
from sqlalchemy.orm import joinedload

from services import BaseService, ValidationError, BusinessLogicError, create_pagination_info
from models import User, Favorite, Notification, Game, Price
from repositories.user_repository import UserRepository


class UserService(BaseService):
    """
    ユーザー関連サービス
    
    ユーザーの認証、プロフィール管理、お気に入り機能、
    通知設定などの機能を提供します。
    
    Attributes:
        User: ユーザーモデルクラス
        Favorite: お気に入りモデルクラス
        Notification: 通知モデルクラス
        Game: ゲームモデルクラス
        Price: 価格モデルクラス
    """
    
    def __init__(self):
        """ユーザーサービスの初期化"""
        super().__init__()
        # リポジトリパターンの使用
        self.user_repository = UserRepository()
        # 標準SQLAlchemyパターンのモデルを直接使用（通知関連はまだリポジトリがないため）
        self.Notification = Notification
        self.Price = Price
    

    
    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        ユーザープロフィールの取得
        
        Args:
            user_id (int): ユーザーID
            
        Returns:
            Dict[str, Any]: ユーザープロフィール情報
        """
        try:
            user = self.user_repository.get_by_id(user_id)
            if not user:
                raise ValidationError("ユーザーが見つかりません", "user_id")
            
            # お気に入り数の取得
            favorites = self.user_repository.get_user_favorites(user_id)
            favorites_count = len(favorites)
            
            # アラート数の取得
            alerts_count = self.Notification.query.filter_by(
                user_id=user_id,
                notification_type='price_alert',
                is_active=True
            ).count()
            
            # 統計情報の計算
            stats = self._calculate_user_stats(user_id)
            
            return self._create_success_response({
                'user': self._serialize_user(user),
                'stats': {
                    'favorites_count': favorites_count,
                    'alerts_count': alerts_count,
                    'total_savings': stats['total_savings'],
                    'deals_found': stats['deals_found']
                }
            })
            
        except ValidationError:
            raise
        except Exception as e:
            return self._handle_error(e, "ユーザープロフィール取得")
    
    def get_user_favorites(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        ユーザーのお気に入り一覧取得
        
        Args:
            user_id (int): ユーザーID
            page (int): ページ番号
            per_page (int): 1ページあたりの件数
            
        Returns:
            Dict[str, Any]: お気に入り一覧とページネーション情報
        """
        try:
            # お気に入り一覧の取得（リポジトリから取得）
            all_favorites = self.user_repository.get_user_favorites(user_id)
            
            # ページネーション処理
            total = len(all_favorites)
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            favorites = all_favorites[start_index:end_index]
            
            # 各お気に入りゲームの最新価格情報を取得
            favorites_with_prices = self._add_price_info_to_favorites(favorites)
            
            pagination = create_pagination_info(page, per_page, total)
            
            return self._create_success_response({
                'favorites': [self._serialize_favorite(fav) for fav in favorites_with_prices],
                'pagination': pagination
            })
            
        except Exception as e:
            return self._handle_error(e, "お気に入り一覧取得")
    
    def add_favorite(self, user_id: int, game_id: int) -> Dict[str, Any]:
        """
        お気に入りの追加
        
        Args:
            user_id (int): ユーザーID
            game_id (int): ゲームID
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # ゲームの存在確認（GameRepositoryを使用することを推奨）
            from repositories.game_repository import GameRepository
            game_repository = GameRepository()
            game = game_repository.get_by_id(game_id)
            if not game:
                raise ValidationError("指定されたゲームが見つかりません", "game_id")
            
            # 既存のお気に入りをチェック
            if self.user_repository.is_game_favorited(user_id, game_id):
                raise BusinessLogicError("このゲームは既にお気に入りに追加されています")
            
            # お気に入りの作成（リポジトリを使用）
            favorite = self.user_repository.add_favorite(user_id, game_id)
            if not favorite:
                raise BusinessLogicError("お気に入りの追加に失敗しました")
            
            self.user_repository.commit()
            
            return self._create_success_response(
                data={'favorite_id': favorite.id},
                message="お気に入りに追加しました"
            )
            
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            self.user_repository.rollback()
            return self._handle_error(e, "お気に入り追加")
    
    def remove_favorite(self, user_id: int, game_id: int) -> Dict[str, Any]:
        """
        お気に入りの削除
        
        Args:
            user_id (int): ユーザーID
            game_id (int): ゲームID
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # お気に入りの削除（リポジトリを使用）
            success = self.user_repository.remove_favorite(user_id, game_id)
            
            if not success:
                raise ValidationError("お気に入りが見つかりません")
            
            self.user_repository.commit()
            
            return self._create_success_response(
                message="お気に入りから削除しました"
            )
            
        except ValidationError:
            raise
        except Exception as e:
            self.user_repository.rollback()
            return self._handle_error(e, "お気に入り削除")
    
    def get_user_notifications(
        self,
        user_id: int,
        notification_type: str,
        is_active: bool,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        ユーザーの通知一覧取得
        
        Args:
            user_id (int): ユーザーID
            notification_type (str, optional): 通知タイプ
            is_active (bool, optional): アクティブ状態
            page (int): ページ番号
            per_page (int): 1ページあたりの件数
            
        Returns:
            Dict[str, Any]: 通知一覧とページネーション情報
        """
        try:
            query = self.Notification.query.filter_by(user_id=user_id)
            
            if notification_type:
                query = query.filter_by(notification_type=notification_type)
            
            if is_active is not None:
                query = query.filter_by(is_active=is_active)
            
            query = query.order_by(desc(self.Notification.created_at))
            
            total = query.count()
            offset = (page - 1) * per_page
            notifications = query.offset(offset).limit(per_page).all()
            
            pagination = create_pagination_info(page, per_page, total)
            
            return self._create_success_response({
                'notifications': [self._serialize_notification(notif) for notif in notifications],
                'pagination': pagination
            })
            
        except Exception as e:
            return self._handle_error(e, "通知一覧取得")
    
    def create_price_alert(
        self,
        user_id: int,
        game_id: int,
        threshold_price: float
    ) -> Dict[str, Any]:
        """
        価格アラートの作成
        
        Args:
            user_id (int): ユーザーID
            game_id (int): ゲームID
            threshold_price (float): 通知価格
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            # 入力値の検証
            self._validate_required_fields(
                {'game_id': game_id, 'threshold_price': threshold_price},
                ['game_id', 'threshold_price']
            )
            
            threshold_price = self._validate_positive_number(threshold_price, "通知価格")
            
            # ゲームの存在確認
            game = self.Game.query.get(game_id)
            if not game:
                raise ValidationError("指定されたゲームが見つかりません", "game_id")
            
            # 既存の価格アラートをチェック
            existing_alert = self.Notification.query.filter_by(
                user_id=user_id,
                game_id=game_id,
                notification_type='price_alert',
                is_active=True
            ).first()
            
            if existing_alert:
                # 既存のアラートがある場合は更新
                existing_alert.threshold_price = threshold_price
                existing_alert.updated_at = datetime.now(timezone.utc)
                message = "価格アラートを更新しました"
                alert_id = existing_alert.id
            else:
                # 新しいアラートを作成
                alert = self.Notification(
                    notification_type='price_alert',
                    title='価格アラート設定',
                    message=f'価格が¥{threshold_price}以下になったら通知します',
                    user_id=user_id,
                    game_id=game_id,
                    priority=2  # 通常の優先度
                )
                db.session.add(alert)
                message = "価格アラートを設定しました"
                alert_id = getattr(alert, 'id', None)
            
            db.session.commit()
            
            return self._create_success_response(
                data={'alert_id': alert_id},
                message=message
            )
            
        except (ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            db.session.rollback()
            return self._handle_error(e, "価格アラート作成")
    
    def delete_price_alert(self, user_id: int, alert_id: int) -> Dict[str, Any]:
        """
        価格アラートの削除
        
        Args:
            user_id (int): ユーザーID
            alert_id (int): アラートID
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            alert = self.Notification.query.filter_by(
                id=alert_id,
                user_id=user_id,
                notification_type='price_alert'
            ).first()
            
            if not alert:
                raise ValidationError("価格アラートが見つかりません")
            
            db.session.delete(alert)
            db.session.commit()
            
            return self._create_success_response(
                message="価格アラートを削除しました"
            )
            
        except ValidationError:
            raise
        except Exception as e:
            db.session.rollback()
            return self._handle_error(e, "価格アラート削除")
    
    def update_notification_settings(
        self,
        user_id: int,
        settings: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        通知設定の更新
        
        Args:
            user_id (int): ユーザーID
            settings (Dict[str, bool]): 通知設定
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            user = self.user_repository.get_by_id(user_id)
            if not user:
                raise ValidationError("ユーザーが見つかりません", "user_id")
            
            # 設定の更新
            if 'email_notifications' in settings:
                user.email_notifications = settings['email_notifications']
            if 'discord_notifications' in settings:
                user.discord_notifications = settings['discord_notifications']
            if 'weekly_digest' in settings:
                user.weekly_digest = settings['weekly_digest']
            if 'deal_alerts' in settings:
                user.deal_alerts = settings['deal_alerts']
            
            user.updated_at = datetime.now(timezone.utc)
            
            self.user_repository.commit()
            
            return self._create_success_response(
                message="通知設定を更新しました"
            )
            
        except ValidationError:
            raise
        except Exception as e:
            self.user_repository.rollback()
            return self._handle_error(e, "通知設定更新")
    
    def update_profile_settings(
        self,
        user_id: int,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        プロフィール設定の更新
        
        Args:
            user_id (int): ユーザーID
            settings (Dict[str, Any]): プロフィール設定
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            user = self.user_repository.get_by_id(user_id)
            if not user:
                raise ValidationError("ユーザーが見つかりません", "user_id")
            
            # 設定の更新
            if 'profile_public' in settings:
                user.profile_public = settings['profile_public']
            
            user.updated_at = datetime.now(timezone.utc)
            
            self.user_repository.commit()
            
            return self._create_success_response(
                message="プロフィール設定を更新しました"
            )
            
        except ValidationError:
            raise
        except Exception as e:
            self.user_repository.rollback()
            return self._handle_error(e, "プロフィール設定更新")
    
    def get_user_activity(
        self,
        user_id: int,
        days: int = 30,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        ユーザーアクティビティの取得
        
        Args:
            user_id (int): ユーザーID
            days (int): 取得期間（日数）
            limit (int): 最大取得件数
            
        Returns:
            Dict[str, Any]: アクティビティ一覧
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # お気に入り追加のアクティビティ（リポジトリから取得）
            all_favorites = self.user_repository.get_user_favorites(user_id)
            # 日付でフィルタリング（リポジトリに日付フィルタ機能を追加することを推奨）
            recent_favorites = [f for f in all_favorites if hasattr(f, 'added_at') and f.added_at >= start_date]
            favorites = sorted(recent_favorites, key=lambda x: x.added_at, reverse=True)[:limit // 2]
            
            # 価格アラート作成のアクティビティ
            alerts = (self.Notification.query
                     .filter(
                         self.Notification.user_id == user_id,
                         self.Notification.notification_type == 'price_alert',
                         self.Notification.created_at >= start_date
                     )
                     .options(joinedload(self.Notification.game))
                     .order_by(desc(self.Notification.created_at))
                     .limit(limit // 2)
                     .all())
            
            activities = []
            
            # お気に入り追加のアクティビティを追加
            for favorite in favorites:
                activities.append({
                    'type': 'favorite_added',
                    'game': self._serialize_game_basic(favorite),
                    'created_at': favorite.added_at.isoformat()
                })
            
            # 価格アラート作成のアクティビティを追加
            for alert in alerts:
                activities.append({
                    'type': 'alert_created',
                    'game': self._serialize_game_basic(alert.game),
                    'threshold_price': float(alert.threshold_price),
                    'created_at': alert.created_at.isoformat()
                })
            
            # 時間順でソート
            activities.sort(key=lambda x: x['created_at'], reverse=True)
            
            return self._create_success_response({
                'activities': activities[:limit]
            })
            
        except Exception as e:
            return self._handle_error(e, "ユーザーアクティビティ取得")
    
    def _calculate_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        ユーザー統計情報の計算
        
        Args:
            user_id (int): ユーザーID
            
        Returns:
            Dict[str, Any]: 統計情報
        """
        # 簡単な統計計算（実際の実装では複雑な計算が必要）
        stats = {
            'total_savings': 0.0,  # 節約金額の合計
            'deals_found': 0       # 発見したセール数
        }
        
        # お気に入りゲームの価格変動から節約金額を計算（リポジトリから取得）
        favorites = self.user_repository.get_user_favorites(user_id)
        
        for favorite in favorites:
            # 価格履歴から節約金額を算出
            prices = (self.Price.query
                     .filter_by(game_id=favorite.id)
                     .order_by(self.Price.updated_at)
                     .all())
            
            if len(prices) >= 2:
                initial_price = prices[0].price
                current_price = prices[-1].price
                if current_price < initial_price:
                    stats['total_savings'] += initial_price - current_price
                    stats['deals_found'] += 1
        
        return stats
    
    def _add_price_info_to_favorites(self, favorites: List) -> List:
        """
        お気に入り一覧に価格情報を付与
        
        Args:
            favorites (List): お気に入り一覧
            
        Returns:
            List: 価格情報付きお気に入り一覧
        """
        for favorite in favorites:
            # 最新の価格情報を取得
            latest_price = (self.Price.query
                           .filter_by(game_id=favorite.game_id)
                           .order_by(desc(self.Price.updated_at))
                           .first())
            
            favorite.latest_price = latest_price
            
            # 価格変動の計算（簡単な例）
            favorite.price_change = None
            if latest_price:
                # 1週間前の価格と比較
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                old_price = (self.Price.query
                           .filter(
                               self.Price.game_id == favorite.game_id,
                               self.Price.updated_at <= week_ago
                           )
                           .order_by(desc(self.Price.updated_at))
                           .first())
                
                if old_price and old_price.price != latest_price.price:
                    change_percent = ((latest_price.price - old_price.price) / old_price.price) * 100
                    favorite.price_change = round(change_percent, 1)
        
        return favorites
    
    def _serialize_user(self, user) -> Dict[str, Any]:
        """
        ユーザーオブジェクトをシリアライズ
        
        Args:
            user: ユーザーオブジェクト
            
        Returns:
            Dict[str, Any]: シリアライズされたユーザー情報
        """
        return {
            'id': user.id,
            'discord_user_id': user.discord_user_id,
            'discord_username': user.discord_username,
            'avatar_url': user.avatar_url,
            'email_notifications': user.email_notifications,
            'discord_notifications': user.discord_notifications,
            'weekly_digest': user.weekly_digest,
            'deal_alerts': user.deal_alerts,
            'profile_public': user.profile_public,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat()
        }
    
    def _serialize_favorite(self, favorite) -> Dict[str, Any]:
        """
        お気に入りオブジェクトをシリアライズ
        
        Args:
            favorite: お気に入りオブジェクト
            
        Returns:
            Dict[str, Any]: シリアライズされたお気に入り情報
        """
        data = {
            'id': favorite.id,
            'game': self._serialize_game_basic(favorite.game),
            'added_at': favorite.added_at.isoformat()
        }
        
        # 価格情報があれば追加
        if hasattr(favorite, 'latest_price') and favorite.latest_price:
            data['latest_price'] = {
                'price': float(favorite.latest_price.price),
                'store': favorite.latest_price.store,
                'updated_at': favorite.latest_price.updated_at.isoformat()
            }
        
        # 価格変動があれば追加
        if hasattr(favorite, 'price_change') and favorite.price_change is not None:
            data['price_change'] = favorite.price_change
        
        return data
    
    def _serialize_notification(self, notification) -> Dict[str, Any]:
        """
        通知オブジェクトをシリアライズ
        
        Args:
            notification: 通知オブジェクト
            
        Returns:
            Dict[str, Any]: シリアライズされた通知情報
        """
        data = {
            'id': notification.id,
            'notification_type': notification.notification_type,
            'is_active': notification.is_active,
            'created_at': notification.created_at.isoformat(),
            'updated_at': notification.updated_at.isoformat()
        }
        
        if notification.game_id and hasattr(notification, 'game'):
            data['game'] = self._serialize_game_basic(notification.game)
        
        if notification.threshold_price:
            data['threshold_price'] = float(notification.threshold_price)
        
        return data
    
    def _serialize_game_basic(self, game) -> Dict[str, Any]:
        """
        ゲームオブジェクトの基本情報をシリアライズ
        
        Args:
            game: ゲームオブジェクト
            
        Returns:
            Dict[str, Any]: シリアライズされたゲーム基本情報
        """
        return {
            'id': game.id,
            'title': game.title,
            'image_url': game.image_url,
            'developer': game.developer,
            'publisher': game.publisher
        }
