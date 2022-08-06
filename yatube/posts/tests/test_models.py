"""Тестирование моделей приложения Posts"""
from random import randint

from django.test import TestCase
from django.conf import settings

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Создание тестовых пользователя группы и поста."""
        cls.user_1 = User.objects.create_user(username='author_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_1,
            text='тест ' * randint(1, 10),
            group=cls.group
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        str_name = {
            str(self.post): self.post.text[:settings.FIRST_CHARS_POST],
            str(self.group): self.group.title
        }
        for name, name_post in str_name.items():
            with self.subTest(name=name):
                self.assertEqual(name, name_post)
