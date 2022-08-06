from django.test import Client, TestCase
from django.urls import reverse

from faker import Faker

from ..models import Group, Post, User, Comment


class PostFormTests(TestCase):
    fake = Faker()

    @classmethod
    def setUpClass(cls):
        """Создаём автора и две группы."""
        super().setUpClass()
        cls.author = User.objects.create_user(username=cls.fake.user_name())
        cls.author_2 = User.objects.create_user(username=cls.fake.user_name())
        cls.group_1 = Group.objects.create(
            title='Первая тестовая группа',
            slug='group_test_1'
        )
        cls.group_2 = Group.objects.create(
            title='Вторая тестовая группа',
            slug='group_test_2'
        )

    def setUp(self):
        """Создаём клиента и пост."""
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.post = Post.objects.create(
            text=self.fake.text(),
            author=self.author,
            group=self.group_1)
        self.post_2 = Post.objects.create(
            text=self.fake.text(),
            author=self.author_2,
            group=self.group_1)

    def test_create_post_form(self):
        """При отправке валидной формы со страницы создания поста
        создаётся новая запись в базе данных.
        """
        post_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group_1.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        first_post = Post.objects.first()
        self.assertEqual(
            Post.objects.count(),
            post_count + 1,
            'Новая запись в базе данных не создана!'
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(self.author.username,)),
        )
        self.assertEqual(first_post.text, self.post.text, 'не тот текст')
        self.assertEqual(first_post.author, self.post.author, 'не тот автор')
        self.assertEqual(first_post.group, self.post.group, 'не та группа')

    def test_edit_post_form(self):
        """Проверка изменений поста в базе данных.
        """
        test_post = Post.objects.create(
            text='test text',
            author=self.author,
            group=self.group_1
        )
        new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='new_group'
        )
        text_new_post = test_post.text
        group_new_post = test_post.group
        count_posts_before = Post.objects.count()
        form_data = {
            'text': 'Измененный текст поста',
            'group': new_group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(test_post.id,)),
            data=form_data
        )
        test_post.refresh_from_db()
        modified_post = test_post
        count_posts_after = Post.objects.count()
        self.assertEqual(
            count_posts_before,
            count_posts_after,
            'Количество постов изменилось!')

        self.assertNotEqual(
            modified_post.text,
            text_new_post,
            'Текст поста не изменился!'
        )
        self.assertNotEqual(
            modified_post.group,
            group_new_post,
            'Группа у поста не изменилась!'
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(test_post.id,)),
        )
        self.assertEqual(
            modified_post.author,
            test_post.author,
            'Не тот автор!'
        )

    def test_authorized_cant_edit_not_author_post(self):
        """Авторизированный пользователь не может редактировать чужой пост."""
        count_posts_before = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post_2.id,)), follow=True)
        expected_url = reverse('posts:post_detail', args=(self.post_2.id,))
        count_posts_after = Post.objects.count()
        self.assertRedirects(response, expected_url)
        self.assertEqual(
            count_posts_before,
            count_posts_after,
            'Количество постов изменилось!')

    def test_not_authorized_cant_create_post_and_redirect_login(self):
        """Неавторизованный пользователь не может создать пост,
        и его перенаправляет на страницу авторизации.
        """
        count_posts_before = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group_1.id
        }
        response = self.client.post(
            reverse('posts:post_create'), data=form_data, follow=True)
        login_url = reverse('users:login')
        create_url = reverse('posts:post_create')
        expected_url = f'{login_url}?next={create_url}'
        count_posts_after = Post.objects.count()
        self.assertRedirects(response, expected_url)
        self.assertEqual(
            count_posts_before,
            count_posts_after,
            'Количество постов изменилось!')

    def test_comment_form_auth(self):
        """Тест авторизованный пользователь может комментировать посты,
        комментарий появляется на странице.
        """
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

        self.assertTrue(
            Comment.objects.filter(
                text='Тестовый комментарий',
            ).exists()
        )
        added_comment = response.context["comments"][0]
        self.assertEqual(added_comment.post, self.post)
        self.assertEqual(added_comment.author, self.author)
        self.assertEqual(added_comment.text, form_data["text"])

    def test_comment_form_not_auth(self):
        """Тест неавторизованный пользователь не может
        комментировать посты,
        комментарий не появляется на странице,
        пользователя перенаправляет на страницу авторизации.
        """
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.client.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertNotEqual(Comment.objects.count(), comments_count + 1)

        self.assertFalse(
            Comment.objects.filter(
                text='Тестовый комментарий',
            ).exists()
        )
        login_url = reverse('users:login')
        create_url = reverse('posts:add_comment', args=(self.post.id,))
        expected_url = f'{login_url}?next={create_url}'
        self.assertRedirects(response, expected_url)


