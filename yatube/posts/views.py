from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404

from posts.forms import PostForm, CommentForm
from posts.models import Post, Group, User, Comment, Follow
from posts.utils import get_paginator


def index(request):
    """Полученные записи передаются в код как объекты класса Post,
    сохраняются в виде списка в переменной posts
    и передаются в словаре context под ключом 'posts'
    в шаблон posts/index.html.
    """
    posts = Post.objects.select_related(
        'author', 'group')

    page_obj = get_paginator(request, posts)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.group_posts.select_related(
        'author', 'group')

    page_obj = get_paginator(request, posts)

    context = {
        'group': group,
        'page_obj': page_obj,
    }

    return render(request, template, context)


def profile(request, username):
    """Страница автора."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group')

    page_obj = get_paginator(request, posts)

    following = (request.user.is_authenticated
                 and request.user.follower.filter(author=author).exists())

    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Подробная информация поста."""
    post = get_object_or_404(Post, id=post_id)
    comments = Comment.objects.filter(post_id=post_id)
    form_comments = CommentForm(request.POST or None)
    context = {
        'post': post,
        'comments': comments,
        'form': form_comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создание поста."""
    form = PostForm(request.POST or None)
    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('posts:profile', username=request.user.username)
    context = {
        'form': form,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, id=post_id)

    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post.id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)

    context = {
        'form': form,
        'is_edit': True,
        'post': post
    }

    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    """Добавить комментарий."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница с постами авторов, на которых подписан текущий пользователь."""
    posts_follow = Post.objects.filter(author__following__user=request.user)
    page_obj = get_paginator(request, posts_follow)
    context = {
        'title': 'Мои подписки',
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписаться на автора."""
    author = get_object_or_404(User, username=username)
    is_follow = request.user.follower.filter(author=author).exists()
    if request.user != author and not is_follow:
        request.user.follower.create(author=author)
    return redirect(
        'posts:profile',
        username=username
    )


@login_required
def profile_unfollow(request, username):
    """Дизлайк, отписка."""
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
