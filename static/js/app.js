/**
 * GameBargain Frontend JavaScript
 * 
 * フロントエンド機能の実装
 * お気に入り管理、検索候補、価格アラートなどの機能を提供します。
 */

// アプリケーション設定
const GameBargain = {
    config: {
        apiBaseUrl: '/api',
        searchDelay: 300,
        toastDuration: 5000,
        maxRetries: 3
    },
    
    // 初期化
    init() {
        this.initEventListeners();
        this.initTooltips();
        this.initSearchSuggestions();
        this.initFavoriteButtons();
        this.initPriceAlerts();
        console.log('GameBargain frontend initialized');
    },

    // イベントリスナーの初期化
    initEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initBootstrapComponents();
        });

        // ページ読み込み完了時の処理
        window.addEventListener('load', () => {
            this.hideLoadingSpinner();
        });

        // エラーハンドリング
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.showToast('エラーが発生しました', 'error');
        });
    },

    // Bootstrapコンポーネントの初期化
    initBootstrapComponents() {
        // Tooltipの初期化
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

        // Popoverの初期化
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    },

    // ツールチップの初期化
    initTooltips() {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    },

    // 検索候補機能の初期化
    initSearchSuggestions() {
        const searchInputs = document.querySelectorAll('input[type="search"]');
        
        searchInputs.forEach(input => {
            let searchTimeout;
            let suggestionsContainer;

            input.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                const query = e.target.value.trim();

                if (query.length < 2) {
                    this.hideSuggestions(input);
                    return;
                }

                searchTimeout = setTimeout(() => {
                    this.fetchSearchSuggestions(query, input);
                }, this.config.searchDelay);
            });

            input.addEventListener('blur', (e) => {
                // 少し遅延させて候補クリックを可能にする
                setTimeout(() => {
                    this.hideSuggestions(input);
                }, 200);
            });

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.hideSuggestions(input);
                }
            });
        });
    },

    // 検索候補の取得
    async fetchSearchSuggestions(query, inputElement) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/search/suggestions?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.suggestions && data.suggestions.length > 0) {
                this.showSuggestions(data.suggestions, inputElement);
            } else {
                this.hideSuggestions(inputElement);
            }
        } catch (error) {
            console.error('Search suggestions error:', error);
        }
    },

    // 検索候補の表示
    showSuggestions(suggestions, inputElement) {
        this.hideSuggestions(inputElement); // 既存の候補を削除

        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'absolute top-full left-0 right-0 bg-gray-700 border border-gray-600 border-t-0 rounded-b-lg shadow-lg z-50 max-h-80 overflow-y-auto';
        
        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'px-4 py-3 cursor-pointer border-b border-gray-600 text-gray-300 hover:bg-gray-600 hover:text-white transition-colors duration-200 last:border-b-0';
            item.textContent = suggestion;
            
            item.addEventListener('click', () => {
                inputElement.value = suggestion;
                this.hideSuggestions(inputElement);
                
                // 検索フォームの送信
                const form = inputElement.closest('form');
                if (form) {
                    form.submit();
                }
            });
            
            suggestionsContainer.appendChild(item);
        });

        // 入力フィールドの親要素に候補を追加
        const parent = inputElement.parentElement;
        parent.style.position = 'relative';
        parent.appendChild(suggestionsContainer);
    },

    // 検索候補の非表示
    hideSuggestions(inputElement) {
        const parent = inputElement.parentElement;
        const existing = parent.querySelector('.absolute.top-full');
        if (existing) {
            existing.remove();
        }
    },

    // お気に入りボタンの初期化
    initFavoriteButtons() {
        const favoriteButtons = document.querySelectorAll('.favorite-btn');
        
        favoriteButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleFavorite(button);
            });
        });
    },

    // お気に入りの切り替え
    async toggleFavorite(button) {
        const gameId = button.dataset.gameId;
        const icon = button.querySelector('i');
        const isFavorited = button.classList.contains('favorited');

        // UI即座更新（楽観的更新）
        this.updateFavoriteButtonUI(button, !isFavorited);

        try {
            const method = isFavorited ? 'DELETE' : 'POST';
            const response = await fetch(`${this.config.apiBaseUrl}/favorites`, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ game_id: parseInt(gameId) })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                // エラー時は元に戻す
                this.updateFavoriteButtonUI(button, isFavorited);
                this.showToast(data.message || 'お気に入りの更新に失敗しました', 'error');
                return;
            }

            this.showToast(data.message, 'success');

        } catch (error) {
            console.error('Favorite toggle error:', error);
            // エラー時は元に戻す
            this.updateFavoriteButtonUI(button, isFavorited);
            this.showToast('ネットワークエラーが発生しました', 'error');
        }
    },

    // お気に入りボタンUIの更新
    updateFavoriteButtonUI(button, favorited) {
        const icon = button.querySelector('i');
        
        if (favorited) {
            icon.classList.remove('bi-heart');
            icon.classList.add('bi-heart-fill');
            button.classList.remove('btn-outline-danger');
            button.classList.add('btn-danger', 'favorited');
            button.setAttribute('title', 'お気に入りから削除');
        } else {
            icon.classList.remove('bi-heart-fill');
            icon.classList.add('bi-heart');
            button.classList.remove('btn-danger', 'favorited');
            button.classList.add('btn-outline-danger');
            button.setAttribute('title', 'お気に入りに追加');
        }

        // ツールチップの更新
        const tooltip = bootstrap.Tooltip.getInstance(button);
        if (tooltip) {
            tooltip.dispose();
            new bootstrap.Tooltip(button);
        }
    },

    // 価格アラート機能の初期化
    initPriceAlerts() {
        const alertButtons = document.querySelectorAll('.price-alert-btn');
        
        alertButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.showPriceAlertModal(button.dataset.gameId);
            });
        });
    },

    // 価格アラートモーダルの表示
    showPriceAlertModal(gameId) {
        // モーダルHTML の生成
        const modalHtml = `
            <div class="modal fade" id="priceAlertModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">価格アラート設定</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="priceAlertForm">
                                <div class="mb-3">
                                    <label for="thresholdPrice" class="form-label">通知価格（円）</label>
                                    <input type="number" class="form-control" id="thresholdPrice" 
                                           placeholder="例: 2000" min="0" step="100" required>
                                    <div class="form-text">この価格以下になったら通知します</div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                            <button type="button" class="btn btn-primary" id="savePriceAlert">設定する</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // モーダルを追加
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('priceAlertModal'));
        
        // 保存ボタンのイベント
        document.getElementById('savePriceAlert').addEventListener('click', () => {
            this.savePriceAlert(gameId, modal);
        });

        // モーダル削除のイベント
        modal._element.addEventListener('hidden.bs.modal', () => {
            modal._element.remove();
        });

        modal.show();
    },

    // 価格アラートの保存
    async savePriceAlert(gameId, modal) {
        const thresholdPrice = document.getElementById('thresholdPrice').value;
        
        if (!thresholdPrice || thresholdPrice <= 0) {
            this.showToast('有効な価格を入力してください', 'error');
            return;
        }

        try {
            const response = await fetch(`${this.config.apiBaseUrl}/price-alerts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    game_id: parseInt(gameId),
                    threshold_price: parseFloat(thresholdPrice)
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showToast('価格アラートを設定しました', 'success');
                modal.hide();
            } else {
                this.showToast(data.message || '設定に失敗しました', 'error');
            }

        } catch (error) {
            console.error('Price alert error:', error);
            this.showToast('ネットワークエラーが発生しました', 'error');
        }
    },

    // トースト通知の表示
    showToast(message, type = 'info') {
        const toastContainer = this.getOrCreateToastContainer();
        
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${this.getToastColor(type)} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi bi-${this.getToastIcon(type)} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement, { delay: this.config.toastDuration });
        
        toast.show();

        // トースト削除のイベント
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    },

    // トーストコンテナの取得または作成
    getOrCreateToastContainer() {
        let container = document.querySelector('.toast-container');
        
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
        }
        
        return container;
    },

    // トーストの色を取得
    getToastColor(type) {
        const colors = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'primary'
        };
        return colors[type] || 'primary';
    },

    // トーストアイコンを取得
    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },

    // ローディングスピナーの表示
    showLoadingSpinner(element) {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        element.appendChild(spinner);
    },

    // ローディングスピナーの非表示
    hideLoadingSpinner() {
        const spinners = document.querySelectorAll('.loading-spinner');
        spinners.forEach(spinner => spinner.remove());
    },

    // ページ遷移時のローディング表示
    showPageLoading() {
        const loadingHtml = `
            <div id="pageLoading" class="position-fixed top-0 start-0 w-100 h-100 bg-white bg-opacity-75 d-flex align-items-center justify-content-center" style="z-index: 9999;">
                <div class="text-center">
                    <div class="loading-spinner mb-3"></div>
                    <p class="text-muted">読み込み中...</p>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    },

    // ページローディングの非表示
    hidePageLoading() {
        const loading = document.getElementById('pageLoading');
        if (loading) {
            loading.remove();
        }
    },

    // API呼び出しのユーティリティ
    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(`${this.config.apiBaseUrl}${endpoint}`, mergedOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    },

    // 価格フォーマット
    formatPrice(price, currency = 'JPY') {
        if (typeof price !== 'number') return '価格未定';
        
        const formatter = new Intl.NumberFormat('ja-JP', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
        
        return formatter.format(price);
    },

    // 日付フォーマット
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },

    // デバッグモード
    enableDebugMode() {
        window.GameBargainDebug = {
            config: this.config,
            showToast: this.showToast.bind(this),
            apiCall: this.apiCall.bind(this)
        };
        console.log('Debug mode enabled. Use window.GameBargainDebug');
    }
};

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
    GameBargain.init();
    
    // デバッグモード（開発環境のみ）
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        GameBargain.enableDebugMode();
    }
});

// グローバルに公開
window.GameBargain = GameBargain;
