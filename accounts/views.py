from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import SignUpForm


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, 'アカウントが作成されました。ようこそ！')
            return redirect('blog:post_list')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('blog:post_list')


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_staff or user.is_superuser:
                    messages.error(request, '管理者アカウントではブログシステムにログインできません。')
                    return redirect('accounts:login')
                else:
                    login(request, user)
                    messages.success(request, 'ログインしました。')
                    return redirect('blog:post_list')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})
