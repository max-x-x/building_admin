import os
from django.conf import settings

SERVICES_CONFIG = [
    {
        "name": "ИИ-чат",
        "icon": "🤖",
        "url": os.getenv('BUILDING_NOTIFICATIONS_URL', 'https://building-notifications.itc-hub.ru')
    },
    {
        "name": "Система уведомлений", 
        "icon": "🔔",
        "url": os.getenv('BUILDING_NOTIFICATIONS_URL', 'https://building-notifications.itc-hub.ru')
    },
    {
        "name": "Сервис Посещений",
        "icon": "📍", 
        "url": os.getenv('VISITS_API_URL', 'https://building-qr.itc-hub.ru')
    },
    {
        "name": "Основной монолит",
        "icon": "🏗️",
        "url": os.getenv('BUILDING_API_URL', 'https://building-api.itc-hub.ru/api/v1')
    },
    {
        "name": "Сервис с полигонами",
        "icon": "🗺️",
        "url": os.getenv('BUILDING_API_URL', 'https://building-api.itc-hub.ru/api/v1')
    },
    {
        "name": "Распознавание текста",
        "icon": "📝",
        "url": os.getenv('BUILDING_CV_URL', 'https://building-cv.itc-hub.ru/api')
    }
]
