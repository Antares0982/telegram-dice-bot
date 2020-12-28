# -*- coding:utf-8 -*-

# Only define handlers and dicts that store info
import time
from telegram import Update, Chat, Bot
from typing import Dict
from telegram.ext import Updater, CallbackContext
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

from gameclass import *
import botdice

import createcard
from cfg import *
from botdicts import *
import copy


if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
                      'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)

dispatcher = updater.dispatcher

"""
CARDINFO_KEYBOARD = [
    [InlineKeyboardButton("姓名", callback_data="姓名")],
    [InlineKeyboardButton("职业", callback_data="职业")]
]
"""

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


global GROUP_KP_DICT, CARDS_LIST, ON_GAME

# read all dicts from file. Initialize the bot service
try:
    GROUP_KP_DICT, CARDS_LIST, ON_GAME = readinfo()
except:
    updater.bot.send_message(
        chat_id=USERID, text="Something went wrong, please check json files!")
    exit()
else:
    updater.bot.send_message(chat_id=USERID, text="Bot is live!")
DETAIL_DICT = {}  # temply stores details

SKILL_DICT = readskilldict()
JOB_DICT = readjobdict()

TEMP_CHECK = {}

def isprivatemsg(update: Update) -> bool:
    if update.effective_chat.id>0:
        return True
    return False

def isgroupmsg(update: Update) -> bool:
    return not isprivatemsg(update)

def searchifkp(id: int) -> bool:
    for keys in GROUP_KP_DICT:
        if GROUP_KP_DICT[keys] == id:
            return True
    return False

def isfromkp(update: Update) -> bool:
    if isprivatemsg(update):
        return searchifkp(update.effective_chat.id)
    if str(update.effective_chat.id) not in GROUP_KP_DICT or GROUP_KP_DICT[str(update.effective_chat.id)]!= update.message.from_user.id:
        return False
    return True


def start(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):  # private message
        context.bot.send_message(chat_id=update.effective_chat.id, text=HELP_TEXT)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def addkp(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to add KP.')
        return False
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    if str(gpid) in GROUP_KP_DICT:
        context.bot.send_message(
            chat_id=gpid, text='This group already has a KP, please delete KP with /delkp first.')
        return False
    GROUP_KP_DICT[str(gpid)] = kpid
    context.bot.send_message(
        chat_id=gpid, text="Bind group (id): " + str(gpid) + " with KP (id): " + str(kpid))
    writekpinfo(GROUP_KP_DICT)
    return True


addkp_handler = CommandHandler('addkp', addkp)
dispatcher.add_handler(addkp_handler)


def delkp(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to delete KP.')
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='This group does not have a KP.')
        return False
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='You are not KP.')
        return False
    GROUP_KP_DICT.pop(str(update.effective_chat.id))
    writekpinfo(GROUP_KP_DICT)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='KP deleted.')
    return True


delkp_handler = CommandHandler('delkp', delkp)
dispatcher.add_handler(delkp_handler)


def reload(update, context) -> bool:
    global GROUP_KP_DICT, CARDS_LIST, ON_GAME
    try:
        GROUP_KP_DICT, CARDS_LIST, ON_GAME = readinfo()
    except:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='"Something went wrong, please check json files!"')
        return False
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Reload successfully')
    return True


reload_handler = CommandHandler('reload', reload)
dispatcher.add_handler(reload_handler)


def showuserlist(update: Update, context: CallbackContext) -> None:
    if isgroupmsg(update): # Do nothing
        return
    if update.effective_chat.id == USERID:
        rttext = "GROUP_KP_LIST:\n"
        for keys in GROUP_KP_DICT:
            rttext += keys + ": "+str(GROUP_KP_DICT[keys])+"\n"
        context.bot.send_message(chat_id=USERID, text=rttext)
        context.bot.send_message(chat_id=USERID, text="CARDS:")
        for i in range(len(CARDS_LIST)):
            context.bot.send_message(chat_id=USERID, text=json.dumps(CARDS_LIST[i], indent=4, ensure_ascii=False))
        context.bot.send_message(chat_id=USERID, text="Game Info:")
        rttext = ""
        for i in range(len(ON_GAME)):
            rttext += str(ON_GAME[i].groupid) + ": " + str(ON_GAME[i].kpid)+"\n"
        context.bot.send_message(chat_id=USERID, text=rttext)
        return
    if isfromkp(update):
        gpid = 0
        for keys in GROUP_KP_DICT:
            if GROUP_KP_DICT[keys] == update.effective_chat.id:
                gpid = int(keys)
                context.bot.send_message(chat_id=USERID, text="Group: "+keys+"\nCARDS:")
                for i in range(len(CARDS_LIST)):
                    if CARDS_LIST[i]["group"]["groupid"] == gpid:
                        context.bot.send_message(chat_id=USERID, text=json.dumps(CARDS_LIST[i], indent=4, ensure_ascii=False))
        for i in range(len(ON_GAME)):
            if ON_GAME[i].kpid == update.effective_chat.id:
                context.bot.send_message(chat_id=USERID, text="Group: "+str(ON_GAME[i].groupid)+"is in a game.")
        return
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)


def getid(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(parse_mode='HTML', chat_id=update.effective_chat.id,
                             text="<code>"+str(update.effective_chat.id)+"</code> \nClick to copy")


getid_handler = CommandHandler('getid', getid)
dispatcher.add_handler(getid_handler)


def newcard(update: Update, context: CallbackContext):
    plid = update.effective_chat.id
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=plid, text="Send private message to generate new card.")
        return False
    if len(context.args) == 0:
        context.bot.send_message(
            chat_id=plid, text="Need groupid to generate new card.")
        return False
    msg = context.args[0]
    global CARDS_LIST, DETAIL_DICT
    if not botdice.isint(msg):
        context.bot.send_message(chat_id=plid,
                                 text="Invalid input. Use '/newcard groupid' to generate card.")
        return False
    gpid = int(msg)
    new_card, detailmsg = createcard.generateNewCard(
        plid, gpid)
    DETAIL_DICT[plid] = detailmsg
    new_card["id"] = len(CARDS_LIST)
    context.bot.send_message(chat_id=plid,
                             text="Card generated. Use /details to see detail.")
    countless50 = 0
    for keys in new_card["data"]:
        if new_card["data"][keys] < 50:
            countless50 += 1
    if countless50 >= 3:
        new_card["discard"] = True
        context.bot.send_message(chat_id=plid,
                                 text="If you want, use /discard to delete this card. After setting age you cannot delete this card.")
    context.bot.send_message(chat_id=plid,
                             text="Long press /setage and type a number to set AGE. If you need help, use /createcardhelp to read help.")
    CARDS_LIST.append(new_card)
    writecards(CARDS_LIST)
    return True


newcard_handler = CommandHandler('newcard', newcard)
dispatcher.add_handler(newcard_handler)


def discard(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to discard.")
        return False
    global CARDS_LIST
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i]["player"]["playerid"] == update.effective_chat.id and CARDS_LIST[i]["discard"] == True:
            CARDS_LIST = CARDS_LIST[:i]+CARDS_LIST[i+1:]
            j = i
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Card deleted.")
            while j < len(CARDS_LIST):
                CARDS_LIST[j]["id"] -= 1
                j += 1
            return True
        elif CARDS_LIST[i]["player"]["playerid"] == update.effective_chat.id:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Card does not meet the condition to be deleted. Please contact KP to delete this card.")
            return False
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Can't find card.")
    return False


discard_handler = CommandHandler('discard', discard)
dispatcher.add_handler(discard_handler)


def details(update: Update, context: CallbackContext):
    global DETAIL_DICT
    if update.effective_chat.id not in DETAIL_DICT or DETAIL_DICT[update.effective_chat.id] == "":
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Nothing to show.")
        return False
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=DETAIL_DICT[update.effective_chat.id])
    DETAIL_DICT[update.effective_chat.id] = ""
    return True


details_handler = CommandHandler('details', details)
dispatcher.add_handler(details_handler)


def getcard(plid: int) -> Tuple[dict, bool]:
    global CARDS_LIST
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i]["player"]["playerid"] == plid:
            return CARDS_LIST[i], True
    return None, False


def setage(update: Update, context: CallbackContext):
    global CARDS_LIST, DETAIL_DICT
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set AGE.")
        return False
    if len(context.args) == 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Need argument to set AGE.")
        return False
    age = context.args[0]
    if not botdice.isint(age):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    age = int(age)
    cardi, ok = getcard(update.effective_chat.id)
    if not ok:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Can't find card.")
        return False
    if "AGE" in cardi["info"] and cardi["info"]["AGE"] > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Age is already set.")
        return False
    cardi["info"]["AGE"] = age
    cardi, detailmsg = createcard.generateOtherAttributes(cardi)
    cardi["cardcheck"]["check1"] = True
    DETAIL_DICT[update.effective_chat.id] = detailmsg
    writecards(CARDS_LIST)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Age is set! To see more infomation, use /details . If age >= 40, you may need to set STR decrease.")
    return True


setage_handler = CommandHandler('setage', setage)
dispatcher.add_handler(setage_handler)


def setstrdec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set STR decrease.")
        return False
    plid = update.effective_chat.id
    global CARDS_LIST
    dec = context.args[0]
    if not botdice.isint(dec):
        context.bot.send_message(
            chat_id=plid, text="Invalid input.")
        return False
    dec = int(dec)
    cardi, ok = getcard(plid)
    if not ok:
        context.bot.send_message(
            chat_id=plid, text="Can't find card.")
        return False
    cardi, hintmsg, needcon = createcard.choosedec(cardi, dec)
    writecards(CARDS_LIST)
    context.bot.send_message(chat_id=plid, text=hintmsg)
    if needcon:
        context.bot.send_message(
            chat_id=plid, text="Use /setcondec to set CON decrease.")
    return True


setstrdec_handler = CommandHandler('setstrdec', setstrdec)
dispatcher.add_handler(setstrdec_handler)


def setcondec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set CON decrease.")
        return False
    dec = context.args[0]
    if not botdice.isint(dec):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    dec = int(dec)
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i]["player"]["playerid"] == update.effective_chat.id:
            CARDS_LIST[i], hintmsg = createcard.choosedec2(
                CARDS_LIST[i], dec)
            writecards(CARDS_LIST)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=hintmsg)
            return True
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Can't find card.")
    return False


setcondec_handler = CommandHandler('setcondec', setcondec)
dispatcher.add_handler(setcondec_handler)


def setjob(update: Update, context: CallbackContext) -> bool:  # Button. need 0-1 args, if len(args)==0, show button and listen
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set job.")
        return False
    plid = update.effective_chat.id
    card1, ok = getcard(plid)
    if not ok:
        context.bot.send_message(
            chat_id=plid, text="Can't find card.")
        return False
    if len(context.args) == 0:
        pass
        return True
    jobname = context.args[0]
    if not IGNORE_JOB_DICT and jobname not in JOB_DICT:
        context.bot.send_message(
            chat_id=plid, text="This job is not allowed!")
        return False
    if jobname not in JOB_DICT:
        context.bot.send_message(
            chat_id=plid, text="This job is not in joblist, you can use /addskill to choose skills you like!")
        return True
    for i in range(3, len(JOB_DICT[jobname])):
        card1["suggestskill"][JOB_DICT[jobname][i]] = SKILL_DICT[JOB_DICT[jobname][i]]
    context.bot.send_message(
        chat_id=plid, text="Skill suggestions generated. Use /addskill to add skills.")
    return True


setjob_handler = CommandHandler('setjob', setjob)
dispatcher.add_handler(setjob_handler)


def addskill(update: Update, context: CallbackContext) -> bool: # Button. need 0-2 args, if len(args)==0 or 1, show button and listen
    if isgroupmsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to add skill.")
        return False
    plid = update.effective_chat.id
    card1, ok = getcard(plid)
    if not ok:
        context.bot.send_message(
            chat_id=plid, text="Can't find card.")
        return False
    if len(context.args) == 0:
        pass
        return True
    if len(context.args) == 1:
        pass
        return True
    skillname = context.args[0]
    skillvalue = context.args[1]
    if not botdice.isint(skillvalue):
        context.bot.send_message(
            chat_id=plid, text="Invalid input.")
    skillvalue = int(skillvalue)
    if skillvalue > card1["skill"]["points"]:
        context.bot.send_message(
            chat_id=plid, text="You don't have so many points.")
        return False
    if skillname in SKILL_DICT:
        card1["skill"][skillname] = SKILL_DICT[skillname]+skillvalue
    else:
        card1["skill"][skillname] = skillvalue
    card1["skill"]["points"] -= skillvalue


# game

# 有KP，且所有卡准备完成时，由KP开始游戏。如果需要更改一些信息，用/abortgame
def startgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game can only be started in a group.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="This group does not have a KP.")
        return False
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can start a game.")
        return False
    global CARDS_LIST, ON_GAME
    gamecards = []
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i]["group"]["groupid"] == update.effective_chat.id:
            if not createcard.checkcard(CARDS_LIST[i]):
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text="Card id: "+str(i)+" is not ready to play.")
                return False
            gamecards.append(copy.deepcopy(CARDS_LIST[i]))
    ON_GAME.append(GroupGame(groupid=update.effective_chat.id,
                             kpid=GROUP_KP_DICT[str(update.effective_chat.id)], cards=gamecards))
    return True


startgame_handler = CommandHandler('startgame', startgame)
dispatcher.add_handler(startgame_handler)


def abortgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game can only be aborted in a group.")
        return False
    if str(update.effective_chat.id) in GROUP_KP_DICT and update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can abort a game.")
        return False
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == update.effective_chat.id:
            t = ON_GAME[i]
            ON_GAME = ON_GAME[:i]+ON_GAME[i+1:]
            del t
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Game aborted.")
            return True
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Game not found.")
    return False


abortgame_handler = CommandHandler('abortgame', abortgame)
dispatcher.add_handler(abortgame_handler)


def endgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game can only be ended in a group.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="This group does not have a KP.")
        return False
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can end a game.")
        return False
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == update.effective_chat.id:
            t = ON_GAME[i]
            ON_GAME = ON_GAME[:i]+ON_GAME[i+1:]
            gamecards = t.cards
            for i in range(len(gamecards)):
                for j in range(len(CARDS_LIST)):
                    if gamecards[i]["player"]["playerid"] == CARDS_LIST[j]["player"]["playerid"]:
                        CARDS_LIST[j] = gamecards[i]
                        CARDS_LIST[j]["player"] = {}  # 解绑
                        CARDS_LIST[j]["group"] = {}  # 解绑
                        break
            del t
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Game end!")
            return True
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Game not found.")
    return False


endgame_handler = CommandHandler('endgame', endgame)
dispatcher.add_handler(endgame_handler)


def findgame(gpid: int) -> Tuple[GroupGame, bool]:
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == gpid:
            return ON_GAME[i], True
    return None, False


def findgamewithkpid(kpid: int) -> Tuple[GroupGame, bool]:
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].kpid == kpid:
            return ON_GAME[i], True
    return None, False


def findcardfromgame(game: GroupGame, plid: int) -> Tuple[dict, bool]:
    for i in game.cards:
        if game.cards[i]["player"]["playerid"] == plid:
            return game.cards[i], True
    return None, False


def switchcard(update: Update, context: CallbackContext):
    game, ok = findgamewithkpid(update.message.from_user.id)
    if not ok:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game not found.")
        return False
    num = context.args[0]
    if not botdice.isint(num):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    num = int(num)
    if num >= len(game.kpcards):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="You don't have so many card.")
        return False
    game.kpctrl = num
    context.bot.send_message(chat_id=update.effective_chat.id, text="Switched to card " +
                             str(num)+", card name is: " + game.kpcards[num]["info"]["name"])
    return True


switchcard_handler = CommandHandler('switchcard', switchcard)
dispatcher.add_handler(switchcard_handler)


def tempcheck(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="No argument found.")
        return False
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Change tempcheck in a group.")
        return False
    if not botdice.isint(context.args[0]) or int(context.args[0]) <= 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Temp check should be positive integer.")
        return False
    game, ok = findgame(update.effective_chat.id)
    if not ok:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="No game found.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT or GROUP_KP_DICT[str(update.effective_chat.id)] != update.message.from_user.id:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only kp can set temp check.")
        return False
    game.tpcheck = int(context.args[0])
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Add temp check successfully.")


def roll(update: Update, context: CallbackContext):
    # 只接受第一个空格前的参数。dicename可能是技能名，可能是3d6，可能是1d4+2d10。骰子环境可能是游戏中，游戏外。需要考虑多个情况
    if len(context.args) == 0:
        pass  # 骰1d100
        return True
    dicename = context.args[0]
    if update.effective_chat.id < 0:  # Group msg
        game, ok = findgame()
        tpcheck, game.tpcheck = game.tpcheck, 0
        if not ok or dicename.find('d') >= 0:
            rttext = botdice.commondice(dicename)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=rttext)
            if rttext == "Invalid input.":
                return False
            return True
        senderid = update.message.from_user.id
        gpid = update.effective_chat.id
        if senderid != GROUP_KP_DICT[str(update.effective_chat.id)]:
            gamecard, ok = findcardfromgame(game, senderid)
        elif game.kpctrl == -1:
            rttext = botdice.commondice(dicename)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=rttext)
            if rttext == "Invalid input.":
                return False
            return True
        else:
            gamecard = game.cards[game.kpctrl]
        test = 0
        if dicename in gamecard["skill"]:
            test = gamecard["skill"][dicename]
        elif dicename in gamecard["data"]:
            test = gamecard["data"][dicename]
        elif dicename == "力量":
            dicename = "STR"
            test = gamecard["data"][dicename]
        elif dicename == "体质":
            dicename = "CON"
            test = gamecard["data"][dicename]
        elif dicename == "体型":
            dicename = "SIZ"
            test = gamecard["data"][dicename]
        elif dicename == "敏捷":
            dicename = "DEX"
            test = gamecard["data"][dicename]
        elif dicename == "外貌":
            dicename = "APP"
            test = gamecard["data"][dicename]
        elif dicename == "智力":
            dicename = "INT"
            test = gamecard["data"][dicename]
        elif dicename == "意志":
            dicename = "POW"
            test = gamecard["data"][dicename]
        elif dicename == "教育":
            dicename = "EDU"
            test = gamecard["data"][dicename]
        elif dicename == "幸运":
            dicename = "LUCK"
            test = gamecard["data"][dicename]
        else:
            pass
            return False
        if "global" in gamecard["tempstatus"]:
            test += gamecard["tempstatus"]["global"]
        if dicename in gamecard["tempstatus"]:
            test += gamecard["tempstatus"]["global"]
        pass
        return True
    rttext = botdice.commondice(dicename)  # private msg
    context.bot.send_message(chat_id=update.effective_chat.id, text=rttext)
    if rttext == "Invalid input.":
        return False
    return True


roll_handler = CommandHandler('roll', roll)
dispatcher.add_handler(roll_handler)


def unknown(update: Update, context: CallbackContext) -> None:
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
    while True:
        try:
            updater.start_polling()
        except:
            time.sleep(30)
            updater.bot.send_message(chat_id=USERID, text="Bot restarting.")
