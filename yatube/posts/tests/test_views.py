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
    @classmethod
    def setUpClass(cls):
        """Создание тестовых авторов и группы."""
        super().setUpClass()
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

    def setUp(self) -> None:
        """Создание клиентов и постов."""
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.author_1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.author_2)
        self.post_1 = Post.objects.create(
            text='Тестовый пост 1',
            author=self.author_1,
            group=self.group_1
        )

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
        group_in_context = response.context['group']
        first_object = response.context['page_obj'][0]

        self.assertIn('group', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(group_in_context, self.group_1)
        self.assertEqual(first_object, self.post_1)

    def test_profile_page_have_correct_context(self):
        """В шаблон profile передается верный контекст."""
        response = self.client.get(
            reverse('posts:profile', args=(self.author_1.username,))
        )
        author_in_context = response.context['author']
        first_object = response.context['page_obj'][0]
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(author_in_context, self.author_1)
        self.assertEqual(first_object, self.post_1)

    def test_post_detail_have_correct_context(self):
        """В шаблон post_detail передается верный контекст."""
        response = self.client.get(
            reverse('posts:post_detail', args=(self.post_1.id,))
        )
        post_from_context = response.context['post']
        self.assertIn('post', response.context)
        self.assertEqual(post_from_context, self.post_1,
                         'В шаблон post_detail передается неверный контекст.'
                         )

    def test_create_post_have_correct_context(self):
        """В шаблон create_post передается верный контекст."""
        response = self.authorized_client_1.get(reverse('posts:post_create'))
        form_in_context = response.context['form']
        self.assertIn('form', response.context)
        self.assertEqual(type(form_in_context), type(PostForm()))

    def test_post_edit_have_correct_context(self):
        """В шаблон страницы post_edit передается верный контекст."""
        response = self.authorized_client_1.get(
            reverse('posts:post_edit', args=(self.post_1.id,))
        )
        form_in_context = response.context['form']
        self.assertIn('form', response.context)
        self.assertEqual(type(form_in_context), type(PostForm()))
        self.assertTrue(response.context['is_edit'])


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        """Создание автора и группы."""
        super().setUpClass()
        cls.author = User.objects.create_user(username='Автор_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_test'
        )

        cls.form = PostForm()

    def setUp(self):
        """Создание некоторого количества постов."""
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

    def test_paginator(self):
        """Тестируем правильное количество постов на последней странице.
        Предполагается, что если на последней странице выводится верное
        количество постов, то на остальных их QTY_POSTS - по умолчанию 10."""
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
                response = self.client.get(address, {'page': quantity_page})
                number_posts_on_page = len(response.context['page_obj'])
                self.assertEqual(number_posts_on_page, count_post)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_1 = User.objects.create_user(username='Author_1')
        cls.post_1 = Post.objects.create(
            text='test text',
            author=cls.author_1
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляет тестовую папку.
        """
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

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
        form_data = {
            'text': 'Тестовый текст',
            'author': self.author_1,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data
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

        response = self.client.get(
            reverse('posts:profile', args=(post_2.author,)))
        images = [post.image for post in response.context['page_obj']]
        self.assertIn(post_2.image, images)

        response = self.client.get(
            reverse('posts:group_list', args=(post_2.group.slug,)))
        images = [post.image for post in response.context['page_obj']]
        self.assertIn(post_2.image, images)

    def test_cache_index(self):
        """Тестирование кэша."""
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        resp_before = response.content
        post_deleted = Post.objects.get(id=1)
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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(
            username='Author_1'
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
        """Проверяем, что авторизованный пользователь может подписаться,
        и новая запись появляется у него в ленте.
        """
        count_before = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,)
            )
        )
        self.assertEqual(Follow.objects.count(), count_before + 1)

        follow_first = Follow.objects.first()
        self.assertEqual(follow_first.author, self.author)
        self.assertEqual(follow_first.user, self.follower)

        # проверяем, что у другого автора подписки не появились
        not_follows = Follow.objects.filter(
            author=self.author,
            user=self.author)
        self.assertEqual(len(not_follows), 0)

    def test_not_add_follow_for_non_auth(self):
        """Неавторизованный пользователь не может подписаться."""
        count_before = Follow.objects.count()
        self.client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,)
            ), follow=True
        )
        self.assertEqual(Follow.objects.count(), count_before)

    def test_remove_follow(self):
        """Авторизованный пользователь может отписаться."""
        count_before = Follow.objects.count()
        # подписываемся на автора
        Follow.objects.create(
            author=self.author,
            user=self.follower
        )
        # проверяем что подписка создалась
        self.assertEqual(Follow.objects.count(), count_before + 1)
        # пользователь отписывается
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.author.username,)
            )
        )
        # проверяем что подписок больше нет
        self.assertEqual(Follow.objects.count(), count_before)
