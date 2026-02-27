# 商品提案書自動作成エージェント (Web App v5) 実装計画書

## ゴール (Goal)
これまでのCLI型ツール (`create_proposal_v4.py`) を、ユーザーフレンドリーな **Webアプリケーション** に進化させます。
PCやタブレットのブラウザ上で「商品検索 → 画像選択 → 提案生成 → 確認・調整 → 保存」の一連のフローを完結できるようにします。

## ユーザー確認事項 (User Review Required)
> [!IMPORTANT]
> **実行環境について**
> - **サーバー**: ローカル環境で `uvicorn` コマンドで起動します。
> - **ブラウザ**: Chrome, Safari 等で `http://localhost:8000` にアクセスして使用します。
> - **依存関係**: 新たに `fastapi`, `uvicorn`, `python-multipart` のインストールが必要です。

## アーキテクチャ (Architecture)

### 技術スタック
- **Backend**: Python (FastAPI) - 高速かつ型安全なAPIサーバー
- **Frontend**: HTML5, CSS3, Vanilla JavaScript - 軽量で依存関係の少ないモダンUI
- **Data Source**: DuckDuckGo (Search), Google Gemini (AI Generation)

### ディレクトリ構成
```
/proposal-engine
├── app_v5.py            # メインアプリケーション (FastAPI)
├── static/              # 静的ファイル
│   ├── index.html       # メインUI HTML
│   ├── style.css        # スタイルシート
│   └── app.js           # フロントエンドロジック
├── templates/           # (Optional) HTMLテンプレート
├── .env                 # 環境変数 (API Key)
└── requirements.txt     # 依存ライブラリ
```

## 実装ステップ (Implementation Steps)

### 1. プロジェクトセットアップ (Project Setup)
- 必要なディレクトリ (`static`) の作成。
- `requirements.txt` の更新とインストール。

### 2. バックエンドAPI実装 (`app_v5.py`)
既存の `create_proposal_v4.py` の関数を再利用し、以下のAPIエンドポイントを作成します。
- `POST /api/search`: 商品情報を検索し、背景情報を取得。
- `POST /api/images`: 商品画像を検索し、URLリストを返す。
- `POST /api/generate`: 確定した商品情報と画像URLを受け取り、Geminiで提案コンテンツを生成。JSONで返す。

### 3. フロントエンド実装 (`static/`)
- **UIデザイン**: 白とパステルカラーを基調とした、清潔感とプレミアム感のあるデザイン。
- **入力フォーム**: 商品名、価格、容量を入力。
- **インタラクティブ画像選択**: 取得した画像をグリッド表示し、クリックで選択。
- **リアルタイム生成**: 「提案書を作成」ボタンでAI生成を実行し、結果を画面にプレビュー表示。
- **編集機能**: 生成されたキャッチコピーや文章を、その場でクリックして編集可能にする（`contenteditable`）。

### 4. 出力・保存機能
- **印刷/PDF化**: ブラウザの標準印刷機能 (`window.print()`) を使い、A4サイズに最適化されたCSS (`@media print`) で綺麗なPDFを出力。

## 検証 (Verification)
- ローカルサーバーを起動し、ブラウザからアクセス。
- 実際の商品名を入力し、エラーなく提案書が生成されるか確認。
- 画像選択やテキスト編集がスムーズに動作するか確認。
