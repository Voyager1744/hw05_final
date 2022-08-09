"""Тест Url страниц."""
from http import HTTPStatus

from django.test import TestCase, Client
from django.urls import reverse

from ..models import Post, Group, User


class PostsUrlTest(TestCase):
    group = None
    author = None

    @classmethod
    def setUpTestData(cls):
        """Создаём Пользователя и группу."""
        cls.author = User.objects.create_user(username='author')
        cls.not_author = User.objects.create_user(username='not_author')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
        )

    def setUp(self) -> None:
        """Создаём авторизованного и неавторизованного
        клиента, автора и пост.
        """
        self.authorized_client = Client()
        self.authorized_client.force_login(self.not_author)
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.author)
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.author,
            group=self.group,
        )

    def test_url_is_available_to_the_authorized(self):
        """Приватные страницы доступны авторизованным пользователям.
        """
        url_names_httpstatus = {
            reverse('posts:post_create'): HTTPStatus.OK,
            reverse('posts:post_edit', args=(self.post.id,)): HTTPStatus.OK,
        }
        for address, httpstatus in url_names_httpstatus.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address, follow=True)
                self.assertEqual(response.status_code, httpstatus)

    def test_url_is_available_to_the_not_authorized(self):
        """Публичные адреса доступны для неавторизованных пользователей.
        """
        url_names_httpstatus = {
            reverse('posts:index'): HTTPStatus.OK,
            reverse('posts:group_list',
                    args=(self.group.slug,)): HTTPStatus.OK,
            reverse('posts:profile',
                    args=(self.author.username,)): HTTPStatus.OK,
        }
        for address, httpstatus in url_names_httpstatus.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, httpstatus)

    def test_availability_404_page(self):
        """Тестирование доступности адреса страницы 404."""
        response = self.client.get('/unexciting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_redirect_guest_client_on_login(self):
        """Тест приватные адреса не доступны для
        неавторизованных пользователей,
        ведут на страницу авторизации.
        """
        login_url = reverse('users:login')
        address_url = reverse('posts:post_edit', args=(self.post.id,))
        expected_url = f'{login_url}?next={address_url}'
        self.assertRedirects(
            self.client.get(address_url), expected_url)

        address_url = reverse('posts:post_create')
        expected_url = f'{login_url}?next={address_url}'
        self.assertRedirects(
            self.client.get(address_url), expected_url)

    def test_redirect_url_edit_post_no_author_to_post(self):
        """Перенаправление всех, кроме автора со страницы
         редактирования на страницу просмотра поста.
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=(self.post.id,)), follow=True)
        expected_url = reverse('posts:post_detail', args=(self.post.id,))
        self.assertRedirects(response, expected_url)

    def test_follow_page_for_auth(self):
        """Доступность адреса /follow/ для авторизованного клиента"""
        response = self.authorized_client.get(
            reverse('posts:follow_index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_follow_page_for_not_auth_redirect(self):
        """Недоступность адреса /follow/ и последующий редирект
        на страницу авторизации для неавторизованных клиентов.
        """
        response = self.client.get(reverse('posts:follow_index'), follow=True)
        login_url = reverse('users:login')
        address = reverse('posts:follow_index')
        expected_url = f'{login_url}?next={address}'
        self.assertRedirects(response, expected_url)
