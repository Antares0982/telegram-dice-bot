# -*- coding:utf-8 -*-

# Only define handlers and dicts that store info
from os import write
import time
import copy
from cryptography.hazmat.backends import interfaces
from telegram import Update, Chat, Bot, replymarkup
from typing import Dict, List
from telegram.ext import Updater, CallbackContext, CallbackQueryHandler
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

from telegram.games.game import Game

from gameclass import *
from botdicts import *
import botdice
import createcard


if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
                      'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)

dispatcher = updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


global GROUP_KP_DICT, CARDS_LIST, ON_GAME
GROUP_KP_DICT: Dict[str, int]
CARDS_LIST: List[GameCard]
ON_GAME: List[GroupGame]

# read all dicts from file. Initialize the bot service
try:
    GROUP_KP_DICT, CARDS_LIST, ON_GAME = readinfo()
except:
    updater.bot.send_message(
        chat_id=USERID, text="Something went wrong, please check json files!")
    exit()
else:
    updater.bot.send_message(chat_id=USERID, text="Bot is live!")
DETAIL_DICT: Dict[int, str] = {}  # temply stores details

SKILL_DICT: dict = readskilldict()
JOB_DICT: dict = createcard.JOB_DICT


def isprivatemsg(update: Update) -> bool:
    if update.effective_chat.id > 0:
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
    if isprivatemsg(update):  # private
        return searchifkp(update.effective_chat.id)
    # if groupmsg, return if msg sender is kp
    if str(update.effective_chat.id) not in GROUP_KP_DICT or GROUP_KP_DICT[str(update.effective_chat.id)] != update.message.from_user.id:
        return False
    return True


def getkpgroup(kpid: int) -> List[int]:
    ans = []
    for keys in GROUP_KP_DICT:  # key is str(groupid)
        if GROUP_KP_DICT[keys] == kpid:
            ans.append(int(keys))
    return ans


def start(update: Update, context: CallbackContext) -> bool:  # Only gives help
    if isprivatemsg(update):  # private message
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=HELP_TEXT)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def addkp(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to add KP.')
        return False
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    global GROUP_KP_DICT
    if str(gpid) in GROUP_KP_DICT:  # Should have no KP
        context.bot.send_message(
            chat_id=gpid, text='This group already has a KP, please delete KP with /delkp first.')
        return False

    GROUP_KP_DICT[str(gpid)] = kpid  # Add KP
    context.bot.send_message(
        chat_id=gpid, text="Bind group (id): " + str(gpid) + " with KP (id): " + str(kpid))
    writekpinfo(GROUP_KP_DICT)  # Write into files
    return True


addkp_handler = CommandHandler('addkp', addkp)
dispatcher.add_handler(addkp_handler)


def delkp(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='Send group message to delete KP.')
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:  # Should have a KP
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='This group does not have a KP.')
        return False
    # Sender should be KP
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='You are not KP.')
        return False
    GROUP_KP_DICT.pop(str(update.effective_chat.id))  # Delete key
    writekpinfo(GROUP_KP_DICT)  # Write into files
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
    time.sleep(1)  # Wait for 1 sec
    return True


reload_handler = CommandHandler('reload', reload)
dispatcher.add_handler(reload_handler)


def showuserlist(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):  # Group msg: do nothing, even sender is USER or KP
        return False
    if update.effective_chat.id == USERID:  # private msg
        rttext = "GROUP_KP_LIST:\n"
        if not GROUP_KP_DICT:
            rttext += "None"
        else:
            for keys in GROUP_KP_DICT:
                rttext += keys + ": "+str(GROUP_KP_DICT[keys])+"\n"
        update.message.reply_text(rttext)
        if len(CARDS_LIST) == 0:
            update.message.reply_text("CARDS: None")
        else:
            update.message.reply_text("CARDS:")
            for i in range(len(CARDS_LIST)):
                time.sleep(0.1)
                update.message.reply_text(json.dumps(
                    CARDS_LIST[i].__dict__, indent=4, ensure_ascii=False))
        time.sleep(0.1)
        rttext = "Game Info:\n"
        if len(ON_GAME) == 0:
            rttext += "None"
        else:
            for i in range(len(ON_GAME)):
                rttext += str(ON_GAME[i].groupid) + \
                    ": " + str(ON_GAME[i].kpid)+"\n"
        update.message.reply_text(rttext)
        return True
    if isfromkp(update):  # private msg
        kpid = update.effective_chat.id
        gpids = getkpgroup(kpid)
        for gpid in gpids:
            if len(CARDS_LIST) == 0:
                update.message.reply_text("Group: "+str(gpid)+"\nCARDS: None")
            else:
                update.message.reply_text("Group: "+str(gpid)+"\nCARDS:")
                for i in range(len(CARDS_LIST)):
                    if CARDS_LIST[i].groupid == gpid:
                        update.message.reply_text(json.dumps(
                            CARDS_LIST[i].__dict__, indent=4, ensure_ascii=False))
        for i in range(len(ON_GAME)):
            if ON_GAME[i].kpid == kpid:
                update.message.reply_text(
                    "Group: "+str(ON_GAME[i].groupid)+"is in a game.")
        return True
    context.bot.send_message(  # Private msg and unauthorized
        chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
    return False


showuserlist_handler = CommandHandler('showuserlist', showuserlist)
dispatcher.add_handler(showuserlist_handler)


def getid(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(parse_mode='HTML', chat_id=update.effective_chat.id,
                             text="<code>"+str(update.effective_chat.id)+"</code> \nClick to copy")
    return update.effective_chat.id


getid_handler = CommandHandler('getid', getid)
dispatcher.add_handler(getid_handler)


def newcard(update: Update, context: CallbackContext):
    plid = update.effective_chat.id
    if isgroupmsg(update):  # Shoule be private msg
        context.bot.send_message(
            chat_id=plid, text="Send private message to generate new card.")
        return False
    if len(context.args) == 0:
        context.bot.send_message(
            chat_id=plid, text="Use '/newcard groupid' to generate card. If you don't know groupid, send /getid in your game group.")
        return False
    msg = context.args[0]
    if not botdice.isint(msg):
        context.bot.send_message(
            chat_id=plid, text="Invalid input. Use '/newcard groupid' to generate card.")
        return False
    global CARDS_LIST, DETAIL_DICT
    gpid = int(msg)
    new_card, detailmsg = createcard.generateNewCard(plid, gpid)
    DETAIL_DICT[plid] = detailmsg
    new_card.id = len(CARDS_LIST)
    context.bot.send_message(
        chat_id=plid, text="Card generated. Use /details to see detailed info.")
    countless50 = 0
    for keys in new_card.data:
        if new_card.data[keys] < 50:
            countless50 += 1
    if countless50 >= 3:
        new_card.discard = True
        context.bot.send_message(
            chat_id=plid, text="If you want, use /discard to delete this card. After setting age you cannot delete this card.")
    context.bot.send_message(
        chat_id=plid, text="Long press /setage and type a number to set AGE. If you need help, use /createcardhelp to read help.")
    CARDS_LIST.append(new_card)
    writecards(CARDS_LIST)
    return True


newcard_handler = CommandHandler('newcard', newcard)
dispatcher.add_handler(newcard_handler)


def discard(update: Update, context: CallbackContext):
    if isgroupmsg(update):  # should be private
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Send private message to discard.")
        return False
    global CARDS_LIST
    plid = update.effective_chat.id  # sender
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].playerid == plid and CARDS_LIST[i].discard == True:
            CARDS_LIST = CARDS_LIST[:i]+CARDS_LIST[i+1:]
            j = i
            update.message.reply_text("Card deleted.")
            while j < len(CARDS_LIST):
                CARDS_LIST[j].id -= 1
                j += 1
            writecards(CARDS_LIST)
            return True
        elif CARDS_LIST[i].playerid == plid:
            update.message.reply_text(
                "Card does not meet the condition to be deleted. Please contact KP to delete this card.")
            return False
    update.message.reply_text("Can't find card.")
    return False


discard_handler = CommandHandler('discard', discard)
dispatcher.add_handler(discard_handler)


def details(update: Update, context: CallbackContext):
    global DETAIL_DICT
    if update.effective_chat.id not in DETAIL_DICT or DETAIL_DICT[update.effective_chat.id] == "":
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Nothing to show.")
        return False
    update.message.reply_text(DETAIL_DICT[update.effective_chat.id])
    DETAIL_DICT[update.effective_chat.id] = ""
    return True


details_handler = CommandHandler('details', details)
dispatcher.add_handler(details_handler)


def getcard(plid: int) -> Tuple[GameCard, bool]:
    global CARDS_LIST
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].playerid == plid:
            return CARDS_LIST[i], True
    return None, False


def setage(update: Update, context: CallbackContext):
    if isgroupmsg(update):  # should be private
        update.message.reply_text("Send private message to set AGE.")
        return False
    if len(context.args) == 0:
        update.message.reply_text("Use '/setage AGE' to set AGE.")
        return False
    age = context.args[0]
    if not botdice.isint(age):
        update.message.reply_text("Invalid input.")
        return False
    age = int(age)
    cardi, ok = getcard(update.effective_chat.id)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if "AGE" in cardi.info and cardi.info["AGE"] > 0:
        update.message.reply_text("Age is already set.")
        return False
    if age < 17 or age > 99:
        update.message.reply_text("Age should be 17-99.")
        return False
    global DETAIL_DICT
    cardi.info["AGE"] = age
    cardi.cardcheck["check1"] = True
    cardi, detailmsg = createcard.generateAgeAttributes(cardi)
    DETAIL_DICT[update.effective_chat.id] = detailmsg
    update.message.reply_text(
        "Age is set! To see more infomation, use /details. If age >= 40, you may need to set STR decrease using '/setstrdec number'.")
    if cardi.cardcheck["check2"]:
        createcard.generateOtherAttributes(cardi)
    writecards(CARDS_LIST)
    return True


setage_handler = CommandHandler('setage', setage)
dispatcher.add_handler(setage_handler)


def setstrdec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set STR decrease.")
        return False
    if len(context.args) == 0:
        update.message.reply_text(
            "Use '/setstrdec STRDEC' to set STR decrease.")
        return False
    plid = update.effective_chat.id
    global CARDS_LIST
    dec = context.args[0]
    if not botdice.isint(dec):
        update.message.reply_text("Invalid input.")
        return False
    dec = int(dec)
    cardi, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    cardi, hintmsg, needcon = createcard.choosedec(cardi, dec)
    if hintmsg == "输入无效":
        update.message.reply_text("Invalid input!")
        return False

    update.message.reply_text(hintmsg)
    if needcon:
        update.message.reply_text("Use /setcondec to set CON decrease.")
    else:
        createcard.generateOtherAttributes(cardi)
        update.message.reply_text("Use /setjob to set job.")
    writecards(CARDS_LIST)
    return True


setstrdec_handler = CommandHandler('setstrdec', setstrdec)
dispatcher.add_handler(setstrdec_handler)


def setcondec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set CON decrease.")
        return False
    dec = context.args[0]
    if not botdice.isint(dec):
        update.message.reply_text("Invalid input.")
        return False
    dec = int(dec)
    plid = update.effective_chat.id
    cardi, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    cardi, hintmsg = createcard.choosedec2(cardi, dec)
    if hintmsg == "输入无效":
        update.message.reply_text("Invalid input!")
        return False
    createcard.generateOtherAttributes(cardi)
    writecards(CARDS_LIST)
    update.message.reply_text(hintmsg)
    return True


setcondec_handler = CommandHandler('setcondec', setcondec)
dispatcher.add_handler(setcondec_handler)


def getskilllevelfromdict(card1: GameCard, keys: str) -> int:
    if keys in SKILL_DICT:
        return SKILL_DICT[keys]
    if keys == "母语":
        return card1.data["EDU"]
    if keys == "闪避":
        return card1.data["DEX"]//2
    return -1


# Button. need 0-1 args, if len(args)==0, show button and listen
def setjob(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set job.")
        return False
    plid = update.effective_chat.id
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if "job" in card1.info:
        update.message.reply_text("Job is already set!")
        return False
    if len(context.args) == 0:
        rtbuttons = [[]]
        for keys in JOB_DICT:
            if len(rtbuttons[len(rtbuttons)-1]) == 3:
                rtbuttons.append([])
            rtbuttons[len(
                rtbuttons)-1].append(InlineKeyboardButton(keys, callback_data="job "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        # Then the task is given to func button()
        update.message.reply_text(
            "Please choose a job:", reply_markup=rp_markup)
        return True
    jobname = context.args[0]
    if not IGNORE_JOB_DICT and jobname not in JOB_DICT:
        update.message.reply_text("This job is not allowed!")
        return False
    if jobname not in JOB_DICT:
        update.message.reply_text(
            "This job is not in joblist, you can use '/addskill skillname points (main/interest)' to choose skills you like! If interest is appended, the skill will cost interest points.")
        card1.skill["points"] = int(card1.data["EDU"]*4)
        writecards(CARDS_LIST)
        return True
    for i in range(3, len(JOB_DICT[jobname])): # Classical jobs
        card1.suggestskill[JOB_DICT[jobname][i]] = getskilllevelfromdict(card1, JOB_DICT[jobname][i])  # int
    update.message.reply_text(
        "Skill suggestions generated. Use /addskill to add skills.")
    if not createcard.generatePoints(card1, jobname): # This trap should not be hit
        update.message.reply_text(
            "Some error occured when generating skill points!")
        return False
    writecards(CARDS_LIST)
    return True


setjob_handler = CommandHandler('setjob', setjob)
dispatcher.add_handler(setjob_handler)


def addmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    if card1.skill["points"] == 0:
        update.message.reply_text("You don't have any main skill points left!")
        return False
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(getskilllevelfromdict(card1, skillname)+card1.skill["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.skill["points"] -= skillvalue - getskilllevelfromdict(card1, skillname)
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - getskilllevelfromdict(card1, skillname)))
    card1.skill[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True


def addsgskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    if not addmainskill(skillname, skillvalue, card1, update):
        return False
    card1.suggestskill.pop(skillname)
    writecards(CARDS_LIST)
    return True



def addintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    if card1.interest["points"] == 0:
        update.message.reply_text(
            "You don't have any interest skill points left!")
        return False
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(getskilllevelfromdict(card1, skillname)+card1.interest["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.interest["points"] -= skillvalue - getskilllevelfromdict(card1, skillname)
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - getskilllevelfromdict(card1, skillname)))
    card1.interest[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True


def cgmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool: # Change main skill level
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(card1.skill[skillname]+card1.skill["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.skill["points"] -= skillvalue - card1.skill[skillname]
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - card1.skill[skillname]))
    card1.skill[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True


def cgintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool: # Change interest skill level
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(card1.interest[skillname]+card1.interest["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.interest["points"] -= skillvalue - card1.interest[skillname]
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - card1.interest[skillname]))
    card1.interest[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True

def addcredit(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    update.message.reply_text("Please set 信用 first!")
    if card1.info["job"] in JOB_DICT:
        m = JOB_DICT[card1.info["job"]][0]
        mm = JOB_DICT[card1.info["job"]][1]
    else:
        m = 5
        mm = 99
    rtbuttons = makeIntButtons(m, mm, "addmainskill", "信用")
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("Add main skill, skill name is: 信用", reply_markup=rp_markup)
    return True

def addskill0(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    rtbuttons = [[]]
    # If skill["points"] is 0, turn to interest.
    if card1.skill["points"] > 0: # Then it must be main skill. After all main skills are added, add interest skills.
        if not card1.suggestskill: # Increase skills already added, because sgskill is empty
            # GOOD TRAP: cgmainskill
            for keys in card1.skill:
                if keys == "points":
                    continue
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+
                                                                        ": "+str(card1.skill[keys]), callback_data="cgmainskill "+keys))
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            update.message.reply_text("You have points:"+str(
                card1.skill["points"])+"\nPlease choose a skill to increase:", reply_markup=rp_markup)
            return True
        # GOOD TRAP: addsgskill
        for keys in card1.suggestskill:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.suggestskill[keys]), callback_data="addsgskill "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("You have points:"+str(
            card1.skill["points"])+"\nPlease choose a main skill:", reply_markup=rp_markup)
        return True
    # turn to interest.
    if card1.interest["points"] <= 0: # HIT BAD TRAP
        update.message.reply_text("You don't have any points left!")
        return False
    # GOOD TRAP: add interest skill. 
    if "母语" not in card1.skill:
        if "母语" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton("母语: "+str(card1.interest["母语"]), callback_data="cgintskill "+"母语"))
        else:
            rtbuttons[0].append(InlineKeyboardButton("母语: "+str(getskilllevelfromdict(card1, "母语")), callback_data="cgintskill "+"母语"))
    if "闪避" not in card1.skill:
        if "闪避" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton("闪避: "+str(card1.interest["闪避"]), callback_data="cgintskill "+"闪避"))
        else:
            rtbuttons[0].append(InlineKeyboardButton("闪避: "+str(getskilllevelfromdict(card1, "闪避")), callback_data="cgintskill "+"闪避"))
    for keys in SKILL_DICT:
        if keys in card1.skill or keys in card1.suggestskill or keys == "克苏鲁神话":
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if keys in card1.interest:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": "+str(card1.interest[keys]), callback_data="cgintskill "+keys))
        else:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": "+str(getskilllevelfromdict(card1, keys)), callback_data="addintskill "+keys))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("You have points:"+str(
        card1.interest["points"])+"\nPlease choose a interest skill:", reply_markup=rp_markup)
    return True

def makeIntButtons(lower: int, upper: int,keystr1: str, keystr2: str, step: int = 10, column: int = 4) -> List[list]:
    rtbuttons = [[]]
    if (lower//step)*step != lower:
        rtbuttons[0].append(InlineKeyboardButton(str(lower), callback_data=keystr1+" "+keystr2+" "+str(lower)))
    t = step+(lower//step)*step
    for i in range(t, upper, step):
        if len(rtbuttons[len(rtbuttons)-1]) == column:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(i), callback_data=keystr1+" "+keystr2+" "+str(i)))
    if (upper//step)*step != upper:
        if len(rtbuttons[len(rtbuttons)-1]) == column:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(upper), callback_data=keystr1+" "+keystr2+" "+str(upper)))
    return rtbuttons

def addskill1(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    # skillname is already checked if in SKILL_DICT
    # First search if args skillname in skill or suggestskill.
    # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
    # Show button for numbers
    skillname = context.args[0]
    m = getskilllevelfromdict(card1, skillname)
    if skillname in card1.skill: # GOOD TRAP: cgmainskill
        mm = card1.skill["points"]+card1.skill[skillname]
        rtbuttons = makeIntButtons(m, min(99, mm), "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Change skill level, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.suggestskill: # GOOD TRAP: addsgskill
        mm = card1.skill["points"] + m
        rtbuttons = makeIntButtons(m, min(99, mm), "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Add suggested skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.interest: # GOOD TRAP: cgintskill
        mm = card1.interest["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Change interest skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if card1.skill["points"] > 0: # GOOD TRAP: addmainskill
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), "addmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Add main skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    # GOOD TRAP: addintskill
    mm = card1.interest["points"]+m
    rtbuttons = makeIntButtons(m, min(99, mm), "addintskill", skillname)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("Add interest skill, skill name is: "+skillname, reply_markup=rp_markup)
    return True


def addskill2(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    skillname = context.args[0]
    skillvalue = int(context.args[1])
    if skillname in card1.skill:  # Change skill level.
        if not cgmainskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if skillname in card1.suggestskill:
        if not addsgskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if skillname in card1.interest:  # Change skill level.
        if not cgintskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    # If cannot judge which skill is, one more arg is needed. Then turn to addskill3()
    if card1.skill["points"] > 0 and card1.interest["points"] > 0:
        update.message.reply_text(
            "Please use '/addskill skillname skillvalue main/interest' to specify!")
        return False
    # HIT GOOD TRAP
    if card1.skill["points"] > 0:
        if not addmainskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if not addintskill(skillname, skillvalue, card1, update):
        return False
    writecards(CARDS_LIST)
    return True


def addskill3(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    skillname = context.args[0]
    skillvalue = int(context.args[1])
    if context.args[2] != "interest" or context.args[2] != "main":
        update.message.reply_text(
            "Is it an interest/main skill? Please specify.")
        return False
    if context.args[2] == "interest" and (skillname in card1.suggestskill or skillname in card1.skill):
        update.message.reply_text("This is a main skill.")
        return False
    if context.args[2] == "main" and skillname in card1.interest:
        update.message.reply_text("This is a main skill.")
        return False
    # HIT GOOD TRAP
    # This means arg3 is "interest". Change skill level.
    if skillname in card1.interest:
        if not cgintskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if skillname in card1.suggestskill:  # Add suggest skill
        if not addsgskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if skillname in card1.skill:  # Change skill level.
        if not cgmainskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if context.args[2] == "main":
        if not addmainskill(skillname, skillvalue, card1, update):
            return False
        writecards(CARDS_LIST)
        return True
    if not addintskill(skillname, skillvalue, card1, update):
        return False
    writecards(CARDS_LIST)
    return True

def basicskillcheck(card1: GameCard) -> int:
    if "母语" in card1.suggestskill:
        return 1
    if "母语" not in card1.skill and "母语" not in card1.interest:
        return 2
    if "闪避" in card1.suggestskill:
        return 3
    if "闪避" not in card1.skill and "闪避" not in card1.interest:
        return 4
    return 0


def setbasicskill(update: Update, context: CallbackContext, card1: GameCard, skillchecktype: int) -> bool:
    if skillchecktype == 1:
        update.message.reply_text("Please add suggested skill '母语' first!")


# Button. need 0-3 args, if len(args)==0 or 1, show button and listen; if len(args)==3, the third should be "interest/main" to give interest skills
# Compicated
def addskill(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):
        update.message.reply_text("Send private message to add skill.")
        return False
    plid = update.effective_chat.id
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if card1.skill["points"] == -1:
        update.message.reply_text(
            "Info not complete. Not allowed to add skill now.")
        return False
    if card1.skill["points"] == 0 and card1.interest["points"] == 0:
        if len(context.args) == 0 or (context.args[0] not in card1.skill and context.args[0] not in card1.interest):
            update.message.reply_text("You don't have any points left!")
            return False
    if "job" not in card1.info:
        update.message.reply_text("Please set job first.")
        return False
    if "信用" not in card1.skill:
        if addcredit(update, context, card1):
            return True
        return False
    if len(context.args) == 0:  # HIT GOOD TRAP
        if addskill0(update, context, card1):
            return True
        return False
    skillname = context.args[0]
    if skillname != "母语" and skillname != "闪避" and (skillname not in SKILL_DICT or skillname == "克苏鲁神话"):  # HIT BAD TRAP
        update.message.reply_text("This skill is not allowed.")
        return False
    if len(context.args) == 1:  # HIT GOOD TRAP
        return addskill1(update, context, card1) # This function only returns True
    skillvalue = context.args[1]
    if not botdice.isint(skillvalue):
        update.message.reply_text("Invalid input.")
    skillvalue = int(skillvalue)
    if len(context.args) >= 3:  # No buttons
        # HIT GOOD TRAP
        if addskill3(update, context, card1):
            return True
        return False
    if addskill2(update, context, update):
        return True
    return False


addskill_handler = CommandHandler('addskill', addskill)
dispatcher.add_handler(addskill_handler)


def button(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        return False
    plid = update.effective_chat.id
    query = update.callback_query
    query.answer()
    args = query.data.split(" ")
    card1, ok = getcard(plid)
    if not ok:
        query.edit_message_text(text="Can't find card.")
        return False
    # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
    if args[0]=="job":  # Job in buttons must be classical
        jobname = args[1]
        card1.info["job"] = jobname
        query.edit_message_text(
            text="Job is set to "+jobname+", now you can choose skills using /addskill.")
        if not createcard.generatePoints(card1, jobname):
            context.bot.send_message(
                chat_id=plid, text="Some error occured when generating skill points!")
            return False
        for i in range(3, len(JOB_DICT[jobname])):  # Classical jobs
            card1.suggestskill[JOB_DICT[jobname][i]
                               ] = getskilllevelfromdict(card1, JOB_DICT[jobname][i])  # int
        writecards(CARDS_LIST)
        return True
    # Increase skills already added, because sgskill is none. second arg is skillname
    if args[0]=="addmainskill":
        if len(args)==3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("Add main skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0]=="cgmainskill":
        if len(args)==3:
            skvalue = int(args[2])
            needpt = skvalue - card1.skill[args[1]]
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+card1.skill[args[1]]
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("Change main skill level, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0]=="addsgskill":
        if len(args)==3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            card1.suggestskill.pop(args[1])
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("Add suggested skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0]=="addintskill":
        if len(args)==3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.interest[args[1]] = skvalue
            card1.interest["points"] -= needpt
            query.edit_message_text(text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.interest["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("Add interest skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0]=="cgintskill":
        if len(args)==3:
            skvalue = int(args[2])
            needpt = skvalue - card1.interest[args[1]]
            card1.interest[args[1]] = skvalue
            card1.interest["points"] -= needpt
            query.edit_message_text(text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        try:
            mm = card1.interest["points"]+card1.interest[args[1]]
        except:
            card1.interest[args[1]] = m
            mm = card1.interest["points"]+m
            writecards(CARDS_LIST)
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("Change interest skill level, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    # HIT BAD TRAP
    return False


dispatcher.add_handler(CallbackQueryHandler(button))


def setname(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):
        update.message.reply_text("Please send private message to set name.")
        return False
    plid = update.effective_chat.id
    if len(context.args) == 0:
        update.message.reply_text("Please use '/setname NAME' to set name.")
        return False
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    card1.info["name"] = context.args[0]
    update.message.reply_text("Name is set to: "+context.args[0]+".")
    card1.cardcheck["check5"] = True
    writecards(CARDS_LIST)
    return True

setname_handler = CommandHandler('setname', setname)
dispatcher.add_handler(setname_handler)


# game
# 有KP，且所有卡准备完成时，由KP开始游戏。如果需要更改一些信息，用/abortgame


def startgame(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        update.message.reply_text("Game can only be started in a group.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        update.message.reply_text("This group does not have a KP.")
        return False
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        update.message.reply_text("Only KP can start a game.")
        return False
    kpid = update.message.from_user.id
    global CARDS_LIST, ON_GAME
    for games in ON_GAME:
        if games.kpid == kpid:
            update.message.reply_text("A KP can only start ONE game at the same time.")
    gamecards = []
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].groupid == update.effective_chat.id:
            cardcheckinfo = createcard.showchecks(CARDS_LIST[i])
            if cardcheckinfo != "All pass.":
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text="Card id: "+str(i)+" is not ready to play. Because:\n"+cardcheckinfo)
                return False
            gamecards.append(copy.deepcopy(CARDS_LIST[i]))
    ON_GAME.append(GroupGame(groupid=update.effective_chat.id,
                             kpid=GROUP_KP_DICT[str(update.effective_chat.id)], cards=gamecards))
    writegameinfo(ON_GAME)
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
            writegameinfo(ON_GAME)
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
                    if gamecards[i].playerid == CARDS_LIST[j].playerid:
                        CARDS_LIST[j] = gamecards[i]
                        CARDS_LIST[j].formerplayerid = CARDS_LIST[j].playerid
                        CARDS_LIST[j].playerid=0  # 解绑
                        CARDS_LIST[j].formergroupid = CARDS_LIST[j].groupid
                        CARDS_LIST[j].groupid=0  # 解绑
                        break
            del t
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Game end!")
            writegameinfo(ON_GAME)
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
        if game.cards[i].playerid == plid:
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
                             str(num)+", card name is: " + game.kpcards[num].info["name"])
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
    writegameinfo(ON_GAME)
    return True


tempcheck_handler = CommandHandler('tempcheck', tempcheck)
dispatcher.add_handler(tempcheck_handler)


def roll(update: Update, context: CallbackContext):
    # 只接受第一个空格前的参数。dicename可能是技能名，可能是3d6，可能是1d4+2d10。骰子环境可能是游戏中，游戏外。需要考虑多个情况
    if len(context.args) == 0:
        update.message.reply_text(botdice.commondice("1d100"))  # 骰1d100
        return True
    dicename = context.args[0]
    if isgroupmsg(update): # Group msg
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
            test = gamecard.skill[dicename]
        elif dicename == "母语":
            test = gamecard.data["EDU"]
        elif dicename == "闪避":
            test = gamecard.data["DEX"]//2
        elif dicename in gamecard.data:
            test = gamecard.data[dicename]
        elif dicename == "力量":
            dicename = "STR"
            test = gamecard.data[dicename]
        elif dicename == "体质":
            dicename = "CON"
            test = gamecard.data[dicename]
        elif dicename == "体型":
            dicename = "SIZ"
            test = gamecard.data[dicename]
        elif dicename == "敏捷":
            dicename = "DEX"
            test = gamecard.data[dicename]
        elif dicename == "外貌":
            dicename = "APP"
            test = gamecard.data[dicename]
        elif dicename == "智力":
            dicename = "INT"
            test = gamecard.data[dicename]
        elif dicename == "意志":
            dicename = "POW"
            test = gamecard.data[dicename]
        elif dicename == "教育":
            dicename = "EDU"
            test = gamecard.data[dicename]
        elif dicename == "幸运":
            dicename = "LUCK"
            test = gamecard.data[dicename]
        else: # HIT BAD TRAP
            update.message.reply_text("Invalid input.")
            return False
        if "global" in gamecard["tempstatus"]:
            test += gamecard.tempstatus["global"]
        if dicename in gamecard["tempstatus"]:
            test += gamecard.tempstatus["global"]
        test += tpcheck
        testval = botdice.dicemdn(1,100)
        rttext = "检定："+dicename+" "+str(testval)+"/"+str(test)+" "
        if (test<50 and testval>95) or (test>=50 and testval==100):
            rttext += "大失败"
        elif testval ==1:
            rttext += "大成功"
        elif testval > test:
            rttext += "失败"
        elif testval > test//2:
            rttext += "普通成功"
        elif testval > test//5:
            rttext += "困难成功"
        else:
            rttext += "极难成功"
        update.message.reply_text(rttext)
        return True
    rttext = botdice.commondice(dicename)  # private msg
    context.bot.send_message(chat_id=update.effective_chat.id, text=rttext)
    if rttext == "Invalid input.":
        return False
    return True


roll_handler = CommandHandler('roll', roll)
dispatcher.add_handler(roll_handler)

def showcardinfo(card1:GameCard) -> str:
    rttext = json.dumps(card1.__dict__, separators=("\n",":"))
    rttext=rttext[1:-1]
    rttext.replace("{","\n")
    rttext.replace("}","\n")
    return rttext


def findkpcards(kpid) -> List[GameCard]:
    ans = []
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].playerid == kpid and GROUP_KP_DICT[str(CARDS_LIST[i].groupid)]==kpid:
            ans.append(CARDS_LIST[i])
    return ans

def showattrinfo(update: Update, card1: GameCard, attrname: str) -> bool:
    if attrname in card1.__dict__:
        ans = card1.__dict__[attrname]
        rttext = ""
        if isinstance(ans, dict):
            for keys in ans:
                rttext += keys+": "+str(ans[keys])
        else:
            rttext = str(ans)
        update.message.reply_text(rttext)
        return True
    for keys in card1.__dict__:
        if isinstance(card1.__dict__[keys], dict):
            if attrname in card1.__dict__[keys]:
                update.message.reply_text(str(card1.__dict__[keys][attrname]))
                return True
    update.message.reply_text("Can't find this attribute of card!")
    return False


def show(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update): # Should not return game info
        if len(context.args) == 0:
            plid = update.effective_chat.id
            card1, ok = getcard(plid)
            if not ok:
                update.message.reply_text("Can't find card. If you are kp, please use '/show kp'.")
                return False
            update.message.reply_text(showcardinfo(card1))
            return True
        attrname = context.args[0]
        if attrname == "kp":
            kpid = update.effective_chat.id
            cards = findkpcards(kpid)
            if len(cards) == 0:
                update.message.reply_text("You have no cards as a kp.")
                return False
            for i in range(len(cards)):
                update.message.reply_text(showcardinfo(cards[i]))
            return True
        plid = update.effective_chat.id
        card1, ok = getcard(plid)
        if not ok:
            update.message.reply_text("Can't find card.")
            return False
        if not showattrinfo(update, card1, attrname):
            return False
        return True
    # Group msg, ON_GAME is needed
    gpid = update.effective_chat.id
    senderid = update.message.from_user.id
    game,ok = findgame(gpid)
    if not ok:
        update.message.reply_text("Can't find game, please send private message to show card info.")
        return False
    if GROUP_KP_DICT[str(gpid)] == senderid: # KP
        if len(context.args)==0:
            update.message.reply_text("Cannot show all info in a group.")
            return False
        attrname = context.args[0]
        if game.kpctrl == -1:
            update.message.reply_text("No card choosen. Use /switchcard to switch card.")
            return False
        if not showattrinfo(update, game.kpcards[game.kpctrl], attrname):
            return False
        return True
    card1, ok = findcardfromgame(game, senderid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if len(context.args) == 0:
        update.message.reply_text(showcardinfo(card1))
        return True
    attrname = context.args[0]
    if not showattrinfo(update, game.kpcards[game.kpctrl], attrname):
        return False
    return True


show_handler = CommandHandler('show', show)
dispatcher.add_handler(show_handler)


# def showgamecard(update: Update, context: CallbackContext) -> bool:
#     pass


# showgamecard_handler = CommandHandler('showgamecard', showgamecard)
# dispatcher.add_handler(showgamecard_handler)

def showids(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):
        update.message.reply_text("Send private message to see IDs.")
        return False
    if not isfromkp(update):
        update.message.reply_text("Not authorized.")
        return False
    kpid = update.effective_chat.id
    game, ok = findgamewithkpid(kpid)
    if not ok:
        cards = CARDS_LIST
    else:
        cards = game.cards
    rttext = ""
    for cardi in cards:
        if GROUP_KP_DICT[str(cardi.groupid)] == kpid:
            rttext += cardi.info["name"]+": "+str(cardi.id)
    update.message.reply_text(rttext)
    return True


showids_handler = CommandHandler('showids', showids)
dispatcher.add_handler(showids_handler)


def modify(update: Update, context: CallbackContext) -> bool:
    if not isfromkp(update):
        update.message.reply_text("Not authorized.")
        return False
    # need 3 args, first: card id, second: attrname, third: value
    if len(context.args)<3:
        update.message.reply_text("Need more arguments.")
        return False
    card_id = context.args[0]
    if not botdice.isint(card_id):
        update.message.reply_text("Invalid id.")
        return False
    card_id = int(card_id)
    kpid = update.message.from_user.id
    game, ok = findgamewithkpid(kpid)
    if not ok:
        if card_id>=len(CARDS_LIST):
            update.message.reply_text("Invalid id.")
            return False
        card1 = CARDS_LIST[card_id]
        if str(card1.groupid) not in GROUP_KP_DICT or GROUP_KP_DICT[str(card1.groupid)]!=kpid:
            update.message.reply_text("Invalid id.")
            return False
    else:
        cards = game.cards
        card1 = ""
        for cardi in cards:
            if cardi.id == card_id:
                card1 = cardi
                break
        if isinstance(card1, str):
            update.message.reply_text("Invalid id.")
            return False
    # Now the valid card is found
    attrname = context.args[1]
    if attrname in card1.__dict__:
        if isinstance(card1.__dict__[attrname], dict):
            update.message.reply_text("Cannot edit dict.")
            return False
        if isinstance(card1.__dict__[attrname], bool):
            if context.args[2] in ["F", "false", "False"]:
                card1.__dict__[attrname] = False
            elif context.args[2] in ["T", "true", "True"]:
                card1.__dict__[attrname] = True
            else:
                update.message.reply_text("Invalid argument.")
                return False
            if ok:
                writegameinfo(ON_GAME)
            else:
                writecards(CARDS_LIST)
            return True
        if isinstance(card1.__dict__[attrname], int):
            if not botdice.isint(context.args[2]):
                update.message.reply_text("Invalid argument.")
                return False
            card1.__dict__[attrname] = int(context.args[2])
            if ok:
                writegameinfo(ON_GAME)
            else:
                writecards(CARDS_LIST)
            return True
        if isinstance(card1.__dict__[attrname], str):
            card1.__dict__[attrname] = context.args[2]
            if ok:
                writegameinfo(ON_GAME)
            else:
                writecards(CARDS_LIST)
            return True
        update.message.reply_text("Type error!!!")
        return False
    for keys in card1.__dict__:
        if isinstance(card1.__dict__[keys], dict):
            if attrname in card1.__dict__[keys]:
                getdict = card1.__dict__[keys]
                if isinstance(getdict[attrname], dict):
                    update.message.reply_text("Cannot edit dict.")
                    return False
                if isinstance(getdict[attrname], bool):
                    if context.args[2] in ["F", "false", "False"]:
                        getdict[attrname] = False
                    elif context.args[2] in ["T", "true", "True"]:
                        getdict[attrname] = True
                    else:
                        update.message.reply_text("Invalid argument.")
                        return False
                    if ok:
                        writegameinfo(ON_GAME)
                    else:
                        writecards(CARDS_LIST)
                    return True
                if isinstance(getdict[attrname], int):
                    if not botdice.isint(context.args[2]):
                        update.message.reply_text("Invalid argument.")
                        return False
                    getdict[attrname] = int(context.args[2])
                    if ok:
                        writegameinfo(ON_GAME)
                    else:
                        writecards(CARDS_LIST)
                    return True
                if isinstance(getdict[attrname], str):
                    getdict[attrname] = context.args[2]
                    if ok:
                        writegameinfo(ON_GAME)
                    else:
                        writecards(CARDS_LIST)
                    return True
                update.message.reply_text("Type error!!!")
                return False
    update.message.reply_text("Cannot find this attribute.")
    return False


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
