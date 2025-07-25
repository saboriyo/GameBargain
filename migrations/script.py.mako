"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}


@main_bp.route('/game/<int:game_id>')
def game_detail(game_id: int):
    try:
        # データベースからゲーム情報を取得
        game = db.session.get(Game, game_id)
        if not game:
            flash('指定されたゲームが見つかりません。', 'error')
            return redirect(url_for('main.index'))
        
        # 価格情報を直接データベースから取得
        prices_db = db.session.query(Price).filter_by(
            game_id=game_id
        ).order_by(Price.updated_at.desc()).limit(5).all()
        
        # 価格情報を整形
        formatted_prices = []
        for price in prices_db:
            formatted_price = {
                'store': price.store,
                'price': float(price.sale_price if price.sale_price else price.regular_price),
                'original_price': float(price.regular_price) if price.regular_price else None,
                'discount_percent': price.discount_rate,
                'store_url': f"https://store.steampowered.com/app/{game_id}/" if price.store == 'steam' else None,
                'updated_at': price.updated_at
            }
            formatted_prices.append(formatted_price)
            current_app.logger.debug(f"整形後の価格情報: {formatted_price}")

        # 最安値を特定
        lowest_price = None
        if formatted_prices:
            lowest_price = min(formatted_prices, key=lambda p: p['price'])
            current_app.logger.debug(f"最安値情報: {lowest_price}")

        # ゲーム情報を整形
        game_data = _format_game_for_web_template(game)
        current_app.logger.debug(f"ゲーム情報: id={game_data['id']}, "
                               f"title={game_data['title']}")

        # お気に入り状態をチェック
        is_favorited = False
        if current_user.is_authenticated:
            favorite = db.session.query(Favorite).filter_by(
                user_id=current_user.user_id,
                game_id=game_id
            ).first()
            is_favorited = favorite is not None

        current_app.logger.info(f"ゲーム詳細表示: game_id={game_id}, "
                              f"title={game.title}, "
                              f"価格数={len(formatted_prices)}, "
                              f"最安値={'あり' if lowest_price else 'なし'}")

        return render_template('game_detail.html', 
                             game=game_data,
                             prices=formatted_prices,
                             lowest_price=lowest_price,
                             is_favorited=is_favorited,
                             page_title=game.title)

    except Exception as e:
        current_app.logger.error(f"ゲーム詳細取得エラー: {e}")
        current_app.logger.exception("詳細なエラー情報:")
        flash('ゲーム情報の取得中にエラーが発生しました。', 'error')
        return redirect(url_for('main.index'))

<!-- 最安値表示 -->
{% if lowest_price and lowest_price['price'] %}
<div class="alert alert-success d-flex align-items-center mb-4">
    <i class="bi bi-trophy-fill fs-4 me-3"></i>
    <div>
        <h5 class="alert-heading mb-1">現在の最安値</h5>
        <div class="d-flex align-items-center">
            <span class="fs-3 fw-bold text-success me-3">¥{{ "{:,}".format(lowest_price['price']|int) }}</span>
            <span class="store-badge store-{{ lowest_price['store'] }}">{{ lowest_price['store']|upper }}</span>
            {% if lowest_price['discount_percent'] and lowest_price['discount_percent'] > 0 %}
            <span class="badge bg-danger ms-2">{{ lowest_price['discount_percent'] }}% OFF</span>
            {% endif %}
        </div>
        <small class="text-muted">更新日時: {{ lowest_price['updated_at'].strftime('%Y年%m月%d日 %H:%M') }}</small>
    </div>
</div>
{% endif %}
