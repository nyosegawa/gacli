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
  version: 2.0.0
---

# Google Analytics Skill

gacli を使って GA4 のアクセス解析データを取得するスキルです。

## Prerequisites

認証確認:

```bash
gacli config
```

`authenticated: no` の場合は `gacli auth` で認証してください。

## Core Pattern: query コマンドを優先する

**`gacli query` は GA4 API への escape hatch です。任意のディメンション・メトリクス・フィルタ・ソートを自由に組み合わせてクエリできます。** 定型コマンド（summary / pages / realtime）では対応できない要求には、必ず `query` を使ってください。

判断基準:
- 単純な日別PV確認 → `gacli summary` でOK
- 単純なページランキング → `gacli pages` でOK
- 国別リアルタイムユーザー → `gacli realtime` でOK
- **それ以外のすべて** → `gacli query` を使う

## `gacli query` — Escape Hatch

### 基本構文

```bash
gacli query -m <METRIC> [-m <METRIC>...] [-d <DIMENSION>...] [OPTIONS]
```

### オプション

| Option | Description |
|---|---|
| `-m, --metric` | メトリクス名（複数指定可、必須） |
| `-d, --dimension` | ディメンション名（複数指定可） |
| `--days N` | 過去N日間（デフォルト: 7） |
| `--hours N` | 過去N時間（--days より優先） |
| `-n, --limit N` | 最大行数（0 = 無制限） |
| `--sort FIELD:desc\|asc` | ソート（デフォルト: desc） |
| `-f, --filter "EXPR"` | フィルタ（複数指定可） |
| `--realtime` | リアルタイム API を使用 |

### フィルタ構文

**文字列フィルタ（ディメンション用）:**
```
"field contains value"
"field exact value"
"field begins_with value"
"field ends_with value"
"field regex pattern"
```

**数値フィルタ（メトリクス用）:**
```
"field > 100"
"field >= 50"
"field < 10"
"field == 0"
```

複数フィルタは AND 結合されます。

### よく使うメトリクス

| Metric | Description |
|---|---|
| `screenPageViews` | ページビュー数 |
| `activeUsers` | アクティブユーザー数 |
| `sessions` | セッション数 |
| `bounceRate` | 直帰率 |
| `averageSessionDuration` | 平均セッション時間 |
| `newUsers` | 新規ユーザー数 |
| `engagedSessions` | エンゲージセッション数 |

### よく使うディメンション

| Dimension | Description |
|---|---|
| `date` | 日付 (YYYYMMDD) |
| `dateHour` | 日時 (YYYYMMDDHH) |
| `pagePath` | ページパス |
| `country` | 国 |
| `city` | 都市 |
| `deviceCategory` | デバイス (desktop/mobile/tablet) |
| `sessionSource` | 流入元 |
| `sessionMedium` | メディア (organic/referral/social 等) |
| `sessionSourceMedium` | ソース/メディア |
| `unifiedScreenName` | ページタイトル（リアルタイム向け） |

### query の使用例

```bash
# 直近3時間のページ別PV
gacli query -m screenPageViews -m activeUsers -d pagePath --hours 3 --sort screenPageViews:desc -n 10

# 日別×ページ別のクロス集計
gacli query -m screenPageViews -d date -d pagePath --days 7 --sort screenPageViews:desc -n 20

# 特定記事のPV推移
gacli query -m screenPageViews -d date --days 30 -f "pagePath contains harness"

# デバイス別ユーザー数
gacli query -m activeUsers -d deviceCategory --days 7

# 流入元別セッション数
gacli query -m sessions -d sessionSourceMedium --days 7 --sort sessions:desc -n 10

# リアルタイムのページ別アクティブユーザー
gacli query -m activeUsers -d unifiedScreenName --realtime --sort activeUsers:desc -n 10

# PVが100以上のページだけ抽出
gacli query -m screenPageViews -d pagePath --days 7 -f "screenPageViews > 100" --sort screenPageViews:desc

# 国×デバイスのクロス集計（リアルタイム）
gacli query -m activeUsers -d country -d deviceCategory --realtime
```

## 定型コマンド（シンプルな確認用）

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
| `gacli realtime` | リアルタイムアクティブユーザー（国別） |

### グローバルフラグ
- `--json` — JSON 出力（パイプ時は自動有効）
- `--profile NAME` — 使用するプロファイルを指定
- `-p PROPERTY_ID` — プロパティIDを一時的に上書き

## JSON Output Schema

全データコマンド共通（query 含む）:

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

1. **`query` を積極的に使う** — 定型コマンドで対応できない要求は迷わず `query` を使う
2. **エラーメッセージの Hint に従う** — What/Why/Fix パターンで次のアクションを提示
3. **日付は `YYYYMMDD` 形式** — JSON 出力の date dimension は `20260319` 形式
4. **値は文字列** — メトリクスの値は数値ではなく文字列で返る。比較時は `tonumber` 等で変換
5. **リアルタイムのディメンションは異なる** — `pagePath` の代わりに `unifiedScreenName` 等を使う
