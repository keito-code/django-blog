# Django CSP実装プロジェクト

## 実施期間
2025年7月29日

## 概要
Djangoブログシステムに対してContent Security Policy (CSP)を実装し、XSS攻撃への防御を強化しました。レポートモードでのデータ収集から始め、248件の違反データを分析し、段階的にセキュリティポリシーを強化しました。

## 実装した機能
- CSPレポート機能の実装（違反データの収集・分析）
- 違反データの分析（248件）→ 必要なCDNのみ許可
- unsafe-inlineの削除によるセキュリティ強化
- nonce機能の実装（django-csp 4.0対応）
- レポートモードから本番モードへの移行
- 実装中に発見したバグの修正

## 技術スタック
- Django 5.2.4
- django-csp 4.0
- Python 3.10
- SQLite3（開発環境）
- Bootstrap 5.3.7（CDN経由）

## 実装プロセス

### 1. 初期実装とデータ収集
- django-cspをレポートモードで実装
- `/csp-report/`エンドポイントを作成し、CSP違反をデータベースに記録
- 通常のブラウジング操作で248件の違反データを収集
- Django shellでデータ分析を実施：
  ```python
  # 違反の内訳
  style-src-elem: 200件（Bootstrap CSS 100件 + Bootstrap Icons CSS 100件）
  font-src: 48件（Bootstrap Iconsのフォントファイル）
  ```

### 2. データ分析に基づく改善
- 違反の原因：CDN（cdn.jsdelivr.net）からのリソース読み込みがCSPでブロック
- 対策：必要最小限のCDNのみを許可リストに追加
  ```python
  'style-src': (SELF, 'https://cdn.jsdelivr.net'),
  'font-src': (SELF, 'https://cdn.jsdelivr.net'),
  ```
- 結果：CDN関連の違反が0件に減少

### 3. unsafe-inline削除による強化
- セキュリティ強化のため`'unsafe-inline'`を削除
- 新たに6件のstyle-src-elem違反を検出
- 原因特定：`post_detail.html`内の`<style>`タグ
- 解決策：インラインスタイルを外部ファイル（`static/style.css`）に移動
- 結果：インラインスタイル違反も0件に

### 4. nonce実装への挑戦
- 初期アプローチ：カスタムミドルウェアでnonce生成を試みる
- 問題：CSPヘッダーにnonceが追加されない
- 調査：Claude Codeを活用してdjango-csp 4.0のドキュメントを調査
- 発見：バージョン4.0で実装方法が変更されていた
  ```python
  # 旧方式（動作しない）
  CSP_INCLUDE_NONCE_IN = ['script-src', 'style-src']
 
  # 新方式（正しい）
  from csp.constants import NONCE, SELF
  'script-src': (SELF, NONCE, 'https://cdn.jsdelivr.net'),
  ```
- 結果：nonce機能が正常に動作

### 5. 本番モード移行と問題解決
本番モードへの移行時に発見・解決した問題：

1. **slug重複エラー**
  - 原因：同一タイトルの記事作成時にslugが重複
  - 解決：`generate_unique_slug()`関数を実装

2. **管理画面でのslug空問題**
  - 原因：管理画面からの記事作成時にslug自動生成が働かない
  - 解決：`admin.py`に`save_model()`メソッドを追加

3. **セキュリティリスク**
  - 問題：管理画面から公開ページへの直接遷移
  - 解決：`view_on_site = False`で無効化

## 成果

### セキュリティ面
- XSS攻撃に対する多層防御を実現
- インラインスクリプト/スタイルの実行を防止
- 信頼できるCDNのみを明示的に許可

### 技術面
- CSP違反の可視化と分析プロセスを確立
- データドリブンなセキュリティポリシー改善
- django-csp 4.0の新機能（NONCE定数）を活用

### 数値的成果
- CSP違反：248件 → 0件
- 許可したCDN：必要最小限の2つのみ
- 発見・修正したバグ：3件

## 学んだこと

### 技術的な学び
1. **CSPの重要性**：エスケープ/サニタイズに加えた追加の防御層として機能
2. **段階的アプローチ**：レポートモード → 分析 → 改善 → 本番モードの流れ
3. **バージョン管理**：ライブラリのバージョンによる実装方法の違い

### 実務的な学び
1. **データドリブンな改善**：推測ではなく実際のデータに基づいて判断
2. **問題解決能力**：予期しない問題への対処と調査方法
3. **セキュリティと利便性のバランス**：必要なリソースは許可しつつ、セキュリティを確保

### プロジェクト管理
1. **適切なツールの選択**：Claude Codeを活用した効率的な問題解決
2. **副次的効果**：CSP実装中に他のバグも発見・修正
3. **ドキュメント化**：実装内容と学びを記録する重要性

## 今後の展望
- HTTPS環境での動作確認
- CSPレポートの定期的な監視体制構築
- より高度なCSP機能（Strict-Dynamic等）の検討
- 他のセキュリティヘッダー（X-Frame-Options、X-Content-Type-Options等）の実装

## 参考リンク
- [django-csp公式ドキュメント](https://django-csp.readthedocs.io/)
- [MDN Web Docs - Content Security Policy](https://developer.mozilla.org/docs/Web/HTTP/CSP)
- [Google Web Fundamentals - CSP](https://developers.google.com/web/fundamentals/security/csp)