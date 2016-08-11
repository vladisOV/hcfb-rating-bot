# -*- coding: utf-8 -*-
import telebot
import cherrypy
from telebot import types
from telebot import apihelper
import sys
from rating_dao import *

reload(sys)
sys.setdefaultencoding('utf-8')
rating_dao = RatingDao()
db_admins = [219662257]
# WEBHOOK_HOST = '10.6.173.127'
# WEBHOOK_PORT = 8443
# WEBHOOK_LISTEN = '0.0.0.0'
#
# WEBHOOK_SSL_CERT = './webhook_cert.pem'
# WEBHOOK_SSL_PRIV = './webhook_pkey.pem'
#
# WEBHOOK_URL_BASE = "https://%s:%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
# WEBHOOK_URL_PATH = "/%s/" % (config.token)

bot = telebot.TeleBot(config.token)


class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(m):
    if not rating_dao.check_user(m.chat.id):
        send_unauthorized_message(m)
    else:
        markup = types.ReplyKeyboardMarkup()
        markup.row('Мой рейтинг', 'Действие')
        markup.row('Возможные улучшения', 'Проблемы')
        bot.send_message(m.chat.id, 'Добро пожаловать, ' + m.from_user.first_name + '! \n'
                                                                                    'Используйте меню для навигации.',
                         reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Меню')
def send_welcome(m):
    markup = types.ReplyKeyboardMarkup()
    markup.row('Мой рейтинг', 'Действие')
    markup.row('Возможные улучшения', 'Проблемы')
    bot.send_message(m.chat.id, 'Меню', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Мой рейтинг')
def send_welcome(m):
    rating_info = rating_dao.get_rating(m.chat.id)
    if rating_info:
        bot.send_message(m.chat.id, 'Ваш рейтинг - ' + str(rating_info[0][0]) + '! \n' +
                         str(rating_info[0][1]))
    else:
        bot.send_message(m.chat.id, 'Информация о рейтинге отсутствует.')


@bot.message_handler(func=lambda message: message.text == 'Проблемы')
def send_welcome(m):
    rows = rating_dao.get_problems(m.chat.id)
    problems = ''
    for (i, row) in enumerate(rows):
        problems += str(i + 1) + '. ' + row[0] + '\n'
    bot.send_message(m.chat.id, problems)


@bot.message_handler(func=lambda message: message.text == 'Действие' or message.text == 'Другое действие')
def send_welcome(m):
    markup = types.ReplyKeyboardMarkup()
    markup.row('Меню', 'Выполнил', 'Другое действие')
    action = rating_dao.get_action(m.chat.id)
    if not action:
        on_action_end(m)
    else:
        bot.send_message(m.chat.id, action, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Выполнил')
def send_welcome(m):
    markup = types.ReplyKeyboardMarkup()
    markup.row('Да, успешно', 'Нет, неуспешно')
    bot.send_message(m.chat.id, 'Подтвердите выполнение:', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Да, успешно')
def send_welcome(m):
    rating_dao.set_action_done(m.chat.id, True)
    markup = types.ReplyKeyboardMarkup()
    markup.row('Меню', 'Выполнил', 'Другое действие')
    action = rating_dao.get_action(m.chat.id)
    if not action:
        on_action_end(m)
    else:
        bot.send_message(m.chat.id, action, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Нет, неуспешно')
def send_welcome(m):
    rating_dao.set_action_done(m.chat.id, False)
    markup = types.ReplyKeyboardHide()
    bot.send_message(m.chat.id, 'Укажите причину:', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Возможные улучшения')
def send_welcome(m):
    rating_comment = rating_dao.get_benefit(m.chat.id)
    bot.send_message(m.chat.id, rating_comment)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def default_test(m):
    if not rating_dao.check_user(m.chat.id):
        send_unauthorized_message(m)
    else:
        is_logged = rating_dao.log_action_comment(m.chat.id, m.text)
        if is_logged:
            bot.send_message(m.chat.id, 'Комментарий получен.')
            markup = types.ReplyKeyboardMarkup()
            markup.row('Меню', 'Выполнил', 'Другое действие')
            action = rating_dao.get_action(m.chat.id)
            if not action:
                on_action_end(m)
            else:
                bot.send_message(m.chat.id, action, reply_markup=markup)
        else:
            bot.send_message(m.chat.id, 'Используйте меню для навигации.')


@bot.message_handler(content_types=['document'])
def handle_docs(m):
    if m.chat.id in db_admins and m.document.file_name == 'db.xlsx':
        document_desc = apihelper.get_file(config.token, m.document.file_id)
        document = apihelper.download_file(config.token, document_desc.get('file_path'))
        rating_dao.insert_db_info(document)


def send_unauthorized_message(m):
    bot.send_message(m.chat.id, 'Авторизация пользователя не выполнена. '
                                'Ваш telegram_id - ' + str(m.chat.id))


def on_action_end(m):
    markup = types.ReplyKeyboardMarkup()
    markup.row('Мой рейтинг', 'Возможные улучшения')
    bot.send_message(m.chat.id,
                     'Какой молодец у нас ' + m.from_user.first_name + ', закрыл все действия! ' +
                     'Теперь ты можешь взять телевизор в кредит под 800%.',
                     reply_markup=markup)


if __name__ == '__main__':
    bot.polling(none_stop=True)
# bot.remove_webhook()
#
# bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
#                 certificate=open(WEBHOOK_SSL_CERT, 'r'))
#
# cherrypy.config.update({
#     'server.socket_host': WEBHOOK_LISTEN,
#     'server.socket_port': WEBHOOK_PORT,
#     'server.ssl_module': 'builtin',
#     'server.ssl_certificate': WEBHOOK_SSL_CERT,
#     'server.ssl_private_key': WEBHOOK_SSL_PRIV
# })
#
# cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})
