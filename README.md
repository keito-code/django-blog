# Django Blog Application

Djangoで作成したブログアプリケーションです。ユーザー認証機能とMarkdown記法に対応しています。

## 🌐 デモサイト

**URL**: https://django-blog-ox35.onrender.com

### 利用可能な機能
- ユーザー登録（`/accounts/register/`）
- ログイン（`/accounts/login/`）
- 記事の投稿・編集・削除
- Markdown記法での記事作成
- コメント機能

### ⚠️ セキュリティポリシー

#### 管理画面について
本番環境では以下のセキュリティ対策を実施しています：
- **管理者アカウントの無効化** - 不正アクセスのリスクを根本的に排除
- **管理画面URLの秘匿化** - デフォルトの`/admin/`から変更済み
- **本番環境での管理機能** - 意図的に無効化し、攻撃対象を削減

デモサイトでは一般ユーザーとして登録し、ブログ機能をお試しください。

#### セキュリティファーストの設計思想
「使わない機能は無効化する」という原則に基づき、本番環境では管理画面へのアクセスを完全に遮断しています。これにより、管理者権限を狙った攻撃を防いでいます。

## 🚀 機能一覧

- ✅ ユーザー認証（登録・ログイン・ログアウト）
- ✅ 記事のCRUD操作（作成・閲覧・更新・削除）
- ✅ Markdown記法対応
- ✅ 下書き保存機能
- ✅ コメント機能
- ✅ ページネーション（10件/ページ）
- ✅ 検索機能
- ✅ レスポンシブデザイン
- ✅ Content Security Policy (CSP) によるXSS対策

## 💻 技術スタック

- **バックエンド**: Django 5.2.4
- **言語**: Python 3.10
- **データベース**: 
  - 開発環境: SQLite3
  - 本番環境: PostgreSQL
- **CSS**: Bootstrap 5.3.7
- **ホスティング**: Render.com
- **バージョン管理**: Git/GitHub
- **セキュリティ**: HTTPS対応、セキュアクッキー設定

## 🔒 実装済みのセキュリティ対策

### 認証・認可
- **環境変数による秘密情報の管理** - SECRET_KEYやデータベース接続情報を環境変数で安全に管理
- **管理画面URLの秘匿化** - デフォルトの`/admin/`から環境変数で動的に変更し、総当たり攻撃を困難に
- **ブルートフォース対策** - django-axesにより5回のログイン失敗で1時間アカウントをロック
- **パスワードポリシー** - 最小8文字、よくあるパスワードの禁止、数字のみのパスワード禁止
- **権限管理** - 投稿の編集・削除は作者本人のみ可能（管理者を除く）

### セキュリティヘッダー・通信
- **HTTPS通信の強制** - 本番環境ではHTTPSへの自動リダイレクト
- **セキュアクッキー** - セッション情報は暗号化通信でのみ送信（SESSION_COOKIE_SECURE）
- **HSTS (HTTP Strict Transport Security)** - ブラウザに対してHTTPS通信のみを強制
- **クリックジャッキング対策** - X-Frame-Options: DENYヘッダーで他サイトへの埋め込みを防止
- **コンテンツタイプスニッフィング対策** - X-Content-Type-Options: nosniffヘッダーを設定

### 入力値の検証・サニタイズ  
- **XSS対策** - bleachライブラリによるHTMLサニタイズで、悪意のあるスクリプトの実行を防止
- **CSRF対策** - Djangoの標準CSRF保護機能を使用、すべてのPOSTリクエストでトークン検証
- **SQLインジェクション対策** - DjangoのORMを使用し、生のSQLクエリを排除

### その他のセキュリティ対策
- **DEBUG=False** - 本番環境でのエラー情報漏洩を防止
- **HttpOnlyクッキー** - JavaScriptからのクッキーアクセスを防止（SESSION_COOKIE_HTTPONLY）
- **管理者ログインの分離** - 管理者アカウントではブログシステムへのログインを禁止

### セキュリティテストと検証
- **XSSテスト** - 8種類の攻撃パターンで検証済み
- **OWASP Top 10 2021準拠** - 主要な脆弱性カテゴリに対する対策を実装

### エラーハンドリングとログ
- **カスタムエラーページ** - 403/404/500エラー用のカスタムページ実装
- **セキュリティログ** - 不正アクセス試行を記録

## 📦 セットアップ方法

### ローカル環境での実行

```bash
# リポジトリのクローン
git clone https://github.com/keito-code/django-blog.git
cd django-blog

# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してSECRET_KEYを設定

# SECRET_KEYの生成方法
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
>>> exit()


# マイグレーション
python manage.py migrate

# 管理者アカウントの作成（ローカルのみ）
python manage.py createsuperuser

# 開発サーバーの起動
python manage.py runserver
 ```
 
### ⚠️ 重要な注意事項
- **SECRET_KEYは必須です** - 環境変数として設定が必要
- **ADMIN_URLは必須です** - 管理画面のURLパスを環境変数で設定

## 🔧 環境変数

### 開発環境（.env ファイル）
```env
SECRET_KEY=your-secret-key-here  # 必須：上記の方法で生成
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
ADMIN_URL=your-admin-url  # 必須：管理画面のURLパス
```

### 本番環境（Render.com）

- `SECRET_KEY`: Djangoシークレットキー(必須)
- `DEBUG`: False（必須）
- `DATABASE_URL`: PostgreSQLの接続URL(自動接続)
- `ALLOWED_HOSTS`: your-site.onrender.com(必須)
- `ADMIN_URL`: 推測困難な管理画面URL(必須)

### 管理画面へのアクセス
管理画面のURLは環境変数`ADMIN_URL`で設定した値になります：
- 開発環境：`http://localhost:8000/{ADMIN_URL}/`
- 本番環境：`https://your-site.onrender.com/{ADMIN_URL}/`

セキュリティのため、本番環境では必ず推測困難なURLを設定してください。

## 📚 主要な依存関係
- `Django==5.2.4` - Webフレームワーク
- `python-decouple` - 環境変数管理
- `dj-database-url` - データベース設定
- `psycopg2-binary` - PostgreSQL接続
- `gunicorn` - 本番用WSGIサーバー
- `Markdown` - Markdown記法対応
- `bleach` - HTMLサニタイズによるXSS対策
- `django-axes` - ブルートフォース攻撃対策

## 📝 今後の改善予定

- [ ] 画像アップロード機能
- [ ] タグ・カテゴリ機能
- [ ] いいね機能
- [ ] ソーシャルメディア共有

## 👤 作者

keito-code