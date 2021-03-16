# -*- coding:utf-8 -*-

import asyncio
from typing import List, Optional, Tuple, TypeVar, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext

from basicfunc import *
from botclass import GameCard, Group, GroupGame, Player, dicebot
from cfg import *
from dicefunc import *

_T = TypeVar("_T")


# 数据
"""
GROUP_KP_DICT: Dict[int, int]
CARDS_DICT: Dict[int, Dict[int, GameCard]]
ON_GAME: List[GroupGame]
HOLD_GAME: List[GroupGame]
GROUP_RULES: Dict[int, GroupRule]
CURRENT_CARD_DICT: Dict[int, Tuple[int, int]]
OPERATION: Dict[int, str] = {}

SKILL_DICT: dict
dicebot.joblist: dict



DETAIL_DICT: Dict[int, str] = {}  # 临时地存储详细信息

  # 在每个按钮的callback加上该标志，如果标志不相等则不处理
"""
# 数据操作

SKILL_PAGES: List[List[str]]


def sendtoAdmin(msg: str) -> None:
    dicebot.updater.bot.send_message(chat_id=ADMIN_ID, text=msg)

# 检测json文件能否正常读取


# 读取完成
dicebot.updater.bot.send_message(
    chat_id=ADMIN_ID, text="Bot is live!")

# Update相关


def getchatid(update: Update) -> int:
    """返回effective_chat.id"""
    return update.effective_chat.id


def getmsgfromid(update: Update) -> int:
    """返回message.from_user.id"""
    return update.message.from_user.id


def isprivatemsg(update: Update) -> bool:
    if update.effective_chat.type == "private":
        return True
    return False


def isgroupmsg(update: Update) -> bool:
    if update.effective_chat.type.find("group") != -1:
        return True
    return False


def getgp(gpid: int) -> Optional[Group]:
    return dicebot.getgp(gpid)


def initgroup(gpid: int) -> Optional[Group]:
    """若gpid未存储过，创建Group对象并返回，否则返回None"""
    gp = getgp(gpid)
    if gp:
        return None
    return dicebot.creategp(gpid)


def forcegetgroup(gpid: int) -> Group:
    gp = getgp(gpid)
    if gp is None:
        return initgroup(gpid)
    return gp


def updateinitgroup(update: Update) -> Optional[Group]:
    if not isgroupmsg(update):
        return None
    gpid = getchatid(update)
    return initgroup(gpid)


def getplayer(plid: int) -> Optional[Player]:
    if plid not in dicebot.players:
        return None
    return dicebot.players[plid]


def initplayer(plid: int) -> Optional[Player]:
    """若plid未存储过，创建Player对象并返回，否则返回None"""
    pl = getplayer(plid)
    if pl:
        return None
    return dicebot.createplayer(plid)


def forcegetplayer(plid: int) -> Player:
    pl = getplayer(plid)
    if pl is None:
        return initplayer(plid)
    return pl


def updateinitplayer(update: Update) -> Optional[Player]:
    if not isprivatemsg(update):
        return None
    plid = getchatid(update)
    return initplayer(plid)


def chatinit(update: Update) -> Union[Player, Group, None]:
    """所有指令使用前调用该函数"""
    if isprivatemsg(update):
        return updateinitplayer(update)
    if isgroupmsg(update):
        return updateinitgroup(update)
    return None


def autoswitchhint(plid: int) -> None:
    dicebot.updater.bot.send_message(chat_id=plid, text="创建新卡时，控制自动切换到新卡")


def executilsfunc(com: str) -> str:
    """使用utils的函数执行一句指令。这个函数应禁止非管理者调用"""
    try:
        exec("t="+com, {})
        return str(locals()['t'])
    except:
        return "执行失败"

# 卡片相关：查 增 删


def cardpop(gpid: int, cdid: int) -> Optional[GameCard]:
    """删除一张卡并返回其数据。返回None则删除失败"""
    # 删除group索引
    gp = getgp(gpid)
    if not gp:
        return None
    if cdid not in gp.cards:
        return None
    card = gp.cards.pop(cdid)
    dicebot.writegroup(gpid)
    # 删除player索引
    pl = getplayer(card.playerid)
    if not pl:
        return None
    pl.cards.pop(cdid)
    if pl.controlling and pl.controlling.id == cdid:
        pl.controlling = None
    dicebot.writeplayer(card.playerid)
    # 删除id
    i = dicebot.allids.index(card.id)
    dicebot.allids = dicebot.allids[:i]+dicebot.allids[i+1:]
    return gp.cards.pop(cdid)


def cardadd(card: GameCard, gpid: int) -> bool:
    """向群内添加一张卡，当卡id重复时返回False"""
    if card.id in dicebot.allids:
        return False
    # 增加id
    dicebot.allids.append(card.id)
    dicebot.allids.sort()
    # 增加群索引
    gp = getgp(gpid)
    if not gp:
        dicebot.groups[gpid] = Group(gpid=gpid)
    card.group = gp
    gp.cards[card.id] = card
    dicebot.writegroup(gpid)
    # 增加pl索引
    pl = getplayer(card.playerid)
    if not pl:
        dicebot.players[card.playerid] = Player(plid=card.playerid)
        pl = dicebot.players[card.playerid]
    pl.cards[card.id] = card
    if pl.controlling:
        autoswitchhint(pl.id)
    pl.controlling = card
    dicebot.writeplayer(pl.id)
    return True


def getcard(gpid: int, cdid: int) -> Optional[GameCard]:
    gp = getgp(gpid)
    if not gp:
        return None
    card = gp.getcard(cdid)
    if not card:
        return None
    return card


# operation 查增删
def addOP(chatid: int, op: str) -> None:
    dicebot.operation[chatid] = op


def popOP(chatid) -> str:
    if chatid not in dicebot.operation:
        return ""
    return dicebot.operation.pop(chatid)


def getOP(chatid) -> str:
    if chatid not in dicebot.operation:
        return ""
    return dicebot.operation[chatid]


def createSkillPages(d: dict) -> List[List[str]]:
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


SKILL_PAGES = createSkillPages(dicebot.skilllist)
# id相关


def getallid() -> List[int]:
    return dicebot.allids()


def getnewids(n: int) -> List[int]:
    """获取n个新的卡id，这些id尽可能小"""
    ids = getallid()
    ans: List[int] = []
    nid = 0
    for _ in range(n):
        while nid in ids:
            nid += 1
        ans.append(nid)
        nid += 1
    return ans


def getoneid() -> int:
    return getnewids(1)[0]


# 查kp
def searchifkp(plid: int) -> bool:
    """判断plid是否至少是一个群的kp"""
    pl = getplayer(plid)
    if not pl:
        pl = initplayer(plid)
    return bool(len(pl.kpgroups))


def isfromkp(update: Update) -> bool:
    """判断消息发送者是否是kp。
    如果是私聊消息，只需要发送者是某群KP即返回True。如果是群聊消息，当发送者是本群KP才返回True"""
    if isprivatemsg(update):  # 私聊消息，搜索所有群判断是否是kp
        return searchifkp(getchatid(update))
    # 如果是群消息，判断该指令是否来自本群kp
    gpid = getchatid(update)
    gp = getgp(gpid)
    if not gp:
        dicebot.groups[gpid] = Group(gpid=gpid)
        return False
    if gp.kp is None or gp.kp.id != getmsgfromid(update):
        return False
    return True


def findcard(plid: int) -> Optional[GameCard]:
    """输入一个player的id，返回该player当前选择中的卡"""
    pl = getplayer(plid)
    if not pl:
        return None
    return pl.controlling


def hascard(plid: int, gpid: int) -> bool:
    """判断一个群内是否已经有pl的卡"""
    pl = getplayer(plid)
    if not pl:
        pl = initplayer(plid)
        return False
    for card in pl.cards.values():
        if card.group.id == gpid:
            return True
    return False


def findcardwithid(cdid: int) -> Optional[GameCard]:
    """输入一个卡id，返回这张卡"""
    for gp in dicebot.groups.values():
        if cdid in gp.cards:
            return gp.cards[cdid]
    return None


def getskillmax(card1: GameCard) -> int:
    aged, ok = skillcantouchmax(card1)
    rule = card1.group.rule
    if aged:
        skillmaxrule = rule.skillmaxAged
    else:
        skillmaxrule = rule.skillmax
    if ok:
        mm = skillmaxrule[1]
    else:
        mm = skillmaxrule[0]
    return mm


def getskilllevelfromdict(card1: GameCard, key: str) -> int:
    """从技能表中读取的技能初始值。

    如果是母语和闪避这样的与卡信息相关的技能，用卡信息来计算初始值"""
    if key in dicebot.skilllist:
        return dicebot.skilllist[key]
    if key == "母语":
        return card1.data.EDU
    if key == "闪避":
        return card1.data.DEX//2
    return -1


def makeIntButtons(lower: int, upper: int, keystr1: str, keystr2: str, step: int = 5, column: int = 4) -> List[list]:
    """返回一个InlineKeyboardButton组成的二维列表。按钮的显示文本是整数。
    `lower`表示最小值，`upper`表示最大值，均是按钮返回结果的一部分。
    `keystr1`, `keystr2`是`callback_data`的内容，按钮的`callback_data`结构为：
    ```
    keystr1+" "+keystr2+" "+str(integer)
    ```
    `step`参数表示按钮会遍历大于`lower`但小于`upper`的所有按钮的间隔。
    `column`参数表示返回的二维列表每行最多有多少个按钮。"""
    IDENTIFIER = dicebot.IDENTIFIER
    rtbuttons = [[]]
    if (lower//step)*step != lower:
        rtbuttons[0].append(InlineKeyboardButton(
            str(lower), callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(lower)))
        t = step+(lower//step)*step
    else:
        t = lower
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


def findgame(gpid: int) -> Optional[GroupGame]:
    """接收一个groupid，返回对应的GroupGame对象"""
    gp = getgp(gpid)
    if not gp:
        return None
    return gp.game


def findcardfromgame(game: GroupGame, plid: int) -> GameCard:
    """从`game`中返回对应的`plid`的角色卡"""
    for i in game.cards.values():
        if i.playerid == plid:
            return i
    return None


def findcardfromgamewithid(game: GroupGame, cdid: int) -> GameCard:
    """从`game`中返回`id`为`cdid`的角色卡"""
    for i in game.cards.values():
        if i.id == cdid:
            return i
    return None


def findDiscardCardsGroupIDTuple(plid: int) -> List[Tuple[Group, int]]:
    """返回`plid`对应的所有`discard`为`True`的卡的`(group, id)`对"""
    ans: List[int] = []
    pl = getplayer(plid)
    if not pl:
        return ans
    for card in pl.cards.values():
        if card.discard or card.groupid == -1:
            ans.append((card.group, card.id))
            if card.groupid == -1:
                card.discard = True
                dicebot.writegroup(card.groupid)
    return ans


def showcardinfo(card1: GameCard) -> str:  # show full card
    """调用`GameCard.__str__`返回`card1`的信息"""
    return str(card1)


def iskeyconstval(d: dict, keyname: str) -> bool:
    if isinstance(d[keyname], bool) or isinstance(d[keyname], str) or isinstance(d[keyname], int):
        return True
    return False


def showvalwithkey(d: dict, keyname: str) -> Optional[str]:
    """输入字典和键，格式化其值为字符串并输出"""
    if keyname not in d:
        return None
    val = d[keyname]
    rttext: str = ""
    if isinstance(val, dict):
        for key in val:
            rttext += key+": "+str(val[key])+"\n"
    elif not iskeyconstval(d, keyname):
        return None
    else:
        rttext = str(val)
    if rttext == "":
        rttext = "None"
    return rttext


def showattrinfo(update: Update, card1: GameCard, attrname: str) -> bool:
    """显示卡中某项具体的数据，并直接由`update`输出到用户。
    不能输出属性`tempstatus`下的子属性。
    如果获取不到`attrname`这个属性，返回False。"""
    rttext = showvalwithkey(card1.__dict__, attrname)
    if rttext is not None:
        update.message.reply_text(rttext)
        return True
    # 没有在最外层找到
    for keys in card1.__dict__:
        if not isinstance(card1.__dict__[keys], dict) or (keys == "tempstatus" and attrname != "global"):
            continue
        rttext = showvalwithkey(card1.__dict__[keys], attrname)
        if rttext is None:
            continue
        update.message.reply_text(rttext)
        return True
    update.message.reply_text("找不到这个属性！")
    return False


def modifythisdict(d: dict, attrname: str, val: str) -> Tuple[str, bool]:
    """修改一个字典`d`。`d`的键为`str`类型，值为`bool`, `int`, `str`其中之一。

    寻找`attrname`是否在字典中，如果不在字典中或键对应的值是`dict`类型，返回不能修改的原因以及`False`。
    否则，返回True的同时返回修改前的值的格式化。"""
    if isinstance(d[attrname], dict):
        return "不能修改dict类型", False
    if isinstance(d[attrname], bool):
        rtmsg = "False"
        if d[attrname]:
            rtmsg = "True"
        if val in ["F", "false", "False", "假"]:
            d[attrname] = False
            val = "False"
        elif val in ["T", "true", "True", "真"]:
            d[attrname] = True
            val = "True"
        else:
            return "无效的值", False
        return rtmsg, True
    if isinstance(d[attrname], int):
        if not isint(val):
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
    kp = getplayer(kpid)
    if not kp:
        return ans
    for card in kp.cards.values():
        if card.group.kp.id == kp.id:
            ans.append(card)
    return ans


def isingroup(gpid: int, userid: int) -> bool:
    """查询某个userid对应的用户是否在群里"""
    try:
        chat = dicebot.updater.bot.get_chat(chat_id=gpid)
        chat.get_member(user_id=userid)
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
    if not isprivatemsg(update) and not isgroupmsg(update):
        return False
    if needrecall and isgroupmsg(update) and isadmin(update, BOT_ID):
        recallmsg(update)
    else:
        if message == "找不到卡。":
            message += "请使用 /switch 切换当前操控的卡再试。"
        elif message.find("参数") != -1:
            message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"
        try:
            msg = update.message.reply_text(message, parse_mode="MarkdownV2")
        except:
            msg = update.message.reply_text(message)
        if message.find("私聊") != -1:
            rtbutton = [[InlineKeyboardButton(
                "跳转到私聊", callback_data="None", url="t.me/"+BOTUSERNAME)]]
            rp_markup = InlineKeyboardMarkup(rtbutton)
            msg.edit_reply_markup(reply_markup=rp_markup)
    return False


def listintersect(l1: List[_T], l2: List[_T]) -> List[_T]:
    if len(l1) > len(l2):
        l1, l2 = l2, l1
    ans: List[_T] = []
    for i in l1:
        if i in l2:
            ans.append(i)
    return ans


def changeplids(gpid: int, oldplid: int, newplid: int) -> None:
    """将某个群中所有`oldplid`持有的卡改为`newplid`持有。
    执行成功之后newplid对应的对象将会被创建"""
    gp = getgp(gpid)
    if not gp:
        return
    pl = getplayer(oldplid)
    if not pl:
        return
    gpcardids = list(gp.cards.keys())
    plcardids = list(pl.cards.keys())
    cardsids = listintersect(gpcardids, plcardids)
    if len(cardsids) == 0:
        return
    newpl = getplayer(newplid)
    if newpl is None:
        newpl: Player = initplayer(newplid)
    for key in cardsids:
        card = pl.cards[key]
        card.playerid = newplid
        card.player = newpl
        newpl.cards[key] = pl.cards.pop(key)
    if pl.controlling is not None:
        card = pl.controlling
        if card.groupid == gpid:
            pl.controlling = None
    dicebot.writegroup(gpid)
    dicebot.writeplayer(oldplid)
    dicebot.writeplayer(newplid)
    return


def changeKP(gpid: int, newkpid: int = 0) -> bool:
    """转移KP权限，接收参数：群id，新KP的id。
    会转移所有原KP控制的角色卡，包括正在进行的游戏。"""
    if newkpid < 0:
        return False
    gp = getgp(gpid)
    if not gp:
        initgroup(gpid)
        return False
    kp = gp.getkp()
    if not kp:
        return False
    if kp.id == newkpid:
        return False
    changeplids(gpid, kp.id, newkpid)
    newkp = forcegetplayer(newkpid)
    game = gp.game
    if game is not None:
        for cardi in game.kpcards.values():
            cardi.playerid = newkpid
        game.kpid = newkpid
    gp.kp = newkp
    dicebot.writegroup(gpid)
    dicebot.writeplayer(kp.id)
    dicebot.writeplayer(newkpid)
    return True


def makejobbutton() -> List[List[InlineKeyboardButton]]:
    """生成全部职业的按钮"""
    rtbuttons = [[]]
    for keys in dicebot.joblist:
        if len(rtbuttons[len(rtbuttons)-1]) == 3:
            rtbuttons.append([])
        rtbuttons[len(
            rtbuttons)-1].append(InlineKeyboardButton(keys, callback_data=dicebot.IDENTIFIER+" job "+keys))
    return rtbuttons


def skillcantouchmax(card1: GameCard) -> Tuple[bool, bool]:
    """判断一张卡当前是否可以新增一个专精技能。

    第一个返回值描述年龄是否符合Aged标准。第二个返回值描述在当前年龄下能否触摸到专精等级"""
    rules = card1.group.rule
    if card1.info.age > rules.skillmaxAged[3]:
        ans1 = True
        skillmaxrule = rules.skillmaxAged
    else:
        ans1 = False
        skillmaxrule = rules.skillmax
    countSpecialSkill = 0
    for skill in card1.skill.skills:
        if card1.skill.skills[skill] > skillmaxrule[0]:
            countSpecialSkill += 1
    for skill in card1.interest.skills:
        if card1.interest.skills[skill] > skillmaxrule[0]:
            countSpecialSkill += 1
    if countSpecialSkill >= skillmaxrule[2]:
        return ans1, False
    return ans1, True


def skillmaxval(skillname: str, card1: GameCard, ismainskill: bool) -> int:
    """通过cost规则，返回技能能达到的最高值。"""
    aged, ok = skillcantouchmax(card1)
    gp = forcegetgroup(card1.groupid)
    if aged:
        skillrule = gp.rule.skillmaxAged
    else:
        skillrule = gp.rule.skillmax
    if ok:
        maxval = skillrule[1]
    else:
        maxval = skillrule[0]
    if skillname == "信用":
        if card1.info.job in dicebot.joblist:
            maxval = min(maxval, dicebot.joblist[card1.info.job][1])
    basicval = -1
    if ismainskill:
        pts = card1.skill.points
        if skillname in card1.skill.skills:
            basicval = card1.skill.skills[skillname]
    else:
        pts = card1.interest.points
        if skillname in card1.interest.skills:
            basicval = card1.interest.skills[skillname]
    costrule = gp.rule.skillcost
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
        if skillname in card1.skill.skills:
            basicval = card1.skill.skills[skillname]
    else:
        if skillname in card1.interest.skills:
            basicval = card1.interest.skills[skillname]
    if basicval == -1:
        basicval = getskilllevelfromdict(card1, skillname)
    if skillval == basicval:
        return 0
    gp = card1.group
    costrule = gp.rule.skillcost
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
    if card1.skill.points == 0:
        return errorHandler(update, "你已经没有剩余点数了")
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, True):
        return errorHandler(update, "目标技能点太高或太低")
    # 计算点数消耗
    costval = evalskillcost(skillname, skillvalue, card1, True)
    card1.skill.points -= costval
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.skill.skills[skillname] = skillvalue
    dicebot.writegroup(card1.groupid)
    return True


def addsgskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """添加一个建议的技能。直接调用`addmainskill`完成。"""
    if not addmainskill(skillname, skillvalue, card1, update):
        return False
    card1.suggestskill.skills.pop(skillname)
    dicebot.writegroup(card1.groupid)
    return True


def addintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """该函数对没有`skillname`这项技能的卡使用。将兴趣技能值设置为`skillvalue`。"""
    if card1.interest.points == 0:
        return errorHandler(update, "你已经没有剩余点数了")
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    # 计算点数消耗
    costval = evalskillcost(skillname, skillvalue, card1, False)
    card1.interest.points -= costval
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.interest.skills[skillname] = skillvalue
    dicebot.writegroup(card1.groupid)
    return True


def cgmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:  # Change main skill level
    """修改主要技能的值。如果将技能点调低，返还技能点数。"""
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, True):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, True)
    card1.skill.points -= costval
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.skill.skills[skillname] = skillvalue
    dicebot.writegroup(card1.groupid)
    return True


# Change interest skill level
def cgintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """修改兴趣技能的值。如果将技能点调低，返还技能点数。"""
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, False)
    card1.interest.points -= costval
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.interest.skills[skillname] = skillvalue
    dicebot.writegroup(card1.groupid)
    return True


def addcredit(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    update.message.reply_text("请先设置信用！")
    gp = card1.group
    if card1.info.job in dicebot.joblist:
        m = dicebot.joblist[card1.info.job][0]
        mm = dicebot.joblist[card1.info.job][1]
    else:
        aged, ok = skillcantouchmax(card1)
        if aged:
            skillmaxrule = gp.rule.skillmaxAged
        else:
            skillmaxrule = gp.rule.skillmax
        m = 0
        if ok:
            mm = skillmaxrule[1]
        else:
            mm = skillmaxrule[0]
    rtbuttons = makeIntButtons(m, mm, "addmainskill", "信用")
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称：信用", reply_markup=rp_markup)
    return True


def cgcredit(update: Update, card1: GameCard) -> bool:
    m = 0
    mm = -1
    if card1.info.job in dicebot.joblist:
        m = dicebot.joblist[card1.info.job][0]
        mm = dicebot.joblist[card1.info.job][1]
    else:
        mm = skillmaxval("信用", card1, True)
    rtbutton = makeIntButtons(m, mm, "cgmainskill", "信用")
    rp_markup = InlineKeyboardMarkup(rtbutton)
    update.message.reply_text(text="修改信用，现在还剩"+str(card1.skill.points)+"点，当前信用："+str(
        card1.skill.skills["信用"]), reply_markup=rp_markup)
    return True


def showskillpages(page: int, card1: GameCard) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    IDENTIFIER = dicebot.IDENTIFIER
    thispageskilllist = SKILL_PAGES[page]
    rttext = "添加/修改兴趣技能，目前的数值/基础值如下："
    rtbuttons = [[]]
    for key in thispageskilllist:
        if key in card1.skill.skills or key in card1.suggestskill.skills:
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if key in card1.interest.skills:
            rttext += "（已有技能）"+key+"："+str(card1.interest.skills[key])+"\n"
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
###########################################################


def buttonjob(query: CallbackQuery, card1: GameCard, args: List[str]) -> bool:
    jobname = args[1]
    if len(args) == 2:
        # 切换至显示职业详情
        jobinfo = dicebot.joblist[jobname]
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
        IDENTIFIER = dicebot.IDENTIFIER
        rtbuttons = [[
            InlineKeyboardButton(
                text="确认", callback_data=IDENTIFIER+" job "+jobname+" True"),
            InlineKeyboardButton(
                text="返回", callback_data=IDENTIFIER+" job "+jobname+" False")
        ]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_reply_markup(rp_markup)
        return True
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    confirm = args[2]  # 只能是True，或False
    if confirm == "False":
        rtbuttons = makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("请选择职业查看详情：")
        query.edit_message_reply_markup(rp_markup)
        return True
    # 确认完成
    card1.info.job = jobname
    query.edit_message_text(
        "职业设置为："+jobname+"\n现在你可以用指令 /addskill 添加技能，首先需要设置信用点。")
    if not generatePoints(card1, jobname):
        query.edit_message_text(
            "生成技能点出错！")
        sendtoAdmin("生成技能出错，位置：buttonjob")
        return False
    for i in range(3, len(dicebot.joblist[jobname])):  # Classical jobs
        card1.suggestskill.set(dicebot.joblist[jobname][i], getskilllevelfromdict(
            card1, dicebot.joblist[jobname][i]))   # int
    dicebot.writegroup(card1.groupid)
    return True


def buttonaddmainskill(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue)
        card1.skill.points -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        dicebot.writegroup(card1.groupid)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttoncgmainskill(query: CallbackQuery,  card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue)
        card1.skill.points -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        dicebot.writegroup(card1.group)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.skill.get(args[1])), reply_markup=rp_markup)
    return True


def buttonaddsgskill(query: CallbackQuery,  card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue)
        card1.skill.points -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        card1.suggestskill.pop(args[1])
        dicebot.writegroup(card1.group)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttonaddintskill(query: CallbackQuery,  card1: Optional[GameCard], args: List[str]) -> bool:
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
        needpt = evalskillcost(args[1], skvalue, card1, False)
        card1.interest.set(args[1], skvalue)
        card1.interest.points -= needpt
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
        dicebot.writegroup(card1.group)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加兴趣技能。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttoncgintskill(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, False)
        card1.interest.set(args[1], skvalue)
        card1.interest.points -= needpt
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
        dicebot.writegroup(card1.group)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.interest.get(args[1])), reply_markup=rp_markup)
    return True


def buttonstrdec(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    strdecval = int(args[2])
    card1, rttext, needcon = choosedec(card1, strdecval)
    if rttext == "输入无效":
        query.edit_message_text(rttext)
        return False
    if needcon:
        rttext += "\n使用 /setcondec 来设置CON（体质）下降值。"
    else:
        generateOtherAttributes(card1)
    query.edit_message_text(rttext)
    dicebot.writegroup(card1.group)
    return True


def buttoncondec(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        query.edit_message_text(text="找不到卡。")
        return False
    condecval = int(args[2])
    card1, rttext = choosedec2(card1, condecval)
    query.edit_message_text(rttext)
    if rttext == "输入无效":
        return False
    generateOtherAttributes(card1)
    dicebot.writegroup(card1.group)
    return True


def buttondiscard(query: CallbackQuery, plid: int, args: List[str]) -> bool:
    gpid, cdid = int(args[1]), int(args[2])
    pl = forcegetplayer(plid)
    if pl.controlling is not None and pl.controlling.groupid == gpid and pl.controlling.id == cdid:
        pl.controlling = None
        dicebot.writeplayer(plid)
    if gpid not in CARDS_DICT or cdid not in CARDS_DICT[gpid] or CARDS_DICT[gpid][cdid].playerid != plid or not CARDS_DICT[gpid][cdid].discard:
        query.edit_message_text("没有找到卡片。")
        return False
    detailinfo = "删除了：\n"+str(CARDS_DICT[gpid][cdid])
    DETAIL_DICT[plid] = detailinfo
    CARDS_DICT[gpid].pop(cdid)
    if len(CARDS_DICT[gpid]) == 0:
        CARDS_DICT.pop(gpid)
    query.edit_message_text("删除了一张卡片，使用 /details 查看详细信息。\n该删除操作不可逆。")
    return True


def buttonswitch(query: CallbackQuery, plid: int, args: List[str]) -> bool:
    gpid, cdid = int(args[1]), int(args[2])
    if gpid not in CARDS_DICT or cdid not in CARDS_DICT[gpid] or CARDS_DICT[gpid][cdid].playerid != plid:
        query.edit_message_text("没有找到卡片。")
        return False
    CURRENT_CARD_DICT[plid] = (gpid, cdid)
    writecurrentcarddict(CURRENT_CARD_DICT)
    cardi = CARDS_DICT[gpid][cdid]
    if "name" not in cardi.info or cardi.info["name"] == "":
        query.edit_message_text("修改成功，现在操作的卡id是："+str(cdid))
    else:
        query.edit_message_text("修改成功，现在操作的卡是："+cardi.info["name"])
    return True


def buttonswitchkp(query: CallbackQuery, kpid: int, args: List[str]) -> bool:
    ctrlid = int(args[1])
    game = findgamewithkpid(kpid)
    if not game:
        query.edit_message_text("没有找到游戏。")
        return False
    cardi = findcardfromgamewithid(game, ctrlid)
    if not cardi or cardi.playerid != kpid:
        query.edit_message_text("没有找到这张npc卡。")
        return False
    game.kpctrl = ctrlid
    writegameinfo(ON_GAME)
    query.edit_message_text("修改操纵的npc卡成功，id为："+str(ctrlid))
    return True


def buttonsetsex(query: CallbackQuery, plid: int,  args: List[str]) -> bool:
    cardi = findcard(plid)
    if not cardi:
        query.edit_message_text("找不到卡。")
        return False
    sex = args[1]
    if sex == "other":
        addOP(plid, "setsex")
        query.edit_message_text("请输入具体的性别：")
        return True
    cardi.info["sex"] = sex
    rttext = "性别设定为"
    if sex == "male":
        rttext += "男性。"
    else:
        rttext += "女性。"
    query.edit_message_text(rttext)
    return True


def getkpctrl(game: GroupGame) -> GameCard:
    for cardi in game.cards:
        if cardi.id == game.kpctrl and cardi.playerid == game.kpid:
            return cardi
    return None


def changecardgpid(oldgpid: int, newgpid: int) -> bool:
    """函数`changegroup`的具体实现。不会检查oldgpid是否是键"""
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


def groupcopy(oldgpid: int, newgpid: int, copyall: bool) -> bool:
    if findgame(oldgpid) or findgame(newgpid):
        return False
    kpid = getkpid(oldgpid)
    if newgpid not in CARDS_DICT:
        CARDS_DICT[newgpid] = {}
    if oldgpid in CARDS_DICT:
        i = 0
        newids = getnewids(len(CARDS_DICT[oldgpid]))
        for cdid in CARDS_DICT[oldgpid]:
            if not copyall and CARDS_DICT[oldgpid][cdid].playerid != kpid:
                continue
            nid = newids[i]
            i += 1
            CARDS_DICT[newgpid][nid] = GameCard(
                CARDS_DICT[oldgpid][cdid].__dict__)
            CARDS_DICT[newgpid][nid].id = nid
            CARDS_DICT[newgpid][nid].groupid = newgpid
    popallempties(CARDS_DICT)
    writecards(CARDS_DICT)
    GROUP_RULES[newgpid] = GroupRule(
        copy.deepcopy(GROUP_RULES[oldgpid].__dict__))
    writerules(GROUP_RULES)
    return True


def addskill0(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """表示指令/addskill 中没有参数的情况。
    创建技能按钮来完成技能的添加。

    因为兴趣技能过多，使用可以翻页的按钮列表。"""
    rtbuttons = [[]]
    # If card1.skill.points is 0, turn to interest.
    # Then it must be main skill. After all main skills are added, add interest skills.
    if card1.skill.points > 0:
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
            update.message.reply_text("剩余点数："+str(
                card1.skill.points)+"\n请选择一项主要技能用于增加技能点", reply_markup=rp_markup)
            return True
        # GOOD TRAP: addsgskill
        for keys in card1.suggestskill:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.suggestskill[keys]), callback_data=IDENTIFIER+" "+"addsgskill "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("剩余点数："+str(
            card1.skill.points)+"\n请选择一项主要技能", reply_markup=rp_markup)
        return True
    # turn to interest.
    if card1.interest.points <= 0:  # HIT BAD TRAP
        return errorHandler(update, "你已经没有多余的点数了，如果需要重新设定某项具体技能的点数，用 '/addskill 技能名'")
    # GOOD TRAP: add interest skill.
    # 显示第一页，每个参数后面带一个当前页码标记
    rttext, rtbuttons = showskillpages(0, card1)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(rttext, reply_markup=rp_markup)
    return True


def addskill1(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """该函数在`/addskill`接收且仅接收一个参数时调用。制作技能数值表。"""
    # skillname is already checked if in SKILL_DICT
    # First search if args skillname in skill or suggestskill.
    # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
    # Show button for numbers
    skillname = context.args[0]
    m = getskilllevelfromdict(card1, skillname)
    if skillname == "信用" and card1.info["job"] in dicebot.joblist:
        m = max(m, dicebot.joblist[card1.info["job"]][0])
    if skillname in card1.skill:  # GOOD TRAP: cgmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.skill[skillname]), reply_markup=rp_markup)
        return True
    if skillname in card1.suggestskill:  # GOOD TRAP: addsgskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.interest:  # GOOD TRAP: cgintskill
        mm = skillmaxval(skillname, card1, False)
        rtbuttons = makeIntButtons(m, mm, "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.interest[skillname]), reply_markup=rp_markup)
        return True
    if card1.skill.points > 0:  # GOOD TRAP: addmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname, reply_markup=rp_markup)
        return True
    mm = skillmaxval(skillname, card1, False)
    rtbuttons = (m, mm, "addintskill", skillname)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "添加兴趣技能。剩余技能点："+str(card1.interest.points)+" 技能名称："+skillname, reply_markup=rp_markup)
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
    if card1.skill.points > 0 and card1.interest.points > 0:
        return errorHandler(update, "请使用'/addskill skillname skillvalue main/interest'来指定技能种类！")
    # HIT GOOD TRAP
    if card1.skill.points > 0:
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


async def timer():
    """凌晨3点进行一次自检"""
    istime = False
    clockhour = 3
    clockmin = 0
    while True:
        nowtime = time.localtime(time.time())
        if not istime and nowtime.tm_hour == clockhour and nowtime.tm_min == clockmin:
            sendtoAdmin("bot自检中！")
            botcheckdata("bot自检中……")
            istime = True
            continue
        if istime:
            if nowtime.tm_min != clockmin:
                istime = False
            await asyncio.sleep(10)
            continue
        await asyncio.sleep(30)


def gamepop(gpid: int) -> GroupGame:
    """终止一场游戏。`/abortgame`的具体实现。"""
    global ON_GAME
    for i in range(len(ON_GAME)):
        if ON_GAME[i].groupid == gpid:
            t = ON_GAME[i]
            ON_GAME = ON_GAME[:i]+ON_GAME[i+1:]
            writegameinfo(ON_GAME)
            return t
    return None


def holdgamepop(gpid: int) -> GroupGame:
    """pop一场暂停的游戏。`/continuegame`的具体实现。"""
    global HOLD_GAME
    for i in range(len(HOLD_GAME)):
        if HOLD_GAME[i].groupid == gpid:
            t = HOLD_GAME[i]
            HOLD_GAME = HOLD_GAME[:i]+HOLD_GAME[i+1:]
            writeholdgameinfo(HOLD_GAME)
            return t
    return None


def isholdinggame(gpid: int) -> bool:
    for game in HOLD_GAME:
        if game.groupid == gpid:
            return True
    return False


def getgamecardsid(game: GroupGame) -> List[int]:
    ans: List[int] = []
    for cardi in game.cards:
        ans.append(cardi.id)
    return ans


def addcardtogame(game: GroupGame, cardi: GameCard) -> None:
    newgamecard = GameCard(cardi.__dict__)
    game.cards.append(newgamecard)
    if game.kpid == cardi.playerid:
        game.kpcards.append(newgamecard)
    writegameinfo(ON_GAME)


def popallempties(d: Dict[Any, dict]) -> bool:
    """将二层字典中一层的空值对应的键删除。如果有空值，返回True，否则返回False"""
    ans: bool = False
    for key in d:
        if not d[key]:
            ans = True
            d.pop(key)
    return ans


def botcheckdata(msg: str, recall: bool = True):
    """进行一次数据自检，检查是否有群因为升级而id变化了"""
    gpids: List[int] = []
    for key in CARDS_DICT:
        gpids.append(key)
    for key in GROUP_KP_DICT:
        if key not in gpids:
            gpids.append(key)
    for gpid in gpids:
        try:
            sendmsg = dicebot.updater.bot.send_message(
                chat_id=gpid, text=msg)
        except error.ChatMigrated as err:
            sendtoAdmin(
                "群id发生变化，原群id："+str(gpid)+"变化为"+str(err.new_chat_id))
            if popallempties(CARDS_DICT):
                writecards(CARDS_DICT)
            ok = findgame(err.new_chat_id)
            for game in ON_GAME:
                if game.groupid == gpid:
                    if ok:  # 直接丢弃旧的游戏数据
                        break
                    game.groupid = err.new_chat_id
                    writegameinfo(ON_GAME)
                    break
            if gpid in CARDS_DICT:
                sendtoAdmin("强制转移群数据中！！")
                changecardgpid(gpid, err.new_chat_id)
                sendtoAdmin("转移群数据完成")
            if gpid in GROUP_KP_DICT:
                GROUP_KP_DICT[err.new_chat_id] = GROUP_KP_DICT.pop(
                    gpid)
                writekpinfo(GROUP_KP_DICT)
        except:
            return False
        else:
            if recall:
                sendmsg.delete()
    sendtoAdmin("自检完成！")
    return True


def getname(cardi: GameCard) -> str:
    """获取角色卡名字信息。
    角色卡没有名字时，返回字符串`None`"""
    if "name" not in cardi.info or cardi.info["name"] == "":
        return "None"
    return cardi.info["name"]


def cardsetage(update: Update, cardi: GameCard, age: int) -> bool:
    if "AGE" in cardi.info and cardi.info["AGE"] > 0:
        popOP(getchatid(update))
        return errorHandler(update, "已经设置过年龄了。")
    if age < 17 or age > 99:
        return errorHandler(update, "年龄应当在17-99岁。")
    cardi.info["AGE"] = age
    cardi.cardcheck["check1"] = True
    cardi, detailmsg = generateAgeAttributes(cardi)
    update.message.reply_text(
        "年龄设置完成！详细信息如下：\n"+detailmsg+"\n如果年龄不小于40，或小于20，需要使用指令'/setstrdec number'设置STR减值。如果需要帮助，使用 /createcardhelp 来获取帮助。")
    if cardi.cardcheck["check2"]:
        generateOtherAttributes(cardi)
    writecards(CARDS_DICT)
    return True


def cardsetsex(update: Update, cardi: GameCard, sex: str) -> bool:
    if sex in ["男", "男性", "M", "m", "male", "雄", "雄性", "公", "man"]:
        cardi.info["sex"] = "male"
        update.message.reply_text("性别设定为男性。")
    elif sex in ["女", "女性", "F", "f", "female", "雌", "雌性", "母", "woman"]:
        cardi.info["sex"] = "female"
        update.message.reply_text("性别设定为女性。")
    else:
        cardi.info["sex"] = sex
        update.message.reply_text(
            "性别设定为："+sex+"。")
    writecards(CARDS_DICT)
    return True


def textnewcard(update: Update) -> bool:
    text = update.message.text
    plid = getchatid(update)
    if not isint(text) or int(text) >= 0:
        return errorHandler(update, "无效群id。如果你不知道群id，在群里发送 /getid 获取群id。")
    gpid = int(text)
    if hascard(plid, gpid) and getkpid(gpid) != plid:
        popOP(plid)
        return errorHandler(update, "你在这个群已经有一张卡了！")
    popOP(plid)
    return getnewcard(update.message.message_id, gpid, plid)


def textsetage(update: Update) -> bool:
    text = update.message.text
    plid = getchatid(update)
    if not isint(text):
        return errorHandler(update, "输入无效，请重新输入")
    cardi = findcard(plid)
    if not cardi:
        popOP(plid)
        return errorHandler(update, "找不到卡")
    if cardsetage(update, cardi, int(text)):
        popOP(plid)
        return True
    return False


def nameset(cardi: GameCard, name: str) -> None:
    cardi.info["name"] = name
    cardi.cardcheck["check5"] = True
    writecards(CARDS_DICT)


def textsetname(update: Update, plid: int) -> bool:
    if plid == 0:  # 私聊情形
        plid = getchatid(update)
    if getmsgfromid(update) != plid:
        return True  # 不处理
    popOP(getchatid(update))
    text = update.message.text
    text = ' '.join(text.split())
    cardi = findcard(plid)
    if not cardi:
        return errorHandler(update, "找不到卡。")
    nameset(cardi, text)
    update.message.reply_text("姓名设置完成："+text)


def textsetsex(update: Update, plid: int) -> bool:
    if plid == 0:  # 私聊情形
        plid = getchatid(update)
    if getmsgfromid(update) != plid:
        return True
    popOP(getchatid(update))
    text = update.message.text
    cardi = findcard(plid)
    if not cardi:
        return errorHandler(update, "找不到卡。")
    return cardsetsex(update, cardi, text)


def textdelcard(update: Update, cardid: int) -> bool:
    cardi = findcardwithid(cardid)
    if not cardi:
        popOP(update.effective_chat.id)
        return errorHandler(update, "找不到卡。")
    kpid = getmsgfromid(update)
    if kpid != getkpid(cardi.groupid):
        return True
    text = update.message.text
    if text != "确认":
        popOP(update.effective_chat.id)
        return errorHandler(update, "已经取消删除卡片操作。")
    update.message.reply_text("卡片已删除。用 /details 查看被删卡片详情。")
    DETAIL_DICT[update.effective_chat.id] = showcardinfo(
        cardpop(cardi.groupid, cardid))
    return True


def getnewcard(msgid: int, gpid: int, plid: int, cdid: int = -1) -> bool:
    """指令`/newcard`的具体实现"""
    if gpid not in CARDS_DICT:
        CARDS_DICT[gpid] = {}
    new_card, detailmsg = generateNewCard(plid, gpid)
    allids = getallid()
    if cdid >= 0 and cdid not in allids:
        new_card.id = cdid
    else:
        if cdid >= 0 and cdid in allids:
            dicebot.updater.bot.send_message(
                chat_id=plid, reply_to_message_id=msgid, text="输入的ID已经被占用，自动获取ID。可以用 /changeid 更换喜欢的id。")
        new_card.id = getoneid()
    dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                     text="角色卡已创建，您的卡id为："+str(new_card.id)+"。详细信息如下：\n"+detailmsg)
    # 如果有3个属性小于50，则discard=true
    if countless50discard(new_card):
        new_card.discard = True
        dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                         text="因为有三项属性小于50，如果你愿意的话可以使用 /discard 来删除这张角色卡。设定年龄后则不能再删除这张卡。")
    dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                     text="长按 /setage 并输入一个数字来设定年龄。如果需要卡片制作帮助，使用 /createcardhelp 来获取帮助。")
    if plid in CURRENT_CARD_DICT:
        dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                         text="创建新卡时，控制自动切换至新卡。如果需要切换你操作的另一张卡，用 /switch 切换")
    cardadd(new_card)
    return True


def botchat(update: Update) -> None:
    if isgroupmsg(update):
        return
    text = update.message.text
    try:
        rttext = text+" = "+str(calculator(text))
    except:
        pass
    if text[:1] == "我":
        update.message.reply_text("你"+text[1:])
        return
    if text.find("傻逼") != -1 or text.find("sb") != -1:
        update.message.reply_text("明白了，你是傻逼")
        return


def plainNewCard() -> dict:
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
        },
        "info": {
        },
        "skill": {
            "points": -1
        },
        "interest": {

        },
        "suggestskill": {

        },
        "cardcheck": {
            "check1": False,  # 年龄是否设定
            "check2": False,  # str, con, dex等设定是否完成
            "check3": False,  # job是否设定完成
            "check4": False,  # skill是否设定完成
            "check5": False  # 名字等是否设定完成
        },
        "attr": {
            "physique": -100,
            "DB": "-100",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "0/0",
            "Armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "exsigplace": "",
            "precious": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": "",
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    return t


def templateNewCard() -> dict:
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
            "STR": 0,
            "CON": 0,
            "SIZ": 0,
            "DEX": 0,
            "APP": 0,
            "INT": 0,
            "POW": 0,
            "EDU": 0,
            "LUCK": 0
        },
        "info": {
            "AGE": 0,
            "job": "",
            "name": "",
            "sex": ""
        },
        "skill": {
            "points": 0
        },
        "interest": {
            "points": 0
        },
        "suggestskill": {

        },
        "cardcheck": {
            "check1": False,  # 年龄是否设定
            "check2": False,  # str, con, dex等设定是否完成
            "check3": False,  # job是否设定完成
            "check4": False,  # skill是否设定完成
            "check5": False  # 名字等是否设定完成
        },
        "attr": {
            "SAN": 0,
            "MAXSAN": 99,
            "MAGIC": 0,
            "MAXLP": 0,
            "LP": 0,
            "physique": -100,
            "DB": "-100",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "1/1d6",
            "Armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "exsigplace": "",
            "precious": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": "",
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    return t


def generateNewCard(userid, groupid) -> Tuple[GameCard, str]:
    newcard = plainNewCard()
    newcard["playerid"] = userid
    newcard["groupid"] = groupid
    card = GameCard(newcard)
    text = ""
    a, b, c = np.random.randint(1, 7, size=3)
    STR = int(5*(a+b+c))
    text += get3d6str("STR", a, b, c)
    a, b, c = np.random.randint(1, 7, size=3)
    CON = int(5*(a+b+c))
    text += get3d6str("CON", a, b, c)
    a, b = np.random.randint(1, 7, size=2)
    SIZ = int(5*(a+b+6))
    text += get2d6_6str("SIZ", a, b)
    a, b, c = np.random.randint(1, 7, size=3)
    DEX = int(5*(a+b+c))
    text += get3d6str("DEX", a, b, c)
    a, b, c = np.random.randint(1, 7, size=3)
    APP = int(5*(a+b+c))
    text += get3d6str("APP", a, b, c)
    a, b = np.random.randint(1, 7, size=2)
    INT = int(5*(a+b+6))
    text += get2d6_6str("INT", a, b)
    a, b, c = np.random.randint(1, 7, size=3)
    POW = int(5*(a+b+c))
    text += get3d6str("POW", a, b, c)
    a, b = np.random.randint(1, 7, size=2)
    EDU = int(5*(a+b+6))
    text += get2d6_6str("EDU", a, b)
    card.data["STR"] = STR
    card.data["CON"] = CON
    card.data["SIZ"] = SIZ
    card.data["DEX"] = DEX
    card.data["APP"] = APP
    card.data["INT"] = INT
    card.data["POW"] = POW
    card.data["EDU"] = EDU
    card.interest.points = INT*2
    return card, text


def EDUenhance(card: GameCard, times: int) -> str:
    if times > 4:
        return ""
    rttext = ""
    timelist = ["一", "二", "三", "四"]
    for j in range(times):
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第"+timelist[j]+"次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第"+timelist[j]+"次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
    return rttext


def generateAgeAttributes(card: GameCard) -> Tuple[GameCard, str]:
    if "AGE" not in card.info:  # This trap should not be hit
        return card, "Attribute: AGE is NONE, please set AGE first"
    AGE = card.info["AGE"]
    luck = int(5*sum(np.random.randint(1, 7, size=3)))
    rttext = ""
    if AGE < 20:
        luck2 = int(5*sum(np.random.randint(1, 7, size=3)))
        if luck < luck2:
            card.data["LUCK"] = luck2
        else:
            card.data["LUCK"] = luck
        rttext += "年龄低于20，幸运得到奖励骰。结果分别为" + \
            str(luck)+", "+str(luck2)+"。教育减5，力量体型合计减5。"
        card.data["STR_SIZ_M"] = -5
        card.data["EDU"] -= 5
    elif AGE < 40:
        card.cardcheck["check2"] = True  # No STR decrease, check2 passes
        rttext += "年龄20-39，得到一次教育增强。"
        rttext += EDUenhance(card, 1)
        rttext += "现在教育：" + str(card.data["EDU"])+"。"
    elif AGE < 50:
        rttext += "年龄40-49，得到两次教育增强。\n"
        rttext += EDUenhance(card, 2)
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_M"] = -5
        card.data["APP"] -= 5
        rttext += "力量体质合计减5，外貌减5。\n"
    elif AGE < 60:
        rttext += "年龄50-59，得到三次教育增强。\n"
        rttext += EDUenhance(card, 3)
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -10
        card.data["APP"] -= 10
        rttext += "力量体质敏捷合计减10，外貌减10。\n"
    elif AGE < 70:
        rttext += "年龄60-69，得到四次教育增强。\n"
        rttext += EDUenhance(card, 4)
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -20
        card.data["APP"] -= 15
        rttext += "力量体质敏捷合计减20，外貌减15。\n"
    elif AGE < 80:
        rttext += "年龄70-79，得到四次教育增强。\n"
        rttext += EDUenhance(card, 4)
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -40
        card.data["APP"] -= 20
        rttext += "力量体质敏捷合计减40，外貌减20。\n"
    else:
        rttext += "年龄80以上，得到四次教育增强。\n"
        rttext += EDUenhance(card, 4)
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -80
        card.data["APP"] -= 25
        rttext += "力量体质敏捷合计减80，外貌减25。\n"
    if AGE >= 20:
        card.data["LUCK"] = luck
        rttext += "幸运："+str(luck)+"\n"
    for keys in card.data:
        if len(keys) > 6:
            rttext += "使用' /setstrdec STRDEC '来设置因为年龄设定导致的STR减少值，根据所设定的年龄可能还需要设置CON减少值。根据上面的提示减少的数值进行设置。\n"
            break
    rttext += "使用 /setjob 进行职业设定。完成职业设定之后，用'/addskill 技能名 技能点数' 来分配技能点，用空格分隔。"
    return card, rttext


# If returns "输入无效", card should not be edited
def choosedec(card: GameCard, strength: int) -> Tuple[GameCard, str, bool]:
    if card.data["STR"] <= strength:
        return card, "输入无效", False
    card.data["STR"] -= strength  # Add it back if "HIT BAD TRAP"
    needCON = False
    rttext = "力量减"+str(strength)+"点，"
    if "STR_SIZ_M" in card.data:  # AGE less than 20
        if strength > -card.data["STR_SIZ_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        card.data["SIZ"] += card.data["STR_SIZ_M"]+strength
        rttext += "体型减"+str(-card.data["STR_SIZ_M"]-strength)+"点。"
        card.data.pop("STR_SIZ_M")
        card.cardcheck["check2"] = True  # No other decrease, check2 passes
    elif "STR_CON_M" in card.data:
        if strength > -card.data["STR_CON_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        card.data["CON"] += card.data["STR_CON_M"]+strength
        rttext += "体质减"+str(-card.data["STR_CON_M"]-strength)+"点。"
        card.data.pop("STR_CON_M")
        card.cardcheck["check2"] = True  # No other decrease, check2 passes
    elif "STR_CON_DEX_M" in card.data:
        if strength > -card.data["STR_CON_DEX_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        if not strength == -card.data["STR_CON_DEX_M"]:
            needCON = True
            card.data["CON_DEX_M"] = card.data["STR_CON_DEX_M"]+strength
            rttext += "体质敏捷合计减"+str(-card.data["CON_DEX_M"])+"点。"
        else:
            rttext += "体质敏捷合计减0点。"
        card.data.pop("STR_CON_DEX_M")
    else:
        return card, "输入无效", False
    return card, rttext, needCON


def choosedec2(card: GameCard, con: int) -> Tuple[GameCard, str]:
    if card.data["CON"] <= con or "CON_DEX_M" not in card.data:
        return card, "输入无效"
    card.data["CON"] -= con
    rttext = "体质减"+str(con)+"点，"
    if con > -card.data["CON_DEX_M"]:
        card.data["CON"] += con
        return card, "输入无效"
    card.data["DEX"] += card.data["CON_DEX_M"]+con
    rttext += "敏捷减"+str(-card.data["CON_DEX_M"]-con)+"点。"
    card.data.pop("CON_DEX_M")
    card.cardcheck["check2"] = True
    return card, rttext


def generateOtherAttributes(card: GameCard) -> Tuple[GameCard, str]:
    """获取到年龄之后，通过年龄计算一些衍生数据。"""
    if not card.cardcheck["check2"]:  # This trap should not be hit
        return card, "Please set DATA decrease first"
    if "SAN" not in card.attr or card.attr["SAN"] == 0:
        card.attr["SAN"] = card.data["POW"]
    card.attr["MAXSAN"] = 99
    if "MAGIC" not in card.attr or card.attr["MAGIC"] == 0:
        card.attr["MAGIC"] = card.data["POW"]//5
    if "MAXLP" not in card.attr or card.attr["MAXLP"] == 0:
        card.attr["MAXLP"] = (card.data["SIZ"]+card.data["CON"])//10
    if "LP" not in card.attr or card.attr["LP"] == 0:
        card.attr["LP"] = card.attr["MAXLP"]
    rttext = "SAN: " + str(card.attr["SAN"])+"\n"
    rttext += "MAGIC: " + str(card.attr["MAGIC"])+"\n"
    rttext += "LP: " + str(card.attr["LP"])+"\n"
    if "physique" not in card.attr or card.attr["physique"] == 0:
        if card.data["STR"]+card.data["SIZ"] < 65:
            card.attr["physique"] = -2
        elif card.data["STR"]+card.data["SIZ"] < 85:
            card.attr["physique"] = -1
        elif card.data["STR"]+card.data["SIZ"] < 125:
            card.attr["physique"] = 0
        elif card.data["STR"]+card.data["SIZ"] < 165:
            card.attr["physique"] = 1
        elif card.data["STR"]+card.data["SIZ"] < 205:
            card.attr["physique"] = 2
        else:
            card.attr["physique"] = 2 + \
                (card.data["STR"]+card.data["SIZ"]-125)//80
    if "DB" not in card.attr or card.attr["DB"] == 0:
        if card.attr["physique"] <= 0:
            card.attr["DB"] = str(card.attr["physique"])
        elif card.attr["physique"] == 1:
            card.attr["DB"] = "1d4"
        else:
            card.attr["DB"] = str(card.attr["physique"]-1)+"d6"
    rttext += "physique: " + str(card.attr["physique"])+"\n"
    return card, rttext


def generatePoints(card: GameCard, job: str):
    if job not in dicebot.joblist:
        return False
    ptrule = dicebot.joblist[job][2]
    pt = 0
    for keys in ptrule:
        if keys in card.data:
            pt += card.data[keys]*ptrule[keys]
        elif len(keys) == 11:
            pt += max(card.data[keys[:3]], card.data[keys[4:7]],
                      card.data[keys[8:]])*ptrule[keys]
        elif keys[:3] in card.data and keys[4:] in card.data:
            pt += max(card.data[keys[:3]], card.data[keys[4:]])*ptrule[keys]
        else:
            return False
    card.skill.points = int(pt)
    return True


def checkcard(card: GameCard) -> bool:
    if "AGE" in card.info:
        card.cardcheck["check1"] = True
    if not card.cardcheck["check1"]:
        return False
    if "STR_SIZ_M" in card.data or "STR_CON_DEX_M" in card.data or "STR_CON_M" in card.data or "CON_DEX_M" in card.data:
        return False
    card.cardcheck["check2"] = True
    if "job" not in card.info:
        return False
    card.cardcheck["check3"] = True
    if card.skill.points != 0:
        return False
    if card.interest.points != 0:  # "points" must be in card.interest
        return False
    card.cardcheck["check4"] = True
    if "name" not in card.info or card.info["name"] == "":
        return False
    card.cardcheck["check5"] = True
    return True


def showchecks(card: GameCard) -> str:
    if checkcard(card):
        return "All pass."
    rttext = ""
    for keys in card.cardcheck:
        if not card.cardcheck[keys]:
            rttext += keys+": False\n"
    return rttext
