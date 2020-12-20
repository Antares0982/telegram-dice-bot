# coding=utf-8

from typing import Dict
from telegram.ext import Updater
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import numpy as np
import json
import re
from cfg import *

if PROXY:
    updater = Updater(token = TOKEN, request_kwargs = {'proxy_url': PROXY_URL}, use_context = True)
else:
    updater = Updater(token = TOKEN, use_context = True)

dispatcher = updater.dispatcher

CARDINFO_KEYBOARD = [
    [InlineKeyboardButton("姓名", callback_data = "姓名")],
    [InlineKeyboardButton("年龄", callback_data = "年龄")],
    [InlineKeyboardButton("职业", callback_data = "职业")]
]

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)

STARTUP = False
USER_DICT = {}
GROUP_DICT = {}

def writeuserinfo():
    pass

def writegroupinfo():
    pass

def readuserinfo():
    pass

def readgroupinfo():
    pass

def startup():#read: USER_DICT and GROUP_DICT
    STARTUP = True
    pass

#Initialize the bot service
startup()

# and renew the 
def start(update, context):
    context.bot.send_message(chat_id = update.effective_chat.id, text = "Welcome!")
    chattype = ""
    if update.effective_chat.id > 0:#private message
        if update.effective_chat.id not in USER_DICT:
            if update.effective_chat.username:
                USER_DICT[update.effective_chat.id] = update.effective_chat.username
            else:
                USER_DICT[update.effective_chat.id] = ""
            chattype = "user"
        else:
            if update.effective_chat.username and USER_DICT[update.effective_chat.id]!=update.effective_chat.username:
                chattype = "user"
                USER_DICT[update.effective_chat.id]=update.effective_chat.username
                context.bot.send_message(chat_id = USERID, text = "User info updated: "+update.effective_chat.id+": "+update.effective_chat.username)
            elif not update.effective_chat.username and USER_DICT[update.effective_chat.id] != "":
                chattype = "user"
                USER_DICT[update.effective_chat.id] = ""
                context.bot.send_message(chat_id = USERID, text = "User info updated: "+update.effective_chat.id+": NONE")
    else:#group message
        if update.effective_chat.id not in GROUP_DICT:
            if update.effective_chat.username:
                GROUP_DICT[update.effective_chat.id] = update.effective_chat.username
            else:
                GROUP_DICT[update.effective_chat.id] = ""
            chattype = "group"
        else:
            if update.effective_chat.username and GROUP_DICT[update.effective_chat.id]!=update.effective_chat.username:
                chattype = "group"
                GROUP_DICT[update.effective_chat.id]=update.effective_chat.username
                context.bot.send_message(chat_id = USERID, text = "Group info updated: "+update.effective_chat.id+": "+update.effective_chat.username)
            elif not update.effective_chat.username and GROUP_DICT[update.effective_chat.id] != "":
                chattype = "group"
                GROUP_DICT[update.effective_chat.id]=""
                context.bot.send_message(chat_id = USERID, text = "Group info updated: "+update.effective_chat.id+": NONE")
    if chattype == "user":
        writeuserinfo()
    elif chattype == "group":
        writegroupinfo()

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def showuserlist(update, context):
    if update.effective_chat.id == USERID:
        userlist = "User:\n"
        for keys in USER_DICT:
            userlist += keys + ": " + USER_DICT[keys] + "\n"
        userlist += "Groups:\n"
        for keys in GROUP_DICT:
            userlist += keys + ": " + USER_DICT[keys] + "\n"
        context.bot.send_message(parse_mode='HTML', chat_id = update.effective_chat.id, text = userlist)
    else:
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Sorry, I didn't understand that command.")

showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)



def newgroup(groupid, context):
    if groupid < 0 and groupid in GROUP_DICT:
        return True
    context.bot.send_message(chat_id = groupid, text = r'Please activate this bot with /start.')
    return False


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
def generateNewCard(userid, groupid)->dict:
    card = {
        "player":{
            "playerid":userid,
            "playername":USER_DICT[userid]
        },
        "group" : {
            "groupid" : groupid,
            "groupname" : GROUP_DICT[groupid]
        }
    }
    STR = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
    CON = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
    SIZ = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+6)
    DEX = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
    APP = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
    INT = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+6)
    POW = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
    EDU = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+6)
    card["data"]={}
    card["data"]["STR"]=STR
    card["data"]["CON"]=CON
    card["data"]["SIZ"]=SIZ
    card["data"]["DEX"]=DEX
    card["data"]["APP"]=APP
    card["data"]["INT"]=INT
    card["data"]["POW"]=POW
    card["data"]["EDU"]=EDU
    card["derived"]={}
    

def generateOtherAttributes(card : dict)->str:
    if "age" not in card["data"]:
        return "Attribute: AGE is NONE, please set AGE first"
    AGE = card["data"]["age"]
    rttext = ""
    if AGE<20:
        newluck = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
        if card["data"]["LUCK"]<newluck:
            card["data"]["LUCK"]=newluck
            rttext+="年龄低于20，幸运已经重骰，现在幸运值："+str(newluck)+"。教育减5，力量体型合计减5"
        else:
            card["data"]["LUCK"]
            rttext+="年龄低于20，幸运重骰低于原始值。教育减5，力量体型合计减5"
        card["data"]["STR_SIZ_M"]=-5
        card["data"]["EDU"]-=5
    elif AGE<40:
        pass
        

def createCard(card:dict)->None:
    totalData = 0
    for keys in card["data"]:
        totalData += card["data"][keys]
    pass

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
