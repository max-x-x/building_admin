from django import forms
from django.contrib.auth.forms import AuthenticationForm

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "input",
        "placeholder": "Email"
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "input",
        "placeholder": "Пароль"
    }))


class InvitationForm(forms.Form):
    ROLE_CHOICES = [
        ('ССК', 'ССК'),
        ('ИКО', 'ИКО'),
        ('Прораб', 'Прораб'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)


class MemoForm(forms.Form):
    title = forms.CharField(max_length=200, label='Название методички')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Описание')
    link = forms.URLField(label='Ссылка на методичку')


class NotificationForm(forms.Form):
    TYPE_CHOICES = [
        ('info', 'ℹ️ Информационное'),
        ('urgent', '🚨 Срочное'),
        ('warning', '⚠️ Предупреждение'),
        ('success', '✅ Успех'),
    ]
    
    RECIPIENT_TYPE_CHOICES = [
        ('all', 'Все пользователи'),
        ('admins', 'Администраторы'),
        ('managers', 'Менеджеры'),
        ('workers', 'Работники'),
        ('specific', 'Конкретный пользователь'),
    ]
    
    title = forms.CharField(max_length=200, label='Заголовок уведомления')
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Сообщение')
    notification_type = forms.ChoiceField(choices=TYPE_CHOICES, label='Тип уведомления')
    recipient_type = forms.ChoiceField(choices=RECIPIENT_TYPE_CHOICES, label='Получатели')
    specific_user = forms.ChoiceField(choices=[], label='Выберите пользователя', required=False)


class ExternalLoginForm(forms.Form):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "input",
        "placeholder": "Email"
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "input",
        "placeholder": "Пароль"
    }))
