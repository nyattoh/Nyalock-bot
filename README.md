# ニャーロックボット (Nyalock Bot)

神威日報のZoom録画とブログ記事を自動取得・文字起こしし、RAGベースのチャットボットで検索・対話できるシステムです。

## 🚀 機能

- **自動取得**: 毎日 JST 01:00/13:00/14:00 に新規データを取得
- **文字起こし**: Zoom録画を逐語文字起こし（口調・フィラー保持）
- **RAG検索**: ブラウザ内でTF-IDF検索、関連文脈を抽出
- **神威口調**: コンテキストに基づいた口調再現での回答生成
- **GitHub Pages**: 静的サイトとして公開、サーバー不要

## 📁 プロジェクト構成

```
nyalock-bot/
├── docs/
│   └── nyalock/                   # チャットボットUI
│       ├── index.html             # メインページ
│       ├── styles.css             # スタイル
│       └── nyalock.js             # RAG検索・UI制御
├── .github/workflows/
│   └── nyalock-cron.yml           # 定期実行ワークフロー
├── import_url.txt                 # 取得対象URL設定
├── extract_video_transcriptions.py # サンプル文字起こし
├── real_transcription_extractor.py # リアルタイム文字起こし
├── whisper_transcription.py       # Whisper API版
├── video_links.txt                # Zoom録画URL一覧
├── blog_links.txt                 # ブログ記事URL一覧
└── *.json/*.txt                   # 生成データ
```

## 🔧 セットアップ

### 1. リポジトリ設定
```bash
git clone <このリポジトリ>
cd nyalock-bot
```

### 2. GitHub Secrets設定
リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定：

- `OPENAI_API_KEY`: OpenAI APIキー（Whisper用）
- `ZOOM_CLIENT_ID`: Zoom API用（オプション）
- `ZOOM_CLIENT_SECRET`: Zoom API用（オプション）

### 3. GitHub Pages有効化
- **Settings** → **Pages**
- **Source**: Deploy from a branch
- **Branch**: main / docs

### 4. 初回実行
- **Actions** タブ → **nyalock-cron** → **Run workflow** でテスト実行

## 📅 自動実行スケジュール

GitHub Actionsが以下の時刻に自動実行：
- **01:00 JST** (16:00 UTC 前日)
- **13:00 JST** (04:00 UTC)
- **14:00 JST** (05:00 UTC)

## 🎯 使用方法

### チャットボット
1. GitHub Pagesで公開されたページにアクセス
2. `https://<ユーザー>.github.io/<リポジトリ名>/nyalock/`
3. 質問を入力して検索・対話

### LLM生成（オプション）
- Cloudflare Workers等で中継エンドポイントを作成
- 設定画面でエンドポイントURLを入力
- 「LLMを使用」をチェックして神威口調での回答生成

## 🔍 データソース

### movie (Zoom録画)
- `import_url.txt`のNotionサイトから記事詳細ページの右パネルZoomリンクを抽出
- Whisper APIで逐語文字起こし（フィラー・口調保持）

### blog (記事)
- `import_url.txt`のGitHub Pagesインデックスから新規記事を抽出
- 本文を正規化して保存

## 📊 生成データ

- `real_transcriptions.json`: 統合データ（movie + blog）
- `real_transcriptions.txt`: 人間可読形式
- `docs/nyalock/`: チャットボット用データ配置先

## 🛠️ 技術スタック

- **スケジューラ**: GitHub Actions (cron)
- **文字起こし**: OpenAI Whisper API
- **検索**: ブラウザ内TF-IDF
- **UI**: Vanilla JavaScript + GitHub Pages
- **LLM**: OpenAI GPT (中継経由)
- **データ**: JSON形式での静的配信

## 📝 ログ・監視

- GitHub Actionsの実行ログで処理状況を確認
- 失敗時は自動で次回リトライ

## 🤝 開発・貢献

- Issues・PRでの改善提案歓迎

## 📄 ライセンス

MIT License

## 🔗 関連リンク

- [チャットボット](docs/nyalock/) - GitHub Pagesで公開されるRAGチャット
