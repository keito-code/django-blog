# Django Blog API

[![CI/CD](https://github.com/keito-code/django-blog/actions/workflows/django.yml/badge.svg)](https://github.com/keito-code/django-blog/actions)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](https://github.com/keito-code/django-blog)


RESTful APIとWebビューを提供するブログアプリケーション

## 🌐 デモサイト & APIドキュメント

**デモサイトURL**: https://django-blog-ox35.onrender.com

**APIドキュメント (Swagger UI)**: https://django-blog-ox35.onrender.com/api/v1/schema/swagger-ui/


## ⚡ 技術スタック

- Django REST Framework
- JWT認証 (SimpleJWT)
- PostgreSQL
- Swagger UI自動生成
- djangorestframework-camel-case


## 📈 開発状況

- ✅ **完成済み**
  - Web版ブログ機能
  - REST API（認証・CRUD）
  - JWT認証システム
  - CORS設定（Vercel対応）
  
- 🚧 **開発中**
  - [Next.jsフロントエンド](https://blog-frontend-ten-xi.vercel.app)


## 📡 主要なAPIエンドポイント

### 認証 (`/api/v1/auth/`)
- `POST /register/` - 新規登録
- `POST /login/` - ログイン（JWT発行）
- `POST /logout/` - ログアウト
- `GET /user/` - ユーザー情報取得

### ブログ (`/api/v1/blog/posts/`)
- `GET /` - 記事一覧
- `POST /` - 記事作成（要認証）
- `GET /{id}/` - 記事詳細
- `PUT /{id}/` - 記事更新（要認証・作者のみ）
- `DELETE /{id}/` - 記事削除（要認証・作者のみ）

詳細な仕様は[Swagger UI](https://django-blog-ox35.onrender.com/api/v1/schema/swagger-ui/)を参照


## 🔧 セットアップ

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```


## 🔧 環境変数

### 開発環境（.env ファイル）
```env
# Django設定
SECRET_KEY=your-secret-key-here # 必須 生成方法は下記参照
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3

# 管理画面
ADMIN_URL=admin # 開発環境では'admin'でOK

# JWT認証
JWT_SECRET_KEY=your-jwt-secret-key-here # 必須：JWT署名用 (SECRET_KEYとは別)

# CORS設定
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### ⚠️ 本番環境での必須変更
- **SECRET_KEY** - 本番用に再生成
- **DEBUG** - False
- **ALLOWED_HOSTS** - your-site.onrender.com
- **DATABASE_URL** - PostgreSQLの接続URL
- **ADMIN_URL** - 推測困難な文字列に変更
- **JWT_SECRET_KEY** - 本番用に別途生成 (SECRET_KEYとは異なる値を推奨)
- **CORS_ALLOWED_ORIGINS** - your-site.vercel.app

### SECRET_KEY / JWT_SECRET_KEYの生成方法
```bash
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
```

## 📝 今後のAPI拡張予定

- [ ] 検索API
- [ ] ページネーションAPI
- [ ] 画像アップロードAPI
- [ ] タグ・カテゴリAPI
- [ ] いいね機能API

## 👤 作者

keito-code