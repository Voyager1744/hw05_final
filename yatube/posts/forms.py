from django.forms import ModelForm, Textarea
from django.utils.translation import gettext_lazy as _

from .models import Post, Comment


class PostForm(ModelForm):
    """Форма для создания и редактирования постов."""

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        widgets = {
            'text': Textarea(attrs={'cols': 80, 'rows': 10}),
        }
        labels = {
            'text': _('Текст поста'),
            'group': _('Выберите группу')
        }
        help_texts = {
            'text': _('Текст нового поста'),
            'group': _('Группа, к которой будет относиться пост')
        }


class CommentForm(ModelForm):
    """Форма для создания и редактирования комментариев."""
    class Meta:
        model = Comment
        fields = ('text',)
        # widgets = {
        #     'text': Textarea(attrs={'cols': 80, 'rows': 10}),
        # }
        # labels = {
        #     'text': _('Текст комментария'),
        # }
