from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.contrib import messages
from .models import Post, Comment
from .forms import PostForm, CommentForm, SearchForm
import markdown


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
    post.content_html = md.convert(post.content)
    
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
            if not post.slug:
                post.slug = slugify(post.title, allow_unicode=False)
                # 空文字列の場合 (日本語タイトル) の処理を追加
                if not post.slug:
                    from django.utils.crypto import get_random_string
                    post.slug = f"post-{get_random_string(8)}"
            
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

            # slugの自動生成
            if not post.slug:
                post.slug = slugify(post.title, allow_unicode=False)
                # 空文字列の場合 (日本語タイトル) の処理を追加
                if not post.slug:
                    post.slug = f"post-{get_random_string(8)}"

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