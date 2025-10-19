from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


class AdminManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Admin(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = AdminManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Invitation(models.Model):
    ROLE_CHOICES = [
        ('ССК', 'ССК (Старший Строительный Контролер)'),
        ('ИКО', 'ИКО (Инженер Контроля Объектов)'),
        ('Прораб', 'Прораб (Производственный Работник)'),
    ]
    
    email = models.EmailField('Email адрес')
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES)
    message = models.TextField('Персональное сообщение', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(Admin, on_delete=models.CASCADE, verbose_name='Создано пользователем')
    
    class Meta:
        verbose_name = 'Приглашение'
        verbose_name_plural = 'Приглашения'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {self.role}"


class Memo(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    file_url = models.URLField('Ссылка на файл', max_length=5000, blank=True, null=True)
    file_name = models.CharField('Имя файла', max_length=255, blank=True, null=True)
    file_size = models.IntegerField('Размер файла (байты)', blank=True, null=True)
    object_id = models.IntegerField('ID объекта', blank=True, null=True)
    object_name = models.CharField('Название объекта', max_length=2049, blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(Admin, on_delete=models.CASCADE, verbose_name='Создано пользователем')
    
    class Meta:
        verbose_name = 'Методичка'
        verbose_name_plural = 'Методички'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class SentNotification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Информационное'),
        ('urgent', 'Срочное'),
        ('warning', 'Предупреждение'),
        ('success', 'Успех'),
    ]
    
    RECIPIENT_TYPE_CHOICES = [
        ('all', 'Все пользователи'),
        ('ssk', 'ССК'),
        ('iko', 'ИКО'),
        ('foreman', 'Прораб'),
    ]
    
    title = models.CharField('Заголовок', max_length=200)
    message = models.TextField('Сообщение')
    notification_type = models.CharField('Тип уведомления', max_length=10, choices=TYPE_CHOICES)
    recipient_type = models.CharField('Тип получателей', max_length=10, choices=RECIPIENT_TYPE_CHOICES)
    specific_user_id = models.CharField('ID конкретного пользователя', max_length=100, blank=True, null=True)
    specific_user_name = models.CharField('Имя конкретного пользователя', max_length=200, blank=True, null=True)
    is_urgent = models.BooleanField('Срочное уведомление', default=False)
    sent_at = models.DateTimeField('Время отправки', auto_now_add=True)
    sent_by = models.ForeignKey(Admin, on_delete=models.CASCADE, verbose_name='Отправлено пользователем')
    read_count = models.IntegerField('Количество прочтений', default=0)
    total_recipients = models.IntegerField('Общее количество получателей', default=0)
    delivery_time = models.FloatField('Время доставки (секунды)', default=0.0)
    
    class Meta:
        verbose_name = 'Отправленное уведомление'
        verbose_name_plural = 'Отправленные уведомления'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_notification_type_display()}"
    
    @property
    def read_percentage(self):
        if self.total_recipients > 0:
            return round((self.read_count / self.total_recipients) * 100, 1)
        return 0


class MaintenanceTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('in_progress', 'В работе'),
        ('resolved', 'Решен'),
        ('closed', 'Закрыт'),
    ]
    
    SOURCE_CHOICES = [
        ('api', 'API'),
        ('manual', 'Ручной'),
        ('system', 'Система'),
    ]
    
    ticket_id = models.CharField('ID тикета', max_length=50, unique=True)
    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание')
    email = models.EmailField('Email', max_length=254)
    user_id = models.CharField('ID пользователя', max_length=100)
    priority = models.CharField('Приоритет', max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField('Статус', max_length=15, choices=STATUS_CHOICES, default='open')
    source = models.CharField('Источник', max_length=10, choices=SOURCE_CHOICES, default='api')
    from_user = models.CharField('От кого', max_length=200, default='Система')
    created_at = models.DateTimeField('Время создания', auto_now_add=True)
    updated_at = models.DateTimeField('Время обновления', auto_now=True)
    assigned_to = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Назначен')
    
    class Meta:
        verbose_name = 'Тикет техподдержки'
        verbose_name_plural = 'Тикеты техподдержки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.ticket_id} - {self.title}"


class TicketReply(models.Model):
    ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name='replies', verbose_name='Тикет')
    author = models.ForeignKey(Admin, on_delete=models.CASCADE, verbose_name='Автор')
    message = models.TextField('Сообщение')
    created_at = models.DateTimeField('Время создания', auto_now_add=True)
    is_internal = models.BooleanField('Внутренний комментарий', default=False)
    
    class Meta:
        verbose_name = 'Ответ на тикет'
        verbose_name_plural = 'Ответы на тикеты'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Ответ на #{self.ticket.ticket_id} от {self.author.username}"


class ServiceStatusLog(models.Model):
    service_name = models.CharField(max_length=200)
    url = models.URLField()
    is_working = models.BooleanField(default=False)
    status_code = models.IntegerField(null=True, blank=True)
    message = models.CharField(max_length=255)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Статус сервиса'
        verbose_name_plural = 'Статусы сервисов'
        ordering = ['-checked_at']

    def __str__(self):
        return f"{self.service_name}: {'OK' if self.is_working else 'FAIL'}"
