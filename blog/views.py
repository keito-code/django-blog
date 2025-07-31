from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
import json
import logging
from .models import Post, Comment, CSPViolation
from .forms import PostForm, CommentForm, SearchForm
import markdown
import bleach


def post_list(request):
    post_list = Post.objects.filter(status='published')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    return render(request, 'blog/post_list.html', {'posts': posts})


def post_detail(request, slug):
    post = get_object_or_404(Post,
                             slug=slug,
                             status='published')
    
    comments = post.comments.filter(active=True)
    new_comment = None
    
    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
            messages.success(request, 'コメントが投稿されました。')
            return redirect(post.get_absolute_url())
    else:
        comment_form = CommentForm()
    
    md = markdown.Markdown(extensions=['extra', 'sane_lists'])
    html = md.convert(post.content)
    
    # 安全なタグのみ許可
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's',
        'ul', 'ol', 'li', 
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre',
        'a', 'img', 'hr'
    ]
    allowed_attrs = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title']
    }
    
    # サニタイズ
    post.content_html = bleach.clean(
        html, 
        tags=allowed_tags, 
        attributes=allowed_attrs,
        strip=True
    )

    return render(request, 'blog/post_detail.html', {
        'post': post,
        'comments': comments,
        'new_comment': new_comment,
        'comment_form': comment_form
    })


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            if 'status' in request.POST:
                post.status = request.POST['status']
            
            post.save()
            if post.status == 'published':
                messages.success(request, '記事が公開されました。')
            else:
                messages.success(request, '記事が下書きとして保存されました。')
            return redirect('blog:post_list')
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form, 'title': '新規投稿'})


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 作者本人または管理者のみ編集可能
    if post.author != request.user and not request.user.is_staff:
        messages.error(request, 'この記事を編集する権限がありません。')
        return redirect('blog:post_list')

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)

            # アクションに応じたステータスを設定
            action = request.POST.get('action', 'save')

            if action == 'publish':
                post.status = 'published'
                post.save()
                messages.success(request, '記事を公開しました。')
                return redirect(post.get_absolute_url())
            elif action == 'draft':
                post.status = 'draft'
                post.save()
                messages.success(request, '下書きを保存しました。')
                return redirect('blog:post_update', pk=post.pk)
            else:  # 'save' またはその他
                # statusは変更せず、現在の状態を維持
                post.save()
                messages.success(request, '記事を保存しました。')
                return redirect('blog:post_update', pk=post.pk)
      
    else:
        form = PostForm(instance=post)

    return render(request, 'blog/post_form.html', {
        'form': form, 
        'post': post,
        'title': '記事編集'
    })


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # 作者本人または管理者のみ削除可能
    if post.author != request.user and not request.user.is_staff:
        messages.error(request, 'この記事を削除する権限がありません。')
        return redirect('blog:post_list')
    if request.method == 'POST':
        post.delete()
        messages.success(request, '記事が削除されました。')
        return redirect('blog:post_list')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


def post_search(request):
    form = SearchForm()
    query = None
    results = []
    
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query),
                status='published'
            )
    
    paginator = Paginator(results, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    return render(request, 'blog/post_search.html', {
        'form': form,
        'query': query,
        'posts': posts
    })


@login_required
def post_draft_list(request):
    posts = Post.objects.filter(status='draft', author=request.user)
    return render(request, 'blog/post_draft_list.html', {'posts': posts})


logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def csp_report(request):
    """CSP違反レポートを受信してデータベースに保存"""
    try:
        # CSPレポートはJSONで送信される
        data = json.loads(request.body.decode('utf-8'))
        csp_report = data.get('csp-report', {})
        
        # IPアドレスを取得（プロキシ経由の場合も考慮）
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # CSPViolationモデルに保存
        violation = CSPViolation.objects.create(
            directive=csp_report.get('violated-directive', ''),
            blocked_uri=csp_report.get('blocked-uri', ''),
            document_uri=csp_report.get('document-uri', ''),
            line_number=csp_report.get('line-number'),
            column_number=csp_report.get('column-number'),
            source_file=csp_report.get('source-file', ''),
            original_policy=csp_report.get('original-policy', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=ip_address
        )
        
        # ログにも記録
        logger.warning(
            f'CSP Violation: {violation.directive} blocked {violation.blocked_uri} '
            f'on {violation.document_uri} from {ip_address}'
        )
        
        return HttpResponse(status=204)  # No Content
        
    except json.JSONDecodeError:
        logger.error('Invalid JSON in CSP report')
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f'Error processing CSP report: {e}')
        return HttpResponse(status=500)