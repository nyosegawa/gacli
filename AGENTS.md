# AGENTS.md

gacli の開発に参加する Coding Agent 向けのガイドです。

## アーキテクチャ

```
gacli/
  cli.py      — Click コマンド定義、出力フォーマット、config管理
  client.py   — GA4 Data API 呼び出し（純粋関数: credentials + params → dict）
  oauth.py    — OAuth フローと認証情報の永続化
tests/
  test_client.py  — client.py の純粋関数テスト
  test_config.py  — config管理の純粋関数テスト
```

### 設計原則

- **cli.py は薄く**: API 呼び出しロジックは client.py に、認証は oauth.py に分離。cli.py は引数パースと出力整形のみ
- **client.py は純粋関数**: `Credentials` と パラメータを受け取り `dict` を返す。副作用なし
- **構造化出力**: 全データコマンドは `--json` フラグ対応。パイプ時は自動で JSON モード
- **エラーメッセージ**: What/Why/Fix パターンで統一。Agent が次のアクションを判断できるようにする

## テスト方針

- **純粋関数テスト中心**: `_parse_response()` や config I/O など、API を叩かずにテストできる関数を重点的にテスト
- **API モック**: `get_client` をモックし、リクエスト構築の正しさを検証
- **E2E テストはしない**: GA4 API の正しさは Google に任せる
- テスト実行: `uv run pytest`

## 新しいコマンドを追加するとき

1. `client.py` に API 呼び出し関数を追加（`Credentials` を第1引数に取り、`dict` を返す）
2. `cli.py` にコマンドを追加（`require_property_id` + `require_credentials` でガード）
3. テーブル表示と `is_json_mode()` による JSON 出力の両方を実装
4. `tests/test_client.py` にリクエスト構築テストを追加

## config 構造

`~/.config/gacli/` に保存:

```
client_secret.json          — OAuth クライアント ID（ユーザーが配置）
default_profile             — デフォルトプロファイル名
profiles/<name>/
  config.json               — {"property_id": "..."}
  credentials.json          — OAuth トークン（自動管理）
```

## 依存関係

- `google-analytics-data` — GA4 Data API クライアント
- `google-auth-oauthlib` — OAuth フロー
- `click` — CLI フレームワーク
- `rich` — テーブル表示
