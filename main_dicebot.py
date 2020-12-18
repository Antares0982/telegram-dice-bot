# coding=utf-8

from telegram.ext import Updater
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
import logging
import numpy as np
import json
import re
from cfg import *

if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token = TOKEN, use_context = True)

dispatcher = updater.dispatcher

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)

STARTUP = False

def startup():
    pass


#Initialize the bot service
def start(update, context):
    if not STARTUP:
        userdict, groupdict = startup()
    context.bot.send_message(chat_id = update.effective_chat.id, text = "Welcome!")
    if update.effective_chat.id > 0:#private message
        if update.effective_chat.id not in userdict:
            userdict[update.effective_chat.id] = update.effective_chat.username
        else userdict[update.effective_chat.id]!= update.effective_chat.username:
            context.bot.send_message(chat_id = USERID, text = "User info updated: "+update.effective_chat.id+": "+update.effective_chat.username)
    else:#group message
        path = PATH_GROUP
        if update.effective_chat.username:
            userinfo = '\n"' + update.effective_chat.title + ': ' + r'<code>' + str(update.effective_chat.id) + r'</code> @' + str(update.effective_chat.username) + '"'
        else:
            userinfo = '\n"' + update.effective_chat.title + ': ' + r'<code>' + str(update.effective_chat.id) + r'</code> ' + '(no username)' + '"'
    with open(path, 'r', encoding = 'utf-8') as f:
        userlist = f.read()
    a = userlist.find(str(update.effective_chat.id))
    if a != -1:
        b = a - 10
        if b < 0:
            b = 0
        while b >= 0:
            c = userlist.find('\n', b, a)
            if c != -1:
                b = userlist.find('\n', a)
                if b == -1:
                    b = len(userlist)
                oldinfo = userlist[c:b]
                userlist = userlist.replace(oldinfo, userinfo)
                with open(path, 'w', encoding = 'utf-8') as f:
                    f.write(userlist)
                break
            else:
                b -= 10
        if b < 0:
            context.bot.send_message(chat_id = USERID, text = "Some error occured!")
    else:
        with open(path, 'a', encoding = 'utf-8') as f:
            f.write(userinfo)
    
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def showuserlist(update, context):
    if update.effective_chat.id == USERID:
        with open(PATH_USER, encoding='utf-8') as f:
            userlist = f.read()
            context.bot.send_message(parse_mode='HTML', chat_id = update.effective_chat.id, text = userlist)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Sorry, I didn't understand that command.")

showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)


def showgrouplist(update, context):
    if update.effective_chat.id == USERID:
        with open(PATH_GROUP, encoding = 'utf-8') as f:
            grouplist = f.read()
            context.bot.send_message(parse_mode = 'HTML', chat_id = update.effective_chat.id, text = grouplist)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Sorry, I didn't understand that command.")

showgrouplist_handler = CommandHandler('showgrouplist', showgrouplist)
dispatcher.add_handler(showgrouplist_handler)


def newgroup(groupid, context):
    if groupid < 0:
        with open(PATH_GROUP, 'r', encoding = 'utf-8') as f:
            if not(str(groupid) in f.read()):
                context.bot.send_message(chat_id = groupid, text = r'Please activate this bot with /start.')
                return True
    return False


def roll1d100(update, context):
    if newgroup(update.effective_chat.id, context):
        return
    rand=np.random.randint(1, 100)
    with open(path_test, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
        RollTest = data[str(update.effective_chat.id)]
    if RollTest > 0 and RollTest < 100:    
        text_roll1d100 = '1d100: （检定/出目） ' + str(RollTest) + '/' + str(rand)
        if rand > 96:
            text_roll1d100 = text_roll1d100 + ' 大失败'
        elif rand < 4:
            text_roll1d100 = text_roll1d100 + ' 大成功'
        elif rand > RollTest:
            text_roll1d100 = text_roll1d100 + ' 失败'
        else:
            text_roll1d100 = text_roll1d100 + ' 成功'
    else:
        text_roll1d100 = '1d100: ' + str(rand)
        if rand > 96:
            text_roll1d100 = text_roll1d100 + ' 大失败'
        elif rand < 4:
            text_roll1d100 = text_roll1d100 + ' 大成功'
    context.bot.send_message(chat_id = update.effective_chat.id, text = text_roll1d100)

roll1d100_handler = CommandHandler('roll1d100', roll1d100)
dispatcher.add_handler(roll1d100_handler)


def roll(update, context):
    if newgroup(update.effective_chat.id, context):
        return
    dicename = str(context.args[0])
    dicearr = dicename.split('d', 1)
    dices = dicearr[0]
    dicenum = dicearr[1]
    dices = dices.replace(' ', "")
    dicenum = dicenum.replace(' ', "")
    if str.isdigit(dices) and str.isdigit(dicenum):
        dices = int(dices)
        dicenum = int(dicenum)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Please check the input.")
        return
    if dices < 20 and dices > 0 and dicenum > 0 and dicenum < 101:
        outmessage = dicename + ': '
        sumaa = 0
        if dices == 1:
            sumaa = np.random.randint(1, dicenum)
            outmessage = outmessage + str(sumaa)
        else:
            for i in range(1, dices + 1):
                a = np.random.randint(1, dicenum)
                outmessage = outmessage+str(a)+'+'
                sumaa += a
            outmessage = outmessage[0:len(outmessage)-1]
            outmessage = outmessage + '=' + str(sumaa)
        context.bot.send_message(chat_id = update.effective_chat.id, text = outmessage)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Please check the input.")
        return

roll_handler = CommandHandler('roll', roll)
dispatcher.add_handler(roll_handler)


def settest(update, context):
    if newgroup(update.effective_chat.id, context):
        return
    testnum = int(' '.join(context.args))
    if not(testnum < 100 and testnum > 0):
        context.bot.send_message(chat_id = update.effective_chat.id, text = r'Please input an integer in 1-99.')
        return
    with open(path_test, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
        data[str(update.effective_chat.id)] = testnum
        with open(path_test, 'w', encoding = 'utf-8') as f1:
            json.dump(data, f1)
        context.bot.send_message(chat_id = update.effective_chat.id, text = r'Test was set successfully: ' + str(testnum))
        
settest_handler = CommandHandler('settest', settest)
dispatcher.add_handler(settest_handler)


def resettest(update, context):
    if newgroup(update.effective_chat.id, context):
        return
    with open(path_test, 'r', encoding = 'utf-8') as f:
        data = json.load(f)
        data[str(update.effective_chat.id)] = 0
        with open(path_test, 'w', encoding = 'utf-8') as f1:
            json.dump(data, f1)
        context.bot.send_message(chat_id = update.effective_chat.id, text = r'Test has been reset successfully.')

resettest_handler = CommandHandler('resettest', resettest)
dispatcher.add_handler(resettest_handler)


def unknown(update, context):
    context.bot.send_message(chat_id = update.effective_chat.id, text = "Sorry, I didn't understand that command.")

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

"""
def echo(update, context):
    context.bot.send_message(chat_id = update.effective_chat.id, text = update.message.text)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)
"""

updater.start_polling()
