# -*- coding:utf-8 -*-
# Only define handlers and dicts that store info

import time
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Updater

from cfg import *
from botdicts import *
import botdice
import createcard

if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
                      'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)

global GROUP_KP_DICT, CARDS_LIST, ON_GAME

GROUP_KP_DICT: Dict[str, int]
CARDS_LIST: List[GameCard]
ON_GAME: List[GroupGame]

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

# returns all groupid in which kpid is a kp


def getkpgroup(kpid: int) -> List[int]:
    ans = []
    for keys in GROUP_KP_DICT:  # key is str(groupid)
        if GROUP_KP_DICT[keys] == kpid:
            ans.append(int(keys))
    return ans


def getcard(plid: int) -> Tuple[GameCard, bool]:
    global CARDS_LIST
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].playerid == plid:
            return CARDS_LIST[i], True
    return None, False


def getskilllevelfromdict(card1: GameCard, keys: str) -> int:
    if keys in SKILL_DICT:
        return SKILL_DICT[keys]
    if keys == "母语":
        return card1.data["EDU"]
    if keys == "闪避":
        return card1.data["DEX"]//2
    return -1


def makeIntButtons(lower: int, upper: int, keystr1: str, keystr2: str, step: int = 10, column: int = 4) -> List[list]:
    rtbuttons = [[]]
    if (lower//step)*step != lower:
        rtbuttons[0].append(InlineKeyboardButton(
            str(lower), callback_data=keystr1+" "+keystr2+" "+str(lower)))
    t = step+(lower//step)*step
    for i in range(t, upper, step):
        if len(rtbuttons[len(rtbuttons)-1]) == column:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(i),
                                                                callback_data=keystr1+" "+keystr2+" "+str(i)))
    if len(rtbuttons[len(rtbuttons)-1]) == column:
        rtbuttons.append([])
    rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(upper),
                                                            callback_data=keystr1+" "+keystr2+" "+str(upper)))
    return rtbuttons


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
        if i.playerid == plid:
            return i, True
    return None, False


def showcardinfo(card1: GameCard) -> str:  # show full card
    rttext = json.dumps(card1.__dict__, separators=(
        "\n", ":"), ensure_ascii=False)
    rttext = rttext[1:-1]
    rttext.replace("{", "\n")
    rttext.replace("}", "\n")
    return rttext


def findkpcards(kpid) -> List[GameCard]:
    ans = []
    for i in CARDS_LIST:
        if i.playerid == kpid and GROUP_KP_DICT[str(i.groupid)] == kpid:
            ans.append(i)
    return ans


def isadicename(dicename: str) -> bool:
    if not botdice.isint(dicename):
        a, b = dicename.split("d", maxsplit=1)
        if not botdice.isint(a) or not botdice.isint(b):
            return False
    return True


def start(update: Update, context: CallbackContext) -> bool:  # Only gives help
    if isprivatemsg(update):  # private message
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=HELP_TEXT)


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
    game, ok = findgame(gpid)
    if ok:
        game.kpid = kpid
        writegameinfo(ON_GAME)
    return True


def delkp(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        update.message.reply_text('Send group message to delete KP.')
        return False
    gpid = update.effective_chat.id
    if str(gpid) not in GROUP_KP_DICT:  # Should have a KP
        update.message.reply_text('This group does not have a KP.')
        return False
    # Sender should be KP
    if update.message.from_user.id != GROUP_KP_DICT[str(gpid)]:
        update.message.reply_text('You are not KP.')
        return False
    GROUP_KP_DICT.pop(str(gpid))  # Delete key
    writekpinfo(GROUP_KP_DICT)  # Write into files
    update.message.reply_text('KP deleted.')
    game, ok = findgame(gpid)
    if ok:
        game.kpid = 0
        writegameinfo(ON_GAME)
    return True


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


def getid(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(parse_mode='HTML', chat_id=update.effective_chat.id,
                             text="<code>"+str(update.effective_chat.id)+"</code> \nClick to copy")
    return update.effective_chat.id


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


def details(update: Update, context: CallbackContext):
    global DETAIL_DICT
    if update.effective_chat.id not in DETAIL_DICT or DETAIL_DICT[update.effective_chat.id] == "":
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Nothing to show.")
        return False
    update.message.reply_text(DETAIL_DICT[update.effective_chat.id])
    DETAIL_DICT[update.effective_chat.id] = ""
    return True


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


def setstrdec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set STR decrease.")
        return False
    plid = update.effective_chat.id
    cardi, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if len(context.args) == 0:
        if "STR_SIZ_M" in cardi.data:
            rtbuttons = makeIntButtons(max(0, 1 - cardi.data["SIZ"] - cardi.data["STR_SIZ_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_SIZ_M"]), "strdec", "", 1)
        elif "STR_CON_M" in cardi.data:
            rtbuttons = makeIntButtons(max(0, 1 - cardi.data["CON"] - cardi.data["STR_CON_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_CON_M"]), "strdec", "", 1)
        elif "STR_CON_DEX_M" in cardi.data:
            rtbuttons = makeIntButtons(max(0, 2 - cardi.data["CON"]-cardi.data["DEX"] - cardi.data["STR_CON_DEX_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_CON_DEX_M"]), "strdec", "", 1)
        else:
            update.message.reply_text("No need to set STR decrease.")
            return False
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Set STR decrease: ", reply_markup=rp_markup)
        return True
    global CARDS_LIST
    dec = context.args[0]
    if not botdice.isint(dec):
        update.message.reply_text("Invalid input.")
        return False
    dec = int(dec)
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


def setcondec(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set CON decrease.")
        return False
    plid = update.effective_chat.id
    cardi, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if len(context.args) == 0:
        if "CON_DEX_M" not in cardi.data:
            update.message.reply_text("No need to set STR decrease.")
            return False
        rtbuttons = makeIntButtons(max(0, 1 - cardi.data["DEX"] - cardi.data["CON_DEX_M"]), min(
            cardi.data["CON"]-1, -cardi.data["CON_DEX_M"]), "condec", "", 1)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Set CON decrease: ", reply_markup=rp_markup)
        return True
    dec = context.args[0]
    if not botdice.isint(dec):
        update.message.reply_text("Invalid input.")
        return False
    dec = int(dec)
    cardi, hintmsg = createcard.choosedec2(cardi, dec)
    if hintmsg == "输入无效":
        update.message.reply_text("Invalid input!")
        return False
    createcard.generateOtherAttributes(cardi)
    writecards(CARDS_LIST)
    update.message.reply_text(hintmsg)
    return True


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
    if not card1.cardcheck["check2"]:
        for keys in card1.data:
            if len(keys) > 4:
                if keys[:3] == "STR":
                    update.message.reply_text(
                        "Please use '/setstrdec STRDEC' to set STR decrease.")
                    break
                else:
                    update.message.reply_text(
                        "Please use '/setcondec CONDEC' to set CON decrease.")
                    break
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
    card1.info["job"] = jobname
    if jobname not in JOB_DICT:
        update.message.reply_text(
            "This job is not in joblist, you can use '/addskill skillname points (main/interest)' to choose skills you like! If interest is appended, the skill will cost interest points.")
        card1.skill["points"] = int(card1.data["EDU"]*4)
        writecards(CARDS_LIST)
        return True
    for i in range(3, len(JOB_DICT[jobname])):  # Classical jobs
        card1.suggestskill[JOB_DICT[jobname][i]] = getskilllevelfromdict(
            card1, JOB_DICT[jobname][i])  # int
    update.message.reply_text(
        "Skill suggestions generated. Use /addskill to add skills.")
    # This trap should not be hit
    if not createcard.generatePoints(card1, jobname):
        update.message.reply_text(
            "Some error occured when generating skill points!")
        return False
    writecards(CARDS_LIST)
    return True


def addmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    if card1.skill["points"] == 0:
        update.message.reply_text("You don't have any main skill points left!")
        return False
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(getskilllevelfromdict(card1, skillname)+card1.skill["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.skill["points"] -= skillvalue - \
        getskilllevelfromdict(card1, skillname)
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
    card1.interest["points"] -= skillvalue - \
        getskilllevelfromdict(card1, skillname)
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - getskilllevelfromdict(card1, skillname)))
    card1.interest[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True


def cgmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:  # Change main skill level
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > min(card1.skill[skillname]+card1.skill["points"], 99):
        update.message.reply_text("Skill value is too high or too low.")
        return False
    card1.skill["points"] -= skillvalue - card1.skill[skillname]
    update.message.reply_text("Skill is set: "+skillname+" "+str(
        skillvalue)+", cost points: "+str(skillvalue - card1.skill[skillname]))
    card1.skill[skillname] = skillvalue
    writecards(CARDS_LIST)
    return True


# Change interest skill level
def cgintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
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
    update.message.reply_text(
        "Add main skill, skill name is: 信用", reply_markup=rp_markup)
    return True


def addskill0(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    rtbuttons = [[]]
    # If skill["points"] is 0, turn to interest.
    # Then it must be main skill. After all main skills are added, add interest skills.
    if card1.skill["points"] > 0:
        if not card1.suggestskill:  # Increase skills already added, because sgskill is empty
            # GOOD TRAP: cgmainskill
            for keys in card1.skill:
                if keys == "points":
                    continue
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys +
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
    if card1.interest["points"] <= 0:  # HIT BAD TRAP
        update.message.reply_text("You don't have any points left!")
        return False
    # GOOD TRAP: add interest skill.
    if "母语" not in card1.skill:
        if "母语" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton(
                "母语: "+str(card1.interest["母语"]), callback_data="cgintskill "+"母语"))
        else:
            rtbuttons[0].append(InlineKeyboardButton(
                "母语: "+str(getskilllevelfromdict(card1, "母语")), callback_data="cgintskill "+"母语"))
    if "闪避" not in card1.skill:
        if "闪避" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton(
                "闪避: "+str(card1.interest["闪避"]), callback_data="cgintskill "+"闪避"))
        else:
            rtbuttons[0].append(InlineKeyboardButton(
                "闪避: "+str(getskilllevelfromdict(card1, "闪避")), callback_data="cgintskill "+"闪避"))
    for keys in SKILL_DICT:
        if keys in card1.skill or keys in card1.suggestskill or keys == "克苏鲁神话":
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if keys in card1.interest:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.interest[keys]), callback_data="cgintskill "+keys))
        else:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": "+str(
                getskilllevelfromdict(card1, keys)), callback_data="addintskill "+keys))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("You have points:"+str(
        card1.interest["points"])+"\nPlease choose a interest skill:", reply_markup=rp_markup)
    return True


def addskill1(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    # skillname is already checked if in SKILL_DICT
    # First search if args skillname in skill or suggestskill.
    # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
    # Show button for numbers
    skillname = context.args[0]
    m = getskilllevelfromdict(card1, skillname)
    if skillname in card1.skill:  # GOOD TRAP: cgmainskill
        mm = card1.skill["points"]+card1.skill[skillname]
        rtbuttons = makeIntButtons(m, min(99, mm), "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Change skill level, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.suggestskill:  # GOOD TRAP: addsgskill
        mm = card1.skill["points"] + m
        rtbuttons = makeIntButtons(m, min(99, mm), "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Add suggested skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.interest:  # GOOD TRAP: cgintskill
        mm = card1.interest["points"]+card1.interest[skillname]
        rtbuttons = makeIntButtons(m, min(99, mm), "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Change interest skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if card1.skill["points"] > 0:  # GOOD TRAP: addmainskill
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), "addmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Add main skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    # GOOD TRAP: addintskill
    mm = card1.interest["points"]+m
    rtbuttons = makeIntButtons(m, min(99, mm), "addintskill", skillname)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "Add interest skill, skill name is: "+skillname, reply_markup=rp_markup)
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
    # HIT BAD TRAP
    if skillname != "母语" and skillname != "闪避" and (skillname not in SKILL_DICT or skillname == "克苏鲁神话"):
        update.message.reply_text("This skill is not allowed.")
        return False
    if len(context.args) == 1:  # HIT GOOD TRAP
        # This function only returns True
        return addskill1(update, context, card1)
    skillvalue = context.args[1]
    if not botdice.isint(skillvalue):
        update.message.reply_text("Invalid input.")
    skillvalue = int(skillvalue)
    if len(context.args) >= 3:  # No buttons
        # HIT GOOD TRAP
        if addskill3(update, context, card1):
            return True
        return False
    if addskill2(update, context, card1):
        return True
    return False


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
    if args[0] == "job":  # Job in buttons must be classical
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
    if args[0] == "addmainskill":
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(
                text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "Add main skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0] == "cgmainskill":
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = skvalue - card1.skill[args[1]]
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(
                text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+card1.skill[args[1]]
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "Change main skill level, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0] == "addsgskill":
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.skill[args[1]] = skvalue
            card1.skill["points"] -= needpt
            query.edit_message_text(
                text="Main skill "+args[1]+" set to "+str(skvalue)+".")
            card1.suggestskill.pop(args[1])
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.skill["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "Add suggested skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0] == "addintskill":
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = skvalue - getskilllevelfromdict(card1, args[1])
            card1.interest[args[1]] = skvalue
            card1.interest["points"] -= needpt
            query.edit_message_text(
                text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
            writecards(CARDS_LIST)
            return True
        m = getskilllevelfromdict(card1, args[1])
        mm = card1.interest["points"]+m
        rtbuttons = makeIntButtons(m, min(99, mm), args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "Add interest skill, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0] == "cgintskill":
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = skvalue - card1.interest[args[1]]
            card1.interest[args[1]] = skvalue
            card1.interest["points"] -= needpt
            query.edit_message_text(
                text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
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
        query.edit_message_text(
            "Change interest skill level, skill name is: "+args[1], reply_markup=rp_markup)
        return True
    if args[0] == "strdec":
        strdecval = int(args[2])
        card1, rttext, needcon = createcard.choosedec(card1, strdecval)
        writecards(CARDS_LIST)
        if needcon:
            rttext += "\nUse /setcondec to set CON decrease."
        query.edit_message_text(rttext)
        return True
    if args[0] == "condec":
        condecval = int(args[2])
        card1, rttext = createcard.choosedec2(card1, condecval)
        writecards(CARDS_LIST)
        query.edit_message_text(rttext)
        return True
    # HIT BAD TRAP
    return False


def setname(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) == 0:
        update.message.reply_text("Please use '/setname NAME' to set name.")
        return False
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    card1.info["name"] = ' '.join(context.args)
    update.message.reply_text("Name is set to: "+card1.info["name"]+".")
    card1.cardcheck["check5"] = True
    writecards(CARDS_LIST)
    return True


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
            update.message.reply_text(
                "A KP can only start ONE game at the same time.")
    gamecards = []
    for i in range(len(CARDS_LIST)):
        if CARDS_LIST[i].groupid == update.effective_chat.id:
            cardcheckinfo = createcard.showchecks(CARDS_LIST[i])
            if cardcheckinfo != "All pass.":
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text="Card id: "+str(i)+" is not ready to play. Because:\n"+cardcheckinfo)
                return False
            gamecards.append(CARDS_LIST[i].__dict__)
            gamecards[-1]["id"] = len(gamecards)-1
    ON_GAME.append(GroupGame(groupid=update.effective_chat.id,
                             kpid=kpid, cards=gamecards))
    writegameinfo(ON_GAME)
    update.message.reply_text("Game start!")
    return True


def abortgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        update.message.reply_text("Game can only be aborted in a group.")
        return False
    if str(update.effective_chat.id) in GROUP_KP_DICT and update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        update.message.reply_text("Only KP can abort a game.")
        return False
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == update.effective_chat.id:
            t = ON_GAME[i]
            ON_GAME = ON_GAME[:i]+ON_GAME[i+1:]
            del t
            update.message.reply_text("Game aborted.")
            writegameinfo(ON_GAME)
            return True
    update.message.reply_text("Game not found.")
    return False


def endgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        update.message.reply_text("Game can only be ended in a group.")
        return False
    if str(update.effective_chat.id) not in GROUP_KP_DICT:
        update.message.reply_text("This group does not have a KP.")
        return False
    if update.message.from_user.id != GROUP_KP_DICT[str(update.effective_chat.id)]:
        update.message.reply_text("Only KP can end a game.")
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
                        t_id = CARDS_LIST[j].id
                        CARDS_LIST[j] = gamecards[i]
                        CARDS_LIST[j].id = t_id
                        CARDS_LIST[j].formerplayerid = CARDS_LIST[j].playerid
                        CARDS_LIST[j].playerid = 0  # 解绑
                        CARDS_LIST[j].formergroupid = CARDS_LIST[j].groupid
                        break
            del t
            update.message.reply_text("Game end!")
            writegameinfo(ON_GAME)
            return True
    update.message.reply_text("Game not found.")
    return False


# /switchcard <id>: switch to a card that KP controlling
def switchcard(update: Update, context: CallbackContext):
    game, ok = findgamewithkpid(update.message.from_user.id)
    if not ok:
        update.message.reply_text("Game not found.")
        return False
    num = context.args[0]
    if not botdice.isint(num):
        update.message.reply_text("Invalid input.")
        return False
    num = int(num)
    if num >= len(game.kpcards):
        update.message.reply_text("You don't have so many card.")
        return False
    game.kpctrl = num
    update.message.reply_text(
        "Switched to card " + str(num)+", card name is: " + game.kpcards[num].info["name"])
    writegameinfo(ON_GAME)
    return True


# /tempcheck <tpcheck:int>: add temp check
# /tempcheck <tpcheck:int> (<cardid> <dicename>): add temp check for one card in a game
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
    if len(context.args) >= 3 and botdice.isint(context.args[1]) and 0 <= int(context.args[1]) and int(context.args[1]) < len(game.cards):
        game.cards[int(context.args[1])].tempstatus[context.args[2]] = int(
            context.args[0])
    else:
        game.tpcheck = int(context.args[0])
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Add temp check successfully.")
    writegameinfo(ON_GAME)
    return True


def roll(update: Update, context: CallbackContext):
    # 只接受第一个空格前的参数。dicename可能是技能名，可能是3d6，可能是1d4+2d10。骰子环境可能是游戏中，游戏外。需要考虑多个情况
    if len(context.args) == 0:
        update.message.reply_text(botdice.commondice("1d100"))  # 骰1d100
        return True
    dicename = context.args[0]
    gpid = update.effective_chat.id
    if isgroupmsg(update):  # Group msg
        game, ok = findgame(gpid)
        if not ok or dicename.find('d') >= 0:
            rttext = botdice.commondice(dicename)
            context.bot.send_message(
                chat_id=update.effective_chat.id, text=rttext)
            if rttext == "Invalid input.":
                return False
            return True
        tpcheck, game.tpcheck = game.tpcheck, 0
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
            gamecard = game.kpcards[game.kpctrl]
        test = 0
        if dicename in gamecard.skill:
            test = gamecard.skill[dicename]
        elif dicename in gamecard.interest:
            test = gamecard.interest[dicename]
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
        elif dicename == "智力" or dicename == "灵感":
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
        elif dicename in SKILL_DICT:
            test = SKILL_DICT[dicename]
        elif dicename[:2] == "暗骰" and (botdice.isint(dicename[2:]) or len(dicename) == 2):
            if len(dicename) != 2:
                test = int(dicename[2:])
            else:
                test = 50
        else:  # HIT BAD TRAP
            print(len(dicename))
            update.message.reply_text("Invalid input.")
            return False
        if "global" in gamecard.tempstatus:
            test += gamecard.tempstatus["global"]
        if dicename in gamecard.tempstatus:
            test += gamecard.tempstatus[dicename]
        test += tpcheck
        testval = botdice.dicemdn(1, 100)[0]
        rttext = "检定："+dicename+" "+str(testval)+"/"+str(test)+" "
        if (test < 50 and testval > 95) or (test >= 50 and testval == 100):
            rttext += "大失败"
        elif testval == 1:
            rttext += "大成功"
        elif testval > test:
            rttext += "失败"
        elif testval > test//2:
            rttext += "普通成功"
        elif testval > test//5:
            rttext += "困难成功"
        else:
            rttext += "极难成功"
        if dicename == "心理学" or dicename[:2] == "暗骰":
            update.message.reply_text("检定："+dicename+" ???/"+str(test))
            context.bot.sendMessage(
                chat_id=GROUP_KP_DICT[str(gpid)], text=rttext)
        else:
            update.message.reply_text(rttext)
        return True
    rttext = botdice.commondice(dicename)  # private msg
    context.bot.send_message(chat_id=update.effective_chat.id, text=rttext)
    if rttext == "Invalid input.":
        return False
    return True


# find a certain attr to show
def showattrinfo(update: Update, card1: GameCard, attrname: str) -> bool:
    if attrname in card1.__dict__:
        ans = card1.__dict__[attrname]
        rttext = ""
        if isinstance(ans, dict):
            for keys in ans:
                rttext += keys+": "+str(ans[keys])+"\n"
        else:
            rttext = str(ans)
        if rttext == "":
            rttext = "None"
        update.message.reply_text(rttext)
        return True
    for keys in card1.__dict__:
        if keys == "tempstatus" and attrname != "global":
            continue
        if isinstance(card1.__dict__[keys], dict):
            if attrname in card1.__dict__[keys]:
                rttext = str(card1.__dict__[keys][attrname])
                if rttext == "":
                    rttext = "None"
                update.message.reply_text(rttext)
                return True
    update.message.reply_text("Can't find this attribute of card!")
    return False

# /show: show card you are controlling
# /show <attrname>: show attr of your card
# (private)/show game: show cards in your game (KP only)
# (private)/show kp: show cards KP controlling (KP only)
# (private)/show group <groupid>: show all cards in a certain group (KP only)


def show(update: Update, context: CallbackContext) -> bool:
    # Should not return game info, unless args[0] == "game"
    if isprivatemsg(update):
        if len(context.args) == 0:
            plid = update.effective_chat.id
            card1, ok = getcard(plid)
            if not ok:
                update.message.reply_text(
                    "Can't find card. If you are kp, please use '/show kp'.")
                return False
            update.message.reply_text(showcardinfo(card1))
            return True
        attrname = context.args[0]
        if attrname == "group":
            kpid = update.effective_chat.id
            # args[1] should be group id
            if len(context.args) < 2:
                update.message.reply_text("Need groupid.")
                return False
            gpid = context.args[1]
            if not botdice.isint(gpid):
                update.message.reply_text("Invalid groupid.")
                return False
            gpid = int(gpid)
            ans = []
            for i in CARDS_LIST:
                if i.groupid == gpid:
                    ans.append(i)
            if len(ans) == 0:
                update.message.reply_text("No card found.")
                return False
            for i in ans:
                update.message.reply_text(showcardinfo(i))
            return True
        if attrname == "game":
            kpid = update.effective_chat.id
            game, ok = findgamewithkpid(kpid)
            if not ok:
                update.message.reply_text("Game not found.")
                return False
            for i in game.cards:
                update.message.reply_text(showcardinfo(i))
            return True
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
    game, ok = findgame(gpid)
    if not ok:
        update.message.reply_text(
            "Can't find game, please send private message to show card info.")
        return False
    if GROUP_KP_DICT[str(gpid)] == senderid:  # KP
        if len(context.args) == 0:
            update.message.reply_text("Cannot show all info in a group.")
            return False
        attrname = context.args[0]
        if game.kpctrl == -1:
            update.message.reply_text(
                "No card choosen. Use /switchcard to switch card.")
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
    if not showattrinfo(update, card1, attrname):
        return False
    return True


# (private)showids: return all card ids in a game/ out of a game
# (private)showids kp: return all card ids kp controlling
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
    if len(context.args) >= 1 and context.args[0] == "kp":
        if not ok:
            update.message.reply_text("Should be in a game.")
            return False
        rttext = ""
        for i in range(len(game.kpcards)):
            rttext += game.kpcards[i].info["name"]+": "+str(i)+"\n"
        update.message.reply_text(rttext)
        return True
    rttext = ""
    for cardi in cards:
        if GROUP_KP_DICT[str(cardi.groupid)] == kpid:
            if cardi.playerid == kpid:
                rttext += "(KP) "
            rttext += cardi.info["name"]+": "+str(cardi.id)+"\n"
    update.message.reply_text(rttext)
    return True


def modify(update: Update, context: CallbackContext) -> bool:
    if not isfromkp(update):
        update.message.reply_text("Not authorized.")
        return False
    # need 3 args, first: card id, second: attrname, third: value
    if len(context.args) < 3:
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
        if card_id >= len(CARDS_LIST):
            update.message.reply_text("Invalid id.")
            return False
        card1 = CARDS_LIST[card_id]
        if str(card1.groupid) not in GROUP_KP_DICT or GROUP_KP_DICT[str(card1.groupid)] != kpid:
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
            update.message.reply_text("Modified.")
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
            update.message.reply_text("Modified.")
            return True
        if isinstance(card1.__dict__[attrname], str):
            card1.__dict__[attrname] = context.args[2]
            if ok:
                writegameinfo(ON_GAME)
            else:
                writecards(CARDS_LIST)
            update.message.reply_text("Modified.")
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
                    update.message.reply_text("Modified.")
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
                    update.message.reply_text("Modified.")
                    return True
                if isinstance(getdict[attrname], str):
                    getdict[attrname] = context.args[2]
                    if ok:
                        writegameinfo(ON_GAME)
                    else:
                        writecards(CARDS_LIST)
                    update.message.reply_text("Modified.")
                    return True
                update.message.reply_text("Type error!!!")
                return False
    update.message.reply_text("Cannot find this attribute.")
    return False


def randombackground(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    rdfaithlist = [
        "毗沙门天",
        "伊斯兰教",
        "海尔·塞拉西一世",
        "耶稣",
        "佛教",
        "道教",
        "无神论",
        "进化论",
        "冷冻休眠",
        "太空探索",
        "因果轮回",
        "共济会",
        "女协",
        "社会正义",
        "占星术",
        "保守党",
        "共产党",
        "民主党",
        "金钱",
        "女权运动",
        "平等主义",
        "工会"
    ]
    rdviplist = [
        "父亲",
        "母亲",
        "继父",
        "继母",
        "哥哥",
        "弟弟",
        "姐姐",
        "妹妹",
        "儿子",
        "女儿",
        "配偶",
        "前任",
        "青梅竹马",
        "明星",
        "另一位调查员",
        "NPC"
    ]
    rdsigplacelist = [
        "学校（母校）",
        "故乡",
        "相识初恋之处",
        "静思之地",
        "社交之地",
        "联系到信念的地方",
        "重要之人的坟墓",
        "家族的地方",
        "生命中最高兴时所在地",
        "工作地点"
    ]
    rdpreciouslist = [
        "与得意技能相关的某件物品",
        "职业必需品",
        "童年遗留物",
        "逝者遗物",
        "重要之人给予之物",
        "收藏品",
        "发掘而不知真相的东西",
        "体育用品",
        "武器",
        "宠物"
    ]
    rdspecialitylist = [
        "慷慨大方",
        "善待动物",
        "梦想家",
        "享乐主义者",
        "冒险家",
        "好厨子",
        "万人迷",
        "忠心",
        "好名头",
        "雄心壮志"
    ]
    card1.background["faith"] = rdfaithlist[botdice.dicemdn(1, len(rdfaithlist))[
        0]-1]
    card1.background["vip"] = rdviplist[botdice.dicemdn(1, len(rdviplist))[
        0]-1]
    card1.background["exsigplace"] = rdsigplacelist[botdice.dicemdn(
        1, len(rdsigplacelist))[0]-1]
    card1.background["precious"] = rdpreciouslist[botdice.dicemdn(
        1, len(rdpreciouslist))[0]-1]
    card1.background["speciality"] = rdspecialitylist[botdice.dicemdn(
        1, len(rdspecialitylist))[0]-1]
    writecards(CARDS_LIST)
    rttext = "faith: "+card1.background["faith"]
    rttext += "\nvip: "+card1.background["vip"]
    rttext += "\nexsigplace: "+card1.background["exsigplace"]
    rttext += "\nprecious: "+card1.background["precious"]
    rttext += "\nspeciality: "+card1.background["speciality"]
    update.message.reply_text(rttext)
    return True


def setsex(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) == 0:
        update.message.reply_text("Please use '/setsex sex' to set sex.")
        return False
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if context.args[0] in ["男", "男性", "M", "m", "male", "雄", "雄性", "公"]:
        card1.info["sex"] = "male"
        update.message.reply_text("Sex is set to male.")
    elif context.args[0] in ["女", "女性", "F", "f", "female", "雌", "雌性", "母"]:
        card1.info["sex"] = "female"
        update.message.reply_text("Sex is set to female.")
    else:
        card1.info["sex"] = context.args[0]
        update.message.reply_text(
            "Sex is set to "+context.args[0]+". Maybe you need to explain what this is?")
    writecards(CARDS_LIST)
    return True


# setbkground <bkgroundname> <bkgroundinfo...>: Need at least 2 args


def setbkground(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) <= 1:
        update.message.reply_text(
            "Please use '/setbkground bkgroundname bkgroudinfo' to set background story.")
        return False
    card1, ok = getcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if context.args[0] not in card1.background:
        rttext = "Cannot find this background name. The background name should be one of:\n"
        for keys in card1.background:
            rttext += keys+"\n"
        update.message.reply_text(rttext)
        return False
    card1.background[context.args[0]] = ' '.join(context.args[1:])
    writecards(CARDS_LIST)
    update.message.reply_text("Add background story successfully.")
    return True


def sancheck(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        update.message.reply_text("Please do san check in a game.")
        return False
    if len(context.args) == 0:
        update.message.reply_text("Need argument.")
        return False
    checkname = context.args[0]
    if checkname.find("/") == -1:
        update.message.reply_text("Seperate your check with a '/'.")
        return False
    checkpass, checkfail = checkname.split(sep='/', maxsplit=1)
    if not isadicename(checkpass) or not isadicename(checkfail):
        update.message.reply_text("Invalid input.")
        return False
    gpid = update.effective_chat.id
    game, ok = findgame(gpid)
    if not ok:
        update.message.reply_text("Please do san check in a game.")
        return False
    if update.message.from_user.id == GROUP_KP_DICT[str(gpid)]:  # KP 进行
        if game.kpctrl == -1:
            update.message.reply_text("Switch to your card.")
            return False
        card1 = game.kpcards[game.kpctrl]
    else:  # 玩家进行
        plid = update.message.from_user.id
        card1, ok = findcardfromgame(game, plid)
        if not ok:
            update.message.reply_text("Can't find card.")
            return False
    rttext = "检定：理智 "
    sanity = card1.attr["SAN"]
    check = botdice.dicemdn(1, 100)[0]
    rttext += str(check)+"/"+str(sanity)+" "
    if (sanity < 50 and check > 95) or (sanity >= 50 and check == 100):  # 大失败
        rttext += "大失败"
        anstype = "大失败"
    elif check > sanity:  # check fail
        rttext += "失败"
        anstype = "失败"
    else:
        rttext += "成功"
        anstype = "成功"
    rttext += "\n损失理智："
    sanloss, m, n = 0, 0, 0
    if anstype == "大失败":
        if botdice.isint(checkfail):
            sanloss = int(checkfail)
        else:
            sanloss = int(checkfail.split("d", maxsplit=1)[
                          0])*int(checkfail.split("d", maxsplit=1)[1])
    elif anstype == "失败":
        if botdice.isint(checkfail):
            sanloss = int(checkfail)
        else:
            m, n = checkfail.split("d", maxsplit=1)
            m, n = int(m), int(n)
            sanloss = int(sum(botdice.dicemdn(m, n)))
    else:
        if botdice.isint(checkpass):
            sanloss = int(checkpass)
        else:
            m, n = checkpass.split("d", maxsplit=1)
            m, n = int(m), int(n)
            sanloss = int(sum(botdice.dicemdn(m, n)))
    card1.attr["SAN"] -= sanloss
    rttext += str(sanloss)+"\n"
    if card1.attr["SAN"] <= 0:
        card1.attr["SAN"] = 0
        card1.status = "mad"
        rttext += "陷入永久疯狂，快乐撕卡~\n"
    elif sanloss > (card1.attr["SAN"]+sanloss)//5:
        rttext += "一次损失五分之一以上理智，进入不定性疯狂状态。\n"
    elif sanloss >= 5:
        rttext += "一次损失5点或以上理智，可能需要进行智力（灵感）检定。\n"
    writegameinfo(ON_GAME)
    update.message.reply_text(rttext)
    return True


def addcard(update: Update, context: CallbackContext) -> bool:
    if isgroupmsg(update):
        update.message.reply_text("Send private message to add card.")
        return False
    if len(context.args) == 0:
        update.message.reply_text("Need args.")
        return False
    if (len(context.args)//2)*2 != len(context.args):
        update.message.reply_text("Argument length should be even.")
    t = createcard.templateNewCard()
    for i in range(0, len(context.args), 2):
        argname = context.args[i]
        argval = context.args[i+1]
        if argname in t and not isinstance(t[argname], dict):
            if isinstance(t[argname], bool):
                if argval == "false" or argval == "False":
                    argval = False
                elif argval == "true" or argval == "True":
                    argval = True
                if not isinstance(argval, bool):
                    update.message.reply_text(
                        argname+" should be boolean type.")
                    return False
                t[argname] = argval
            elif isinstance(t[argname], int):
                if not botdice.isint(argval):
                    update.message.reply_text(argname+" should be int type.")
                    return False
                t[argname] = int(argval)
            else:
                t[argname] = argval
        elif argname in t and isinstance(t[argname], dict):
            update.message.reply_text(
                argname+" is a dict, cannot assign a dict.")
            return False
        else:
            notattr = True
            for keys in t:
                if not isinstance(t[keys], dict) or argname not in t[keys]:
                    continue
                notattr = False
                if isinstance(t[keys][argname], bool):
                    if argval == "false" or argval == "False":
                        argval = False
                    elif argval == "true" or argval == "True":
                        argval = True
                    if not isinstance(argval, bool):
                        update.message.reply_text(
                            argname+" should be boolean type.")
                        return False
                    t[keys][argname] = argval
                elif isinstance(t[keys][argname], int):
                    if not botdice.isint(argval):
                        update.message.reply_text(
                            argname+" should be int type.")
                        return False
                    t[keys][argname] = int(argval)
                else:
                    t[keys][argname] = argval
            if notattr:
                if argname not in SKILL_DICT and argname != "闪避" and argname != "母语":
                    update.message.reply_text(
                        argname+" not found in card template.")
                    return False
                if not botdice.isint(argval):
                    update.message.reply_text(argname+" should be int type.")
                    return False
                t["skill"][argname] = int(argval)
    if t["groupid"] == 0:
        update.message.reply_text("Need groupid!")
        return False
    if not isfromkp(update):
        if t["playerid"] != 0:
            update.message.reply_text("Cannot set playerid.")
            return False
        t["playerid"] = update.effective_chat.id
    else:
        kpid = update.effective_chat.id
        if GROUP_KP_DICT[str(t["groupid"])] != kpid and t["playerid"] != 0 and t["playerid"] != kpid:
            update.message.reply_text("Cannot set playerid.")
            return False
        if t["playerid"] == 0:
            t["playerid"] = kpid
    card1 = GameCard(t)
    card1.id = len(CARDS_LIST)
    rttext = createcard.showchecks(card1)
    if rttext != "All pass.":
        update.message.reply_text(
            "Add card successfully, but card didn't pass card checks.")
        update.message.reply_text(rttext)
    else:
        update.message.reply_text("Add card successfully.")
    CARDS_LIST.append(card1)
    writecards(CARDS_LIST)
    return True


def unknown(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.id > 0:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
