"""Тестирование контекста."""
import shutil
import tempfile

from random import randint

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User, Follow


class PostViewTest(TestCase):
    author_1 = None
    group_1 = None

    @classmethod
    def setUpTestData(cls):
        """Создание тестовых авторов и группы."""
        cls.author_1 = User.objects.create_user(username='Author_1')
        cls.author_2 = User.objects.create_user(username='Author_2')
        cls.group_1 = Group.objects.create(
            title='Тестовая_Группа_1',
            slug='group_1'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая_Группа_2',
            slug='group_2'
        )
        cls.post_1 = Post.objects.create(
            text='Тестовый пост 1',
            author=cls.author_1,
            group=cls.group_1
        )

    def setUp(self) -> None:
        """Создание клиентов."""
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.author_1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.author_2)

    def test_url_uses_correct_template(self):
        """Приватные адреса используют соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', args=(self.post_1.id,)):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_1.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_url_uses_correct_template_for_not_auth(self):
        """Публичные адреса используют соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', args=(self.group_1.slug,)):
                'posts/group_list.html',
            reverse('posts:profile', args=(self.author_1.username,)):
                'posts/profile.html',
            reverse('posts:post_detail', args=(self.post_1.id,)):
                'posts/post_detail.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_have_correct_context(self):
        """В шаблон index передается верный контекст."""
        response = self.client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertIn('page_obj', response.context)
        self.assertEqual(first_object, self.post_1)

    def test_group_list_have_correct_context(self):
        """В шаблон group_list передается верный контекст."""
        response = self.client.get(
            reverse('posts:group_list', args=(self.group_1.slug,))
        )
        self.assertIn('group', response.context)
        self.assertIn('page_obj', response.context)
        group_in_context = response.context['group']
        first_object = response.context['page_obj'][0]
        self.assertEqual(group_in_context, self.group_1)
        self.assertEqual(first_object, self.post_1)

    def test_profile_page_have_correct_context(self):
        """В шаблон profile передается верный контекст."""
        response = self.client.get(
            reverse('posts:profile', args=(self.author_1.username,))
        )
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        author_in_context = response.context['author']
        first_object = response.context['page_obj'][0]
        self.assertEqual(author_in_context, self.author_1)
        self.assertEqual(first_object, self.post_1)

    def test_post_detail_have_correct_context(self):
        """В шаблон post_detail передается верный контекст."""
        response = self.client.get(
            reverse('posts:post_detail', args=(self.post_1.id,))
        )
        self.assertIn('post', response.context)
        post_from_context = response.context['post']
        self.assertEqual(post_from_context, self.post_1,
                         'В шаблон post_detail передается неверный контекст.'
                         )

    def test_create_post_have_correct_context(self):
        """В шаблон create_post передается верный контекст."""
        response = self.authorized_client_1.get(reverse('posts:post_create'))
        self.assertIn('form', response.context)
        form_in_context = response.context['form']
        self.assertEqual(type(form_in_context), type(PostForm()))

    def test_post_edit_have_correct_context(self):
        """В шаблон страницы post_edit передается верный контекст."""
        response = self.authorized_client_1.get(
            reverse('posts:post_edit', args=(self.post_1.id,))
        )
        self.assertIn('form', response.context)
        form_in_context = response.context['form']
        self.assertEqual(type(form_in_context), type(PostForm()))
        self.assertTrue(response.context['is_edit'])

    def test_url_follow_uses_correct_template(self):
        """Адресу /follow/ для авторизованных клиентов
         соответствует шаблон follow.html.
        """
        self.assertTemplateUsed(
            self.authorized_client_1.get(reverse('posts:follow_index')),
            'posts/follow.html'
        )

    def test_nonexistent_page_pattern_fits_404(self):
        """Несуществующему адресу соответствует шаблон 404.html."""
        self.assertTemplateUsed(
            self.authorized_client_1.get('/unexciting_page/'),
            'core/404.html'
        )


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Создание автора, группы и некоторого количества постов."""
        cls.author = User.objects.create_user(username='Автор_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_test'
        )

    def test_paginator(self):
        """Тестируем правильное количество постов на последней странице.
        Предполагается, что если на последней странице выводится верное
        количество постов, то на остальных их QTY_POSTS - по умолчанию 10."""
        self.number_create_posts = randint(
            settings.QTY_POSTS + 1, settings.QTY_POSTS * 2)
        posts = []
        for i in range(self.number_create_posts):
            posts.append(Post(
                text=f'test_text_{i}',
                author=self.author,
                group=self.group))
        self.few_posts = Post.objects.bulk_create(posts)
        self.count_post_page = self.number_create_posts - settings.QTY_POSTS
        url_name = {
            reverse('posts:index'): self.count_post_page,
            reverse('posts:group_list',
                    args=(self.group.slug,)): self.count_post_page,
            reverse('posts:profile',
                    args=(self.author.username,)): self.count_post_page
        }
        quantity_page = self.number_create_posts // settings.QTY_POSTS + 1

        for address, count_post in url_name.items():
            with self.subTest(address=address):
                response = self.client.get(address, {'page': 1})
                number_posts_on_page = len(response.context['page_obj'])
                self.assertEqual(number_posts_on_page, settings.QTY_POSTS)
                response = self.client.get(address, {'page': quantity_page})
                number_posts_on_page = len(response.context['page_obj'])
                self.assertEqual(number_posts_on_page, count_post)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Создаём автора и пост."""
        cls.author_1 = User.objects.create_user(username='Author_1')
        cls.post_1 = Post.objects.create(
            text='test text',
            author=cls.author_1
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляет тестовую папку.
        """
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        """Создаём авторизованного клиента.
        """
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author_1)

    def test_image_on_page(self):
        """Тест отображения картинок на разных страницах.
        """
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        Post.objects.create(
            text='Тестовый текст',
            author=self.author_1,
            image=uploaded
        )
        self.assertEqual(Post.objects.count(), post_count + 1)

        post_2 = Post.objects.create(
            text='test text 2',
            author=self.author_1,
            group=Group.objects.create(
                title='test_title',
                slug='test_slug'
            ),
            image=uploaded
        )

        response = self.client.get(
            reverse('posts:post_detail', args=(post_2.id,)))
        image_in_context = response.context['post'].image
        self.assertEqual(post_2.image, image_in_context)

        response = self.client.get(
            reverse('posts:index'))
        images = [post.image for post in response.context['page_obj']]
        self.assertIn(post_2.image, images)

    def test_cache_index(self):
        """Тестирование кэша."""
        new_test_post = Post.objects.create(
            text='Новый тестовый текст',
            author=self.author_1,
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        resp_before = response.content
        post_deleted = Post.objects.get(id=new_test_post.id)
        post_deleted.delete()
        response_another = self.authorized_client.get(
            reverse('posts:index')
        )
        resp_after = response_another.content
        self.assertTrue(resp_before == resp_after)
        cache.clear()
        response_another = self.authorized_client.get(
            reverse('posts:index')
        )
        resp_after = response_another.content
        self.assertFalse(resp_before == resp_after)


class FollowTest(TestCase):
    author = None

    @classmethod
    def setUpTestData(cls):
        """Создаём автора и подписчика."""
        cls.author = User.objects.create(
            username='Author_1'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='test_text'
        )
        cls.follower = User.objects.create(
            username='Follower_1'
        )

    def setUp(self) -> None:
        """Создаём авторизованного клиента.
        """
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)

    def test_add_follow(self):
        """Проверяем, что авторизованный пользователь может подписаться.
        """
        self.author_2 = User.objects.create(
            username='Author_2'
        )
        count_before = Follow.objects.filter(
            user=self.follower, author=self.author_2).count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author_2.username,)
            )
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.follower, author=self.author_2).count(),
            count_before + 1
        )

        follow_last = Follow.objects.last()
        self.assertEqual(follow_last.author, self.author_2)
        self.assertEqual(follow_last.user, self.follower)

    def test_not_add_follow_for_non_auth(self):
        """Неавторизованный пользователь не может подписаться."""
        count_before = Follow.objects.filter(
            user=self.follower, author=self.author).count()
        self.client.get(
            reverse('posts:profile_follow', args=(self.author.username,))
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.follower, author=self.author).count(),
            count_before
        )

    def test_remove_follow(self):
        """Авторизованный пользователь может отписаться."""
        self.objects_create = User.objects.create(username='Author_2')
        self.self_objects_create = self.objects_create
        self.author_2 = self.self_objects_create
        count_before = Follow.objects.filter(
            user=self.follower, author=self.author_2).count()
        self.create = Follow.objects.create(author=self.author_2,
                                            user=self.follower)
        self.assertEqual(Follow.objects.filter(
            user=self.follower, author=self.author_2).count(),
                         count_before + 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.author_2.username,)
            )
        )
        self.assertEqual(Follow.objects.filter(
            user=self.follower, author=self.author_2).count(), count_before)

    def test_show_author_post_on_follower_page(self):
        """Отображение постов автора в ленте подписок у
        подписанных на автора пользователей.
        """
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn('page_obj', response.context)
        post_text = response.context['page_obj'][0].text
        self.assertEqual(post_text, self.post.text)

    def test_not_show_author_post_on_not_follower_page(self):
        """Отсутствие постов автора в ленте подписок у
        неподписанных на автора пользователей.
        """
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn('page_obj', response.context)

        self.authorized_client.logout()
        User.objects.create_user(
            username='user_temp',
            password='pass'
        )
        self.authorized_client.login(username='user_temp', password='pass')
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_user_not_follow_yourself(self):
        """Пользователь не может подписаться сам на себя."""
        count_before = Follow.objects.filter(
            user=self.follower, author=self.follower).count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.follower.username,)
            )
        )
        self.assertEqual(
            Follow.objects.filter(
                user=self.follower, author=self.follower).count(),
            count_before
        )
