# -*- coding:utf-8 -*-

from inspect import isfunction
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.base import TelegramObject
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext, Updater
from telegram.message import Message

from cfg import *
from botdicts import *
import botdice
import createcard

# 代理设置
if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
                      'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)

# 数据
GROUP_KP_DICT: Dict[int, int]
CARDS_DICT: Dict[int, Dict[int, GameCard]]
ON_GAME: List[GroupGame]
GROUP_RULES: Dict[int, GroupRule]

ID_POOL: List[int] = []

CURRENT_CARD_DICT: Dict[int, Tuple[int, int]]

SKILL_DICT: dict
JOB_DICT: dict

SKILL_PAGES: List[List[str]]

DETAIL_DICT: Dict[int, str] = {}  # 临时地存储详细信息

IDENTIFIER = str(time.time())  # 在每个按钮的callback加上该标志，如果标志不相等则不处理


def createSkillPages(d: dict) -> List[List[List[str]]]:
    """创建技能的分页列表，用于添加兴趣技能"""
    # 一页16个，分四行
    skillPaged: List[List[str]] = [[]]
    for key in d:
        if key == "克苏鲁神话":
            continue
        if len(skillPaged[len(skillPaged)-1]) == 16:
            skillPaged.append([])
        skillPaged[len(skillPaged)-1].append(key)
    return skillPaged


def addIDpool(idpool: List[int]):
    """读取全部卡ID，用于防止卡id重复"""
    for gpids in CARDS_DICT:
        for cdids in CARDS_DICT[gpids]:
            idpool.append(cdids)
            idpool.sort()


# 检测json文件能否正常读取
try:
    GROUP_KP_DICT, CARDS_DICT, ON_GAME = readinfo()
    CURRENT_CARD_DICT = readcurrentcarddict()
    SKILL_DICT = readskilldict()
    SKILL_PAGES = createSkillPages(SKILL_DICT)
    JOB_DICT = createcard.JOB_DICT
    GROUP_RULES = readrules()
except:
    updater.bot.send_message(
        chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
    exit()

# 读取完成
FIRST_MSG: Message = updater.bot.send_message(
    chat_id=ADMIN_ID, text="Bot is live!")
addIDpool(ID_POOL)


def sendtoAdmin(msg: str) -> None:
    updater.bot.send_message(chat_id=ADMIN_ID, text=msg)


def getchatid(update: Update) -> int:
    return update.effective_chat.id


def getkpid(gpid: int) -> int:
    if gpid not in GROUP_KP_DICT:
        return -1
    return GROUP_KP_DICT[gpid]


def isprivatemsg(update: Update) -> bool:
    if update.effective_chat.id > 0:
        return True
    return False


def isgroupmsg(update: Update) -> bool:
    return not isprivatemsg(update)


def searchifkp(plid: int) -> bool:
    """判断plid是否是kp"""
    for keys in GROUP_KP_DICT:
        if GROUP_KP_DICT[keys] == plid:
            return True
    return False


def isfromkp(update: Update) -> bool:
    """判断消息发送者是否是kp。

    如果是私聊消息，只需要发送者是某群KP即返回True。如果是群聊消息，当发送者是本群KP才返回True"""
    if isprivatemsg(update):  # 私聊消息，判断是否是kp
        return searchifkp(update.effective_chat.id)
    # 如果是群消息，判断该指令是否来自本群kp
    if getkpid(update.effective_chat.id) != update.message.from_user.id:
        return False
    return True


def findkpgroups(kpid: int) -> List[int]:
    """返回kp所对应的所有群"""
    ans = []
    for keys in GROUP_KP_DICT:  # key is str(groupid)
        if getkpid(keys) == kpid:
            ans.append(keys)
    return ans


def findcard(plid: int) -> Tuple[GameCard, bool]:
    """输入一个player的id，返回该player当前选择中的卡"""
    if plid not in CURRENT_CARD_DICT:
        return None, False
    gpid, cdid = CURRENT_CARD_DICT[plid]
    if gpid not in CARDS_DICT or cdid not in CARDS_DICT[gpid]:
        CURRENT_CARD_DICT.pop(plid)
        writecurrentcarddict(CURRENT_CARD_DICT)
        return None, False
    return CARDS_DICT[gpid][cdid], True


def findcardwithid(cdid: int) -> Tuple[GameCard, bool]:
    """输入一个卡id，返回这张卡"""
    if cdid not in ID_POOL:
        return None, False
    for gpid in CARDS_DICT:
        if cdid in CARDS_DICT[gpid]:
            return CARDS_DICT[gpid][cdid], True
    return None, False


def findallplayercards(plid: int) -> List[Tuple[int, int]]:
    """输入一个player的id，返回他的所有卡"""
    ans: List[Tuple[int, int]] = []
    for gpid in CARDS_DICT:
        for cdid in CARDS_DICT[gpid]:
            if CARDS_DICT[gpid][cdid].playerid == plid:
                ans.append((gpid, cdid))
    return ans


def initrules(gpid: int) -> None:
    """如果`gpid`对应的群没有Rules，创建一个新的`GroupRule`对象。"""
    if gpid in GROUP_RULES:
        return
    GROUP_RULES[gpid] = GroupRule()
    writerules(GROUP_RULES)


def skillcantouchmax(card1: GameCard) -> Tuple[bool, bool]:
    """判断一张卡当前是否可以新增一个专精技能。

    第一个返回值描述年龄是否符合Aged标准。第二个返回值描述在当前年龄下能否触摸到专精等级"""
    initrules(card1.groupid)
    if card1.info["AGE"] > GROUP_RULES[card1.groupid].skillmaxAged[3]:
        ans1 = True
        skillmaxrule = GROUP_RULES[card1.groupid].skillmaxAged
    else:
        ans1 = False
        skillmaxrule = GROUP_RULES[card1.groupid].skillmax
    countSpecialSkill = 0
    for skill in card1.skill:
        if skill == "points":
            continue
        if card1.skill[skill] > skillmaxrule[0]:
            countSpecialSkill += 1
    for skill in card1.interest:
        if skill == "points":
            continue
        if card1.interest[skill] > skillmaxrule[0]:
            countSpecialSkill += 1
    if countSpecialSkill >= skillmaxrule[2]:
        return ans1, False
    return ans1, True


def getskilllevelfromdict(card1: GameCard, key: str) -> int:
    """从技能表中读取的技能初始值。

    如果是母语和闪避这样的与卡信息相关的技能，用卡信息来计算初始值"""
    if key in SKILL_DICT:
        return SKILL_DICT[key]
    if key == "母语":
        return card1.data["EDU"]
    if key == "闪避":
        return card1.data["DEX"]//2
    return -1


def makeIntButtons(lower: int, upper: int, keystr1: str, keystr2: str, step: int = 5, column: int = 4) -> List[list]:
    """返回一个InlineKeyboardButton组成的二维列表。按钮的显示文本是整数。

    `lower`表示最小值，`upper`表示最大值，均是按钮的一部分。

    `keystr1`, `keystr2`是`callback_data`的内容，按钮的`callback_data`结构为：
    ```
    keystr1+" "+keystr2+" "+str(integer)
    ```
    `step`参数表示按钮会遍历大于`lower`但小于`upper`的所有`step`的倍数。

    `column`参数表示返回的二维列表每行最多有多少个按钮。"""
    rtbuttons = [[]]
    if (lower//step)*step != lower:
        rtbuttons[0].append(InlineKeyboardButton(
            str(lower), callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(lower)))
    t = step+(lower//step)*step
    for i in range(t, upper, step):
        if len(rtbuttons[len(rtbuttons)-1]) == column:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(i),
                                                                callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(i)))
    if len(rtbuttons[len(rtbuttons)-1]) == column:
        rtbuttons.append([])
    rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(upper),
                                                            callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(upper)))
    return rtbuttons


def findgame(gpid: int) -> Tuple[GroupGame, bool]:
    """接收一个groupid，返回对应的GroupGame对象"""
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == gpid:
            return ON_GAME[i], True
    return None, False


def findgamewithkpid(kpid: int) -> Tuple[GroupGame, bool]:
    """接收一个kpid，返回对应的GroupGame对象"""
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].kpid == kpid:
            return ON_GAME[i], True
    return None, False


def findcardfromgame(game: GroupGame, plid: int) -> Tuple[GameCard, bool]:
    """从`game`中返回对应的`plid`的角色卡"""
    for i in game.cards:
        if i.playerid == plid:
            return i, True
    return None, False


def findcardfromgamewithid(game: GroupGame, cdid: int) -> Tuple[GameCard, bool]:
    """从`game`中返回`id`为`cdid`的角色卡"""
    for i in game.cards:
        if i.id == cdid:
            return i, True
    return None, False


def findDiscardCardsGroupIDTuple(plid: int) -> List[Tuple[int, int]]:
    """返回`plid`对应的所有`discard`为`True`的卡的`(groupid, id)`对"""
    ans: List[int] = []
    for gpids in CARDS_DICT:
        for cdids in CARDS_DICT[gpids]:
            if CARDS_DICT[gpids][cdids].playerid == plid:
                if CARDS_DICT[gpids][cdids].discard:
                    ans.append((gpids, cdids))
    return ans


def showcardinfo(card1: GameCard) -> str:  # show full card
    """调用`GameCard.__str__`返回`card1`的信息"""
    return str(card1)


def showvalwithkey(d: dict, keyname: str) -> Tuple[str, bool]:
    if keyname not in d:
        return None, False
    val = d[keyname]
    rttext: str = ""
    if isinstance(val, dict):
        for key in val:
            rttext += key+": "+str(val[key])+"\n"
    else:
        rttext = str(val)
    if rttext == "":
        rttext = "None"
    return rttext, True
# find a certain attr to show


def showattrinfo(update: Update, card1: GameCard, attrname: str) -> bool:
    """显示卡中某项具体的数据，并直接由`update`输出到用户。
    不能输出属性`tempstatus`下的子属性。
    如果获取不到`attrname`这个属性，返回False。"""
    rttext, ok = showvalwithkey(card1.__dict__, attrname)
    if ok:
        update.message.reply_text(rttext)
        return True
    # 没有在最外层找到
    for keys in card1.__dict__:
        if not isinstance(card1.__dict__[keys], dict) or (keys == "tempstatus" and attrname != "global"):
            continue
        rttext, ok = showvalwithkey(card1.__dict__[keys], attrname)
        if not ok:
            continue
        update.message.reply_text(rttext)
        return True
    update.message.reply_text("找不到这个属性！")
    return False


def modifythisdict(d: dict, attrname: str, val: str) -> Tuple[str, bool]:
    """修改一个字典`d`。`d`的键为`str`类型，值为`bool`, `int`, `str`其中之一。

    寻找`attrname`是否在字典中，如果不在字典中或键对应的值是`dict`类型，返回`False`。
    返回True的同时返回修改前的值的字符串。"""
    if isinstance(d[attrname], dict):
        return "不能修改dict类型", False
    if isinstance(d[attrname], bool):
        rtmsg = "False"
        if d[attrname]:
            rtmsg = "True"
        if val in ["F", "false", "False"]:
            d[attrname] = False
            val = "False"
        elif val in ["T", "true", "True"]:
            d[attrname] = True
            val = "True"
        else:
            return "无效的值", False
        return rtmsg, True
    if isinstance(d[attrname], int):
        if not botdice.isint(val):
            return "无效的值", False
        rtmsg = str(d[attrname])
        d[attrname] = int(val)
        return rtmsg, True
    if isinstance(d[attrname], str):
        rtmsg: str = d[attrname]
        d[attrname] = val
        return rtmsg, True
    # 对应的值不是可修改的三个类型之一，也不是dict类型
    return "类型错误！", False


def findattrindict(d: dict, key: str) -> dict:
    """从字典（键为字符串，值为字典或`int`, `str`, `bool`类型）中找到某个键所在的那层字典并返回。
    搜索子字典时，如果`key`不是`global`，忽略`tempstatus`对应的字典。"""
    if key in d:
        return d
    for k1 in d:
        if not isinstance(d[k1], dict) or (k1 == "tempstatus" and key != "global"):
            continue
        t = findattrindict(d[k1], key)
        if t:
            return t
    return None


def modifycardinfo(card1: GameCard, attrname: str, val: str) -> Tuple[str, bool]:
    """修改`card1`的某项属性。

    因为`card1`的属性中有字典，`attrname`可能是其属性里的某项，
    所以可能还要遍历`card1`的所有字典。"""
    if attrname in card1.__dict__:
        rtmsg, ok = modifythisdict(card1.__dict__, attrname, val)
        if not ok:
            return rtmsg, ok
        return "卡id："+str(card1.id)+"的属性："+attrname+"从"+rtmsg+"修改为"+val, True
    for key in card1.__dict__:
        if not isinstance(card1.__dict__[key], dict) or key == "tempstatus":
            continue
        if attrname in card1.__dict__[key]:
            rtmsg, ok = modifythisdict(card1.__dict__[key], attrname, val)
            if not ok:
                return rtmsg, ok
            return "卡id："+str(card1.id)+"的属性："+attrname+"从"+rtmsg+"修改为"+val, True
    return "找不到该属性", False


def findkpcards(kpid) -> List[GameCard]:
    """查找`kpid`作为kp，所控制的NPC卡片，并做成列表全部返回"""
    ans = []
    for gpid in CARDS_DICT:
        if not getkpid(gpid) == kpid:
            continue
        for cardid in CARDS_DICT[gpid]:
            if CARDS_DICT[gpid][cardid].playerid == kpid:
                ans.append(CARDS_DICT[gpid][cardid])
    return ans


def isadicename(dicename: str) -> bool:
    """判断`dicename`是否是一个可以计算的骰子字符串。

    一个可以计算的骰子字符串应当是类似于这样的字符串：`3`或`3d6`或`2d6+6+1d10`，即单项骰子或数字，也可以是骰子与数字相加"""
    if not botdice.isint(dicename):  # 不是数字，先判断是否有'+'
        if dicename.find("+") == -1:  # 没有'+'，判断是否是单项骰子
            if dicename.find("d") == -1:
                return False
            a, b = dicename.split("d", maxsplit=1)
            if not botdice.isint(a) or not botdice.isint(b):
                return False
            return True
        else:  # 有'+'，split后递归判断是否每一项都是单项骰子
            dices = dicename.split("+")
            for dice in dices:
                if not isadicename(dice):
                    return False
            return True
    # 是数字
    if int(dicename) > 0:
        return True
    return False


def isingroup(update: Update, userid: int) -> bool:
    """查询某个userid对应的用户是否在群里"""
    try:
        update.effective_chat.get_member(userid)
    except:
        return False
    return True


def isadmin(update: Update, userid: int) -> bool:
    """检测发消息的人是不是群管理员"""
    if isprivatemsg(update):
        return False
    admins = update.effective_chat.get_administrators()
    for admin in admins:
        if admin.user.id == userid:
            return True
    return False


def recallmsg(update: Update) -> bool:
    """撤回群消息。如果自己不是管理员，不做任何事"""
    if isprivatemsg(update) or not isadmin(update, BOT_ID):
        return False
    update.message.delete()
    return True


def errorHandler(update: Update,  message: str, needrecall: bool = False) -> False:
    """指令无法执行时，调用的函数。
    固定返回`False`，并回复错误信息。
    如果`needrecall`为`True`，在Bot是对应群管理的情况下将删除那条消息。"""
    if needrecall and isgroupmsg(update) and isadmin(update, BOT_ID):
        recallmsg(update)
    else:
        if message == "找不到卡。":
            message += "请使用 /switch 切换当前操控的卡再试。"
        elif message.find("参数") != -1:
            message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"
        update.message.reply_text(message, parse_mode="MarkdownV2")
    return False


def changeKP(gpid: int, newkpid: int = 0) -> bool:
    """转移KP权限，接收参数：群id，新KP的id。

    会转移所有原KP控制的角色卡，包括正在进行的游戏"""
    if newkpid < 0:
        return False
    oldkpid = getkpid(gpid)
    if oldkpid == newkpid:
        return False
    for cdid in CARDS_DICT[gpid]:
        cardi = CARDS_DICT[gpid][cdid]
        if cardi.playerid == oldkpid:
            cardi.playerid = newkpid
        writecards(CARDS_DICT)
    game, ok = findgame(gpid)
    if ok:
        for cardi in game.kpcards:
            cardi.playerid = newkpid
        game.kpid = newkpid
        writegameinfo(ON_GAME)
    if oldkpid in CURRENT_CARD_DICT:
        currentcardgpid, _ = CURRENT_CARD_DICT[oldkpid]
        if currentcardgpid == gpid:
            CURRENT_CARD_DICT.pop(oldkpid)
            writecurrentcarddict(CURRENT_CARD_DICT)
    if newkpid != 0:
        GROUP_KP_DICT[gpid] = newkpid
        writekpinfo(GROUP_KP_DICT)
    else:
        if gpid in GROUP_KP_DICT:
            GROUP_KP_DICT.pop(gpid)
            writekpinfo(GROUP_KP_DICT)
    return True


def start(update: Update, context: CallbackContext) -> None:
    """显示bot的帮助信息，群聊时不显示"""
    if isprivatemsg(update):  # private message
        update.message.reply_text(HELP_TEXT)
    else:
        update.message.reply_text("Dice bot已启用！")


def addkp(update: Update, context: CallbackContext) -> bool:
    """添加KP。在群里发送`/addkp`将自己设置为KP。
    如果这个群已经有一名群成员是KP，则该指令无效。
    若原KP不在群里，该指令可以替换KP。

    如果原KP在群里，需要先发送`/delkp`来撤销自己的KP，或者管理员用`/transferkp`来强制转移KP权限。"""
    if isprivatemsg(update):
        return errorHandler(update, '发送群消息添加KP')
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    initrules(gpid)
    # 判断是否已经有KP
    if gpid in GROUP_KP_DICT:
        # 已有KP
        if not isingroup(update, getkpid(gpid)):
            if not changeKP(gpid, kpid):  # 更新NPC卡拥有者
                return errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发
            return True
        return errorHandler(update, '这个群已经有一位KP了，请先让TA发送 /delkp 撤销自己的KP。如果需要强制更换KP，请管理员用\'/transferkp kpid\'添加本群成员为KP，或者 /transferkp 将自己设为KP。')
    # 该群没有KP，可以直接添加KP
    # delkp指令会将KP的卡playerid全部改为0，检查如果有id为0的卡，id设为新kp的id
    for cdid in CARDS_DICT[gpid]:
        cardi = CARDS_DICT[gpid][cdid]
        if cardi.playerid == 0:
            cardi.playerid = kpid
    writecards(CARDS_DICT)
    game, ok = findgame(gpid)
    if ok:
        game.kpid = kpid
        for cardi in game.kpcards:
            cardi.playerid = kpid
        writegameinfo(ON_GAME)
    update.message.reply_text(
        "绑定群(id): " + str(gpid) + "与KP(id): " + str(kpid))
    GROUP_KP_DICT[gpid] = kpid  # 更新KP表
    writekpinfo(GROUP_KP_DICT)
    return True


def transferkp(update: Update, context: CallbackContext) -> bool:
    """转移KP权限，只有群管理员可以使用这个指令。
    当前群没有KP时或当前群KP为管理员时，无法使用。

    `/transferkp`：将当前群KP权限转移到自身。

    `/transferkp --kpid`将当前群KP权限转移到某个群成员。
    如果指定的`kpid`不在群内则无法设定。"""
    if isprivatemsg(update):
        return errorHandler(update, "发送群消息强制转移KP权限")
    if not isadmin(update, update.message.from_user.id):
        return errorHandler(update, "没有权限", True)
    gpid = update.effective_chat.id
    if getkpid(gpid) == -1:
        return errorHandler(update, "没有KP", True)
    if isadmin(update, getkpid(gpid)):
        return errorHandler(update, "KP是管理员，无法转移")
    newkpid: int
    if len(context.args) != 0:
        if not botdice.isint(context.args[0]):
            return errorHandler(update, "参数需要是整数", True)
        newkpid = int(context.args[0])
    else:
        newkpid = update.message.from_user.id
    if newkpid == getkpid(gpid):
        return errorHandler(update, "原KP和新KP相同", True)
    if not changeKP(gpid, newkpid):
        return errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发
    return True


def delkp(update: Update, context: CallbackContext) -> bool:
    """撤销自己的KP权限。只有当前群内KP可以使用该指令。
    在撤销KP之后的新KP会自动获取原KP的所有NPC的卡片"""
    if isprivatemsg(update):
        return errorHandler(update, '发群消息撤销自己的KP权限')
    gpid = update.effective_chat.id
    if getkpid(gpid) == -1:
        return errorHandler(update, '本群没有KP', True)
    if update.message.from_user.id != getkpid(gpid):
        return errorHandler(update, '你不是KP', True)
    if not changeKP(gpid):
        return errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发
    update.message.reply_text('KP已撤销')
    return True


def reload(update: Update, context: CallbackContext) -> bool:
    """重新读取所有文件，只有bot管理者可以使用"""
    global GROUP_KP_DICT, CARDS_DICT, ON_GAME, CURRENT_CARD_DICT, ID_POOL, GROUP_RULES
    if update.message.from_user.id != ADMIN_ID:
        return errorHandler(update, "没有权限", True)
    try:
        GROUP_KP_DICT, CARDS_DICT, ON_GAME = readinfo()
        CURRENT_CARD_DICT = readcurrentcarddict()
        GROUP_RULES = readrules()
        ID_POOL = []
        addIDpool(ID_POOL)
    except:
        return errorHandler(update, "读取文件出现问题，请检查json文件！")
    update.message.reply_text('成功重新读取文件。')
    return True


def showuserlist(update: Update, context: CallbackContext) -> bool:
    """显示所有信息。非KP无法使用这一指令。"""
    if isgroupmsg(update):  # Group msg: do nothing, even sender is USER or KP
        return errorHandler(update, "没有这一指令", True)
    if update.effective_chat.id == ADMIN_ID:  # 全部显示
        rttext = "GROUP_KP_LIST:\n"
        if not GROUP_KP_DICT:
            rttext += "None"
        else:
            for keys in GROUP_KP_DICT:
                rttext += str(keys) + ": "+str(GROUP_KP_DICT[keys])+"\n"
        update.message.reply_text(rttext)
        if not CARDS_DICT:
            update.message.reply_text("CARDS: None")
        else:
            update.message.reply_text("CARDS:")
            for gpids in CARDS_DICT:
                time.sleep(0.5)
                update.message.reply_text("group:"+str(gpids))
                for cdids in CARDS_DICT[gpids]:
                    update.message.reply_text(str(CARDS_DICT[gpids][cdids]))
                    time.sleep(0.5)
        time.sleep(0.5)
        rttext = "Game Info:\n"
        if not ON_GAME:
            rttext += "None"
        else:
            for i in range(len(ON_GAME)):
                rttext += str(ON_GAME[i].groupid) + \
                    ": " + str(ON_GAME[i].kpid)+"\n"
        update.message.reply_text(rttext)
        return True
    if isfromkp(update):  # private msg
        kpid = update.effective_chat.id
        gpids = findkpgroups(kpid)
        if len(CARDS_DICT) == 0:
            return errorHandler(update, "没有角色卡")
        rttext1: str = ""
        rttext2: str = ""
        for gpid in gpids:
            if gpid not in CARDS_DICT:
                update.message.reply_text("群: "+str(gpid)+" 没有角色卡")
            else:
                update.message.reply_text("群: "+str(gpid)+" 角色卡:")
                for cdid in CARDS_DICT[gpid]:
                    update.message.reply_text(str(CARDS_DICT[gpid][cdid]))
        for i in range(len(ON_GAME)):
            if ON_GAME[i].kpid == kpid:
                update.message.reply_text(
                    "群："+str(ON_GAME[i].groupid)+"正在游戏中")
        return True
    return errorHandler(update, "没有这一指令", True)


def getid(update: Update, context: CallbackContext) -> None:
    """获取所在聊天环境的id。私聊使用该指令发送用户id，群聊使用该指令则发送群id"""
    chatid = getchatid(update)
    update.message.reply_text("<code>"+str(chatid) +
                              "</code> \n点击即可复制", parse_mode='HTML')


def showrule(update: Update, context: CallbackContext) -> bool:
    """显示当前群内的规则。"""
    if isprivatemsg(update):
        return errorHandler(update, "请在群内查看规则")
    gpid = getchatid(update)
    if gpid not in GROUP_RULES:
        initrules(gpid)
    rule = GROUP_RULES[gpid]
    update.message.reply_text(str(rule))
    return True


def setrule(update: Update, context: CallbackContext) -> bool:
    """设置游戏的规则。
    一个群里游戏有自动生成的默认规则，使用本指令可以修改这些规则。

    `/setrule --args`修改规则。`--args`格式如下：

    `rulename1:str --rules1:List[int] rulename2:str --rule2:List[int] ...`

    一次可以修改多项规则。
    有可能会出现部分规则设置成功，但部分规则设置失败的情况，
    查看返回的信息可以知道哪些部分已经成功修改。

    规则的详细说明：

    skillmax：接收长度为3的数组，记为r。`r[0]`是一般技能上限，
    `r[1]`是个别技能的上限，`r[2]`表示个别技能的个数。

    skillmaxAged：年龄得到的技能上限增加设定。
    接收长度为4的数组，记为r。`r[0]`至`r[2]`同上，
    但仅仅在年龄大于`r[3]`时开启该设定。`r[3]`等于100代表不开启该设定。

    skillcost：技能点数分配时的消耗。接收长度为偶数的数组，记为r。
    若i为偶数（或0），`r[i]`表示技能点小于`r[i+1]`时，
    需要分配`r[i]`点点数来获得1点技能点。r的最后一项必须是100。
    例如：`r=[1,80,2,100]`，则从10点升至90点需要花费`1*70+2*10=90`点数。

    greatsuccess：大成功范围。接收长度为4的数组，记为r。
    `r[0]-r[1]`为检定大于等于50时大成功范围，否则是`r[2]-r[3]`。

    greatfail：大失败范围。同上。"""
    if isprivatemsg(update):
        return errorHandler(update, "请在群内用该指令设置规则")
    gpid = update.effective_chat.id
    initrules(gpid)
    if not isfromkp(update):
        return errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return errorHandler(update, "需要参数", True)
    if botdice.isint(context.args[0]):
        return errorHandler(update, "参数无效", True)
    gprule = GROUP_RULES[gpid]
    ruledict: Dict[str, List[int]] = {}
    i = 0
    while i < len(context.args):
        j = i+1
        tplist: List[int] = []
        while j < len(context.args):
            if botdice.isint(context.args[j]):
                tplist.append(int(context.args[j]))
                j += 1
            else:
                break
        ruledict[context.args[i]] = tplist
        i = j
    del i, j
    msg, ok = gprule.changeRules(ruledict)
    writerules(GROUP_RULES)
    if not ok:
        return errorHandler(update, msg)
    update.message.reply_text(msg)
    return True


def createcardhelp(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(CREATE_CARD_HELP, parse_mode="MarkdownV2")


def newcard(update: Update, context: CallbackContext) -> bool:
    """随机生成一张新的角色卡。需要一个群id作为参数。
    只接受私聊消息。

    如果发送者不是KP，那么只能在一个群内拥有最多一张角色卡。


    `/newcard --groupid`新建一张卡片，绑定到`groupid`对应的群。
    如果不知道群id，请先发送`/getid`到群里获取id。

    `/newcard --groupid --cardid`新建一张卡片，绑定到`groupid`对应的群的同时，
    将卡片id设置为`cardid`，`cardid`必须是非负整数。
    当指定的卡id已经被别的卡占用的时候，将自动获取未被占用的id。

    当生成时有至少三项基础属性低于50时，可以使用`/discard`来放弃并删除这张角色卡。
    创建新卡之后，当前控制卡片会自动切换到新卡，详情参见
    `/help switch`。"""
    plid = update.effective_chat.id
    if isgroupmsg(update):  # 只接受私聊消息
        return errorHandler(update, "发送私聊消息创建角色卡。")
    if len(context.args) == 0:
        return errorHandler(update, "使用'/newcard groupid'来创建新角色卡。如果你不知道groupid，在群里发送 /getid 获取群id。如果需要帮助，请使用 /createcardhelp 查看建卡帮助。")
    msg = context.args[0]
    if not botdice.isint(msg) or int(msg) >= 0:
        return errorHandler(update, "无效群id。如果你不知道groupid，在群里发送 /getid 获取群id。使用'/newcard groupid'来创建新角色卡。")
    gpid = int(msg)
    initrules(gpid)
    # 符合建卡条件，开始处理
    # 检查(pl)是否已经有卡
    if gpid in CARDS_DICT:
        for cdid in CARDS_DICT[gpid]:
            if CARDS_DICT[gpid][cdid].playerid == plid and getkpid(gpid) != plid:
                return errorHandler(update, "你在这个群已经有一张卡了！")
    # 符合建卡条件，生成新卡
    if gpid not in CARDS_DICT:
        CARDS_DICT[gpid] = {}
    new_card, detailmsg = createcard.generateNewCard(plid, gpid)
    DETAIL_DICT[plid] = detailmsg
    if len(context.args) > 1 and botdice.isint(context.args[1]) and int(context.args[1]) not in ID_POOL and int(context.args[1]) > 0:
        new_card.id = int(context.args[1])
    else:
        if len(context.args) > 1 and botdice.isint(context.args[1]) and (int(context.args[1]) in ID_POOL or int(context.args[1]) < 0):
            update.message.reply_text("输入的ID已经被占用，自动获取ID")
        nid = 0
        while nid in ID_POOL:
            nid += 1
        new_card.id = nid
        ID_POOL.append(nid)
        ID_POOL.sort()
    update.message.reply_text(
        "角色卡已创建，您的卡id为："+str(new_card.id)+"。使用 /details 查看角色卡详细信息。")
    # 如果有3个属性小于50，则discard=true
    countless50 = 0
    for keys in new_card.data:
        if new_card.data[keys] < 50:
            countless50 += 1
    if countless50 >= 3:
        new_card.discard = True
        update.message.reply_text(
            "因为有三项属性小于50，如果你愿意的话可以使用 /discard 来删除这张角色卡。设定年龄后则不能再删除这张卡。")
    update.message.reply_text(
        "长按 /setage 并输入一个数字来设定年龄。如果需要帮助，使用 /createcardhelp 来获取帮助。")
    CARDS_DICT[new_card.groupid][new_card.id] = new_card
    writecards(CARDS_DICT)
    if plid in CURRENT_CARD_DICT:
        update.message.reply_text("创建新卡时，控制自动切换至新卡")
    CURRENT_CARD_DICT[plid] = (new_card.groupid, new_card.id)
    writecurrentcarddict(CURRENT_CARD_DICT)
    return True

# (private)/discard (--groupid/--cardid) 删除对应卡片。


def discard(update: Update, context: CallbackContext):
    """该指令用于删除角色卡。
    通过识别卡中`discard`是否为`True`来判断是否可以删除这张卡。
    如果`discard`为`False`，需要玩家向KP申请，让KP修改`discard`属性为`True`。

    指令格式如下：
    `/discard (--groupid_1/--cardid_1 --groupid_2/--cardid_2 ...)`。
    可以一次输入多个群或卡id来批量删除。

    无参数时，如果只有一张卡可以删除，自动删除那张卡。
    否则，会创建一组按钮来让玩家选择要删除哪张卡。

    有参数时，
    若其中一个参数为群id（负数），则删除该群内所有可删除的卡。
    若其中一个参数为卡id，删除对应的那张卡。
    找不到参数对应的卡时，该参数会被忽略。"""
    if isgroupmsg(update):
        return errorHandler(update, "发送私聊消息删除卡。")
    plid = update.effective_chat.id  # 发送者
    # 先找到所有可删除的卡，返回一个列表
    discardgpcdTupleList = findDiscardCardsGroupIDTuple(plid)
    if len(context.args) > 0:
        # 求args提供的卡id与可删除的卡id的交集
        trueDiscardTupleList: List[Tuple[int, int]] = []
        for gpid, cdid in discardgpcdTupleList:
            if str(gpid) in context.args or str(cdid) in context.args:
                trueDiscardTupleList.append((gpid, cdid))
        if len(trueDiscardTupleList) == 0:  # 交集为空集
            update.message.reply_text("输入的（群/卡片）ID均无效。")
            return False
        if len(trueDiscardTupleList) == 1:
            gpid, cdid = trueDiscardTupleList[0]
            rttext = "删除卡："+str(cdid)
            if "name" in CARDS_DICT[gpid][cdid].info and CARDS_DICT[gpid][cdid].info["name"] != "":
                rttext += "\nname: "+str(CARDS_DICT[gpid][cdid].info["name"])
            rttext += "\n/details 显示删除的卡片信息。删除操作不可逆。"
            update.message.reply_text(rttext)
        else:
            update.message.reply_text(
                "删除了"+str(len(trueDiscardTupleList))+"张卡片。\n/details 显示删除的卡片信息。删除操作不可逆。")
        detailinfo = ""
        for gpid, cdid in trueDiscardTupleList:
            if cdid in ID_POOL:
                ID_POOL.pop(ID_POOL.index(cdid))
            else:
                sendtoAdmin("删除了ID池中未出现的卡，请检查代码")
            detailinfo += "删除卡片：\n" + \
                str(CARDS_DICT[gpid][cdid])+"\n"  # 获取删除的卡片的详细信息
            CARDS_DICT[gpid].pop(cdid)
            if len(CARDS_DICT[gpid]) == 0:
                CARDS_DICT.pop(gpid)
            if plid in CURRENT_CARD_DICT and CURRENT_CARD_DICT[plid][0] == gpid and CURRENT_CARD_DICT[plid][1] == cdid:
                CURRENT_CARD_DICT.pop(plid)
                writecurrentcarddict(CURRENT_CARD_DICT)
        DETAIL_DICT[plid] = detailinfo
        writecards(CARDS_DICT)
        return True
    if len(discardgpcdTupleList) > 1:  # 创建按钮，接下来交给按钮完成
        rtbuttons: List[List[str]] = [[]]
        for gpid, cdid in discardgpcdTupleList:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            if "name" in CARDS_DICT[gpid][cdid].info and CARDS_DICT[gpid][cdid].info["name"] != 0:
                cardname: str = CARDS_DICT[gpid][cdid].info["name"]
            else:
                cardname: str = str(cdid)
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(cardname,
                                                                    callback_data=IDENTIFIER+" "+"discard "+str(gpid)+" "+str(cdid)))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("请点击要删除的卡片：", reply_markup=rp_markup)
        return True
    if len(discardgpcdTupleList) == 1:
        gpid, cdid = discardgpcdTupleList[0]
        if plid in CURRENT_CARD_DICT and CURRENT_CARD_DICT[plid][0] == gpid and CURRENT_CARD_DICT[plid][1] == cdid:
            CURRENT_CARD_DICT.pop(plid)
            writecurrentcarddict(CURRENT_CARD_DICT)
        rttext = "删除卡："+str(cdid)
        if "name" in CARDS_DICT[gpid][cdid].info and CARDS_DICT[gpid][cdid].info["name"] != "":
            rttext += "\nname: "+str(CARDS_DICT[gpid][cdid].info["name"])
        rttext += "\n/details 显示删除的卡片信息。删除操作不可逆。"
        update.message.reply_text(rttext)
        detailinfo = "删除卡片：\n"+str(CARDS_DICT[gpid][cdid])+"\n"
        DETAIL_DICT[plid] = detailinfo
        CARDS_DICT[gpid].pop(cdid)
        if cdid in ID_POOL:
            ID_POOL.pop(ID_POOL.index(cdid))
        else:
            sendtoAdmin("删除了ID池中未出现的卡，请检查代码")
        if len(CARDS_DICT[gpid]) == 0:
            CARDS_DICT.pop(gpid)
        writecards(CARDS_DICT)
        return True
    # 没有可删除的卡
    return errorHandler(update, "找不到可删除的卡。")


def details(update: Update, context: CallbackContext):
    """显示详细信息。
    该指令主要是为了与bot交互时产生尽量少的文本消息而设计。

    当一些指令产生了“详细信息”时，这些详细信息会被暂时存储。
    当使用`/details`查看了这些“详细信息”，该“信息”将从存储中删除，即只能读取一次。
    如果没有查看上一个“详细信息”，就又获取到了下一个“详细信息”，
    上一个“详细信息”将会被覆盖。"""
    if update.effective_chat.id not in DETAIL_DICT or DETAIL_DICT[update.effective_chat.id] == "":
        DETAIL_DICT[update.effective_chat.id] = ""
        return errorHandler(update, "没有可显示的信息。")
    update.message.reply_text(DETAIL_DICT[update.effective_chat.id])
    DETAIL_DICT[update.effective_chat.id] = ""
    return True


def setage(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        return errorHandler(update, "发送私聊消息设置年龄。")
    if len(context.args) == 0:
        return errorHandler(update, "使用'/setage AGE'来设置年龄。")
    age = context.args[0]
    if not botdice.isint(age):
        return errorHandler(update, "输入无效")
    age = int(age)
    cardi, ok = findcard(update.effective_chat.id)
    if not ok:
        return errorHandler(update, "找不到卡。")
    if "AGE" in cardi.info and cardi.info["AGE"] > 0:
        return errorHandler(update, "已经设置过年龄了。")
    if age < 17 or age > 99:
        return errorHandler(update, "年龄应当在17-99岁。")
    global DETAIL_DICT
    cardi.info["AGE"] = age
    cardi.cardcheck["check1"] = True
    cardi, detailmsg = createcard.generateAgeAttributes(cardi)
    DETAIL_DICT[update.effective_chat.id] = detailmsg
    update.message.reply_text(
        "年龄设置完成！如果需要查看详细信息，使用 /details。如果年龄不小于40，或小于20，需要使用指令'/setstrdec number'设置STR减值。如果需要帮助，使用 /createcardhelp 来获取帮助。")
    if cardi.cardcheck["check2"]:
        createcard.generateOtherAttributes(cardi)
    writecards(CARDS_DICT)
    return True


def setstrdec(update: Update, context: CallbackContext):
    """设置力量（STR）的减少值。因为年龄的设定，会导致力量属性减少。
    一般而言，年龄导致的需要减少的属性数目至少是两项，其中一项会是力量。
    它们减少的总值是定值。
    当只有两项需要下降时，用力量的减少值，就能自动计算出另一项减少值。
    但如果有三项下降，那么其中一项会是体质（CON）。
    那么可能需要再使用`/setcondec`指令。

    `/setstrdec`生成按钮来让玩家选择力量下降多少。

    `/setstrdec --STRDEC`可以直接指定力量的下降值。"""
    if isgroupmsg(update):
        return errorHandler(update, "Send private message to set STR decrease.")
    plid = update.effective_chat.id
    cardi, ok = findcard(plid)
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
    global CARDS_DICT
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
    writecards(CARDS_DICT)
    return True


def setcondec(update: Update, context: CallbackContext):
    """设置体质（CON）的减少值。请先参见帮助`/help setstrdec`。

    `/setcondec`生成按钮来让玩家选择体质下降多少。

    `/setcondec --CONDEC`可以直接指定体质的下降值。"""
    if isgroupmsg(update):
        update.message.reply_text("Send private message to set CON decrease.")
        return False
    plid = update.effective_chat.id
    cardi, ok = findcard(plid)
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
    writecards(CARDS_DICT)
    update.message.reply_text(hintmsg)
    return True


def makejobbutton() -> List[List[InlineKeyboardButton]]:
    """生成全部职业的按钮"""
    rtbuttons = [[]]
    for keys in JOB_DICT:
        if len(rtbuttons[len(rtbuttons)-1]) == 3:
            rtbuttons.append([])
        rtbuttons[len(
            rtbuttons)-1].append(InlineKeyboardButton(keys, callback_data=IDENTIFIER+" "+"job "+keys))
    return rtbuttons


# Button. need 0-1 args, if len(args)==0, show button and listen
def setjob(update: Update, context: CallbackContext) -> bool:
    """设置职业。

    `/setjob`生成按钮来设定职业。点击职业将可以查看对应的推荐技能，
    以及对应的信用范围和主要技能点计算方法。再点击确认即可确认选择该职业。
    确认了职业就不能再更改。

    `/setjob --job`将职业直接设置为给定职业。
    如果允许非经典职业，需要参数`IGNORE_JOB_DICT`为`True`，
    否则不能设置。如果设置了非经典职业，技能点计算方法为教育乘4。

    在力量、体质等属性减少值计算完成后才可以设置职业。"""
    if isgroupmsg(update):
        return errorHandler(update, "发送私聊消息设置职业。")
    plid = update.effective_chat.id
    card1, ok = findcard(plid)
    if not ok:
        return errorHandler(update, "找不到卡。")
    if not card1.cardcheck["check2"]:
        for keys in card1.data:
            if len(keys) > 4:
                if keys[:3] == "STR":
                    return errorHandler(update, "请先使用'/setstrdec --STRDEC'来设置力量下降值。")
                else:
                    return errorHandler(update, "请先使用'/setcondec --CONDEC'来设置体质下降值。")
        sendtoAdmin("卡片检查出错，位置：setjob")
        return errorHandler(update, "错误！卡片检查：2不通过，但没有找到原因。")
    if "job" in card1.info:
        update.message.reply_text("职业已经设定了！如果需要帮助，使用 /createcardhelp 来获取帮助。")
        return False
    if len(context.args) == 0:
        rtbuttons = makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        # 设置职业的任务交给函数buttonjob
        update.message.reply_text(
            "请选择职业查看详情：", reply_markup=rp_markup)
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
        writecards(CARDS_DICT)
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
    writecards(CARDS_DICT)
    return True


def showjoblist(update: Update, context: CallbackContext) -> None:
    """显示职业列表"""
    rttext = "职业列表："
    for job in JOB_DICT:
        rttext += job+"\n"


def skillmaxval(skillname: str, card1: GameCard, ismainskill: bool) -> int:
    """通过cost规则，返回技能能达到的最高值。"""
    aged, ok = skillcantouchmax(card1)
    if aged:
        skillrule = GROUP_RULES[card1.groupid].skillmaxAged
    else:
        skillrule = GROUP_RULES[card1.groupid].skillmax
    if ok:
        maxval = skillrule[1]
    else:
        maxval = skillrule[0]
    basicval = -1
    if ismainskill:
        pts = card1.skill["points"]
        if skillname in card1.skill:
            basicval = card1.skill[skillname]
    else:
        pts = card1.interest["points"]
        if skillname in card1.interest:
            basicval = card1.interest[skillname]
    costrule = GROUP_RULES[card1.groupid].skillcost
    if basicval == -1:
        basicval = getskilllevelfromdict(card1, skillname)
    if len(costrule) <= 2:
        skillmax = (pts+basicval*costrule[0])//costrule[0]
        return min(maxval, skillmax)
    # 有非默认的规则，长度不为2
    i = 1
    skillmax = basicval
    while i < len(costrule):
        if (costrule[i]-skillmax)*costrule[i-1] <= pts:
            pts -= (costrule[i]-skillmax)*costrule[i-1]
            skillmax = costrule[i]
            i += 2
        else:
            return min(maxval, (pts+skillmax*costrule[i-1])//costrule[i-1])
    return min(maxval, skillmax)


def evalskillcost(skillname: str, skillval: int, card1: GameCard, ismainskill: bool) -> int:
    """返回由当前技能值增加到目标值需要消耗多少点数。如果目标技能值低于已有值，返回负数"""
    if skillval > 99:
        return 10000  # HIT BAD TRAP
    basicval = -1
    if ismainskill:
        if skillname in card1.skill:
            basicval = card1.skill[skillname]
    else:
        if skillname in card1.interest:
            basicval = card1.interest[skillname]
    if basicval == -1:
        basicval = getskilllevelfromdict(card1, skillname)
    if skillval == basicval:
        return 0
    initrules(card1.groupid)
    costrule = GROUP_RULES[card1.groupid].skillcost
    if skillval < basicval:
        # 返还技能点，返回负数
        if len(costrule) <= 2:
            return (skillval-basicval)*costrule[0]
        i = len(costrule)-1
        while i >= 0 and costrule[i] >= basicval:
            i -= 2
        if i < 0:
            return (skillval-basicval)*costrule[0]
        if skillval >= costrule[i]:
            return (skillval-basicval)*costrule[i+1]
        ans = 0
        while i >= 0 and skillval < costrule[i]:
            ans += (basicval-costrule[i])*costrule[i+1]
            basicval = costrule[i]
            i -= 2
        return -(ans+(basicval-skillval)*costrule[i+1])
    # 增加点数，返回值为正
    if skillval <= costrule[1]:
        return (skillval-basicval)*costrule[0]
    i = 1
    ans = 0
    while skillval > costrule[i]:
        ans += costrule[i-1]*(costrule[i]-basicval)
        basicval = costrule[i]
        i += 2
    return ans + costrule[i-1]*(costrule[i]-basicval)


def addmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """该函数对没有`skillname`这项技能的卡使用。将主要技能值设置为`skillvalue`。"""
    if card1.skill["points"] == 0:
        return errorHandler(update, "你已经没有剩余点数了")
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, True):
        return errorHandler(update, "目标技能点太高或太低")
    # 计算点数消耗
    costval = evalskillcost(skillname, skillvalue, card1, True)
    card1.skill["points"] -= costval
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.skill[skillname] = skillvalue
    writecards(CARDS_DICT)
    return True


def addsgskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """添加一个建议的技能。直接调用`addmainskill`完成。"""
    if not addmainskill(skillname, skillvalue, card1, update):
        return False
    card1.suggestskill.pop(skillname)
    writecards(CARDS_DICT)
    return True


def addintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """该函数对没有`skillname`这项技能的卡使用。将兴趣技能值设置为`skillvalue`。"""
    if card1.interest["points"] == 0:
        return errorHandler(update, "你已经没有剩余点数了")

    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    # 计算点数消耗
    costval = evalskillcost(skillname, skillvalue, card1, False)
    card1.interest["points"] -= costval
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.interest[skillname] = skillvalue
    writecards(CARDS_DICT)
    return True


def cgmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:  # Change main skill level
    """修改主要技能的值。如果将技能点调低，返还技能点数。"""

    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, True):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, True)
    card1.skill["points"] -= costval
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.skill[skillname] = skillvalue
    writecards(CARDS_DICT)
    return True


# Change interest skill level
def cgintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """修改兴趣技能的值。如果将技能点调低，返还技能点数。"""

    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, False)
    card1.interest["points"] -= costval
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.interest[skillname] = skillvalue
    writecards(CARDS_DICT)
    return True


def addcredit(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    update.message.reply_text("请先设置信用！")
    if card1.info["job"] in JOB_DICT:
        m = JOB_DICT[card1.info["job"]][0]
        mm = JOB_DICT[card1.info["job"]][1]
    else:
        aged, ok = skillcantouchmax(card1)
        if aged:
            skillmaxrule = GROUP_RULES[card1.groupid].skillmaxAged
        else:
            skillmaxrule = GROUP_RULES[card1.groupid].skillmax
        m = 0
        if ok:
            mm = skillmaxrule[1]
        else:
            mm = skillmaxrule[0]
    rtbuttons = makeIntButtons(m, mm, "addmainskill", "信用")
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "Add main skill, skill name is: 信用", reply_markup=rp_markup)
    return True


def showskillpages(page: int, card1: GameCard) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    page
    thispageskilllist = SKILL_PAGES[page]
    rttext = "添加/修改兴趣技能，目前的数值/基础值如下："
    rtbuttons = [[]]
    for key in thispageskilllist:
        if key in card1.skill or key in card1.suggestskill:
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if key in card1.interest:
            rttext += "（已有技能）"+key+"："+str(card1.interest[key])+"\n"
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(text=key,
                                                                    callback_data=IDENTIFIER+" cgintskill "+key))
            continue
        rttext += key+"："+str(getskilllevelfromdict(card1, key))+"\n"
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(text=key,
                                                                callback_data=IDENTIFIER+" addintskill "+key))
    if page == 0:
        rtbuttons.append([InlineKeyboardButton(
            text="下一页", callback_data=IDENTIFIER+" addintskill page 1")])
    elif page == len(SKILL_PAGES)-1:
        rtbuttons.append([InlineKeyboardButton(
            text="上一页", callback_data=IDENTIFIER+" addintskill page "+str(page-1))])
    else:
        rtbuttons.append([InlineKeyboardButton(text="上一页", callback_data=IDENTIFIER+" addintskill page "+str(
            page-1)), InlineKeyboardButton(text="下一页", callback_data=IDENTIFIER+" addintskill page "+str(page+1))])
    return rttext, rtbuttons


def addskill0(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """表示指令/addskill 中没有参数的情况。
    创建技能按钮来完成技能的添加。

    因为兴趣技能过多，使用可以翻页的按钮列表。"""
    pass
    rtbuttons = [[]]
    # If card1.skill["points"] is 0, turn to interest.
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
                                                                        ": "+str(card1.skill[keys]), callback_data=IDENTIFIER+" "+"cgmainskill "+keys))
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            update.message.reply_text("You have points:"+str(
                card1.skill["points"])+"\nPlease choose a skill to increase:", reply_markup=rp_markup)
            return True
        # GOOD TRAP: addsgskill
        for keys in card1.suggestskill:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.suggestskill[keys]), callback_data=IDENTIFIER+" "+"addsgskill "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("You have points:"+str(
            card1.skill["points"])+"\nPlease choose a main skill:", reply_markup=rp_markup)
        return True
    # turn to interest.
    if card1.interest["points"] <= 0:  # HIT BAD TRAP
        update.message.reply_text("You don't have any points left!")
        return False
    # GOOD TRAP: add interest skill.
    # 显示第一页，每个参数后面带一个当前页码标记
    rttext, rtbuttons = showskillpages(0, card1)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(rttext, reply_markup=rp_markup)
    return True
    """
    if "母语" not in card1.skill:
        if "母语" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton(
                "母语: "+str(card1.interest["母语"]), callback_data=IDENTIFIER+" "+"cgintskill "+"母语"))
        else:
            rtbuttons[0].append(InlineKeyboardButton(
                "母语: "+str(getskilllevelfromdict(card1, "母语")), callback_data=IDENTIFIER+" "+"cgintskill "+"母语"))
    if "闪避" not in card1.skill:
        if "闪避" in card1.interest:
            rtbuttons[0].append(InlineKeyboardButton(
                "闪避: "+str(card1.interest["闪避"]), callback_data=IDENTIFIER+" "+"cgintskill "+"闪避"))
        else:
            rtbuttons[0].append(InlineKeyboardButton(
                "闪避: "+str(getskilllevelfromdict(card1, "闪避")), callback_data=IDENTIFIER+" "+"cgintskill "+"闪避"))
    for keys in SKILL_DICT:
        if keys in card1.skill or keys in card1.suggestskill or keys == "克苏鲁神话":
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if keys in card1.interest:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.interest[keys]), callback_data=IDENTIFIER+" "+"cgintskill "+keys))
        else:
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": "+str(
                getskilllevelfromdict(card1, keys)), callback_data=IDENTIFIER+" "+"addintskill "+keys))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("You have points:"+str(
        card1.interest["points"])+"\nPlease choose a interest skill:", reply_markup=rp_markup)
    return True
    """


def addskill1(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """该函数在`/addskill`接收且仅接收一个参数时调用。制作技能数值表。"""
    # skillname is already checked if in SKILL_DICT
    # First search if args skillname in skill or suggestskill.
    # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
    # Show button for numbers
    skillname = context.args[0]
    m = getskilllevelfromdict(card1, skillname)
    if skillname in card1.skill:  # GOOD TRAP: cgmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Change skill level, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.suggestskill:  # GOOD TRAP: addsgskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Add suggested skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.interest:  # GOOD TRAP: cgintskill
        mm = skillmaxval(skillname, card1, False)
        rtbuttons = makeIntButtons(m, mm, "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Change interest skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    if card1.skill["points"] > 0:  # GOOD TRAP: addmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "Add main skill, skill name is: "+skillname, reply_markup=rp_markup)
        return True
    mm = skillmaxval(skillname, card1, False)
    rtbuttons = (m, mm, "addintskill", skillname)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "Add interest skill, skill name is: "+skillname, reply_markup=rp_markup)
    return True


def addskill2(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """该函数在`/addskill`接收且仅接收两个参数时调用。直接修改技能值。"""
    skillname = context.args[0]
    skillvalue = int(context.args[1])
    if skillname in card1.skill:  # Change skill level.
        return cgmainskill(skillname, skillvalue, card1, update)
    if skillname in card1.suggestskill:
        return addsgskill(skillname, skillvalue, card1, update)
    if skillname in card1.interest:  # Change skill level.
        return cgintskill(skillname, skillvalue, card1, update)
    # If cannot judge which skill is, one more arg is needed. Then turn to addskill3()
    if card1.skill["points"] > 0 and card1.interest["points"] > 0:
        return errorHandler(update, "请使用'/addskill skillname skillvalue main/interest'来指定技能种类！")
    # HIT GOOD TRAP
    if card1.skill["points"] > 0:
        return addmainskill(skillname, skillvalue, card1, update)
    return addintskill(skillname, skillvalue, card1, update)


def addskill3(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """该函数在`/addskill`接收三个参数时调用。直接修改技能值。"""
    skillname = context.args[0]
    skillvalue = int(context.args[1])
    if context.args[2] != "interest" and context.args[2] != "main":
        return errorHandler(update, "这是main（主要）还是interest（兴趣）技能？请在第三个参数位置指明")
    if context.args[2] == "interest" and (skillname in card1.suggestskill or skillname in card1.skill):
        return errorHandler(update, "这是main（主要）技能")
    if context.args[2] == "main" and skillname in card1.interest:
        return errorHandler(update, "这是interest（兴趣）技能")
    # HIT GOOD TRAP
    if skillname in card1.interest:
        # This means arg3 is "interest". Change skill level.
        return cgintskill(skillname, skillvalue, card1, update)
    if skillname in card1.suggestskill:  # Add suggest skill
        return addsgskill(skillname, skillvalue, card1, update)
    if skillname in card1.skill:  # Change skill level.
        return cgmainskill(skillname, skillvalue, card1, update)
    if context.args[2] == "main":
        return addmainskill(skillname, skillvalue, card1, update)
    return addintskill(skillname, skillvalue, card1, update)


# Button. need 0-3 args, if len(args)==0 or 1, show button and listen; if len(args)==3, the third should be "interest/main" to give interest skills
# Compicated
def addskill(update: Update, context: CallbackContext) -> bool:
    """该函数用于增加/修改技能。

    增加技能这一功能非常复杂，它的详细功能被拆分为4个函数。
    该函数只做基础的检查工作。检查通过后给4个拆分出的函数调用。"""
    if isgroupmsg(update):
        return errorHandler(update, "发私聊消息来增改技能", True)
    plid = update.effective_chat.id
    card1, ok = findcard(plid)
    if not ok:
        return errorHandler(update, "找不到卡。")
    if card1.skill["points"] == -1:
        return errorHandler(update, "信息不完整，无法添加技能")
    if card1.skill["points"] == 0 and card1.interest["points"] == 0 and len(context.args) == 0:
        if len(context.args) == 0 or (context.args[0] not in card1.skill and context.args[0] not in card1.interest):
            return errorHandler(update, "你已经没有技能点了，请添加参数来修改具体的技能！")
    if "job" not in card1.info:
        return errorHandler(update, "请先设置职业")
    if "信用" not in card1.skill:
        return addcredit(update, context, card1)
    if len(context.args) == 0:  # HIT GOOD TRAP
        return addskill0(update, context, card1)
    skillname = context.args[0]
    # HIT BAD TRAP
    if skillname != "母语" and skillname != "闪避" and (skillname not in SKILL_DICT or skillname == "克苏鲁神话"):
        return errorHandler(update, "无法设置这个技能")
    if len(context.args) == 1:  # HIT GOOD TRAP
        # This function only returns True
        return addskill1(update, context, card1)
    skillvalue = context.args[1]
    if not botdice.isint(skillvalue):
        return errorHandler(update, "第二个参数：无效输入")
    skillvalue = int(skillvalue)
    # HIT GOOD TRAP
    if len(context.args) >= 3:
        # No buttons
        return addskill3(update, context, card1)
    return addskill2(update, context, card1)


def showskilllist(update: Update, context: CallbackContext) -> None:
    """显示技能列表"""
    rttext = "技能：基础值\n"
    rttext += "母语：等于EDU\n"
    rttext += "闪避：等于DEX的一半"
    for skill in SKILL_DICT:
        rttext += skill+"："+str(SKILL_DICT[skill])+"\n"
    update.message.reply_text(rttext)


def buttonjob(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    jobname = args[1]
    if len(args) == 2:
        # 切换至显示职业详情
        jobinfo = JOB_DICT[jobname]
        rttext = "如果确认选择该职业，请点击下面按钮进行确认。职业信息如下\n信用点范围："
        rttext += str(jobinfo[0])+"至"+str(jobinfo[1])+"\n"
        pointsrule = jobinfo[2]
        sep = ""
        for key in pointsrule:
            if len(key) < 4:
                rttext += sep+key+"*"+str(pointsrule[key])
            elif len(key) == 7:
                rttext += sep+key[:3]+"或"+key[4:]+"之一*"+str(pointsrule[key])
            else:
                rttext += sep+key[:3]+"或"+key[4:7]+"或" + \
                    key[8:]+"之一*"+str(pointsrule[key])
            sep = "+"
        rttext += "\n推荐技能：\n"
        sep = ""
        for i in range(3, len(jobinfo)):
            rttext += sep+jobinfo[i]
            sep = "，"
        query.edit_message_text(rttext)
        rtbuttons = [[
            InlineKeyboardButton(
                text="确认", callback_data=IDENTIFIER+" job "+jobname+" True"),
            InlineKeyboardButton(
                text="返回", callback_data=IDENTIFIER+" job "+jobname+" False")
        ]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_reply_markup(rp_markup)
        return True
    confirm = args[2]  # 只能是True，或False
    if confirm == "False":
        rtbuttons = makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("请选择职业查看详情：")
        query.edit_message_reply_markup(rp_markup)
        return True
    # 确认完成
    card1.info["job"] = jobname
    query.edit_message_text(
        "职业设置为："+jobname+"\n现在你可以用指令 /addskill 添加技能，首先需要设置信用点。")
    if not createcard.generatePoints(card1, jobname):
        query.edit_message_text(
            "生成技能点出错！")
        sendtoAdmin("生成技能出错，位置：buttonjob")
        return False
    for i in range(3, len(JOB_DICT[jobname])):  # Classical jobs
        card1.suggestskill[JOB_DICT[jobname][i]
                           ] = getskilllevelfromdict(card1, JOB_DICT[jobname][i])  # int
    writecards(CARDS_DICT)
    return True


def buttonaddmainskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = skvalue - getskilllevelfromdict(card1, args[1])
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="Main skill "+args[1]+" set to "+str(skvalue)+".")
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "Add main skill, skill name is: "+args[1], reply_markup=rp_markup)
    return True


def buttoncgmainskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = skvalue - card1.skill[args[1]]
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="Main skill "+args[1]+" set to "+str(skvalue)+".")
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "Change main skill level, skill name is: "+args[1], reply_markup=rp_markup)
    return True


def buttonaddsgskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = skvalue - getskilllevelfromdict(card1, args[1])
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="Main skill "+args[1]+" set to "+str(skvalue)+".")
        card1.suggestskill.pop(args[1])
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "Add suggested skill, skill name is: "+args[1], reply_markup=rp_markup)
    return True


def buttonaddintskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    """响应KeyboardButton的addintskill请求。

    因为使用的是能翻页的列表，所以有可能位置1的参数是`page`，
    且位置2的参数是页码。"""
    if args[1] == "page":
        rttext, rtbuttons = showskillpages(int(args[2]), card1)
        query.edit_message_text(rttext)
        query.edit_message_reply_markup(InlineKeyboardMarkup(rtbuttons))
        return True
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = skvalue - getskilllevelfromdict(card1, args[1])
        card1.interest[args[1]] = skvalue
        card1.interest["points"] -= needpt
        query.edit_message_text(
            text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "Add interest skill, skill name is: "+args[1], reply_markup=rp_markup)
    return True


def buttoncgintskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = skvalue - card1.interest[args[1]]
        card1.interest[args[1]] = skvalue
        card1.interest["points"] -= needpt
        query.edit_message_text(
            text="Interest skill "+args[1]+" set to "+str(skvalue)+".")
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "Change interest skill level, skill name is: "+args[1], reply_markup=rp_markup)
    return True


def buttonstrdec(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    strdecval = int(args[2])
    card1, rttext, needcon = createcard.choosedec(card1, strdecval)
    writecards(CARDS_DICT)
    if needcon:
        rttext += "\n使用 /setcondec 来设置CON（体质）下降值。"
    query.edit_message_text(rttext)
    return True


def buttoncondec(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    condecval = int(args[2])
    card1, rttext = createcard.choosedec2(card1, condecval)
    writecards(CARDS_DICT)
    query.edit_message_text(rttext)
    return True


def buttondiscard(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    plid = update.effective_chat.id
    gpid, cdid = int(args[1]), int(args[2])
    if plid in CURRENT_CARD_DICT and CURRENT_CARD_DICT[plid][0] == gpid and CURRENT_CARD_DICT[plid][1] == cdid:
        CURRENT_CARD_DICT.pop(plid)
        writecurrentcarddict(CURRENT_CARD_DICT)
    if gpid not in CARDS_DICT or cdid not in CARDS_DICT[gpid] or CARDS_DICT[gpid][cdid].playerid != plid or not CARDS_DICT[gpid][cdid].discard:
        query.edit_message_text("没有找到卡片。")
        return False
    detailinfo = "删除了：\n"+str(CARDS_DICT[gpid][cdid])
    DETAIL_DICT[plid] = detailinfo
    CARDS_DICT[gpid].pop(cdid)
    if cdid in ID_POOL:
        ID_POOL.pop(ID_POOL.index(cdid))
    else:
        sendtoAdmin("删除了ID池中未出现的卡，请检查代码")
    if len(CARDS_DICT[gpid]) == 0:
        CARDS_DICT.pop(gpid)
    query.edit_message_text("删除了一张卡片，使用 /details 查看详细信息。\n该删除操作不可逆。")
    return True


def buttonswitch(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    plid = update.effective_chat.id
    gpid, cdid = int(args[1]), int(args[2])
    if gpid not in CARDS_DICT or cdid not in CARDS_DICT[gpid] or CARDS_DICT[gpid][cdid].playerid != plid:
        query.edit_message_text("没有找到卡片。")
        return False
    CURRENT_CARD_DICT[plid] = (gpid, cdid)
    writecurrentcarddict(CURRENT_CARD_DICT)
    cardi = CARDS_DICT[gpid][cdid]
    if "name" not in cardi.info or cardi.info["name"] == "":
        query.edit_message_text("修改成功，现在操作的卡是："+str(cdid))
    else:
        query.edit_message_text("修改成功，现在操作的卡是："+cardi.info["name"])
    return True


def button(update: Update, context: CallbackContext):
    """所有按钮请求经该函数处理。功能十分复杂，拆分成多个子函数来处理。
    接收到按钮的参数后，转到对应的子函数处理。"""
    if isgroupmsg(update):
        return False
    query = update.callback_query
    query.answer()
    args = query.data.split(" ")
    identifier = args[0]
    if identifier != IDENTIFIER:
        query.edit_message_text(text="该请求已经过期。")
        return False
    args = args[1:]
    plid = update.effective_chat.id
    card1, ok = findcard(plid)
    if not ok and args[0] != "switch" and args[0] != "discard":
        query.edit_message_text(text="找不到卡。")
        return False
    # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
    if args[0] == "job":  # Job in buttons must be classical
        return buttonjob(query, update, card1, args)
    # Increase skills already added, because sgskill is none. second arg is skillname
    if args[0] == "addmainskill":
        return buttonaddmainskill(query, update, card1, args)
    if args[0] == "cgmainskill":
        return buttoncgmainskill(query, update, card1, args)
    if args[0] == "addsgskill":
        return buttonaddsgskill(query, update, card1, args)
    if args[0] == "addintskill":
        return buttonaddintskill(query, update, card1, args)
    if args[0] == "cgintskill":
        return buttoncgintskill(query, update, card1, args)
    if args[0] == "strdec":
        return buttonstrdec(query, update, card1, args)
    if args[0] == "condec":
        return buttoncondec(query, update, card1, args)
    if args[0] == "discard":
        return buttondiscard(query, update, card1, args)
    if args[0] == "switch":
        return buttonswitch(query, update, card1, args)
    # HIT BAD TRAP
    return False


def setname(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) == 0:
        update.message.reply_text("Please use '/setname NAME' to set name.")
        return False
    card1, ok = findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    card1.info["name"] = ' '.join(context.args)
    update.message.reply_text("Name is set to: "+card1.info["name"]+".")
    card1.cardcheck["check5"] = True
    writecards(CARDS_DICT)
    return True


def startgame(update: Update, context: CallbackContext) -> bool:
    """开始一场游戏。

    这一指令将拷贝本群内所有卡，之后将用拷贝的卡片副本进行游戏，修改属性将不会影响到游戏外的原卡属性。
    如果要正常结束游戏，使用`/endgame`可以将游戏的角色卡数据覆写到原本的数据上。
    如果要放弃这些游戏内进行的修改，使用`/abortgame`会直接删除这些副本副本"""
    if isprivatemsg(update):
        return errorHandler(update, "游戏需要在群里进行")
    if getkpid(update.effective_chat.id) == -1:
        return errorHandler(update, "这个群没有KP")
    if not isfromkp(update):
        return errorHandler(update, "游戏应由KP发起", True)
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    for games in ON_GAME:
        if games.kpid == kpid:
            return errorHandler(update, "一个KP一次只能同时主持一场游戏。")
    if popallempties(CARDS_DICT):
        writecards(CARDS_DICT)
    if gpid not in CARDS_DICT:
        update.message.reply_text("注意！本群没有卡片。游戏开始。")
        ON_GAME.append(
            GroupGame(groupid=update.effective_chat.id, kpid=kpid, cards=[]))
        writegameinfo(ON_GAME)
        return True
    gamecards = []
    for cdid in CARDS_DICT[gpid]:
        cardcheckinfo = createcard.showchecks(CARDS_DICT[gpid][cdid])
        if cardcheckinfo != "All pass.":
            return errorHandler(update, "卡片: "+str(cdid)+"还没有准备好。因为：\n"+cardcheckinfo)
        gamecards.append(CARDS_DICT[gpid][cdid].__dict__)
    ON_GAME.append(GroupGame(groupid=update.effective_chat.id,
                             kpid=kpid, cards=gamecards))
    writegameinfo(ON_GAME)
    update.message.reply_text("游戏开始！")
    return True


def abortgame(update: Update, context: CallbackContext) -> bool:
    if isprivatemsg(update):
        return errorHandler(update, "发送群聊消息来中止游戏")
    if update.message.from_user.id != getkpid(gpid):
        return errorHandler(update, "只有KP可以中止游戏", True)
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
        return errorHandler(update, "该指令仅用于群聊")
    if getkpid(update.effective_chat.id) == -1:
        return errorHandler(update, "这个群没有KP")
    if update.message.from_user.id != getkpid(update.effective_chat.id):
        update.message.reply_text("Only KP can end a game.")
        return False
    global CARDS_DICT, ON_GAME
    gpid = update.effective_chat.id
    kpid = getkpid(gpid)
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == gpid:
            t = ON_GAME[i]
            ON_GAME = ON_GAME[:i]+ON_GAME[i+1:]
            writegameinfo(ON_GAME)
            gamecards = t.cards
            for cardi in gamecards:
                if cardi.playerid in CURRENT_CARD_DICT and CURRENT_CARD_DICT[cardi.playerid][0] == gpid and CURRENT_CARD_DICT[cardi.playerid][1] == cardi.id:
                    CURRENT_CARD_DICT.pop(cardi.playerid)
                cardi.playerid = kpid
                if cardi.id not in CARDS_DICT[gpid]:
                    CARDS_DICT[gpid][cardi.id] = cardi
                    continue
                CARDS_DICT[gpid].pop(cardi.id)
                CARDS_DICT[gpid][cardi.id] = cardi
            writecurrentcarddict(CURRENT_CARD_DICT)
            del t
            update.message.reply_text("游戏结束！")
            writecards(CARDS_DICT)
            return True
    update.message.reply_text("没找到进行中的游戏。")
    return False


# /switch (--id): 切换进行修改操作时控制的卡，可以输入gpid，也可以是cdid
def switch(update: Update, context: CallbackContext):
    if isgroupmsg(update):
        update.message.reply_text("对bot私聊来切换卡。")
        return False
    plid = update.effective_chat.id
    if len(context.args) > 0:
        if not botdice.isint(context.args[0]):
            update.message.reply_text("输入无效。")
            return False
        numid = int(context.args[0])
        if numid < 0:
            gpid = numid
            cardscount = 0
            temptuple: Tuple[int, int] = (0, 0)
            for cdid in CARDS_DICT[gpid]:
                if CARDS_DICT[gpid][cdid].playerid == plid:
                    cardscount += 1
                    if cardscount > 1:
                        update.message.reply_text(
                            "在这个群你有多于一张卡，请输入具体的卡id。如果不知道自己的卡id，用 /showmycards 来显示ID。")
                        return False
                    temptuple = (gpid, cdid)
            if cardscount == 0:
                update.message.reply_text("你在这个群没有卡。")
                return False
            rttext = "切换成功，现在操作的卡：\n"
            cardi = CARDS_DICT[gpid][temptuple[1]]
            if "name" in cardi.info and cardi.info["name"] != "":
                rttext += cardi.info["name"]+": "+str(cardi.id)
            else:
                rttext += "(No name): "+str(cardi.id)
            CURRENT_CARD_DICT[plid] = temptuple
            writecurrentcarddict(CURRENT_CARD_DICT)
            update.message.reply_text(rttext)
            return True
        else:
            cdid = numid
            for gpid in CARDS_DICT:
                if cdid in CARDS_DICT[gpid]:
                    rttext = "切换成功，现在操作的卡：\n"
                    cardi = CARDS_DICT[gpid][cdid]
                    if "name" in cardi.info and cardi.info["name"] != "":
                        rttext += cardi.info["name"]+": "+str(cardi.id)
                    else:
                        rttext += "(No name): "+str(cardi.id)
                    CURRENT_CARD_DICT[plid] = (gpid, cdid)
                    writecurrentcarddict(CURRENT_CARD_DICT)
                    update.message.reply_text(rttext)
                    return True
            update.message.reply_text("找不到这张卡。")
            return False
    mycardslist = findallplayercards(plid)
    if len(mycardslist) == 0:
        update.message.reply_text("你没有任何卡。")
        return False
    if len(mycardslist) == 1:
        gpid, cdid = mycardslist[0]
        rttext = "你只有一张卡，自动切换。现在操作的卡：\n"
        cardi = CARDS_DICT[gpid][cdid]
        if "name" in cardi.info and cardi.info["name"] != "":
            rttext += cardi.info["name"]+": "+str(cardi.id)
        else:
            rttext += "(No name): "+str(cardi.id)
        update.message.reply_text(rttext)
        CURRENT_CARD_DICT[plid] = (gpid, cdid)
        writecurrentcarddict(CURRENT_CARD_DICT)
        return True
    # 多个选项。创建按钮
    rtbuttons = [[]]
    for gpid, cdid in mycardslist:
        cardi = CARDS_DICT[gpid][cdid]
        cardiname: str
        if "name" not in cardi.info or cardi.info["name"] == "":
            cardiname = str(cdid)
        else:
            cardiname = cardi.info["name"]
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
            cardiname, callback_data=IDENTIFIER+" "+"switch "+str(gpid)+" "+str(cdid)))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("请选择要切换控制的卡：", reply_markup=rp_markup)
    # 交给按钮来完成
    return True


def switchkp(update: Update, context: CallbackContext):
    """用于KP切换游戏中进行对抗时使用的NPC卡片。

    `/switchkp --cardid` 切换到id为cardid的卡并控制。"""
    game, ok = findgamewithkpid(update.message.from_user.id)
    if not ok:
        return errorHandler(update, "没找到游戏", True)
    num = context.args[0]
    if not botdice.isint(num) or int(num) < 0:
        return errorHandler(update, "无效输入", True)
    cdid = int(num)
    for i in range(len(game.kpcards)):
        cardi = game.kpcards[i]
        if cardi.id == cdid:
            game.kpctrl = i
            update.message.reply_text(
                "切换到卡" + str(num)+"，角色名称：" + cardi.info["name"])
            writegameinfo(ON_GAME)
            return True
    return errorHandler(update, "没有找到这张卡", True)


def showmycards(update: Update, context: CallbackContext) -> bool:
    """显示自己所持的卡"""
    pass

# /tempcheck --tpcheck:int: add temp check
# /tempcheck --tpcheck:int (--cardid --dicename): add temp check for one card in a game


def tempcheck(update: Update, context: CallbackContext):
    """增加一个临时的检定修正。该指令只能在游戏中使用。"""
    if len(context.args) == 0:
        return errorHandler(update, "没有参数", True)
    if update.effective_chat.id > 0:
        return errorHandler(update, "在群里设置临时检定")
    if not botdice.isint(context.args[0]):
        return errorHandler(update, "临时检定修正应当是整数", True)
    game, ok = findgame(update.effective_chat.id)
    if not ok:
        return errorHandler(update, "没有进行中的游戏", True)
    if getkpid(update.effective_chat.id) != update.message.from_user.id:
        return errorHandler(update, "KP才可以设置临时检定", True)
    if len(context.args) >= 3 and botdice.isint(context.args[1]) and 0 <= int(context.args[1]):
        card, ok = findcardfromgamewithid(game, int(context.args[1]))
        if not ok:
            return errorHandler(update, "找不到这张卡", True)
        card.tempstatus[context.args[2]] = int(context.args[0])
        update.message.reply_text(
            "新增了对id为"+context.args[1]+"卡的检定修正\n修正项："+context.args[2]+"修正值："+context.args[0])
    else:
        game.tpcheck = int(context.args[0])
        update.message.reply_text("新增了仅限一次的全局检定修正："+context.args[0])
    writegameinfo(ON_GAME)
    return True


def roll(update: Update, context: CallbackContext):
    """基本的骰子功能。

    只接受第一个空格前的参数`dicename`。
    `dicename`可能是技能名，可能是`3d6`，可能是`1d4+2d10`。
    骰子环境可能是游戏中，游戏外。"""
    #
    if len(context.args) == 0:
        update.message.reply_text(botdice.commondice("1d100"))  # 骰1d100
        return True
    dicename = context.args[0]
    gpid = update.effective_chat.id
    if isgroupmsg(update):  # Group msg
        initrules(gpid)
        game, ok = findgame(gpid)
        # 检查输入参数是不是一个基础骰子，如果是则直接计算骰子
        if not ok or dicename.find('d') >= 0:
            rttext = botdice.commondice(dicename)
            if rttext == "Invalid input.":
                return errorHandler(update, "无效输入")
            update.message.reply_text(rttext)
            return True
        # 获取临时检定
        tpcheck, game.tpcheck = game.tpcheck, 0
        if tpcheck != 0:
            writegameinfo(ON_GAME)
        senderid = update.message.from_user.id
        gpid = update.effective_chat.id
        if senderid != getkpid(gpid):
            gamecard, ok = findcardfromgame(game, senderid)
        elif game.kpctrl == -1:
            rttext = botdice.commondice(dicename)
            if rttext == "Invalid input.":
                return errorHandler(update, "无效输入")
            update.message.reply_text(rttext)
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
            return errorHandler(update, "无效输入")
        if "global" in gamecard.tempstatus:
            test += gamecard.tempstatus["global"]
        if dicename in gamecard.tempstatus:
            test += gamecard.tempstatus[dicename]
        test += tpcheck
        testval = botdice.dicemdn(1, 100)[0]
        rttext = "检定："+dicename+" "+str(testval)+"/"+str(test)+" "
        greatsuccessrule = GROUP_RULES[gpid].greatsuccess
        greatfailrule = GROUP_RULES[gpid].greatfail
        if (test < 50 and testval >= greatfailrule[2] and testval <= greatfailrule[3]) or (test >= 50 and testval >= greatfailrule[0] and testval <= greatfailrule[1]):
            rttext += "大失败"
        elif (test < 50 and testval >= greatsuccessrule[2] and testval <= greatsuccessrule[3]) or (test >= 50 and testval >= greatsuccessrule[0] and testval <= greatsuccessrule[1]):
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
            if getkpid(gpid) == -1:
                return errorHandler(update, "本群没有KP！请先添加一个KP再试！！")
            update.message.reply_text("检定："+dicename+" ???/"+str(test))
            context.bot.send_message(
                chat_id=getkpid(gpid), text=rttext)
        else:
            update.message.reply_text(rttext)
        return True
    rttext = botdice.commondice(dicename)  # private msg
    update.message.reply_text(rttext)
    if rttext == "Invalid input.":
        return False
    return True


def show(update: Update, context: CallbackContext) -> bool:
    """显示目前操作中的卡片的信息。
    /show card: 显示当前操作的整张卡片的信息
    /show --attrname: 显示卡片的某项具体属性
    """
    if len(context.args) == 0:
        return errorHandler(update, "需要参数")
    if isprivatemsg(update):
        plid = update.effective_chat.id
        card1, ok = findcard(plid)
        if not ok:
            return errorHandler(update, "找不到卡。")
        if context.args[0] == "card":
            update.message.reply_text(showcardinfo(card1))
            return True
        attrname = context.args[0]
        if not showattrinfo(update, card1, attrname):
            return False
        return True
    # 群消息
    gpid = update.effective_chat.id
    senderid = update.message.from_user.id
    # KP
    if getkpid(gpid) == senderid and context.args[0] == "card":
        return errorHandler(update, "为保护NPC或敌人信息，不可以在群内显示KP整张卡片", True)
    game, ingame = findgame(gpid)
    if not ingame:  # 显示游戏外数据，需要提示
        cardi, ok = findcard(senderid)
        if not ok:
            return errorHandler(update, "找不到卡。")
    else:
        if isfromkp(update):
            if game.kpctrl != -1:
                cardi = game.kpcards[game.kpctrl]
            else:
                return errorHandler(update, "注意：kpctrl值为-1")
        else:
            cardi, ok = findcardfromgame(game, senderid)
    # 显示游戏内数据，需要提示是游戏内/外的卡
    if context.args[0] == "card":
        rttext = ""
        if ingame:
            rttext += "显示游戏中的卡片：\n"
        else:
            rttext += "显示游戏外的卡片：\n"
        rttext += showcardinfo(cardi)
        update.message.reply_text(rttext)
        return True
    attrname = context.args[0]
    if ingame:
        update.message.reply_text("显示游戏中的卡片：")
    else:
        update.message.reply_text("显示游戏外的卡片：")
    if not showattrinfo(update, cardi, attrname):
        return False
    return True


def showkp(update: Update, context: CallbackContext) -> bool:
    """这一指令是为KP设计的。

    (private)/showkp game: 显示发送者主持的游戏中所有的卡
    (private)/showkp card: 显示发送者作为KP控制的所有卡
    (private)/showkp group --groupid: 显示发送者是KP的某个群内的所有卡"""
    # Should not return game info, unless args[0] == "game"
    if isgroupmsg(update):
        return errorHandler(update, "使用该指令请发送私聊消息", True)
    if len(context.args) == 0:
        return errorHandler(update, "需要参数")
    arg = context.args[0]
    if arg == "group":
        kpid = update.effective_chat.id
        # args[1] should be group id
        if len(context.args) < 2:
            return errorHandler(update, "需要群ID")
        gpid = context.args[1]
        if not botdice.isint(gpid):
            return errorHandler(update, "无效ID")
        gpid = int(gpid)
        if gpid not in CARDS_DICT:
            return errorHandler(update, "这个群没有卡")
        ans: List[GameCard] = []
        for cdid in CARDS_DICT[gpid]:
            ans.append(CARDS_DICT[gpid][cdid])
        if len(ans) == 0:
            return errorHandler(update, "没有找到卡")
        for i in ans:
            update.message.reply_text(showcardinfo(i))
        return True
    if arg == "game":
        kpid = update.effective_chat.id
        game, ok = findgamewithkpid(kpid)
        if not ok:
            return errorHandler(update, "没有找到游戏")
        for i in game.cards:
            update.message.reply_text(showcardinfo(i))
        return True
    if arg == "kp":
        kpid = update.effective_chat.id
        cards = findkpcards(kpid)
        if len(cards) == 0:
            return errorHandler(update, "你没有控制的卡")
        for i in range(len(cards)):
            update.message.reply_text(showcardinfo(cards[i]))
        return True
    return errorHandler(update, "无法识别的参数")


def showcard(update: Update, context: CallbackContext) -> bool:
    """显示某张卡的信息。

    `/showcard --cardid (--attrname)`: 显示卡id为`cardid`的卡片的信息。
    如果第二个参数存在，则显示这一项数据。

    显示前会检查发送者是否有权限显示这张卡。在这些情况下，无法显示卡：

    群聊环境：显示非本群的卡片，或者显示本群PL以外的卡片；

    私聊环境：作为PL，显示非自己控制的卡片；KP想显示非自己管理的群的卡片。"""
    if len(context.args) == 0:
        return errorHandler(update, "需要参数")
    if not botdice.isint(context.args[0]):
        return errorHandler(update, "参数不是整数", True)
    cdid = int(context.args[0])
    cardi, ok = findcardwithid(cdid)
    if not ok:
        return errorHandler(update, "没有这张卡", True)
    if isprivatemsg(update):
        # 检查是否合法
        if isfromkp(update):  # KP
            kpid = update.effective_chat.id
            if kpid != ADMIN_ID and getkpid(cardi.groupid) != kpid:
                return errorHandler(update, "没有权限")
        else:
            # 非KP，只能显示自己的卡
            plid = update.effective_chat.id
            if plid != ADMIN_ID and cardi.playerid != plid:
                return errorHandler(update, "没有权限")
        # 有权限，开始处理
        if len(context.args) >= 2:
            if not showattrinfo(update, cardi, context.args[1]):
                return False
            return True
        # 显示整张卡
        update.message.reply_text(showcardinfo(cardi))
        return True
    # 处理群聊消息
    gpid = update.effective_chat.id
    if cardi.groupid != gpid or cardi.playerid == getkpid(gpid) or cardi.type != "PL":
        return errorHandler(update, "不可显示该卡", True)
    # 有权限，开始处理
    if len(context.args) >= 2:
        if not showattrinfo(update, cardi, context.args[1]):
            return False
        return True
    update.message.reply_text(showcardinfo(cardi))
    return True

# (private)
# (private)showids game: return all card ids in a game
# (private)showids kp: return all card ids kp controlling


def showids(update: Update, context: CallbackContext) -> bool:
    """用于显示卡的名字-id对。群聊时使用只能显示游戏中PL的卡片id。

    `showids`: 显示游戏外的卡id。

    `showids game`: 显示游戏中的卡id。

    私聊时，只有KP可以使用该指令。两个指令同上，但结果将更详细，结果会包括KP主持游戏的所有群的卡片。额外有一个功能：

    `showids kp`: 返回KP游戏中控制的所有卡片id"""
    if isgroupmsg(update):
        gpid = update.effective_chat.id
        if len(context.args) == 0:
            if gpid not in CARDS_DICT:
                return errorHandler(update, "本群没有卡")
            rttext = ""
            for cdid in CARDS_DICT[gpid]:
                cardi = CARDS_DICT[gpid][cdid]
                if cardi.playerid == getkpid(gpid) or cardi.type != "PL":
                    continue
                rttext += str(cardi.id)+": "
                if "name" not in cardi.info or cardi.info["name"] == "":
                    rttext += "No name\n"
                else:
                    rttext += cardi.info["name"]+"\n"
            if rttext == "":
                return errorHandler(update, "本群没有卡")
            update.message.reply_text(rttext)
            return True
        if context.args[0] != "game":
            return errorHandler(update, "无法识别的参数", True)
        game, ok = findgame(gpid)
        if not ok:
            return errorHandler(update, "没有进行中的游戏", True)
        rttext = ""
        for cardi in game.cards:
            if cardi in game.kpcards or cardi.type != "PL":
                continue
            rttext += str(cardi.id)+": "
            if "name" not in cardi.info or cardi.info["name"] == "":
                rttext += "No name\n"
            else:
                rttext += cardi.info["name"]+"\n"
        if rttext == "":
            return errorHandler(update, "游戏中没有卡")
        update.message.reply_text(rttext)
        return True
    # 下面处理私聊消息
    if not isfromkp(update):
        return errorHandler(update, "没有权限")
    kpid = update.effective_chat.id
    game, ok = findgamewithkpid(kpid)
    if len(context.args) >= 1:
        if context.args[0] != "kp" and context.args[0] != "game":
            return errorHandler(update, "无法识别的参数")
        if context.args[0] == "kp":
            if not ok:
                return errorHandler(update, "该参数只返回游戏中你的卡片，但你目前没有主持游戏")
            cards = game.kpcards
        else:
            if not ok:
                return errorHandler(update, "你目前没有主持游戏")
            cards = game.cards
        rttext = ""
        if len(cards) == 0:
            return errorHandler(update, "游戏中KP没有卡")
        for cardi in cards:
            if "name" in cardi.info and cardi.info["name"] != "":
                rttext += str(cardi.id)+": "+cardi.info["name"]+"\n"
            else:
                rttext += str(cardi.id) + ": No name\n"
        update.message.reply_text(rttext)
        return True
    # 不带参数，显示全部该KP做主持的群中的卡id
    kpgps = findkpgroups(kpid)
    rttext = ""
    if popallempties(CARDS_DICT):
        writecards(CARDS_DICT)
    for gpid in kpgps:
        if gpid not in CARDS_DICT:
            continue
        for cdid in CARDS_DICT[gpid]:
            if CARDS_DICT[gpid][cdid].playerid == kpid:
                rttext += "(KP) "
            if "name" in CARDS_DICT[gpid][cdid].info and CARDS_DICT[gpid][cdid].info["name"].strip() != "":
                rttext += str(CARDS_DICT[gpid][cdid].id) + \
                    ": "+CARDS_DICT[gpid][cdid].info["name"]+"\n"
            else:
                rttext += str(CARDS_DICT[gpid][cdid].id) + ": No name\n"
    if rttext == "":
        return errorHandler(update, "没有可显示的卡")
    update.message.reply_text(rttext)
    return True


def modify(update: Update, context: CallbackContext) -> bool:
    """强制修改某张卡某个属性的值。
    需要注意可能出现的问题，使用该指令前，请三思。

    `/modify --cardid --arg --value (game)`: 修改id为cardid的卡的value，要修改的参数是arg。
    带game时修改的是游戏内卡片数据，不指明时默认游戏外
    （对于游戏中与游戏外卡片区别，参见 `/help startgame`）。
    修改对应卡片的信息必须要有对应的KP权限，或者是BOT的管理者。
    id和groupid这两个属性不可以修改。
    想要修改id，请使用指令
    `/changeid --cardid --newid`
    （参考`/help changeid`）。
    想要修改所属群，使用指令
    `/changegroup --cardid --newgroupid`
    （参考`/help changegroup`）。"""
    if not isfromkp(update) and update.effective_chat.id != ADMIN_ID:
        return errorHandler(update, "没有权限", True)
    # need 3 args, first: card id, second: attrname, third: value
    if len(context.args) < 3:
        return errorHandler(update, "需要至少3个参数", True)
    if context.args[1] == "id" or context.args[1] == "groupid":
        return errorHandler(update, "该属性无法修改", True)
    card_id = context.args[0]
    if not botdice.isint(card_id):
        return errorHandler(update, "无效ID", True)
    card_id = int(card_id)
    if update.message.from_user.id == ADMIN_ID:  # 最高控制权限
        if len(context.args) == 3 or context.args[3] != "game":
            cardi, ok = findcardwithid(card_id)
            if not ok:
                return errorHandler(update, "找不到该ID对应的卡。")
            rtmsg, ok = modifycardinfo(cardi, context.args[1], context.args[2])
            if not ok:
                update.message.reply_text(rtmsg)
                return False
            update.message.reply_text("修改了游戏外的卡片！\n"+rtmsg)
            writecards(CARDS_DICT)
            return True
        cardi, ok = findcardwithid(card_id)
        if not ok:
            return errorHandler(update, "找不到游戏外对应卡片，请务必核查ID是否输入有误！")
        game, ok = findgame(cardi.groupid)
        if not ok:
            return errorHandler(update, "找不到游戏", True)
        cardi, ok = findcardfromgamewithid(game, card_id)
        if not ok:
            update.message.reply_text("警告：找不到游戏中的卡，数据出现不一致！")
            sendtoAdmin("警告：游戏内外卡片信息出现不一致，位置：/modify")
            return False
        rtmsg, ok = modifycardinfo(cardi, context.args[1], context.args[2])
        if not ok:
            update.message.reply_text(rtmsg)
            return False
        update.message.reply_text("修改了游戏中的卡片！\n"+rtmsg)
        writecards(ON_GAME)
        return True
    # 处理有权限的非BOT控制者，即kp
    kpid = update.message.from_user.id
    if len(context.args) <= 3 or context.args[3] != "game":
        cardi, ok = findcardwithid(card_id)
        if not ok:
            return errorHandler(update, "找不到该ID对应的卡。")
        if getkpid(cardi.groupid) != kpid:
            return errorHandler(update, "没有权限", True)
        rtmsg, ok = modifycardinfo(cardi, context.args[1], context.args[2])
        if not ok:
            update.message.reply_text(rtmsg)
            return False
        update.message.reply_text("修改了游戏外的卡片！\n"+rtmsg)
        writecards(CARDS_DICT)
        return True
    game, ok = findgamewithkpid(kpid)
    if not ok:
        return errorHandler(update, "没有进行中的游戏", True)
    cardi, ok = findcardfromgamewithid(card_id)
    if not ok:
        return errorHandler(update, "找不到游戏中的卡")
    rtmsg, ok = modifycardinfo(cardi, context.args[1], context.args[2])
    if not ok:
        update.message.reply_text(rtmsg)
        return False
    update.message.reply_text("修改了游戏中的卡片！\n"+rtmsg)
    writecards(ON_GAME)
    return True


def changeid(update: Update, context: CallbackContext) -> bool:
    """修改卡片id。卡片的所有者或者KP均有使用该指令的权限。

    指令格式：
    `/changeid --cardid --newid`

    如果`newid`已经被占用，则指令无效。
    这一行为将同时改变游戏内以及游戏外的卡id。"""
    if len(context.args) < 2:
        return errorHandler(update, "至少需要两个参数。")
    if not botdice.isint(context.args[0]) or not botdice.isint(context.args[1]):
        return errorHandler(update, "参数错误", True)
    oldid = int(context.args[0])
    newid = int(context.args[1])
    if newid < 0:
        return errorHandler(update, "负数id无效", True)
    if newid == oldid:
        return errorHandler(update, "前后id相同", True)
    if newid in ID_POOL:
        return errorHandler(update, "该ID已经被占用")
    cardi, ok = findcardwithid(oldid)
    if not ok:
        return errorHandler(update, "找不到该ID对应的卡")
    plid = update.message.from_user.id
    gpid = cardi.groupid
    if plid != ADMIN_ID and cardi.playerid != plid and getkpid(gpid) != plid:
        return errorHandler(update, "非控制者且没有权限", True)
    # 有修改权限，开始处理
    if oldid in ID_POOL:
        ID_POOL.pop(ID_POOL.index(oldid))
    ID_POOL.append(newid)
    ID_POOL.sort()
    CARDS_DICT[gpid][newid] = CARDS_DICT[gpid].pop(oldid)
    CARDS_DICT[gpid][newid].id = newid
    writecards(CARDS_DICT)
    if "name" in cardi.info and cardi.info["name"] != "":
        rtmsg = "修改了卡片："+cardi.info["name"]+"的id至"+str(newid)
    else:
        rtmsg = "修改了卡片：No name 的id至"+str(newid)
    # 判断游戏是否也在进行，进行的话也要修改游戏内的卡
    game, ok = findgame(gpid)
    if ok:
        card2, ok = findcardfromgamewithid(game, oldid)
        if not ok:
            errorHandler(update, "游戏内没有找到对应的卡")
            sendtoAdmin("游戏内外数据不一致，位置：changeid")
        else:
            rtmsg += "\n游戏内id同步修改了。"
        card2.id = newid
        writegameinfo(ON_GAME)
    update.message.reply_text(rtmsg)
    return True


def changecardgpid(oldgpid: int, newgpid: int) -> bool:
    """函数`changegroup`的具体实现"""
    if newgpid not in CARDS_DICT:  # 直接将整个字典pop出来
        CARDS_DICT[newgpid] = CARDS_DICT.pop(oldgpid)
        for cdid in CARDS_DICT[newgpid]:
            CARDS_DICT[newgpid][cdid].groupid = newgpid
    else:  # 因为目标群有卡，不可以直接复制，遍历原群所有键
        for cdid in CARDS_DICT[oldgpid]:
            CARDS_DICT[newgpid][cdid] = CARDS_DICT[oldgpid].pop(cdid)
            CARDS_DICT[newgpid][cdid].groupid = newgpid
        CARDS_DICT.pop(oldgpid)
    writecards(CARDS_DICT)


def changegroup(update: Update, context: CallbackContext) -> bool:
    """修改卡片的所属群。
    一般只用于卡片创建时输入了错误的群id。
    比较特殊的情形：
    如果需要将某个群的所有卡片全部转移到另一个群，
    第一个参数写为负数的`groupid`即可。这一操作需要原群的kp权限。
    在原群进行游戏时，这个指令无效。

    指令格式：
    `/changegroup --groupid/--cardid --newgroupid`
    """
    if len(context.args) < 2:
        return errorHandler(update, "至少需要2个参数")
    if not botdice.isint(context.args[0]) or not botdice.isint(context.args[1]):
        return errorHandler(update, "参数错误", True)
    newgpid = int(context.args[1])
    if newgpid >= 0:
        return errorHandler(update, "转移的目标群id应该是负数", True)
    if int(context.args[0]) < 0:  # 转移全部群卡片
        oldgpid = int(context.args[0])
        _, ok = findgame(oldgpid)
        if ok:
            return errorHandler(update, "游戏正在进行，无法转移")
        kpid = update.message.from_user.id
        if getkpid(oldgpid) != kpid and kpid != ADMIN_ID:
            return errorHandler(update, "没有权限", True)
        if len(CARDS_DICT[oldgpid]) == 0:
            return errorHandler(update, "原群没有卡片！")
        # 检查权限通过
        numofcards = len(CARDS_DICT[oldgpid])
        changecardgpid(oldgpid, newgpid)
        update.message.reply_text(
            "操作成功，已经将"+str(numofcards)+"张卡片从群："+str(oldgpid)+"移动到群："+str(newgpid))
        return True
    # 转移一张卡片
    cdid = int(context.args[0])
    cardi, ok = findcardwithid(cdid)
    if not ok:
        return errorHandler(update, "找不到这个id的卡片", True)
    oldgpid = cardi.groupid
    _, ok = findgame(oldgpid)
    if ok:
        return errorHandler(update, "游戏正在进行，无法转移")
    if newgpid not in CARDS_DICT:
        CARDS_DICT[newgpid] = {}
    CARDS_DICT[newgpid][cdid] = CARDS_DICT[oldgpid].pop(cdid)
    CARDS_DICT[newgpid][cdid].groupid = newgpid
    writecards(CARDS_DICT)
    cardname = "No name"
    if "name" in cardi.info and cardi.info["name"] != "":
        cardname = cardi.info["name"]
    update.message.reply_text(
        "操作成功，已经将卡片"+cardname+"从群："+str(oldgpid)+"移动到群："+str(newgpid))
    return True


def randombackground(update: Update, context: CallbackContext) -> bool:
    """生成随机的背景故事。

    获得当前发送者修改中的卡，生成随机的背景故事并写入。"""
    plid = update.message.from_user.id
    card1, ok = findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    # 随机信仰
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
    writecards(CARDS_DICT)
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
    card1, ok = findcard(plid)
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
    writecards(CARDS_DICT)
    return True


# setbkground --bkgroundname --bkgroundinfo...: Need at least 2 args


def setbkground(update: Update, context: CallbackContext) -> bool:
    """设置背景信息。

    指令格式如下：
    `/setbkground bkgroundname bkgroudinfo...`

    其中第一个参数是背景的名称，只能是下面几项之一：

    `description`故事、
    `faith`信仰、
    `vip`重要之人、
    `exsigplace`意义非凡之地、
    `precious`珍视之物、
    `speciality`性格特质、
    `dmg`曾经受过的伤、
    `terror`恐惧之物、
    `myth`神秘学相关物品、
    `thirdencounter`第三类接触。

    第二至最后一个参数将被空格连接成为一段文字，填入背景故事中。"""
    plid = update.message.from_user.id
    if len(context.args) <= 1:
        update.message.reply_text(
            "Please use '/setbkground bkgroundname bkgroudinfo' to set background story.")
        return False
    card1, ok = findcard(plid)
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
    writecards(CARDS_DICT)
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
    # KP 进行
    if update.message.from_user.id == getkpid(gpid):
        if game.kpctrl == -1:
            return errorHandler(update, "请先切换到你的卡")
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
    initrules(gpid)
    greatfailrule = GROUP_RULES[gpid].greatfail
    if (sanity < 50 and check >= greatfailrule[2] and check <= greatfailrule[3]) or (sanity >= 50 and check >= greatfailrule[0] and check <= greatfailrule[1]):  # 大失败
        rttext += "大失败"
        anstype = "大失败"
    elif check > sanity:  # check fail
        rttext += "失败"
        anstype = "失败"
    else:
        rttext += ""
        anstype = ""
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
    """使用已有信息添加一张卡片，模板使用的是NPC/怪物模板。指令格式如下：

    `/addcard --attr_1 --val_1 --attr_2 --val_2 …… --attr_n -- val_n`，
    其中`attr`是卡的直接属性，或卡的某个属性（字典）中的键。不可以直接添加tempstatus这个属性。
    `name`和背景信息不支持空格，如果要设置这一项信息，需要之后用别的指令来修改。

    卡的属性只有三种类型的值：`int`, `str`, `bool`，函数会自动判断对应的属性是什么类型，
    其中`bool`类型`attr`对应的`val`只能是`true`, `True`, `false`, `False`之一。

    如果遇到无法识别的属性，将无法创建卡片。
    参数中，必须的`attr`之一为`groupid`，如果找不到`groupid`将无法添加卡片。
    `playerid`会自动识别为发送者，无需填写`playerid`。
    指令使用者是KP的情况下，才可以指定`playerid`这个属性，否则卡片无效。
    给定`id`属性的话，在指定的卡id已经被占用的时候，会重新自动选取。"""
    if isgroupmsg(update):
        return errorHandler(update, "向我发送私聊消息来添加卡", True)
    if len(context.args) == 0:
        return errorHandler(update, "需要参数")
    if (len(context.args)//2)*2 != len(context.args):
        update.message.reply_text("参数长度应该是偶数")
    t = createcard.templateNewCard()
    # 遍历args获取attr和val
    for i in range(0, len(context.args), 2):
        argname: str = context.args[i]
        argval = context.args[i+1]
        dt = findattrindict(t, argname)
        if not dt:  # 可能是技能，否则返回
            if argname in SKILL_DICT or argname == "母语" or argname == "闪避":
                dt = t["skill"]
                dt[argname] = 0  # 这一行是为了防止之后判断类型报错
            else:
                return errorHandler(update, "属性 "+argname+" 在角色卡模板中没有找到")
        if isinstance(dt[argname], dict):
            return errorHandler(update, argname+"是dict类型，不可直接赋值")
        if isinstance(dt[argname], bool):
            if argval == "false" or argval == "False":
                argval = False
            elif argval == "true" or argval == "True":
                argval = True
            if not isinstance(argval, bool):
                return errorHandler(update, argname+"应该为bool类型")
            dt[argname] = argval
        elif isinstance(dt[argname], int):
            if not botdice.isint(argval):
                return errorHandler(update, argname+"应该为int类型")
            dt[argname] = int(argval)
        else:
            dt[argname] = argval
    # 参数写入完成
    # 检查groupid是否输入了
    if t["groupid"] == 0:
        return errorHandler(update, "需要groupid！")
    initrules(t["groupid"])
    # 检查是否输入了以及是否有权限输入playerid
    if not isfromkp(update):
        if t["playerid"] != 0 and t["playerid"] != update.effective_chat.id:
            return errorHandler(update, "没有权限设置playerid")
        t["playerid"] = update.effective_chat.id
    else:
        kpid = update.effective_chat.id
        if getkpid(t["groupid"]) != kpid and t["playerid"] != 0 and t["playerid"] != kpid:
            return errorHandler(update, "没有权限设置playerid")
        if t["playerid"] == 0:
            t["playerid"] = kpid
    # 生成成功
    card1 = GameCard(t)
    # 添加id
    if "id" not in context.args or int(context.args[context.args.index("id")+1]) < 0 or card1.id in ID_POOL:
        update.message.reply_text("输入了已被占用的id，或id未设置。自动获取id")
        nid = 0
        while nid in ID_POOL:
            nid += 1
        card1.id = nid
    ID_POOL.append(card1.id)
    ID_POOL.sort()
    # 卡检查
    rttext = createcard.showchecks(card1)
    if rttext != "All pass.":
        update.message.reply_text(
            "卡片添加成功，但没有通过开始游戏的检查。")
        update.message.reply_text(rttext)
    else:
        update.message.reply_text("卡片添加成功")
    CARDS_DICT[card1.groupid][card1.id] = card1
    writecards(CARDS_DICT)
    return True


def helper(update: Update, context: CallbackContext) -> True:
    """查看指令对应函数的说明文档。

    `/help --command`查看指令对应的文档。"""
    if len(context.args) == 0:
        pass
        return True
    allfuncs = globals()
    funcname = context.args[0]
    if funcname == "help":
        funcname = "helper"
    if funcname in allfuncs and isfunction(allfuncs[funcname]) and allfuncs[funcname].__doc__:
        rttext: str = allfuncs[funcname].__doc__
        ind = rttext.find("    ")
        while ind != -1:
            rttext = rttext[:ind]+rttext[ind+4:]
            ind = rttext.find("    ")
        try:
            update.message.reply_text(rttext, parse_mode="MarkdownV2")
        except:
            update.message.reply_text("Markdown格式parse错误，请检查并改写文档")
            return False
        return True
    return errorHandler(update, "找不到这个指令，或这个指令没有帮助信息。")


def unknown(update: Update, context: CallbackContext) -> None:
    errorHandler(update, "没有这一指令", True)
