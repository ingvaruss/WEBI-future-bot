import os
import logging
import asyncio
import threading
import base64
import requests
import time
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
KLING_AI_API_KEY = os.getenv('KLING_AI_API_KEY')
KLING_AI_SECRET_KEY = os.getenv('KLING_AI_SECRET_KEY')

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения!")

# ОБНОВЛЕННАЯ КЛАВИАТУРА с магическими архетипами
MAGIC_KEYBOARD = ReplyKeyboardMarkup([
    ['🧙 АРХИМАГ', '🐉 ХРАНИТЕЛЬ ДРАКОНОВ'],
    ['🌿 ДУХ ПРИРОДЫ', '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ'],
    ['💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР', '🎭 МАСКА ТЫСЯЧИ ЛИКОВ'],
    ['🌐 Наш сайт', '🔮 Случайное превращение']
], resize_keyboard=True, one_time_keyboard=True)

# Хранилище для временных данных пользователей
user_data = {}

# Создаем Flask app для здоровья сервиса
web_app = Flask(__name__)


@web_app.route('/')
def home():
    return '🔮 WEBI-future Магическая Лаборатория работает!'


@web_app.route('/healthz')
def health_check():
    return 'OK', 200


def run_web_server():
    """Запускает веб-сервер в отдельном потоке"""
    web_app.run(host='0.0.0.0', port=5000, debug=False)


class UserState:
    def __init__(self):
        self.photo_id = None
        self.photo_file = None
        self.selected_archetype = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    user_data[user_id] = UserState()

    await update.message.reply_text(
        '🔮 **Добро пожаловать в WEBI-future Магическую Лабораторию!**\n\n'
        'Я открываю порталы в параллельные реальности и раскрываю твои скрытые магические облики!\n\n'
        '✨ **Доступные магические архетипы:**\n'
        '• 🧙 АРХИМАГ - повелитель древних заклинаний\n'
        '• 🐉 ХРАНИТЕЛЬ ДРАКОНОВ - друг мифических существ\n'
        '• 🌿 ДУХ ПРИРОДЫ - воплощение живой природы\n'
        '• ⚡ ПОВЕЛИТЕЛЬ СТИХИЙ - контроль над огнем, водой, воздухом и землей\n'
        '• 💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР - форма из чистой энергии\n'
        '• 🎭 МАСКА ТЫСЯЧИ ЛИКОВ - многоликий хамелеон реальностей\n\n'
        '**Пришли своё фото и выбери магическое превращение!**',
        reply_markup=MAGIC_KEYBOARD
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    try:
        user_id = update.effective_user.id

        if user_id not in user_data:
            user_data[user_id] = UserState()

        # Получаем файл фото
        photo_file = await update.message.photo[-1].get_file()
        user_data[user_id].photo_file = photo_file
        user_data[user_id].photo_id = update.message.photo[-1].file_id

        logger.info(f"Получено фото от пользователя {user_id}")

        await update.message.reply_text(
            '📸 **Фото принято!** Магический анализ начался...\n\n'
            'Теперь выбери один из магических архетипов для превращения:',
            reply_markup=MAGIC_KEYBOARD
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text(
            '⚠️ Магические помехи! Не удалось проанализировать фото.\n'
            'Попробуй отправить другое изображение.',
            reply_markup=MAGIC_KEYBOARD
        )


async def generate_ai_video(photo_path: str, prompt: str) -> str:
    """Генерация AI-видео через Kling AI API"""
    logger.info("🎯 ФУНКЦИЯ generate_ai_video ВЫЗВАНА")
    try:
        api_key = os.getenv('KLING_AI_API_KEY')
        secret_key = os.getenv('KLING_AI_SECRET_KEY')

        if not api_key or not secret_key:
            logger.warning("API ключи Kling AI не настроены")
            return None

        logger.info("🎯 Проверяем доступность Kling AI API...")

        # ПРОБНЫЙ ЗАПРОС - проверяем аутентификацию
        test_url = "https://api.klingai.com/v1/models"  # или другой endpoint для проверки

        headers = {
            "X-API-Key": api_key,
            "X-Secret-Key": secret_key,
        }

        try:
            test_response = requests.get(test_url, headers=headers, timeout=10)
            logger.info(f"🎯 Тестовый запрос: статус {test_response.status_code}")
            if test_response.status_code != 200:
                logger.error(f"🎯 Ошибка аутентификации: {test_response.text}")
                return None
        except Exception as e:
            logger.error(f"🎯 Ошибка подключения к Kling AI: {e}")
            return None

        # Если дошли сюда - API доступно, но нужен правильный URL для генерации
        logger.info("🎯 Kling AI доступен, но нужен правильный endpoint для генерации видео")
        return None

    except Exception as e:
        logger.error(f"Ошибка генерации AI-видео: {e}")
        return None


async def wait_for_video_generation(task_id: str, headers: dict) -> str:
    """Ожидание завершения генерации видео"""
    max_attempts = 30  # Максимум 30 попыток (около 2.5 минут)
    attempt = 0

    while attempt < max_attempts:
        try:
            # Проверяем статус задачи
            status_url = f"https://api.klingai.com/v1/videos/status/{task_id}"
            response = requests.get(status_url, headers=headers, timeout=30)

            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status")

                if status == "completed":
                    video_url = status_data.get("video_url")
                    logger.info(f"🎯 Видео сгенерировано: {video_url}")
                    return video_url
                elif status == "failed":
                    logger.error(f"Генерация видео не удалась: {status_data.get('error')}")
                    return None
                else:
                    # Генерация еще в процессе
                    logger.info(f"Статус генерации: {status}, ждем...")
                    await asyncio.sleep(5)  # Ждем 5 секунд перед следующей проверкой
                    attempt += 1
            else:
                logger.error(f"Ошибка проверки статуса: {response.status_code}")
                await asyncio.sleep(5)
                attempt += 1

        except Exception as e:
            logger.error(f"Ошибка при проверке статуса: {e}")
            await asyncio.sleep(5)
            attempt += 1

    logger.error("Превышено время ожидания генерации видео")
    return None


async def show_magical_transformation(update: Update, archetype: str, progress_msg):
    """Показывает магическое превращение (заглушка)"""
    archetype_descriptions = {
        '🧙 АРХИМАГ': 'архимагом - повелителем древних заклинаний',
        '🐉 ХРАНИТЕЛЬ ДРАКОНОВ': 'хранителем драконов - другом мифических существ',
        '🌿 ДУХ ПРИРОДЫ': 'духом природы - воплощением живой природы',
        '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ': 'повелителем стихий - контролером огня, воды, воздуха и земли',
        '💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР': 'кристаллическим аватаром - формой из чистой энергии',
        '🎭 МАСКА ТЫСЯЧИ ЛИКОВ': 'маской тысячи ликов - многоликим хамелеоном реальностей'
    }

    completion_messages = {
        '🧙 АРХИМАГ': 'Теперь ты обладаешь знанием древних заклинаний и магической мудростью! 📖✨',
        '🐉 ХРАНИТЕЛЬ ДРАКОНОВ': 'Драконы признали в тебе друга и хранителя! 🐲🔥',
        '🌿 ДУХ ПРИРОДЫ': 'Природа обрела в тебе своё голос и защитника! 🌳🍃',
        '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ': 'Стихии покорились твоей воле! Огонь, вода, воздух и земля служат тебе! 🌪️🔥',
        '💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР': 'Ты стал воплощением чистой энергии и света! 💎🌈',
        '🎭 МАСКА ТЫСЯЧИ ЛИКОВ': 'Ты обрёл способность менять облики между реальностями! 🎭🔄'
    }

    selected_description = archetype_descriptions.get(archetype, 'магическое существо')

    await progress_msg.edit_text(
        f'**✨ МАГИЧЕСКОЕ ПРЕВРАЩЕНИЕ ЗАВЕРШЕНО!**\n\n'
        f'Ты успешно превратился в {selected_description}!\n\n'
        f'{completion_messages.get(archetype, "Магия работает!")}\n\n'
        f'🚀 **WEBI-future** открывает порталы в новые реальности!\n\n'
        f'🔗 Посети наш сайт: https://prusya.pythonanywhere.com/\n\n'
        f'Хочешь испытать другое превращение? Присылай новое фото!'
    )


async def handle_archetype_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора магического архетипа с AI-видео"""
    try:
        user_id = update.effective_user.id
        text = update.message.text

        # Обработка кнопки "Наш сайт"
        if text == '🌐 Наш сайт':
            await update.message.reply_text(
                '🌐 **WEBI-future Project**\n\n'
                'Посетите нашу магическую лабораторию:\n'
                'https://prusya.pythonanywhere.com/\n\n'
                '✨ _Скоро: единое магическое пространство!_',
                reply_markup=MAGIC_KEYBOARD
            )
            return

        # Обработка кнопки "Случайное превращение"
        if text == '🔮 Случайное превращение':
            import random
            archetypes = [
                '🧙 АРХИМАГ', '🐉 ХРАНИТЕЛЬ ДРАКОНОВ', '🌿 ДУХ ПРИРОДЫ',
                '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ', '💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР', '🎭 МАСКА ТЫСЯЧИ ЛИКОВ'
            ]
            text = random.choice(archetypes)
            await update.message.reply_text(
                f'🎲 **Судьба выбирает за тебя!**\nВыпало: {text}',
                reply_markup=MAGIC_KEYBOARD
            )

        if user_id not in user_data or not user_data[user_id].photo_file:
            await update.message.reply_text(
                'Сначала пришли мне фото для магического анализа! 📸',
                reply_markup=MAGIC_KEYBOARD
            )
            return

        # Промпты для каждого архетипа (на английском для лучшего качества AI)
        archetype_prompts = {
            '🧙 АРХИМАГ': "magical transformation into an ancient archmage, glowing robes, mystical energy, floating runes, fantasy style, cinematic, high quality, magical transformation, detailed facial features, epic lighting",
            '🐉 ХРАНИТЕЛЬ ДРАКОНОВ': "person transforming into a dragon keeper, scales appearing on skin, dragon wings growing, mythical landscape with dragons flying, epic fantasy, dynamic motion, cinematic quality",
            '🌿 ДУХ ПРИРОДЫ': "person transforming into a nature spirit, body merging with leaves and vines, flowers blooming around, serene forest background, organic transformation, magical, cinematic",
            '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ': "person transforming into an elemental master, controlling fire, water, air, and earth, swirling elements around, powerful, dynamic, epic, fantasy, cinematic",
            '💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР': "person transforming into a crystalline avatar, body becoming transparent and refracting light, sparkling energy, geometric patterns, magical transformation, cinematic",
            '🎭 МАСКА ТЫСЯЧИ ЛИКОВ': "person transforming, face shifting through multiple masks and identities, surreal, mysterious, magical, changing appearances rapidly, cinematic quality"
        }

        selected_prompt = archetype_prompts.get(text)
        if not selected_prompt:
            await update.message.reply_text(
                'Пожалуйста, выбери магический архетип из предложенных ниже 👇',
                reply_markup=MAGIC_KEYBOARD
            )
            return

        user_data[user_id].selected_archetype = text

        # Уникальные описания процессов для каждого архетипа с анимированными эмодзи
        process_descriptions = {
            '🧙 АРХИМАГ': [
                "📖 Чтение древних гримуаров... ✨",
                "🔍 Поиск заклинаний... 🌟",
                "✨ Активация магического поля... 💫"
            ],
            '🐉 ХРАНИТЕЛЬ ДРАКОНОВ': [
                "🐲 Установление связи с драконами... 🔥",
                "🏔️ Поиск в мифических горах... 🌄",
                "🔥 Настройка драконьей ауры... 🐉"
            ],
            '🌿 ДУХ ПРИРОДЫ': [
                "🌳 Связь с древними лесами... 🍃",
                "🍃 Наполнение природной энергией... 🌸",
                "💫 Пробуждение духов природы... 🌿"
            ],
            '⚡ ПОВЕЛИТЕЛЬ СТИХИЙ': [
                "🌪️ Балансирование стихий... 🔥",
                "🔥 Настройка элементальной магии... 💧",
                "⚡ Концентрация природных сил... 🌪️"
            ],
            '💎 КРИСТАЛЛИЧЕСКИЙ АВАТАР': [
                "💎 Кристаллизация энергии... ✨",
                "🌈 Настройка светового спектра... 🌟",
                "✨ Формирование энергетической матрицы... 💎"
            ],
            '🎭 МАСКА ТЫСЯЧИ ЛИКОВ': [
                "🎭 Поиск в многомерном пространстве... 🔄",
                "🔄 Калибровка масок реальности... 🌌",
                "💫 Синхронизация параллельных личностей... 🎭"
            ]
        }

        process_steps = process_descriptions.get(text, [
            "🔮 Анализ магического потенциала... ✨",
            "✨ Подготовка превращения... 🌟",
            "🎭 Финальная магическая настройка... 💫"
        ])

        # Процесс магической генерации с прогрессом
        progress_msg = await update.message.reply_text(
            f'**🔮 WEBI-future запускает магическое превращение!**\n'
            f'Цель: {text}\n\n'
            f'_{process_steps[0]}_'
        )

        # Скачиваем фото пользователя
        photo_file = user_data[user_id].photo_file
        photo_path = f"temp_photo_{user_id}.jpg"
        await photo_file.download_to_drive(photo_path)

        await asyncio.sleep(3)
        await progress_msg.edit_text(
            f'**🔮 WEBI-future запускает магическое превращение!**\n'
            f'Цель: {text}\n\n'
            f'_{process_steps[1]}_'
        )

        await asyncio.sleep(3)
        await progress_msg.edit_text(
            f'**🔮 WEBI-future запускает магическое превращение!**\n'
            f'Цель: {text}\n\n'
            f'_{process_steps[2]}_'
        )

        await asyncio.sleep(2)

        # Пытаемся сгенерировать AI-видео
        try:
            await progress_msg.edit_text(
                f'**🔮 WEBI-future запускает магическое превращение!**\n'
                f'Цель: {text}\n\n'
                f'_🎬 Создаю магическое видео... (это займет 1-2 минуты)_'
            )

            # ОТЛАДКА: Проверяем дошли ли до сюда
            logger.info("🎯 ДОШЛИ ДО ВЫЗОВА AI-API")

            # Здесь будет вызов AI-API
            video_url = await generate_ai_video(photo_path, selected_prompt)

            # ОТЛАДКА: Проверяем что вернула функция
            logger.info(f"🎯 generate_ai_video вернула: {video_url}")

            if video_url:
                # Отправляем полученное видео
                await update.message.reply_video(
                    video=video_url,
                    caption=f'**✨ МАГИЧЕСКОЕ ПРЕВРАЩЕНИЕ ЗАВЕРШЕНО!**\n\n'
                            f'Ты успешно превратился в {text}!\n\n'
                            f'🚀 **WEBI-future** открывает порталы в новые реальности!',
                    reply_markup=MAGIC_KEYBOARD
                )
                await progress_msg.delete()
            else:
                # Если AI-видео не сгенерировалось, показываем заглушку
                await show_magical_transformation(update, text, progress_msg)

        except Exception as ai_error:
            logger.error(f"Ошибка AI-генерации: {ai_error}")
            # Если AI не работает, показываем стандартное превращение
            await show_magical_transformation(update, text, progress_msg)

        # Очищаем временные файлы
        if os.path.exists(photo_path):
            os.remove(photo_path)

        # Сбрасываем состояние
        user_data[user_id] = UserState()

    except Exception as e:
        logger.error(f"Ошибка при магическом превращении: {e}")
        await update.message.reply_text(
            '⚠️ Магические помехи! Превращение не удалось.\n'
            'Попробуй начать заново с команды /start',
            reply_markup=MAGIC_KEYBOARD
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text

    if any(archetype in text for archetype in [
        'АРХИМАГ', 'ХРАНИТЕЛЬ ДРАКОНОВ', 'ДУХ ПРИРОДЫ',
        'ПОВЕЛИТЕЛЬ СТИХИЙ', 'КРИСТАЛЛИЧЕСКИЙ АВАТАР',
        'МАСКА ТЫСЯЧИ ЛИКОВ', 'Наш сайт', 'Случайное превращение'
    ]):
        await handle_archetype_selection(update, context)
    else:
        await update.message.reply_text(
            '🔮 **WEBI-future Магическая Лаборатория** приветствует тебя!\n\n'
            'Я специализируюсь на раскрытии скрытых магических обликов.\n\n'
            'Отправь мне своё фото и выбери магическое превращение из меню!',
            reply_markup=MAGIC_KEYBOARD
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")


async def on_startup(app: Application):
    """Функция, которая выполняется при запуске бота"""
    print("🔄 WEBI-future Магическая Лаборатория запускается...")
    print("✅ Бот успешно активирован и готов к работе!")


async def on_shutdown(app: Application):
    """Функция, которая выполняется при остановке бота"""
    print("🔄 WEBI-future Магическая Лаборатория останавливается...")
    print("👋 До новых встреч в магических реальностях!")


def main():
    """Основная функция запуска бота"""
    print("🔮 Инициализация WEBI-future Магической Лаборатории...")

    # Запускаем веб-сервер в отдельном потоке для Render
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("🌐 HTTP-сервер запущен на порту 5000")

    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)

    print("🚀 Запуск бота в режиме polling...")

    # Запускаем бота в режиме polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )


if __name__ == '__main__':
    main()
