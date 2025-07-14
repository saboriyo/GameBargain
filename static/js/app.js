// GameBargain JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 初期化処理
    initializeApp();
});

function initializeApp() {
    console.log('GameBargain App initialized');
    
    // フェードインアニメーション
    addFadeInAnimation();
    
    // 検索フォームの強化
    enhanceSearchForm();
    
    // ツールチップの初期化
    initializeTooltips();
    
    // 統計データの更新
    updateStats();
}

// フェードインアニメーション
function addFadeInAnimation() {
    const elements = document.querySelectorAll('.card, .alert');
    elements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// 検索フォームの強化
function enhanceSearchForm() {
    const searchInputs = document.querySelectorAll('input[name="q"]');
    
    searchInputs.forEach(input => {
        // プレースホルダーアニメーション
        input.addEventListener('focus', function() {
            this.style.transform = 'scale(1.02)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        input.addEventListener('blur', function() {
            this.style.transform = 'scale(1)';
        });
        
        // エンターキーでの検索
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                this.closest('form').submit();
            }
        });
    });
}

// ツールチップの初期化
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 統計データの更新
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // 統計データを更新（もしページに統計セクションがあれば）
            updateStatElement('total-games', data.total_games);
            updateStatElement('total-users', data.total_users);
            updateStatElement('price-updates-today', data.price_updates_today);
            updateStatElement('notifications-sent-today', data.notifications_sent_today);
        })
        .catch(error => {
            console.log('統計データの取得に失敗しました:', error);
        });
}

function updateStatElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        animateNumber(element, parseInt(element.textContent) || 0, value);
    }
}

// 数値アニメーション
function animateNumber(element, start, end) {
    const duration = 1000;
    const startTime = performance.now();
    
    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // イージング関数
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (end - start) * eased);
        
        element.textContent = current.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }
    
    requestAnimationFrame(animate);
}

// お気に入り機能
function addToFavorites(gameId) {
    // ログインチェック
    if (!isUserLoggedIn()) {
        showLoginModal();
        return;
    }
    
    fetch('/api/favorites', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ game_id: gameId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('お気に入りに追加しました！', 'success');
            updateFavoriteButton(gameId, true);
        } else {
            showNotification('お気に入りの追加に失敗しました。', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('エラーが発生しました。', 'error');
    });
}

// 価格通知設定
function setNotification(gameId) {
    if (!isUserLoggedIn()) {
        showLoginModal();
        return;
    }
    
    const targetPrice = prompt('希望価格を入力してください（円）:');
    if (!targetPrice || isNaN(targetPrice)) {
        return;
    }
    
    fetch('/api/notifications', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            game_id: gameId,
            target_price: parseInt(targetPrice)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`¥${parseInt(targetPrice).toLocaleString()} 以下になったら通知します！`, 'success');
        } else {
            showNotification('通知設定に失敗しました。', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('エラーが発生しました。', 'error');
    });
}

// 通知表示
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // 5秒後に自動削除
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// ユーザーログイン状態チェック
function isUserLoggedIn() {
    // サーバーサイドで設定されたユーザー情報をチェック
    return window.currentUser && window.currentUser.is_authenticated;
}

// ログインモーダル表示
function showLoginModal() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal') || createLoginModal());
    modal.show();
}

// ログインモーダル作成
function createLoginModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'loginModal';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">ログインが必要です</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>この機能を使用するにはログインが必要です。</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                    <a href="/auth/login" class="btn btn-primary">ログイン</a>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

// CSRFトークン取得
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// お気に入りボタンの状態更新
function updateFavoriteButton(gameId, isFavorite) {
    const buttons = document.querySelectorAll(`[onclick="addToFavorites(${gameId})"]`);
    buttons.forEach(button => {
        if (isFavorite) {
            button.innerHTML = '<i class="fas fa-heart me-1" style="color: red;"></i>お気に入り済み';
            button.className = button.className.replace('btn-outline-primary', 'btn-outline-danger');
        }
    });
}

// 価格フォーマット
function formatPrice(price) {
    return `¥${parseInt(price).toLocaleString()}`;
}

// エラーハンドリング
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
});

// パフォーマンス監視
window.addEventListener('load', function() {
    const loadTime = performance.now();
    console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
});
