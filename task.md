# 商品提案書自動作成エージェント構築

- [x] 要件定義とフロー設計 (Implementation Plan作成)
- [x] ユーザーへの提案と確認 (notify_user)
- [x] Pythonスクリプトの実装 (商品リサーチ、構成案作成)
- [x] 画像検索・処理ロジックの実装
- [x] 出力フォーマット (Markdown/HTML) の作成
- [x] 動作テストと検証

## Phase 2: アプリ改造 (v2)
- [x] A4縦サイズへのレイアウト変更
- [x] 印刷/PDF保存ボタンの実装
- [x] A4一枚に収まるようCSS調整
- [x] 会社情報（右上の連絡先）の追加
- [x] 動作確認 (v2)

## Phase 3: アプリ改造 (v3)
- [x] v3ファイルの作成
- [x] 商品画像のサイズ拡大 (1.5倍)
- [x] レイアウト再調整 (画像拡大に伴う調整)
- [x] キャッチコピーの上下余白拡大
- [x] 垂直方向のレイアウトバランス調整（余白活用）
- [x] 動作確認 (v3)
- [x] 入力項目追加（容量）と価格表示の変更
- [x] 動作確認 (v3 args)
- [x] 価格表示の微調整（色統一、フォントサイズ、全角スペース）
- [x] 動作確認 (v3 format)

## Phase 4: Refinement & Advanced Features (v4)
- [x] v4ファイルの作成 (v3からのコピー)
- [x] デスクトップへのデプロイ (`~/Desktop/商品提案エージェント`)
- [x] Gemeniモデル修正 (flash-preview)

## Phase 5: Web App Implementation (v5)
- [x] **Project Setup**
    - [x] 必要なライブラリのインストール (`fastapi`, `uvicorn`, `python-multipart` 等)
    - [x] ディレクトリ構造の作成 (`static/`, `templates/`)
- [x] **Backend Implementation (FastAPI)**
    - [x] `app_v5.py` の作成
    - [x] 既存ロジック (`create_proposal_v4.py`) の移植とAPI化 (3 step)
        - [x] `/api/search` (商品検索)
        - [x] `/api/images` (画像検索)
        - [x] `/api/generate` (提案書生成)
- [x] **Frontend Implementation**
    - [x] `static/index.html` (メインUI) の作成
    - [x] `static/style.css` (モダンでプレミアムなデザイン) の作成
    - [x] `static/app.js` (Web UIロジック) の作成
- [x] **Integration & Testing**
    - [x] 検索・画像選択・生成フローの結合テスト
    - [x] PDF保存/印刷機能の確認
- [x] **Final Polish**
    - [x] デザイン微調整
    - [x] エラーハンドリングの強化

## Phase 6: Editing Features (v5.1)
- [ ] **Context Editing (Comment/Text)**
    - [ ] 既に `contenteditable` は設定済みだが、保存時や編集の挙動を確認・強化する。
- [ ] **Image Replacement**
    - [ ] メイン画像をクリックした際に、サイドバーで選択中の画像を反映させる、またはURLを直接入力して差し替える機能の実装。
    - [ ] あるいは、画像のドラッグ＆ドロップ対応（任意ファイルをアップロード）も検討。
    - [ ] 今回はまず、「メイン画像をクリックしたら、現在サイドバーで選択されている画像に差し変わる」機能を実装する。
