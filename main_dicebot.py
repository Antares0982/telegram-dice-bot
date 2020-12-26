# coding=utf-8

# Only define handlers and dicts that store info

from numpy.lib.function_base import append
from telegram import Update, Chat
from typing import Dict
from telegram.ext import Updater, CallbackContext
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

import numpy as np
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

CARDINFO_KEYBOARD = [
    [InlineKeyboardButton("姓名", callback_data="姓名")],
    [InlineKeyboardButton("职业", callback_data="职业")]
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# read all dicts from file. Initialize the bot service
USER_GROUP_DICT, GROUP_KP_DICT, GROUP_PL_CARD_DICT, CARDS_LIST, ON_GAME = readinfo()

DETAIL_DICT = {} # temply stores details

SKILL_DICT = readskilldict()

def start(update: Update, context: CallbackContext) -> bool:
    chatid = update.effective_chat.id
    if chatid > 0:  # private message
        context.bot.send_message(chat_id=chatid, text=HELP_TEXT)
        # store only username
    return True


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def addkp(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.chat_id < 0:
        if str(update.effective_chat.id) not in GROUP_KP_DICT:
            GROUP_KP_DICT[str(update.effective_chat.id)] = update.message.from_user.id
            context.bot.send_message(chat_id=update.effective_chat.id, text="Bind group (id): " + str(
                update.effective_chat.id) + " with KP (id): " + str(update.message.from_user.id))
            writekpinfo(GROUP_KP_DICT)
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


def delkp(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.chat_id < 0:
        if str(update.effective_chat.id) in GROUP_KP_DICT:
            if update.message.from_user.id == GROUP_KP_DICT[str(update.effective_chat.id)]:
                GROUP_KP_DICT.pop(update.effective_chat.id)
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text='KP deleted.')
                return True
            context.bot.send_message(
                chat_id=update.effective_chat.id, text='You are not KP.')
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


def reload(update, context) -> bool:
    global USER_GROUP_DICT, GROUP_KP_DICT, GROUP_PL_CARD_DICT, CARDS_LIST, ON_GAME
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Reload successful')
    USER_GROUP_DICT, GROUP_KP_DICT, GROUP_PL_CARD_DICT, CARDS_LIST, ON_GAME = readinfo()
    return True


reload_handler = CommandHandler('reload', reload)
dispatcher.add_handler(reload_handler)


def bind(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.chat_id < 0:
        USER_GROUP_DICT[update.message.from_user.id] = update.effective_chat.id
        context.bot.send_message(chat_id=update.effective_chat.id, text="Bind user (id): " + str(
            update.message.from_user.id) + " with group (id): " + str(update.effective_chat.id))
        writeusergroupinfo(USER_GROUP_DICT)
        return True
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to bind.')
        return False


bind_handler = CommandHandler('bind', bind)
dispatcher.add_handler(bind_handler)


def showuserlist(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id == USERID:
        pass
    else:
        if update.effective_chat.id > 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)



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


def getid(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(parse_mode='HTML', chat_id=update.effective_chat.id,
                             text="<code>"+str(update.effective_chat.id)+"</code> \n点击即可复制")


getid_handler = CommandHandler('getid', getid)
dispatcher.add_handler(getid_handler)


def newcard(update: Update, context: CallbackContext):
    if update.effective_chat.id < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to generate new card.")
        return False
    msg = context.args[0]
    msg = msg.strip()
    global CARDS_LIST, DETAIL_DICT
    if str.isdigit(msg):
        gpid = int(msg)
        new_card, detailmsg = createcard.generateNewCard(update.effective_chat.id, gpid)
        DETAIL_DICT[str(update.effective_chat.id)] = detailmsg
        new_card["id"] = len(CARDS_LIST)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Card generated. Use /details to see detail.")
        countless50 = 0
        for keys in new_card["data"]:
            if new_card["data"][keys]<50:
                countless50+=1
        if countless50>=3:
            new_card["discard"]=True
            context.bot.send_message(chat_id=update.effective_chat.id, text="If you want, use /discard to delete this card. After setting age you cannot delete this card.")
        else:
            new_card["discard"]=False
        context.bot.send_message(chat_id=update.effective_chat.id, text="Long press /setage and type a number to set AGE. If you need help, use /createcardhelp to read help.")
        CARDS_LIST.append(new_card)
        writecards(CARDS_LIST)
        return True
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Invalid input. Use '/newcard groupid' to generate card.")
    return False


newcard_handler = CommandHandler('newcard', newcard)
dispatcher.add_handler(newcard_handler)





def discard(update: Update, context: CallbackContext):
    if update.effective_chat.id < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to discard.")
        return False
    global CARDS_LIST
    for i in range(CARDS_LIST):
        if CARDS_LIST[i]["user"]["userid"] == update.effective_chat.id and CARDS_LIST[i]["discard"] == True:
            CARDS_LIST=CARDS_LIST[:i]+CARDS_LIST[i+1:]
            j=i
            context.bot.send_message(chat_id=update.effective_chat.id, text="Card deleted.")
            while j<len(CARDS_LIST):
                CARDS_LIST[j]["id"]-=1
                j+=1
            return True
        elif CARDS_LIST[i]["user"]["userid"] == update.effective_chat.id:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Card does not meet the condition to be deleted. Please contact KP to delete this card.")
            return False
    context.bot.send_message(chat_id=update.effective_chat.id, text="Can't find card.")
    return False


discard_handler = CommandHandler('discard', discard)
dispatcher.add_handler(discard_handler)





def details(update: Update, context: CallbackContext):
    global DETAIL_DICT
    if update.effective_chat.id not in DETAIL_DICT or DETAIL_DICT[update.effective_chat.id]=="":
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Nothing to show.")
        return False
    context.bot.send_message(chat_id=update.effective_chat.id, text=DETAIL_DICT[update.effective_chat.id])
    DETAIL_DICT[update.effective_chat.id] = ""
    return True


details_handler = CommandHandler('details', details)
dispatcher.add_handler(details_handler)


def getcard(plid: int) -> tuple(dict, bool):
    global CARDS_LIST
    for i in range(CARDS_LIST):
        if CARDS_LIST[i]["player"]["playerid"]==plid:
            return CARDS_LIST[i], True
    return None, False


def setage(update: Update, context: CallbackContext):
    global CARDS_LIST
    if update.effective_chatid < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set AGE.")
        return False
    age = context.args[0]
    if not str.isdigit(age):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    age = int(age)
    cardi, ok = getcard(update.effective_chatid)
    if not ok:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Can't find card.")
        return False
    cardi["info"]["AGE"] = age
    cardi, hintmsg = createcard.generateOtherAttributes(cardi)
    writecards(CARDS_LIST)
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=hintmsg)
    return True
    


setage_handler = CommandHandler('setage', setage)
dispatcher.add_handler(setage_handler)


def setstrdec(update: Update, context: CallbackContext):
    if update.effective_chatid < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set STR decrease.")
        return False
    global CARDS_LIST
    dec = context.args[0]
    if not str.isdigit(dec):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    dec = int(dec)
    cardi, ok = getcard(update.effective_chatid)
    if not ok:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Can't find card.")
        return False
    cardi, hintmsg = createcard.choosedec(cardi, dec)
    writecards(CARDS_LIST)
    context.bot.send_message(chat_id=update.effective_chat.id, text=hintmsg)
    return True
    


setstrdec_handler = CommandHandler('setstrdec', setstrdec)
dispatcher.add_handler(setstrdec_handler)


def setcondec(update: Update, context: CallbackContext):
    if update.effective_chatid < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set CON decrease.")
        return False
    dec = context.args[0]
    dec = dec.strip()
    if str.isdigit(dec):
        dec = int(dec)
        for i in range(CARDS_LIST):
            if CARDS_LIST[i]["user"]["userid"] == update.effective_chat.id:
                CARDS_LIST[i], hintmsg = createcard.choosedec2(
                    CARDS_LIST[i], dec)
                writecards(CARDS_LIST)
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=hintmsg)
                return True
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Can't find card.")
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Invalid input.")
    return False


setcondec_handler = CommandHandler('setcondec', setcondec)
dispatcher.add_handler(setcondec_handler)



def setjob(update: Update, context: CallbackContext) -> bool: # Button
    pass


setjob_handler = CommandHandler('setjob', setjob)
dispatcher.add_handler(setjob_handler)


def addskill(update: Update, context: CallbackContext) -> bool:
    if update.effective_chatid < 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to set CON decrease.")
        return False
    card1, ok = getcard(update.effective_chat.id)
    if not ok:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Can't find card.")
        return False
    skillname = context.args[0]
    skillvalue = context.args[1]
    if not str.isdigit(skillvalue):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid input.")
    skillvalue=int(skillvalue)
    if skillvalue > card1["skill"]["points"]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="You don't have so many points.")
        return False
    if skillname in SKILL_DICT:
        card1["skill"][skillname] = SKILL_DICT[skillname]+skillvalue
    else:
        card1["skill"][skillname] = skillvalue
    card1["skill"]["points"] -= skillvalue


# start game

def startgame(update: Update, context: CallbackContext) -> bool: # 有KP，且所有卡准备完成时，由KP开始游戏。如果需要更改一些信息，用/abortgame
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game can only be started in a group.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="This group does not have a KP.")
        return False
    if update.message.from_user.id!=GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can start a game.")
        return False
    global CARDS_LIST, ON_GAME
    gamecards = []
    for i in range(CARDS_LIST):
        if CARDS_LIST[i]["group"]["groupid"] == update.effective_chat.id:
            if not createcard.checkcard(CARDS_LIST[i]):
                context.bot.send_message(chat_id=update.effective_chat.id, text="Card id: "+str(i)+" is not ready to play.")
                return False
            gamecards.append(copy.deepcopy(CARDS_LIST[i]))
    ON_GAME.append(GroupGame(groupid=update.effective_chat.id, kpid=GROUP_KP_DICT[str(update.effective_chatid)], cards=gamecards))
    return True


startgame_handler = CommandHandler('startgame', startgame)
dispatcher.add_handler(startgame_handler)


def abortgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Game can only be aborted in a group.")
        return False
    if str(update.effective_chat.id) in GROUP_KP_DICT and update.message.from_user.id!=GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can abort a game.")
        return False
    global ON_GAME
    for i in range(ON_GAME):
        if ON_GAME[i].groupid == update.effective_chat.id:
            t = ON_GAME[i]
            ON_GAME=ON_GAME[:i]+ON_GAME[i+1:]
            del t
            context.bot.send_message(chat_id=update.effective_chat.id, text="Game aborted.")
            return True
    context.bot.send_message(chat_id=update.effective_chat.id, text="Game not found.")
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
    if update.message.from_user.id!=GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Only KP can end a game.")
        return False
    global ON_GAME
    for i in range(ON_GAME):
        if ON_GAME[i].groupid == update.effective_chat.id:
            t = ON_GAME[i]
            ON_GAME=ON_GAME[:i]+ON_GAME[i+1:]
            gamecards = t.cards
            for i in range(gamecards):
                for j in range(CARDS_LIST):
                    if gamecards[i]["player"]["playerid"] == CARDS_LIST[j]["player"]["playerid"]:
                        CARDS_LIST[j] = gamecards[i]
                        CARDS_LIST[j]["player"] = {} # 解绑
                        CARDS_LIST[j]["group"] = {} # 解绑
                        break
            del t
            context.bot.send_message(chat_id=update.effective_chat.id, text="Game end!")
            return True
    context.bot.send_message(chat_id=update.effective_chat.id, text="Game not found.")
    return False
    

endgame_handler = CommandHandler('endgame', endgame)
dispatcher.add_handler(endgame_handler)


def findgame(gpid: int) -> tuple(GroupGame, bool):
    global ON_GAME
    for i in range(ON_GAME):
        if ON_GAME[i].groupid == gpid:
            return ON_GAME[i], True
    return None, False


def findgamewithkpid(kpid: int) -> tuple(GroupGame, bool):
    global ON_GAME
    for i in range(ON_GAME):
        if ON_GAME[i].kpid == kpid:
            return ON_GAME[i], True
    return None, False


def findcardfromgame(game: GroupGame, plid: int) -> tuple(dict, bool):
    for i in game.cards:
        if game.cards[i]["player"]["playerid"] == plid:
            return game.cards[i], True
    return None, False


def switchcard(update: Update, context: CallbackContext):
    game, ok = findgamewithkpid(update.message.from_user.id)
    if not ok:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Game not found.")
        return False
    num = context.args[0]
    if not str.isdigit(num):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid input.")
        return False
    num = int(num)
    if num >=len(game.kpcards):
        context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have so many card.")
        return False
    game.kpctrl = num
    context.bot.send_message(chat_id=update.effective_chat.id, text="Switched to card "+str(num)+", card name is: "+ game.kpcards[num]["info"]["name"])
    return True


switchcard_handler = CommandHandler('switchcard', switchcard)
dispatcher.add_handler(switchcard_handler)


def roll(update: Update, context: CallbackContext):
    dicename = context.args[0] # 只接受第一个空格前的参数。dicename可能是技能名，可能是3d6，可能是1d4+2d10。骰子环境可能是游戏中，游戏外。需要考虑多个情况
    if update.effective_chat.id<0: # Group msg
        game, ok = findgame()
        if not ok or dicename.find('d')>=0:
            rttext = botdice.commondice(dicename)
            context.bot.send_message(chat_id=update.effective_chat.id, text=rttext)
            if rttext == "Invalid input.":
                return False
            return True
        senderid = update.message.from_user.id
        gpid = update.effective_chat.id
        if senderid!=GROUP_KP_DICT[str(update.effective_chat.id)]:
            gamecard, ok = findcardfromgame(game, senderid)
        elif game.kpctrl == -1:
            pass
            return False
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
    rttext = botdice.commondice(dicename) # private msg
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
    updater.start_polling()
