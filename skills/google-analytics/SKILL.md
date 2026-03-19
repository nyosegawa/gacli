---
name: google-analytics
description: >
  GA4アクセス解析をgacliで実行する。
  PV・ユーザー数・セッション数の確認、人気ページランキング、リアルタイムユーザー数の取得。
  Use when user asks to "アクセス解析", "PV確認", "アクセス数", "人気ページ",
  "Google Analytics", "GA4", "gacli", "analytics report",
  or any analytics/traffic related operation.
compatibility: Requires gacli installed and authenticated (gacli auth). Claude Code only.
metadata:
  author: sakasegawa
  version: 1.0.0
---

# Google Analytics Skill

gacli を使って GA4 のアクセス解析データを取得するスキルです。

## Prerequisites

認証確認:

```bash
gacli config
```

`authenticated: no` の場合は `gacli auth` で認証してください。

## Core Pattern: Profile → Command → Output

1. **Profile** — プロファイルで認証とプロパティIDを管理
2. **Command** — データコマンドでレポート取得
3. **Output** — `--json` で構造化出力、パイプで自動 JSON

## Command Quick Reference

### セットアップ
| Command | Description |
|---|---|
| `gacli auth [--profile NAME]` | ブラウザで OAuth 認証 |
| `gacli config -p <PROPERTY_ID> [--profile NAME] [--set-default]` | プロパティID設定 |
| `gacli profiles` | プロファイル一覧 |

### データ取得
| Command | Description |
|---|---|
| `gacli summary [-d DAYS]` | 日別サマリー（PV / ユーザー / セッション）|
| `gacli pages [-d DAYS] [-n LIMIT]` | ページ別 PV ランキング |
| `gacli realtime` | リアルタイムアクティブユーザー |

### グローバルフラグ
- `--json` — JSON 出力（パイプ時は自動有効）
- `--profile NAME` — 使用するプロファイルを指定
- `-p PROPERTY_ID` — プロパティIDを一時的に上書き

## Common Workflows

### 1. 直近のアクセス状況を確認

```bash
# 過去7日間のサマリー
gacli summary

# 過去30日間
gacli summary -d 30
```

### 2. 人気ページを調べる

```bash
# トップ10ページ
gacli pages

# トップ20、過去30日間
gacli pages -n 20 -d 30
```

### 3. リアルタイムの状況

```bash
gacli realtime
```

### 4. 他のツールと組み合わせる

```bash
# JSON で取得して jq で加工
gacli --json summary | jq '.rows[] | select(.activeUsers | tonumber > 10)'

# 特定ページのPVだけ抽出
gacli --json pages | jq '.rows[] | select(.pagePath | contains("/posts/"))'
```

### 5. 複数サイトのレポート

```bash
# プロファイル切り替え
gacli --profile blog summary
gacli --profile work summary
```

## JSON Output Schema

全データコマンド共通:

```json
{
  "dimensions": ["date"],
  "metrics": ["screenPageViews", "activeUsers", "sessions"],
  "rows": [
    {
      "date": "20260319",
      "screenPageViews": "17",
      "activeUsers": "21",
      "sessions": "21"
    }
  ],
  "row_count": 1
}
```

## Important Notes

1. **エラーメッセージの Hint に従う** — What/Why/Fix パターンで次のアクションを提示
2. **`--json` を使う** — プログラムからの利用時は常に `--json` を指定
3. **日付は `YYYYMMDD` 形式** — JSON 出力の date dimension は `20260319` 形式
4. **値は文字列** — メトリクスの値は数値ではなく文字列で返る。比較時は `tonumber` 等で変換
