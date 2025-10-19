import os
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date
from django.conf import settings
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


def send_notification_to_api(recipient_type, subject, body, access_token):
    """
    Отправка уведомления через API
    """
    try:
        data = {
            "to": recipient_type,
            "subject": subject,
            "body": body,
            "is_html": False,
            "access_token": access_token
        }
        
        response = requests.post(
            f'{settings.BUILDING_NOTIFICATIONS_URL}/broadcast/notification',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response_text': response.text
        }
            
    except requests.RequestException as e:
        return {
            'success': False,
            'status_code': 0,
            'response_text': str(e)
        }

@login_required
def dashboard(request):
    # Статистика для карточек
    today = date.today()
    today_invitations = Invitation.objects.filter(created_at__date=today).count()
    # Получаем количество посещений сегодня
    today_visits = 0
    try:
        response = requests.get(
            f'{settings.VISITS_API_URL}/sessions/list',
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            today = date.today()
            
            for session in sessions:
                visit_date_raw = session.get('visit_date')
                if visit_date_raw:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(visit_date_raw.replace('Z', '+00:00'))
                        # Проверяем, что посещение было сегодня
                        if dt.date() == today:
                            today_visits += 1
                    except Exception as e:
                        pass
    except requests.RequestException as e:
        pass
    today_notifications = SentNotification.objects.filter(sent_at__date=today).count()
    # Получаем количество пользователей из API
    total_users = 0
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                f'{settings.BUILDING_API_URL}/users',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                users_list = data.get('items', [])
                total_users = len(users_list)
    except requests.RequestException as e:
        pass
    total_memos = Memo.objects.count()
    open_tickets = MaintenanceTicket.objects.filter(status='open').count()
    
    # Получаем количество активных объектов из API
    active_objects = 0
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                f'{settings.BUILDING_API_URL}/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                objects_list = data.get('items', [])
                active_objects = len([obj for obj in objects_list if obj.get('status') == 'active'])
    except requests.RequestException as e:
        pass

    # Получаем количество элементов в лаборатории
    laboratory_count = 0
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                f'{settings.BUILDING_API_URL}/deliveries/list?status=sent_to_lab',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                laboratory_count = len(data.get('items', []))
    except requests.RequestException as e:
        pass

    # Получаем количество поставок из API
    total_deliveries = 0
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                f'{settings.BUILDING_API_URL}/deliveries/list',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                total_deliveries = data.get('total', 0)
    except requests.RequestException as e:
        pass
    
    services_status = []
    working_modules_count = 0
    for service in SERVICES_CONFIG:
        last_log = ServiceStatusLog.objects.filter(service_name=service["name"]).order_by('-checked_at').first()
        if last_log:
            is_working = last_log.is_working
            if is_working:
                working_modules_count += 1
            services_status.append({
                "name": service["name"],
                "icon": service["icon"],
                "is_working": is_working,
                "message": "Работает" if is_working else "Недоступен"
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
        "today_visits": today_visits,
        "today_notifications": today_notifications,
        "total_users": total_users,
        "total_memos": total_memos,
        "open_tickets": open_tickets,
        "active_objects": active_objects,
        "laboratory_count": laboratory_count,
        "total_deliveries": total_deliveries,
        "services_status": services_status,
        "working_modules_count": working_modules_count,
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
                    f'{settings.BUILDING_API_URL}/auth/login',
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

@login_required
def notifications(request):
    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            message = form.cleaned_data['message']
            notification_type = form.cleaned_data['notification_type']
            recipient_type = form.cleaned_data['recipient_type']

            # Отправляем на API
            access_token = request.session.get('access_token', '')
            result = send_notification_to_api(recipient_type, title, message, access_token)

            # Сохраняем в БД
            notification = SentNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                recipient_type=recipient_type,
                specific_user_id=None,
                specific_user_name=None,
                sent_by=request.user,
                total_recipients=1,
                delivery_time=0.0,
                read_count=1 if result['success'] else 0
            )
            
            if result['success']:
                messages.success(request, f"Уведомление '{title}' успешно отправлено!")
            else:
                messages.error(request, f"Ошибка при отправке уведомления: {result['response_text']}")

            return redirect('notifications')
    else:
        form = NotificationForm()

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
                f'{settings.BUILDING_API_URL}/users',
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
            'objects_count': item.get('objects_count', 0),
            'violations_count': item.get('violations_total', 0),
            'violations_closed': item.get('violations_closed', 0),
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
    # Получаем данные лаборатории из API
    laboratory_data = {
        'violations': 0,
        'ready': 0,
        'in_laboratory': 0,
        'total': 0
    }
    materials_list = []
    
    try:
        access_token = request.session.get('access_token')
        if access_token:
            # Выводим полный curl запрос в терминал
            print(f"🌐 CURL запрос к API Laboratory:")
            print(f"curl -X GET f'{settings.BUILDING_API_URL}/deliveries/list?status=sent_to_lab' \\")
            print(f"  -H 'Authorization: Bearer {access_token}' \\")
            print(f"  -H 'Content-Type: application/json'")
            print(f"")
            
            response = requests.get(
                f'{settings.BUILDING_API_URL}/deliveries/list?status=sent_to_lab',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                deliveries = data.get('items', [])
                
                # Подсчитываем статистику по статусам доставок
                violations = 0
                ready = 0
                in_laboratory = len(deliveries)  # Все доставки со статусом sent_to_lab
                total = len(deliveries)
                
                for delivery in deliveries:
                    status = delivery.get('status', '')
                    if 'violation' in status.lower() or 'нарушение' in status.lower():
                        violations += 1
                    elif 'ready' in status.lower() or 'готов' in status.lower():
                        ready += 1
                    
                    # Формируем список материалов для таблицы
                    materials_list.append({
                        'name': delivery.get('material_name', delivery.get('name', 'Неизвестный материал')),
                        'date': delivery.get('created_at', delivery.get('date', '')),
                        'object': delivery.get('object_name', f"Объект #{delivery.get('object_id', 'N/A')}"),
                        'status': delivery.get('status', 'Неизвестно'),
                        'id': delivery.get('id', ''),
                    })
                
                # Рассчитываем проценты
                violations_percent = (violations * 100) // total if total > 0 else 0
                ready_percent = (ready * 100) // total if total > 0 else 0
                laboratory_percent = (in_laboratory * 100) // total if total > 0 else 0
                
                laboratory_data = {
                    'violations': violations,
                    'ready': ready,
                    'in_laboratory': in_laboratory,
                    'total': total,
                    'violations_percent': violations_percent,
                    'ready_percent': ready_percent,
                    'laboratory_percent': laboratory_percent
                }
                
                print(f"✅ API Laboratory успешно: статус {response.status_code}")
                print(f"📊 Получены данные лаборатории:")
                print(f"   - Нарушения: {laboratory_data['violations']}")
                print(f"   - Готово: {laboratory_data['ready']}")
                print(f"   - В лаборатории: {laboratory_data['in_laboratory']}")
                print(f"   - Всего: {laboratory_data['total']}")
                print(f"📋 Полный ответ API:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"❌ API Laboratory ошибка {response.status_code}: {response.text}")
        else:
            print("⚠️ Access token не найден для API Laboratory")
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса к API Laboratory: {e}")
    
    context = {
        'laboratory_data': laboratory_data,
        'materials_list': materials_list,
    }
    return render(request, "laboratory.html", context)

@login_required
def visits(request):
    visits_data = []
    total_visits = 0
    query = (request.GET.get('q') or '').strip()
    role_filter = request.GET.get('role', 'all')
    sort = request.GET.get('sort', 'date_desc')
    date_from_str = (request.GET.get('date_from') or '').strip()
    date_to_str = (request.GET.get('date_to') or '').strip()
    
    # Получаем данные пользователей и объектов
    users_data = {}
    objects_data = {}
    
    if request.method == "POST":
        try:
            access_token = request.session.get('access_token')
            if not access_token:
                messages.error(request, "Ошибка авторизации")
                return redirect('visits')

            user_id = request.POST.get('user_id')
            object_id = request.POST.get('object_id')
            area_id = request.POST.get('area_id')
            visit_date = request.POST.get('visit_date')
            user_role = request.POST.get('user_role')

            if not user_id or not object_id or not area_id or not visit_date:
                messages.error(request, "Заполните все поля")
                return redirect('visits')

            # Конвертируем дату в ISO формат (добавляем время по умолчанию)
            if visit_date:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(visit_date)
                    visit_date = dt.strftime('%Y-%m-%dT12:00:00Z')
                except:
                    pass

            payload = {
                "user_id": user_id,
                "user_role": user_role or "",
                "object_id": int(object_id),
                "area_id": int(area_id),
                "visit_date": visit_date
            }

            resp = requests.post(
                f"{settings.VISITS_API_URL}/sessions/create",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=15
            )

            if 200 <= resp.status_code < 300:
                messages.success(request, "Посещение добавлено")
            else:
                messages.error(request, f"Ошибка создания: {resp.status_code}")
        except Exception as e:
            messages.error(request, "Ошибка отправки запроса")
        return redirect('visits')

    try:
        access_token = request.session.get('access_token')
        if access_token:
            # Получаем пользователей
            users_response = requests.get(
                f'{settings.BUILDING_API_URL}/users',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if users_response.status_code == 200:
                users_list = users_response.json().get('items', [])
                for user in users_list:
                    users_data[user.get('id')] = {
                        'fio': user.get('full_name') or user.get('email') or 'Неизвестно',
                        'email': user.get('email') or '',
                        'role': user.get('role', '')
                    }
            
            # Получаем объекты
            objects_response = requests.get(
                f'{settings.BUILDING_API_URL}/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if objects_response.status_code == 200:
                objects_list = objects_response.json().get('items', [])
                for obj in objects_list:
                    objects_data[obj.get('id')] = {
                        'name': obj.get('name') or f'Объект #{obj.get("id")}',
                        'address': obj.get('address') or 'Адрес не указан'
                    }
    except requests.RequestException as e:
        print(f"❌ Ошибка получения данных пользователей/объектов: {e}")
    
    try:
        response = requests.get(
            f'{settings.VISITS_API_URL}/sessions/list',
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            total_visits = data.get('total', 0)
            
            # Маппинг ролей для отображения
            role_display_map = {
                'ssk': 'ССК',
                'iko': 'ИКО',
                'foreman': 'Прораб',
                'admin': 'Админ',
            }
            
            for session in sessions:
                user_id = session.get('user_id')
                object_id = session.get('object_id')
                
                # Получаем данные пользователя
                user_info = users_data.get(user_id, {})
                user_fio = user_info.get('fio', f'ID: {user_id[:8]}...')
                user_email = user_info.get('email', '')
                
                # Получаем данные объекта
                object_info = objects_data.get(object_id, {})
                object_name = object_info.get('name', f'Объект #{object_id}')
                object_address = object_info.get('address', 'Адрес не указан')
                
                # Обрабатываем дату
                visit_date_raw = session.get('visit_date')
                visit_date_formatted = visit_date_raw
                if visit_date_raw:
                    try:
                        from datetime import datetime
                        # Парсим ISO дату
                        dt = datetime.fromisoformat(visit_date_raw.replace('Z', '+00:00'))
                        visit_date_formatted = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        visit_date_formatted = visit_date_raw
                
                visits_data.append({
                    "id": session.get('id'),
                    "user_id": user_id,
                    "user_fio": user_fio,
                    "user_email": user_email,
                    "role": role_display_map.get(session.get('user_role'), session.get('user_role', '')),
                    "object_id": object_id,
                    "object_name": object_name,
                    "object_address": object_address,
                    "area_name": session.get('area_name'),
                    "visit_date": visit_date_formatted,
                    "status": "completed"
                })

            from datetime import datetime
            parsed_visits = []
            for v in visits_data:
                dt = None
                try:
                    dt = datetime.strptime(v["visit_date"], "%d.%m.%Y %H:%M") if v["visit_date"] else None
                except Exception:
                    dt = None
                parsed_visits.append({**v, "_dt": dt})

            if query:
                ql = query.lower()
                parsed_visits = [v for v in parsed_visits if (v["user_fio"] or '').lower().find(ql) != -1 or (v["object_name"] or '').lower().find(ql) != -1 or (v["user_email"] or '').lower().find(ql) != -1]

            if role_filter and role_filter != 'all':
                parsed_visits = [v for v in parsed_visits if (v["role"] or '') == role_filter]

            def parse_date(s):
                try:
                    return datetime.strptime(s, "%Y-%m-%d")
                except Exception:
                    return None

            date_from = parse_date(date_from_str)
            date_to = parse_date(date_to_str)
            if date_from or date_to:
                filtered = []
                for v in parsed_visits:
                    ok = True
                    if date_from and v["_dt"] and v["_dt"] < date_from:
                        ok = False
                    if date_to and v["_dt"] and v["_dt"] > (date_to.replace(hour=23, minute=59, second=59)):
                        ok = False
                    if ok:
                        filtered.append(v)
                parsed_visits = filtered

            if sort == 'date_asc':
                parsed_visits.sort(key=lambda v: (v["_dt"] is None, v["_dt"]))
            elif sort == 'date_desc':
                parsed_visits.sort(key=lambda v: (v["_dt"] is None, v["_dt"]), reverse=True)
            elif sort == 'name_asc':
                parsed_visits.sort(key=lambda v: (v["user_fio"] or '').lower())
            elif sort == 'name_desc':
                parsed_visits.sort(key=lambda v: (v["user_fio"] or '').lower(), reverse=True)

            visits_data = [{k: v[k] for k in v if k != '_dt'} for v in parsed_visits]

        else:
            visits_data = []
    except requests.RequestException:
        visits_data = []

    context = {
        "visits": visits_data,
        "total_visits": total_visits,
        "q": query,
        "role": role_filter,
        "sort": sort,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "users_options": [
            {"id": uid, "label": f"{info['fio']} ({info['email']})", "role": info.get('role', '')}
            for uid, info in users_data.items()
        ],
        "objects_options": [
            {"id": oid, "label": f"{info['name']} — {info['address']}"}
            for oid, info in objects_data.items()
        ]
    }
    return render(request, "visits.html", context)

@login_required
def maintenance(request):
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
        
        # Проверяем обязательные поля
        required_fields = ['title', 'description', 'email', 'user_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Обязательные поля отсутствуют: {", ".join(missing_fields)}'
            }, status=400)
        
        # Генерируем уникальный ID тикета
        ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
        
        # Создаем тикет
        ticket = MaintenanceTicket.objects.create(
            ticket_id=ticket_id,
            title=data.get('title'),
            description=data.get('description'),
            email=data.get('email'),
            user_id=data.get('user_id'),
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
        
        # Отправляем уведомление конкретному пользователю о закрытии тикета
        try:
            notification_data = {
                "user_id": ticket.user_id,
                "email": ticket.email,
                "subject": f"Тикет #{ticket.ticket_id} закрыт",
                "message": f'Ваш тикет "{ticket.title}" был закрыт.\nОтвет: {message}'
            }
            
            notif_response = requests.post(
                f'{settings.BUILDING_NOTIFICATIONS_URL}/send/notification',
                headers={'Content-Type': 'application/json'},
                json=notification_data,
                timeout=10
            )
            print(f"📤 Уведомление пользователю отправлено: {notif_response.status_code}")
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления пользователю: {e}")
        
        # Закрываем тикет
        ticket.status = 'closed'
        ticket.save()
        print(f"✅ Тикет #{ticket.ticket_id} закрыт")
        
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
                    f"{settings.BUILDING_NOTIFICATIONS_URL}/role/notification",
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
def deliveries(request):
    deliveries_list = []
    total_deliveries = 0
    objects_list = []
    status_counts = {
        'scheduled': 0,
        'awaiting_lab': 0,
        'in_transit': 0,
        'delivered': 0,
        'cancelled': 0
    }
    
    # Параметры фильтрации и пагинации
    object_filter = request.GET.get('object_id', '')
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    current_page = (offset // limit) + 1
    
    if request.method == "POST":
        try:
            access_token = request.session.get('access_token')
            if not access_token:
                return JsonResponse({'success': False, 'error': 'Ошибка авторизации'}, status=401)
            
            object_id = request.POST.get('object_id')
            work_item_id = request.POST.get('work_item_id')
            planned_date = request.POST.get('planned_date')
            notes = request.POST.get('notes', '')
            
            if not object_id or not work_item_id or not planned_date:
                return JsonResponse({'success': False, 'error': 'Заполните все обязательные поля'}, status=400)
            
            data = {
                "object_id": int(object_id),
                "work_item_id": int(work_item_id),
                "planned_date": planned_date,
                "notes": notes
            }
            
            response = requests.post(
                f'{settings.BUILDING_API_URL}/deliveries',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=15
            )
            
            if response.status_code == 200 or response.status_code == 201:
                print("Поставка создана успешно, начинаем отправку уведомлений")
                # Отправляем уведомления
                try:
                    # Получаем информацию об объекте
                    object_response = requests.get(
                        f'{settings.BUILDING_API_URL}/objects/{object_id}',
                        headers={
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        },
                        timeout=15
                    )
                    
                    if object_response.status_code == 200:
                        object_data = object_response.json()
                        object_name = object_data.get('name', 'Неизвестный объект')
                        
                        # Отправляем уведомление прорабу
                        if object_data.get('foreman'):
                            foreman_data = object_data['foreman']
                            notification_data = {
                                "user_id": foreman_data['id'],
                                "email": foreman_data['email'],
                                "subject": "Запланирована новая поставка",
                                "message": f"На объект {object_name} запланирована новая поставка на {planned_date}"
                            }
                            notif_response = requests.post(
                                f'{settings.BUILDING_NOTIFICATIONS_URL}/send/notification',
                                headers={'Content-Type': 'application/json'},
                                json=notification_data,
                                timeout=10
                            )
                            print(f"Уведомление прорабу отправлено: {notif_response.status_code}")
                        
                        # Отправляем уведомление ССК
                        if object_data.get('ssk'):
                            ssk_data = object_data['ssk']
                            notification_data = {
                                "user_id": ssk_data['id'],
                                "email": ssk_data['email'],
                                "subject": "Запланирована новая поставка",
                                "message": f"На объект {object_name} запланирована новая поставка на {planned_date}"
                            }
                            notif_response = requests.post(
                                f'{settings.BUILDING_NOTIFICATIONS_URL}/send/notification',
                                headers={'Content-Type': 'application/json'},
                                json=notification_data,
                                timeout=10
                            )
                            print(f"Уведомление ССК отправлено: {notif_response.status_code}")
                        
                        return JsonResponse({'success': True, 'message': f'Поставка создана! Объект: {object_name}. Уведомления отправлены.'})
                    else:
                        return JsonResponse({'success': True, 'message': f'Поставка создана! Ошибка получения данных объекта: {object_response.status_code}'})
                except Exception as e:
                    print(f"Ошибка отправки уведомлений: {e}")
                    import traceback
                    traceback.print_exc()
                    return JsonResponse({'success': True, 'message': f'Поставка создана! Ошибка уведомлений: {str(e)}'})
            else:
                return JsonResponse({'success': False, 'error': f'Ошибка API: {response.status_code}'}, status=400)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    try:
        access_token = request.session.get('access_token')
        if access_token:
            # Получаем поставки с фильтрацией и пагинацией
            deliveries_params = {
                'limit': limit,
                'offset': offset
            }
            if object_filter:
                deliveries_params['object_id'] = object_filter
                
            deliveries_response = requests.get(
                f'{settings.BUILDING_API_URL}/deliveries/list',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params=deliveries_params,
                timeout=15
            )
            
            if deliveries_response.status_code == 200:
                data = deliveries_response.json()
                deliveries_list = data.get('items', [])
                total_deliveries = data.get('total', 0)
                
                for delivery in deliveries_list:
                    status = delivery.get('status', 'unknown')
                    if status in status_counts:
                        status_counts[status] += 1
                
                print(f"✅ API Deliveries успешно: получено {len(deliveries_list)} поставок")
            else:
                print(f"❌ API Deliveries ошибка {deliveries_response.status_code}: {deliveries_response.text}")
            
            # Получаем объекты для формы
            objects_response = requests.get(
                f'{settings.BUILDING_API_URL}/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            
            if objects_response.status_code == 200:
                objects_data = objects_response.json()
                objects_list = objects_data.get('items', [])
                print(f"✅ API Objects успешно: получено {len(objects_list)} объектов")
            else:
                print(f"❌ API Objects ошибка {objects_response.status_code}: {objects_response.text}")
            
        else:
            print("❌ Токен не найден в сессии для API")
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса к API: {e}")

    # Вычисляем пагинацию
    total_pages = (total_deliveries + limit - 1) // limit if total_deliveries > 0 else 1
    has_prev = current_page > 1
    has_next = current_page < total_pages
    last_offset = (total_pages - 1) * limit
    
    context = {
        "deliveries": deliveries_list,
        "total_deliveries": total_deliveries,
        "status_counts": status_counts,
        "objects": objects_list,
        "object_filter": object_filter,
        "current_page": current_page,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_offset": max(0, offset - limit),
        "next_offset": offset + limit,
        "last_offset": last_offset,
        "limit": limit,
    }
    return render(request, "deliveries.html", context)


@login_required
def reports(request):
    context = {}
    return render(request, "reports.html", context)

@login_required
def api_user_objects(request, user_id):
    """API для получения объектов пользователя"""
    try:
        access_token = request.session.get('access_token')
        if not access_token:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        # Получаем все объекты
        response = requests.get(
            f'{settings.BUILDING_API_URL}/objects',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            objects_list = data.get('items', [])
            
            # Фильтруем объекты, где пользователь является ССК, прорабом или ИКО
            user_objects = []
            for obj in objects_list:
                ssk = obj.get('ssk') or {}
                foreman = obj.get('foreman') or {}
                iko = obj.get('iko') or {}
                
                if (ssk.get('id') == user_id or 
                    foreman.get('id') == user_id or 
                    iko.get('id') == user_id):
                    user_objects.append({
                        'id': obj.get('id'),
                        'name': obj.get('name'),
                        'address': obj.get('address')
                    })
            
            return JsonResponse({'objects': user_objects})
        else:
            return JsonResponse({'error': 'Failed to fetch objects'}, status=500)
            
    except requests.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_object_detail(request, object_id):
    """API для получения детальной информации об объекте"""
    try:
        access_token = request.session.get('access_token')
        if not access_token:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        response = requests.get(
            f'{settings.BUILDING_API_URL}/objects/{object_id}',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            areas = data.get('areas', [])
            
            # Извлекаем участки (sub_areas)
            area_list = []
            for area in areas:
                sub_areas = area.get('sub_areas', [])
                for sub_area in sub_areas:
                    area_list.append({
                        'id': sub_area.get('id'),
                        'name': sub_area.get('name')
                    })
            
            return JsonResponse({'areas': area_list})
        else:
            return JsonResponse({'error': 'Failed to fetch object details'}, status=500)
            
    except requests.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def objects_page(request):
    objects_list = []
    try:
        access_token = request.session.get('access_token')
        if access_token:
            response = requests.get(
                f'{settings.BUILDING_API_URL}/objects',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                objects_list = data.get('items', [])
                
                # Подсчитываем объекты по статусам
                status_counts = {
                    'active': 0,
                    'activation_pending': 0,
                    'suspended': 0,
                    'completed': 0,
                    'draft': 0,
                }
                
                for obj in objects_list:
                    status = obj.get('status', 'unknown')
                    if status in status_counts:
                        status_counts[status] += 1
                
            pass
        else:
            pass
    except requests.RequestException as e:
        pass

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
            
            url = f'{settings.BUILDING_API_URL}/objects'
            print(f"🌐 Создание объекта: POST {url}")
            print(f"📤 Данные: {data}")
            
            response = requests.post(
                url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=15
            )
            
            print(f"📡 Ответ API: {response.status_code}")
            print(f"📄 Тело ответа: {response.text}")
            
            if response.status_code == 200:
                messages.success(request, "Объект успешно создан!")
            else:
                messages.error(request, f"Ошибка создания объекта: {response.status_code}")
                
        except requests.RequestException as e:
            messages.error(request, f"Ошибка соединения с API: {str(e)}")
        
        return redirect("objects")

    return render(request, "objects.html", {
        "objects": objects_list,
        "status_counts": status_counts if 'status_counts' in locals() else {
            'active': 0,
            'activation_pending': 0,
            'suspended': 0,
            'completed': 0
        }
    })


