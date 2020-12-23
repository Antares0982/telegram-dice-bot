# coding=utf-8

from typing import Dict
from telegram.ext import Updater
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import numpy as np

import re
import createcard
from cfg import *
from botdicts import *

if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
                      'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)

dispatcher = updater.dispatcher

CARDINFO_KEYBOARD = [
    [InlineKeyboardButton("姓名", callback_data="姓名")],
    [InlineKeyboardButton("年龄", callback_data="年龄")],
    [InlineKeyboardButton("职业", callback_data="职业")]
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# read all dicts from file. Initialize the bot service
USER_DICT, GROUP_DICT, USER_GROUP_DICT, GROUP_KP_DICT, GROUP_PL_CARD_DICT = readinfo()


def start(update, context) -> bool:
    chattype = ""  # if info changed, chattype indicates which file should be written
    chatid = update.effective_chat.id
    uname = update.effective_chat.username
    if chatid > 0:  # private message
        context.bot.send_message(chat_id=chatid, text=HELP_TEXT)
        # store only username
        if chatid not in USER_DICT:
            if uname:
                USER_DICT[chatid] = uname
            else:
                USER_DICT[chatid] = ""
            chattype = "user"
        else:
            if uname and USER_DICT[chatid] != uname:
                chattype = "user"
                USER_DICT[chatid] = uname
                context.bot.send_message(
                    chat_id=USERID, text="User info updated: "+chatid+": "+uname)
            elif not uname and USER_DICT[chatid] != "":
                chattype = "user"
                USER_DICT[chatid] = ""
                context.bot.send_message(
                    chat_id=USERID, text="User info updated: "+chatid+": NONE")
    else:  # group message
        context.bot.send_message(chat_id=chatid, text="Activated!")
        if chatid not in GROUP_DICT:
            if uname:
                GROUP_DICT[chatid] = uname
            else:
                GROUP_DICT[chatid] = ""
            chattype = "group"
        else:
            if uname and GROUP_DICT[chatid] != uname:
                chattype = "group"
                GROUP_DICT[chatid] = uname
                context.bot.send_message(
                    chat_id=USERID, text="Group info updated: " + chatid + ": " + uname)
            elif not uname and GROUP_DICT[chatid] != "":
                chattype = "group"
                GROUP_DICT[chatid] = ""
                context.bot.send_message(
                    chat_id=USERID, text="Group info updated: "+chatid+": NONE")
    if chattype == "user":
        writeuserinfo(USER_DICT)
    elif chattype == "group":
        writegroupinfo(GROUP_DICT)
    return True


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def addkp(update, context) -> bool:
    if update.effective_chat.chat_id < 0:
        if update.effective_chat.id not in GROUP_DICT:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=r'Please activate this bot with /start first.')
            return False
        if update.effective_chat.id not in GROUP_KP_DICT:
            GROUP_KP_DICT[update.effective_chat.id] = update.message.from_user.id
            context.bot.send_message(chat_id=update.effective_chat.id, text="Bind group (id): " + str(
                update.effective_chat.id) + " with KP (id): " + str(update.message.from_user.id))
            return True
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=r'This group already has a KP, please delete KP with /delkp first.')
            return False
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to add KP.')
        return False


addkp_handler = CommandHandler('addkp', addkp)
dispatcher.add_handler(addkp_handler)


def delkp(update, context) -> bool:
    if update.effective_chat.chat_id < 0:
        if update.effective_chat.id not in GROUP_DICT:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=r'Please activate this bot with /start first.')
            return False
        if update.effective_chat.id in GROUP_KP_DICT:
            if update.message.from_user.id == GROUP_KP_DICT[update.effective_chat.id]:
                GROUP_KP_DICT.pop(update.effective_chat.id)
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text='KP deleted.')
                return True
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='You are not KP. Only KP can delete KP.')
            return False
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='This group does not have a KP.')
            return False
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to delete KP.')
        return False


delkp_handler = CommandHandler('delkp', delkp)
dispatcher.add_handler(delkp_handler)


def bind(update, context) -> bool:
    if update.effective_chat.chat_id < 0:
        if update.effective_chat.id not in GROUP_DICT:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=r'Please activate this bot with /start first.')
            return False
        USER_GROUP_DICT[update.message.from_user.id] = update.effective_chat.id
        context.bot.send_message(chat_id=update.effective_chat.id, text="Bind user (id): " + str(
            update.message.from_user.id) + " with group (id): " + str(update.effective_chat.id))
        return True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to bind.')
        return False


bind_handler = CommandHandler('bind', bind)
dispatcher.add_handler(bind_handler)


def showuserlist(update, context) -> None:
    if update.effective_chat.id == USERID:
        userlist = "User:\n"
        for keys in USER_DICT:
            userlist += keys + ": " + USER_DICT[keys] + "\n"
        userlist += "Groups:\n"
        for keys in GROUP_DICT:
            userlist += keys + ": " + USER_DICT[keys] + "\n"
        context.bot.send_message(
            parse_mode='HTML', chat_id=update.effective_chat.id, text=userlist)
    else:
        if update.effective_chat.id > 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)


def newgroup(groupid, context):
    if groupid < 0 and groupid in GROUP_DICT:
        return False
    context.bot.send_message(
        chat_id=groupid, text=r'Please activate this bot with /start.')
    return True


"""
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
"""


def card(update, context):
    text = context.args[0]
    if update.effective_chat.id < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to generate new card.")
        return False
    text = text.strip()
    createcard.generateNewCard(update.effective_chat.id)


card_handler = CommandHandler('card', card)
dispatcher.add_handler(card_handler)


def discard(update, context):
    pass


discard_handler = CommandHandler('discard', discard)
dispatcher.add_handler(discard_handler)


def roll(update, context):  # this function will be complicated
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
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please check the input.")
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
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=outmessage)
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Please check the input.")
        return


roll_handler = CommandHandler('roll', roll)
dispatcher.add_handler(roll_handler)

"""
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
"""


def unknown(update, context):
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

"""
def echo(update, context):
    context.bot.send_message(chat_id = update.effective_chat.id, text = update.message.text)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)
"""

if __name__ == "__main__":
    updater.start_polling()
