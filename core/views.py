import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date
from .forms import InvitationForm, MemoForm, NotificationForm, ExternalLoginForm
from .models import Invitation, Memo, SentNotification, MaintenanceTicket, TicketReply, ServiceStatusLog, Admin
from .services_config import SERVICES_CONFIG
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login as auth_login, logout as auth_logout
import json
import uuid
import requests
import time
import random


def get_users_from_api():
    """
    Заглушка функции получения списка пользователей по API
    В реальном проекте здесь будет запрос к внешнему API
    """
    # Заглушка данных пользователей из API
    users = [
        {"id": "user_001", "name": "Иванов Иван Иванович", "role": "ССК", "email": "ivanov@example.com"},
        {"id": "user_002", "name": "Петров Петр Петрович", "role": "ИКО", "email": "petrov@example.com"},
        {"id": "user_003", "name": "Сидоров Сидор Сидорович", "role": "Прораб", "email": "sidorov@example.com"},
        {"id": "user_004", "name": "Козлов Козел Козлович", "role": "Администратор", "email": "kozlov@example.com"},
        {"id": "user_005", "name": "Смирнов Смир Смирнович", "role": "Менеджер", "email": "smirnov@example.com"},
        {"id": "user_006", "name": "Волков Волк Волкович", "role": "Работник", "email": "volkov@example.com"},
    ]
    
    # В реальном проекте здесь будет:
    # response = requests.get(os.getenv("USERS_API_URL"))
    # response.raise_for_status()
    # return response.json()
    
    return users


def send_notification_to_api(title, message, notification_type, recipient_type, specific_user_id=None):
    """
    Заглушка функции отправки уведомления по API
    В реальном проекте здесь будет запрос к внешнему API
    """
    try:
        # Имитируем отправку на API
        data = {
            "title": title,
            "message": message,
            "type": notification_type,
            "recipients": recipient_type,
            "specific_user_id": specific_user_id,
            "timestamp": time.time()
        }
        
        # Заглушка - имитируем задержку API
        time.sleep(random.uniform(0.5, 2.0))
        
        # В реальном проекте здесь будет:
        # response = requests.post(os.getenv("NOTIFICATION_API_URL"), json=data)
        # response.raise_for_status()
        
        print(f"Отправка уведомления на API: {data}")
        return True
        
    except Exception as e:
        print(f"Ошибка отправки на API: {e}")
        return False

@login_required
def dashboard(request):
    # Статистика для карточек
    today = date.today()
    today_invitations = Invitation.objects.filter(created_at__date=today).count()
    today_logs = 156  # Заглушка
    today_notifications = SentNotification.objects.filter(sent_at__date=today).count()
    total_users = 1247  # Заглушка
    total_memos = Memo.objects.count()
    open_tickets = MaintenanceTicket.objects.filter(status='open').count()
    
    services_status = []
    for service in SERVICES_CONFIG:
        last_log = ServiceStatusLog.objects.filter(service_name=service["name"]).order_by('-checked_at').first()
        if last_log:
            services_status.append({
                "name": service["name"],
                "icon": service["icon"],
                "is_working": last_log.is_working,
                "message": "Работает" if last_log.is_working else "Недоступен"
            })
        else:
            services_status.append({
                "name": service["name"],
                "icon": service["icon"],
                "is_working": None,
                "message": "Нет данных"
            })

    context = {
        "today_invitations": today_invitations,
        "today_logs": today_logs,
        "today_notifications": today_notifications,
        "total_users": total_users,
        "total_memos": total_memos,
        "open_tickets": open_tickets,
        "services_status": services_status,
    }
    return render(request, "dashboard.html", context)



def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        form = ExternalLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                response = requests.post(
                    'https://building-api.itc-hub.ru/api/v1/auth/login',
                    json={"email": email, "password": password},
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    request.session['access_token'] = data.get('access')
                    request.session['refresh_token'] = data.get('refresh')
                    user_email = data.get('user', {}).get('email') or email
                    user, _ = Admin.objects.get_or_create(email=user_email)
                    auth_login(request, user)
                    return redirect('dashboard')
                else:
                    form.add_error(None, "Неверные учетные данные или ошибка сервера")
            except requests.RequestException:
                form.add_error(None, "Сервис аутентификации недоступен")
    else:
        form = ExternalLoginForm()
    return render(request, "login.html", {"form": form})


def logout_view(request):
    request.session.pop('access_token', None)
    request.session.pop('refresh_token', None)
    auth_logout(request)
    return redirect('login')


@login_required
def logs(request):
    return render(request, "logs.html")

@login_required
def notifications(request):
    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            message = form.cleaned_data['message']
            notification_type = form.cleaned_data['notification_type']
            recipient_type = form.cleaned_data['recipient_type']
            specific_user = form.cleaned_data.get('specific_user', '')

            # Получаем данные о конкретном пользователе
            specific_user_id = None
            specific_user_name = None
            if recipient_type == 'specific' and specific_user:
                users = get_users_from_api()
                user_data = next((u for u in users if u['id'] == specific_user), None)
                if user_data:
                    specific_user_id = user_data['id']
                    specific_user_name = user_data['name']

            # Сохраняем в БД
            notification = SentNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                recipient_type=recipient_type,
                specific_user_id=specific_user_id,
                specific_user_name=specific_user_name,
                sent_by=request.user,
                total_recipients=1 if recipient_type == 'specific' else 100,  # Заглушка
                delivery_time=random.uniform(1.0, 3.0),  # Заглушка
                read_count=1 if recipient_type == 'specific' else random.randint(80, 95)  # Заглушка
            )

            # Отправляем на API (заглушка)
            success = send_notification_to_api(title, message, notification_type, recipient_type, specific_user_id)
            
            if success:
                messages.success(request, f"Уведомление '{title}' успешно отправлено!")
            else:
                messages.error(request, "Ошибка при отправке уведомления на API")

            return redirect('notifications')
    else:
        form = NotificationForm()

    # Получаем список пользователей для формы
    users = get_users_from_api()
    user_choices = [(user['id'], f"{user['name']} ({user['role']})") for user in users]
    form.fields['specific_user'].choices = user_choices

    # Получаем статистику из БД
    today = date.today()
    today_count = SentNotification.objects.filter(sent_at__date=today).count()
    total_count = SentNotification.objects.count()
    
    # Показатели, которые можно взять из таблицы без запросов
    urgent_count = SentNotification.objects.filter(notification_type='urgent').count()
    info_count = SentNotification.objects.filter(notification_type='info').count()

    recent_notifications = SentNotification.objects.all()[:10]

    context = {
        "form": form,
        "today_count": today_count,
        "total_count": total_count,
        "urgent_count": urgent_count,
        "info_count": info_count,
        "recent_notifications": recent_notifications,
    }
    return render(request, "notifications.html", context)

@login_required
def users(request):
    api_items = []
    try:
        access_token = request.session.get('access_token')
        if access_token:
            query = request.GET.get('search', '') or ''
            role_filter = request.GET.get('role', 'all')
            params = {}
            if query:
                params['query'] = query
            api_role_map = {
                'ССК': 'ssk',
                'ИКО': 'iko',
                'Прораб': 'foreman',
                'Админ': 'admin',
            }
            if role_filter and role_filter != 'all':
                role_param = api_role_map.get(role_filter, role_filter)
                if role_param:
                    params['role'] = role_param

            resp = requests.get(
                'https://building-api.itc-hub.ru/api/v1/users',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                api_items = data.get('items', [])
                print(f"✅ API Users ok: total={len(api_items)}")
            else:
                print(f"❌ API Users status={resp.status_code} body={resp.text}")
        else:
            print('❌ API Users: токен отсутствует в сессии')
    except requests.RequestException as e:
        print(f"❌ API Users ошибка запроса: {e}")

    role_display_map = {
        'ssk': 'ССК',
        'iko': 'ИКО',
        'foreman': 'Прораб',
        'admin': 'Админ',
    }

    users_data = []
    for item in api_items:
        role_key = item.get('role')
        users_data.append({
            'id': item.get('id'),
            'fio': item.get('full_name') or item.get('email') or '',
            'email': item.get('email') or '',
            'phone': item.get('phone') or '',
            'role': role_display_map.get(role_key, role_key or ''),
            'role_key': role_key or '',
            'objects_count': 0,
            'violations_count': 0,
            'status': 'active',
            'objects': [],
        })

    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')

    ssk_count = len([u for u in api_items if u.get('role') == 'ssk'])
    iko_count = len([u for u in api_items if u.get('role') == 'iko'])
    prorab_count = len([u for u in api_items if u.get('role') == 'foreman'])
    admin_count = len([u for u in api_items if u.get('role') == 'admin'])
    total_users = ssk_count + iko_count + prorab_count + admin_count

    context = {
        'users': users_data,
        'total_users': total_users,
        'ssk_count': ssk_count,
        'iko_count': iko_count,
        'prorab_count': prorab_count,
        'current_role': role_filter,
        'search_query': search_query,
        'api_users_raw': api_items,
        'api_users_json': json.dumps(api_items, ensure_ascii=False),
    }
    return render(request, 'users.html', context)

@login_required
def laboratory(request):
    return render(request, "laboratory.html")

@login_required
def visits(request):
    # Заглушка данных посещений из API
    visits_data = [
        {
            "id": 1,
            "fio": "Иванов Иван Иванович",
            "role": "ССК",
            "object": "Объект #1 - ул. Пушкина, д. 10",
            "visit_date": "2024-12-15",
            "purpose": "Контроль качества работ",
            "status": "completed",
            "notes": "Выявлены незначительные нарушения"
        },
        {
            "id": 2,
            "fio": "Петров Петр Петрович",
            "role": "ИКО",
            "object": "Объект #2 - ул. Ленина, д. 25",
            "visit_date": "2024-12-15",
            "purpose": "Инспекция объекта",
            "status": "completed",
            "notes": "Все работы выполнены согласно нормативам"
        },
        {
            "id": 3,
            "fio": "Сидоров Сидор Сидорович",
            "role": "Прораб",
            "object": "Объект #3 - ул. Гагарина, д. 5",
            "visit_date": "2024-12-14",
            "purpose": "Координация работ",
            "status": "completed",
            "notes": "Планирование следующего этапа"
        },
        {
            "id": 4,
            "fio": "Козлов Козел Козлович",
            "role": "ССК",
            "object": "Объект #4 - ул. Мира, д. 15",
            "visit_date": "2024-12-14",
            "purpose": "Проверка материалов",
            "status": "completed",
            "notes": "Проверка качества бетонной смеси"
        },
        {
            "id": 5,
            "fio": "Смирнов Смир Смирнович",
            "role": "ИКО",
            "object": "Объект #5 - ул. Советская, д. 8",
            "visit_date": "2024-12-13",
            "purpose": "Технический надзор",
            "status": "completed",
            "notes": "Рекомендации по улучшению процесса"
        },
        {
            "id": 6,
            "fio": "Волков Волк Волкович",
            "role": "Прораб",
            "object": "Объект #6 - ул. Центральная, д. 12",
            "visit_date": "2024-12-13",
            "purpose": "Управление бригадой",
            "status": "completed",
            "notes": "Обучение новых сотрудников"
        },
        {
            "id": 7,
            "fio": "Новиков Николай Николаевич",
            "role": "ССК",
            "object": "Объект #7 - ул. Промышленная, д. 3",
            "visit_date": "2024-12-12",
            "purpose": "Контроль безопасности",
            "status": "completed",
            "notes": "Проверка соблюдения ТБ"
        },
        {
            "id": 8,
            "fio": "Морозов Михаил Михайлович",
            "role": "ИКО",
            "object": "Объект #8 - ул. Садовая, д. 7",
            "visit_date": "2024-12-12",
            "purpose": "Анализ качества",
            "status": "scheduled",
            "notes": "Запланированная проверка"
        }
    ]

    # Статистика
    total_visits = len(visits_data)
    completed_visits = len([v for v in visits_data if v['status'] == 'completed'])
    scheduled_visits = len([v for v in visits_data if v['status'] == 'scheduled'])

    context = {
        "visits": visits_data,
        "total_visits": total_visits,
        "completed_visits": completed_visits,
        "scheduled_visits": scheduled_visits,
    }
    return render(request, "visits.html", context)

@login_required
def maintenance(request):
    # Создаем тестовые тикеты если их нет
    if MaintenanceTicket.objects.count() == 0:
        # Создаем тестовые тикеты
        test_tickets = [
            {
                'ticket_id': 'TICKET-001',
                'title': 'Ошибка подключения к базе данных',
                'description': 'Сервис не может подключиться к основной базе данных. Ошибка возникает при попытке выполнения запросов.',
                'status': 'open',
                'from_user': 'Иванов И.И. (Основной монолит)'
            },
            {
                'ticket_id': 'TICKET-002',
                'title': 'Медленная загрузка страниц',
                'description': 'Пользователи жалуются на медленную загрузку страниц в админ панели.',
                'status': 'open',
                'from_user': 'Петров П.П. (Админ панель)'
            },
            {
                'ticket_id': 'TICKET-003',
                'title': 'Проблема с отправкой уведомлений',
                'description': 'Уведомления не доставляются пользователям через email.',
                'status': 'open',
                'from_user': 'Сидоров С.С. (Система уведомлений)'
            },
            {
                'ticket_id': 'TICKET-004',
                'title': 'Ошибка в API полигонов',
                'description': 'API возвращает некорректные координаты полигонов объектов.',
                'status': 'open',
                'from_user': 'Козлов К.К. (Сервис с полигонами)'
            },
            {
                'ticket_id': 'TICKET-005',
                'title': 'Проблема с аутентификацией',
                'description': 'Некоторые пользователи не могут войти в систему.',
                'status': 'open',
                'from_user': 'Смирнов С.С. (Система аутентификации)'
            }
        ]
        
        for ticket_data in test_tickets:
            MaintenanceTicket.objects.create(**ticket_data)
    
    # Получаем все тикеты
    tickets = MaintenanceTicket.objects.all().order_by('-created_at')
    
    # Статистика
    total_tickets = tickets.count()
    new_tickets = tickets.filter(replies__isnull=True).count()
    closed_tickets = tickets.filter(replies__isnull=False).count()
    
    context = {
        "tickets": tickets,
        "total_tickets": total_tickets,
        "new_tickets": new_tickets,
        "closed_tickets": closed_tickets,
    }
    return render(request, "maintenance.html", context)

# API эндпоинты
@csrf_exempt
@require_http_methods(["POST"])
def api_create_ticket(request):
    """API для создания тикета от других сервисов"""
    try:
        data = json.loads(request.body)
        
        # Генерируем уникальный ID тикета
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
        
        # Создаем тикет
        ticket = MaintenanceTicket.objects.create(
            ticket_id=ticket_id,
            title=data.get('title', 'Без заголовка'),
            description=data.get('description', ''),
            from_user=data.get('from_user', 'Система'),
            source='api'
        )
        
        return JsonResponse({
            'success': True,
            'ticket_id': ticket.ticket_id,
            'message': 'Тикет успешно создан'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_http_methods(["GET"])
def api_get_tickets(request):
    """API для получения списка тикетов"""
    try:
        tickets = MaintenanceTicket.objects.all().order_by('-created_at')
        
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                'id': ticket.id,
                'ticket_id': ticket.ticket_id,
                'title': ticket.title,
                'description': ticket.description,
                'priority': ticket.get_priority_display(),
                'status': ticket.get_status_display(),
                'from_user': ticket.from_user,
                'created_at': ticket.created_at.isoformat(),
                'updated_at': ticket.updated_at.isoformat(),
                'replies_count': ticket.replies.count()
            })
        
        return JsonResponse({
            'success': True,
            'tickets': tickets_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def api_get_memos(request):
    """API для получения списка методичек"""
    try:
        memos = Memo.objects.all().order_by('-created_at')
        
        memos_data = []
        for memo in memos:
            memos_data.append({
                'id': memo.id,
                'title': memo.title,
                'description': memo.description,
                'link': memo.link,
                'created_at': memo.created_at.isoformat(),
                'created_by': memo.created_by.email if memo.created_by else None
            })
        
        return JsonResponse({
            'success': True,
            'memos': memos_data,
            'total': len(memos_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_create_memo(request):
    """API для создания методички"""
    try:
        data = json.loads(request.body)
        
        title = data.get('title')
        description = data.get('description')
        link = data.get('link')
        
        if not all([title, description, link]):
            return JsonResponse({
                'success': False,
                'error': 'Необходимы поля: title, description, link'
            }, status=400)
        
        memo = Memo.objects.create(
            title=title,
            description=description,
            link=link,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'success': True,
            'memo_id': memo.id,
            'message': 'Методичка успешно создана'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_reply_ticket(request):
    """API для ответа на тикет"""
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        message = data.get('message')
        
        if not ticket_id or not message:
            return JsonResponse({
                'success': False,
                'error': 'Необходимы ticket_id и message'
            }, status=400)
        
        try:
            ticket = MaintenanceTicket.objects.get(ticket_id=ticket_id)
        except MaintenanceTicket.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Тикет не найден'
            }, status=404)
        
        # Создаем ответ
        reply = TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            message=message
        )
        
        # Автоматически закрываем тикет после ответа оператора
        ticket.status = 'closed'
        ticket.save()
        
        # Отправляем уведомление на API о закрытии тикета
        try:
            # Здесь можно добавить отправку на внешний API
            print(f"Тикет {ticket.ticket_id} закрыт после ответа оператора")
        except Exception as e:
            print(f"Ошибка отправки уведомления о закрытии тикета: {e}")
        
        return JsonResponse({
            'success': True,
            'reply_id': reply.id,
            'message': 'Ответ успешно добавлен'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def memos(request):
    if request.method == "POST":
        form = MemoForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            link = form.cleaned_data['link']

            # Сохраняем в БД
            memo = Memo.objects.create(
                title=title,
                description=description,
                link=link,
                created_by=request.user
            )

            # Отправляем на API (заглушка)
            data = {
                "title": title,
                "description": description,
                "link": link
            }
            try:
                # response = requests.post(os.getenv("API_URL") + "/memos/", json=data)
                # response.raise_for_status()
                messages.success(request, f"Методичка '{title}' успешно добавлена!")
            except requests.RequestException as e:
                messages.error(request, f"Ошибка при отправке на API: {e}")

            return redirect('memos')
    else:
        form = MemoForm()

    # Получаем методички из БД (пока заглушка для API)
    memos_list = Memo.objects.all()
    
    # Заглушка данных из API
    api_memos = [
        {
            "title": "Техника безопасности на стройке",
            "description": "Основные правила и требования безопасности при проведении строительных работ",
            "link": "https://example.com/safety-manual.pdf"
        },
        {
            "title": "Контроль качества бетонных работ",
            "description": "Методические указания по контролю качества бетонных смесей и конструкций",
            "link": "https://example.com/concrete-quality.pdf"
        },
        {
            "title": "Документооборот в строительстве",
            "description": "Порядок ведения документации и отчетности на строительном объекте",
            "link": "https://example.com/documentation.pdf"
        }
    ]

    context = {
        "form": form,
        "memos_list": memos_list,
        "api_memos": api_memos,
    }
    return render(request, "memos.html", context)

@login_required
def invitations(request):
    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            email = form.cleaned_data['email']
            message = form.cleaned_data.get('message', '')

            invitation = Invitation.objects.create(
                email=email,
                role=role,
                message=message,
                created_by=request.user
            )

            role_mapping = {
                'ССК': 'ssk',
                'ИКО': 'iko',
                'Прораб': 'prorab',
            }
            role_id = role_mapping.get(role)
            if not role_id:
                messages.error(request, "Некорректная роль")
                return redirect('invitations')
            payload = {
                "role_id": role_id,
                "email": email
            }
            try:
                response = requests.post(
                    "http://localhost:8001/role/notification",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                if 200 <= response.status_code < 300:
                    messages.success(request, f"Приглашение для {email} с ролью {role} отправлено!")
                else:
                    messages.error(request, f"API вернул статус {response.status_code}")
            except requests.RequestException as e:
                messages.error(request, f"Ошибка при отправке на API: {e}")

            return redirect('invitations')
    else:
        form = InvitationForm()

    # Получаем статистику из БД
    today = date.today()
    today_count = Invitation.objects.filter(created_at__date=today).count()
    total_count = Invitation.objects.count()
    ssk_count = Invitation.objects.filter(role='ССК').count()
    iko_count = Invitation.objects.filter(role='ИКО').count()
    recent_invitations = Invitation.objects.all()[:10]

    context = {
        "form": form,
        "today_count": today_count,
        "total_count": total_count,
        "ssk_count": ssk_count,
        "iko_count": iko_count,
        "recent_invitations": recent_invitations,
    }
    return render(request, "invitations.html", context)\

@login_required
def objects_page(request):
    objects_list = []
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                'https://building-api.itc-hub.ru/api/v1/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                objects_list = data.get('items', [])
            else:
                print(f"❌ API Objects ошибка {response.status_code}: {response.text}")
        else:
            print("❌ Токен не найден в сессии")
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса к API Objects: {str(e)}")

    if request.method == "POST":
        name = request.POST.get("name")
        address = request.POST.get("address")

        if not name or not address:
            messages.error(request, "Заполните все обязательные поля!")
            return redirect("objects")

        try:
            access_token = request.session.get('access_token')
            if not access_token:
                messages.error(request, "Ошибка авторизации")
                return redirect("objects")

            data = {
                "name": name,
                "address": address
            }
            
            response = requests.post(
                'https://building-api.itc-hub.ru/api/v1/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                messages.success(request, "Объект успешно создан!")
            else:
                messages.error(request, f"Ошибка создания объекта: {response.status_code}")
                
        except requests.RequestException as e:
            messages.error(request, f"Ошибка соединения с API: {str(e)}")
        
        return redirect("objects")

    return render(request, "objects.html", {
        "objects": objects_list
    })


@login_required
def object_detail(request, object_id):
    # Заглушка данных из API - меняем статус для демонстрации
    is_activated = object_id % 2 == 0  # четные ID = активированы
    
    api_data = {
        "id": object_id,
        "address": "ул. Пушкина, д. 10",
        "status": "activated" if is_activated else "requires_activation",
        "responsible_foreman": "Прораб Петров",
        "responsible_iko": "ИКО Сидоров" if is_activated else None,
        "work_list": [
            {
                "name": "Земляные работы",
                "description": "Рытье котлована под фундамент",
                "start_date": "2024-01-15",
                "end_date": "2024-01-25",
                "completed": True
            },
            {
                "name": "Бетонные работы", 
                "description": "Заливка фундамента",
                "start_date": "2024-01-26",
                "end_date": "2024-02-05",
                "completed": False
            },
            {
                "name": "Кровельные работы",
                "description": "Устройство кровли",
                "start_date": "2024-02-06",
                "end_date": "2024-02-20",
                "completed": False
            }
        ] if is_activated else [],  # Пустой список если не активирован
        "schedule": "https://example.com/schedule.pdf" if is_activated else None,
        "visits": [
            {
                "fio": "Иванов Иван Иванович",
                "date": "2024-01-10"
            },
            {
                "fio": "Петров Петр Петрович", 
                "date": "2024-01-12"
            }
        ],
        "deliveries": [
            {
                "date": "2024-01-08",
                "supplier": "ООО Стройматериалы",
                "materials": "Бетон, арматура",
                "invoice_link": "https://example.com/invoice1.pdf"
            },
            {
                "date": "2024-01-15",
                "supplier": "ИП Кровельные работы",
                "materials": "Кровельные материалы",
                "invoice_link": "https://example.com/invoice2.pdf"
            }
        ],
        "violations": {
            "total": 5,
            "fixed": 3,
            "link": "https://example.com/violations.pdf"
        } if is_activated else None,
        "documents_count": 12 if is_activated else 3,
        "documentation_link": "https://example.com/object-docs.pdf" if is_activated else None,
        "planned_deliveries": [
            {
                "date": "2024-02-01",
                "supplier": "ООО МеталлСтрой",
                "materials": "Металлические конструкции",
                "status": "planned"
            },
            {
                "date": "2024-02-10", 
                "supplier": "ИП ЭлектроМонтаж",
                "materials": "Электрокабели, розетки",
                "status": "confirmed"
            }
        ] if is_activated else [],
        "polygon_data": {
            "coordinates": "55.7558° N, 37.6176° E",
            "area": "2,500 м²",
            "points": [
                {"lat": 55.7558, "lng": 37.6176},
                {"lat": 55.7568, "lng": 37.6186},
                {"lat": 55.7578, "lng": 37.6196},
                {"lat": 55.7568, "lng": 37.6206}
            ]
        } if is_activated else None  # Для неактивированных объектов полигон может быть или не быть
    }

    # Рассчитываем прогресс работ
    work_progress = 0
    if api_data["work_list"]:
        completed_works = sum(1 for work in api_data["work_list"] if work.get("completed", False))
        total_works = len(api_data["work_list"])
        work_progress = int((completed_works / total_works) * 100)

    context = {
        "object": api_data,
        "work_progress": work_progress,
    }
    return render(request, "object_detail.html", context)
