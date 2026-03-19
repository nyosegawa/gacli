# gacli

マルチプロファイル対応のシンプルな Google Analytics 4 CLI。gcloud 不要。

## インストール

```bash
uv tool install --from . gacli
```

## セットアップ

### 1. OAuth クライアント ID を作成

1. **Google Analytics Data API** を有効化（[リンク](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)）
2. OAuth クライアント ID を作成（[リンク](https://console.cloud.google.com/auth/clients/create)）→ アプリの種類: **デスクトップアプリ**
3. JSON をダウンロードして以下に保存:

```
~/.config/gacli/client_secret.json
```

### 2. 認証

```bash
gacli auth
```

ブラウザが開きます。GA4 プロパティにアクセスできる Google アカウントでログインしてください。

### 3. プロパティ ID を設定

[Google Analytics](https://analytics.google.com/) > 管理 > プロパティの設定 でプロパティ ID を確認。

```bash
gacli config -p <PROPERTY_ID>
```

## 使い方

```bash
gacli summary          # 日別サマリー（PV / ユーザー / セッション、過去7日間）
gacli summary -d 30    # 過去30日間
gacli pages            # ページ別 PV ランキング
gacli pages -n 20      # トップ20
gacli realtime         # リアルタイムアクティブユーザー
```

### JSON 出力

全データコマンドが `--json` に対応。パイプ時は自動で JSON モードになります。

```bash
gacli --json summary
gacli pages | jq '.rows[] | select(.pagePath | contains("/posts/"))'
```

## 使用例: Claude Code Agent Skill

gacli には [Claude Code Agent Skill](./skills/google-analytics/SKILL.md) が付属しています。リンクすれば、自然言語でアクセス解析ができます:

```
❯ 今日のアクセスどうだった？

⏺ Skill(google-analytics)
  ⎿  Successfully loaded skill

⏺ Bash(gacli summary -d 1)
⏺ Bash(gacli pages -d 1 -n 10)
⏺ Bash(gacli realtime)

⏺ 今日（3/19）のアクセス状況です。

  | 指標         | 数値 |
  |-------------|------|
  | PV          | 66   |
  | ユーザー数   | 68   |
  | セッション数 | 68   |

  人気ページ Top 5:
  1. /posts/docs-in-agent-era/ — 19 PV
  2. /posts/harness-engineering-best-practices-2026/ — 19 PV
  3. /posts/japanese-handwriting-ocr-comparison/ — 7 PV

  リアルタイム: 261人がアクティブ（うち247人が日本から）
```

有効化:

```bash
ln -s /path/to/gacli/skills/google-analytics ~/.claude/skills/google-analytics
```

## マルチプロファイル

複数サイト・複数 Google アカウントをプロファイルで管理。

```bash
# プロファイル作成
gacli auth --profile blog
gacli config -p 111111 --profile blog --set-default

gacli auth --profile work        # 別の Google アカウントでログイン
gacli config -p 222222 --profile work

# プロファイル指定で実行
gacli --profile work summary

# プロファイル一覧
gacli profiles
```

認証情報と設定はプロファイルごとに `~/.config/gacli/profiles/<name>/` に保存されます。

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `gacli auth` | ブラウザで認証 |
| `gacli config` | 設定の表示・更新 |
| `gacli profiles` | プロファイル一覧 |
| `gacli summary` | 日別サマリー（PV、ユーザー、セッション）|
| `gacli pages` | ページ別 PV ランキング |
| `gacli realtime` | リアルタイムアクティブユーザー |
