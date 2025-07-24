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

### ⚠️ 管理画面について
セキュリティを考慮し、本番環境では管理者アカウントを作成していません。
一般ユーザーとして登録して、すべての機能をお試しください。

## 🚀 機能一覧

- ✅ ユーザー認証（登録・ログイン・ログアウト）
- ✅ 記事のCRUD操作（作成・閲覧・更新・削除）
- ✅ Markdown記法対応
- ✅ 下書き保存機能
- ✅ コメント機能
- ✅ ページネーション（10件/ページ）
- ✅ 検索機能
- ✅ レスポンシブデザイン

## 💻 技術スタック

- **バックエンド**: Django 5.2.4
- **言語**: Python 3.10
- **データベース**: 
  - 開発環境: SQLite3
  - 本番環境: PostgreSQL
- **CSS**: Bootstrap 5.3.7
- **ホスティング**: Render.com
- **バージョン管理**: Git/GitHub

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
**SECRET_KEYは必須です。** defaultを削除したため、`.env`ファイルにSECRET_KEYを設定しないとアプリケーションは起動しません。


## 🔧 環境変数

### 開発環境（.env ファイル）
```env
SECRET_KEY=your-secret-key-here  # 必須：上記の方法で生成
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

### 本番環境（Render.com）

- `SECRET_KEY`: Djangoシークレットキー(必須)
- `DEBUG`: False（必須）
- `DATABASE_URL`: PostgreSQLの接続URL(自動接続)
- `ALLOWED_HOSTS`: your-site.onrender.com(必須)

## 📚 主要な依存関係
- `Django==5.2.4` - Webフレームワーク
- `python-decouple`- 環境変数管理
- `dj-database-url`- データベース設定
- `psycopg2-binary`- PostgreSQL接続
- `gunicorn`- 本番用WSGIサーバー
- `Markdown`- Markdown記法対応

## 📝 今後の改善予定

- [ ] 画像アップロード機能
- [ ] タグ・カテゴリ機能
- [ ] いいね機能
- [ ] ソーシャルメディア共有

## 👤 作者

keito-code