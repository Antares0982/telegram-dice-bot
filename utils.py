# -*- coding:utf-8 -*-

import json
from typing import (Dict, Iterable, Iterator, KeysView, List, Optional, Tuple,
                    TypeVar, Union, overload)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext
from telegram.message import Message

from basicfunc import *
from botclass import GameCard, Group, GroupGame, Player, dicebot
from cfg import *
from dicefunc import *

_T = TypeVar("_T")

# FLAGS

CANREAD = 1
OWNCARD = 2
CANSETINFO = 4
CANDISCARD = 8
CANMODIFY = 16

INGROUP = 1
GROUPKP = 2
GROUPADMIN = 4
BOTADMIN = 8

SKILL_PAGES: List[List[str]]


# 读取完成
dicebot.sendtoAdmin("Bot is live!")


def __getgp(gpid: Union[int, Update]) -> Optional[Group]:
    return dicebot.getgp(gpid)


def initgroup(gpid: int) -> Optional[Group]:
    """若gpid未存储过，创建Group对象并返回，否则返回None"""
    gp = __getgp(gpid)
    return gp.renew(dicebot.updater) if gp else dicebot.creategp(gpid)


def __forcegetgroup(gpid: Union[int, Update]) -> Group:
    return dicebot.forcegetgroup(gpid)


def updateinitgroup(update: Update) -> Optional[Group]:
    if not isgroupmsg(update):
        return None
    gpid = getchatid(update)
    return initgroup(gpid)


def __getplayer(plid: Union[int, Update]) -> Optional[Player]:
    return dicebot.getplayer(plid)


def initplayer(plid: int) -> Optional[Player]:
    """若plid未存储过，创建Player对象并返回，否则返回None"""
    pl = __getplayer(plid)
    return pl.renew(dicebot.updater) if pl else dicebot.createplayer(plid)


def __forcegetplayer(plid: Union[int, Update]) -> Player:
    return dicebot.forcegetplayer(plid)


def updateinitplayer(update: Update) -> Optional[Player]:
    if not isprivatemsg(update):
        return None
    plid = getchatid(update)
    return initplayer(plid)


def chatinit(update: Update) -> Union[Player, Group, None]:
    """所有指令使用前调用该函数"""
    dicebot.checkconsistency()
    if isprivatemsg(update):
        return updateinitplayer(update)
    if isgroupmsg(update):
        initplayer(getmsgfromid(update))
        return updateinitgroup(update)
    return None


# 卡片相关：查 增 删

@overload
def cardpop(card: GameCard) -> Optional[GameCard]:
    ...


@overload
def cardpop(id: int) -> Optional[GameCard]:
    ...


def cardpop(id) -> Optional[GameCard]:
    """删除一张卡并返回其数据。返回None则删除失败"""
    if isinstance(id, int):
        return dicebot.popcard(id) if dicebot.getcard(id) is not None else None
    card = id
    if card.isgamecard:
        return dicebot.popgamecard(card.id)
    return dicebot.popcard(card.id)


def cardadd(card: GameCard, gpid: int) -> bool:
    """添加一张游戏外的卡，当卡id重复时返回False。该函数忽略原本card.groupid"""
    if card.id in dicebot.allids:
        return False
    # 增加id
    dicebot.allids.append(card.id)
    dicebot.allids.sort()
    # 增加群索引
    gp = __forcegetgroup(gpid)
    card.group = gp
    card.groupid = gpid
    gp.cards[card.id] = card
    gp.write()
    # 增加pl索引
    pl = __forcegetplayer(card.playerid)
    pl.cards[card.id] = card
    card.player = pl
    if pl.controlling:
        dicebot.autoswitchhint(pl.id)
    pl.controlling = card
    pl.write()
    return True


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


def createSkillPages() -> List[List[str]]:
    """创建技能的分页列表，用于添加兴趣技能"""
    # 一页16个
    skillPaged: List[List[str]] = [["母语", "闪避"]]
    for key in dicebot.skilllist:
        if key == "克苏鲁神话":
            continue
        if len(skillPaged[len(skillPaged)-1]) == 16:
            skillPaged.append([])
        skillPaged[len(skillPaged)-1].append(key)
    return skillPaged


SKILL_PAGES = createSkillPages()
# id相关


def getnewids(n: int) -> List[int]:
    """获取n个新的卡id，这些id尽可能小"""
    ids = dicebot.allids
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
def searchifkp(pl: Player) -> bool:
    """判断plid是否至少是一个群的kp"""
    return bool(len(pl.kpgroups))


def isfromkp(update: Update) -> bool:
    """判断消息发送者是否是kp。
    如果是私聊消息，只需要发送者是某群KP即返回True。如果是群聊消息，当发送者是本群KP才返回True"""
    if isprivatemsg(update):  # 私聊消息，搜索所有群判断是否是kp
        return searchifkp(__forcegetplayer(update))

    # 如果是群消息，判断该指令是否来自本群kp
    gp = __forcegetgroup(update)
    return gp.kp is not None and gp.kp == __forcegetplayer(update)


def findcard(plid: int) -> Optional[GameCard]:
    """输入一个player的id，返回该player当前选择中的卡"""
    pl = __getplayer(plid)
    if not pl:
        return None
    return pl.controlling


def hascard(plid: int, gpid: int) -> bool:
    """判断一个群内是否已经有pl的卡"""
    pl = __getplayer(plid)
    if not pl:
        pl = initplayer(plid)
        return False

    return any(card.group.id == gpid for card in pl.cards.values())


def findcardwithid(cdid: int) -> Optional[GameCard]:
    """输入一个卡id，返回这张卡"""
    for gp in dicebot.groups.values():
        if cdid in gp.cards:
            return gp.cards[cdid]
    return None


def getreplyplayer(update: Update) -> Optional[Player]:
    """如果有回复的人，调用forcegetplayer获取玩家信息，否则返回None"""
    if isprivatemsg(update):
        return None
    if isgroupmsg(update):
        return dicebot.forcegetplayer(update.message.reply_to_message.from_user.id) if update.message.reply_to_message is not None else None


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
    if lower > upper:
        upper = lower

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
    gp = __getgp(gpid)
    if not gp:
        return None
    return gp.game


def findexistgame(gpid: int) -> Optional[GroupGame]:
    gp = __getgp(gpid)
    if not gp:
        return None
    return gp.getexistgame()


def findcardfromgame(game: GroupGame, pl: Player) -> GameCard:
    """从`game`中返回对应的`plid`的角色卡"""
    for i in pl.gamecards.values():
        if i.group == game.group:
            return i
    return None


def findcardfromgroup(pl: Player, gp: Group) -> Optional[GameCard]:
    """返回pl在gp中的其中一张卡，无法返回多张卡"""
    for i in pl.cards.values():
        if i.group == gp:
            return i
    return None


def findcardfromgamewithid(game: GroupGame, cdid: int) -> GameCard:
    """从`game`中返回`id`为`cdid`的角色卡"""
    return game.cards[cdid] if cdid in game.cards else None


def findAllDiscardCards(pl: Player) -> List[GameCard]:
    """返回`plid`对应的所有`discard`为`True`的卡"""
    return [card for card in pl.cards.values() if checkaccess(pl, card) & CANDISCARD]


def findDiscardCardsWithGpidCdid(pl: Player, cardslist: List[int]) -> List[GameCard]:
    ans: List[int] = []

    for id in cardslist:
        if id < 0:  # 群id
            gp = dicebot.getgp(id)
            if gp is None:
                continue
            for card in gp.cards.values():
                if checkaccess(pl, card) & CANDISCARD:
                    ans.append(card.id)
        else:
            card = gp.getcard(id)
            if card is None:
                continue
            if checkaccess(pl, card) & CANDISCARD:
                ans.append(card.id)

    ans = list(set(ans))

    return [dicebot.getcard(x) for x in ans]


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
        if not isinstance(d[k1], dict) or (k1 == "tempstatus" and key != "GLOBAL"):
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
    kp = __getplayer(kpid)
    if not kp:
        return ans
    for card in kp.cards.values():
        if card.group.kp.id == kp.id:
            ans.append(card)
    return ans


def iterintersect(l1: Iterable[_T], l2: Iterable[_T]) -> Iterator[_T]:
    if len(l1) > len(l2):
        l1, l2 = l2, l1

    ans: List[_T] = []
    for i in l1:
        if i in l2:
            ans.append(i)

    return iter(ans)


def changecardsplid(gp: Group, oldpl: Player, newpl: Player) -> None:
    """将某个群中所有`oldplid`持有的卡改为`newplid`持有。"""
    oplk = list(oldpl.cards.keys())
    for key in oplk:

        card = oldpl.cards[key]
        if card.group != gp:
            continue

        card.playerid = newpl.id
        card.player = newpl
        newpl.cards[key] = oldpl.cards.pop(key)

    for key in oldpl.gamecards.keys():

        card = oldpl.gamecards[key]
        if card.group != gp:
            continue

        card.playerid = newpl.id
        card.player = newpl
        newpl.gamecards[key] = oldpl.gamecards.pop(key)

    if oldpl.controlling is not None and oldpl.controlling.group == gp:
        oldpl.controlling = None

    oldpl.write()
    newpl.write()
    return


def changeKP(gp: Group, newkp: Player) -> bool:
    """转移KP权限，接收参数：群id，新KP的id。
    会转移所有原KP控制的角色卡，包括正在进行的游戏。"""
    kp = gp.kp
    if not kp:
        return False
    if kp == newkp:
        return False

    changecardsplid(gp, kp, newkp)

    dicebot.delkp(kp)
    dicebot.addkp(newkp)

    gp.write()
    kp.write()
    newkp.write()
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


def skillcantouchmax(card1: GameCard, jumpskill: Optional[str] = None) -> Tuple[bool, bool]:
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

    card1.skill.check()

    for skill in card1.skill.allskills():
        if (skill == "母语" or skill == "闪避") and getskilllevelfromdict(card1, skill) == card1.skill.get(skill):
            continue
        if jumpskill is not None and skill == jumpskill:
            continue
        if card1.skill.get(skill) > skillmaxrule[0]:
            countSpecialSkill += 1

    for skill in card1.interest.allskills():
        if (skill == "母语" or skill == "闪避") and getskilllevelfromdict(card1, skill) == card1.interest.get(skill):
            continue
        if jumpskill is not None and skill == jumpskill:
            continue
        if card1.interest.get(skill) > skillmaxrule[0]:
            countSpecialSkill += 1

    return (ans1, True) if countSpecialSkill < skillmaxrule[2] else (ans1, False)


def skillmaxval(skillname: str, card1: GameCard, ismainskill: bool) -> int:
    """通过cost规则，返回技能能达到的最高值。"""
    aged, ok = skillcantouchmax(card1, skillname)
    gp = __forcegetgroup(card1.groupid)

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
        if skillname in card1.skill.allskills():
            basicval = card1.skill.get(skillname)
    else:
        pts = card1.interest.points
        if skillname in card1.interest.allskills():
            basicval = card1.interest.get(skillname)

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
        if skillname in card1.skill.allskills():
            basicval = card1.skill.get(skillname)
    else:
        if skillname in card1.interest.allskills():
            basicval = card1.interest.get(skillname)
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
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.skill.set(skillname, skillvalue, costval)
    card1.write()
    return True


def addsgskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """添加一个建议的技能。直接调用`addmainskill`完成。"""
    if not addmainskill(skillname, skillvalue, card1, update):
        return False
    card1.suggestskill.pop(skillname)
    card1.write()
    return True


def addintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """该函数对没有`skillname`这项技能的卡使用。将兴趣技能值设置为`skillvalue`。"""
    if card1.interest.points == 0:
        return errorHandler(update, "你已经没有剩余点数了")
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    # 计算点数消耗
    costval = evalskillcost(skillname, skillvalue, card1, False)
    update.message.reply_text(
        "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    card1.interest.set(skillname, skillvalue, costval)
    card1.write()
    return True


def cgmainskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:  # Change main skill level
    """修改主要技能的值。如果将技能点调低，返还技能点数。"""
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, True):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, True)
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.skill.set(skillname, skillvalue, costval)
    card1.write()
    return True


# Change interest skill level
def cgintskill(skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
    """修改兴趣技能的值。如果将技能点调低，返还技能点数。"""
    if skillvalue < getskilllevelfromdict(card1, skillname) or skillvalue > skillmaxval(skillname, card1, False):
        return errorHandler(update, "目标技能点太高或太低")
    costval = evalskillcost(skillname, skillvalue, card1, False)
    if costval >= 0:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
    else:
        update.message.reply_text(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
    card1.interest.set(skillname, skillvalue, costval)
    card1.group.write()
    return True


def addcredit(update: Update, card1: GameCard) -> bool:
    update.message.reply_text("请先设置信用！")
    gp = card1.group
    if card1.info.job in dicebot.joblist:
        m = dicebot.joblist[card1.info.job][0]
        mm = dicebot.joblist[card1.info.job][1]
    else:
        aged, ok = skillcantouchmax(card1, "信用")
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
        card1.skill.get("信用")), reply_markup=rp_markup)
    return True


def showskillpages(page: int, card1: GameCard) -> Tuple[str, List[List[InlineKeyboardButton]]]:
    IDENTIFIER = dicebot.IDENTIFIER
    thispageskilllist = SKILL_PAGES[page]
    rttext = f"添加/修改兴趣技能，剩余点数：{str(card1.interest.points)}。目前的数值/基础值如下："
    rtbuttons = [[]]
    for key in thispageskilllist:
        if key in card1.skill.allskills() or key in card1.suggestskill.allskills():
            continue
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        if key in card1.interest.allskills():
            rttext += "（已有技能）"+key+"："+str(card1.interest.get(key))+"\n"
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

        IDENTIFIER = dicebot.IDENTIFIER
        rtbuttons = [[
            InlineKeyboardButton(
                text="确认", callback_data=IDENTIFIER+" job "+jobname+" True"),
            InlineKeyboardButton(
                text="返回", callback_data=IDENTIFIER+" job "+jobname+" False")
        ]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(rttext, reply_markup=rp_markup)
        return True
    if not card1:
        return errorHandlerQ(query, "找不到卡。")
    confirm = args[2]  # 只能是True，或False
    if confirm == "False":
        rtbuttons = makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text("请选择职业查看详情：", reply_markup=rp_markup)
        return True
    # 确认完成
    card1.info.job = jobname
    query.edit_message_text(
        "职业设置为："+jobname+"\n现在你可以用指令 /addskill 添加技能，首先需要设置信用点。")
    if not generatePoints(card1):
        dicebot.sendtoAdmin("生成技能出错，位置：buttonjob")
        return errorHandlerQ(query, "生成技能点出错！")
    for i in range(3, len(dicebot.joblist[jobname])):  # Classical jobs
        card1.suggestskill.set(dicebot.joblist[jobname][i], getskilllevelfromdict(
            card1, dicebot.joblist[jobname][i]))   # int
    card1.group.write()
    return True


def buttonaddmainskill(query: CallbackQuery, card1: GameCard, args: List[str]) -> bool:
    if card1 is None:
        return errorHandlerQ(query, "找不到卡。")

    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue, needpt)
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        card1.group.write()
        if card1.skill.points or card1.interest.points:
            addskill0(card1)
        return True

    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttoncgmainskill(query: CallbackQuery,  card1: GameCard, args: List[str]) -> bool:
    if card1 is None:
        return errorHandlerQ(query, "找不到卡。")

    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue, needpt)
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        card1.group.write()
        if card1.skill.points or card1.interest.points:
            addskill0(card1)
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
        return errorHandlerQ(query, "找不到卡。")
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill.set(args[1], skvalue, needpt)
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
        card1.suggestskill.pop(args[1])
        card1.group.write()
        if card1.skill.points or card1.interest.points:
            addskill0(card1)
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
        card1.interest.set(args[1], skvalue, needpt)
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
        card1.write()
        if card1.skill.points or card1.interest.points:
            addskill0(card1)
        else:
            dicebot.sendto(
                card1.player, "接下来，如果没有设置过的话，请使用 /setname 设置姓名、 /setsex 设置性别、 /setbkg 设置背景信息。")
            dicebot.updater.bot.send_message(
                card1.player.id, "背景设定中必要的部分有：故事、信仰、重要之人、意义非凡之地、珍视之物、性格特质。如果需要帮助，请点击`/help setbkg`并发送给我。", parse_mode="MarkdownV2")
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
        return errorHandlerQ(query, "找不到卡。")
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, False)
        card1.interest.set(args[1], skvalue, needpt)
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
        card1.group.write()
        if card1.skill.points or card1.interest.points:
            addskill0(card1)
        return True

    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.interest.get(args[1])), reply_markup=rp_markup)
    return True


def buttonchoosedec(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        return errorHandlerQ(query, "找不到卡。")

    if card1.data.datadec is None:
        return errorHandlerQ(query, "不需要设置降值。")

    dname = args[1]
    decnames = card1.data.datadec[0].split('_')
    if dname not in decnames:
        return errorHandlerQ(query, "无法为该属性设置降值。")

    if len(decnames) == 2:
        anotherdecname = decnames[0] if dname == decnames[1] else decnames[1]
        rtbuttons = makeIntButtons(max(0, 1-card1.data.__dict__[anotherdecname]-card1.data.datadec[1]), min(
            card1.data.__dict__[dname]-1, -card1.data.datadec[1]), f"{dname}dec", "", 1)
    elif len(decnames) == 3:
        decnames.pop(decnames.index(dname))
        d1 = decnames[0]
        d2 = decnames[1]
        rtbuttons = makeIntButtons(max(0, 2-card1.data.__dict__[d1]-card1.data.__dict__[d2]-card1.data.datadec[1]), min(
            card1.data.__dict__[dname]-1, -card1.data.datadec[1]
        ), f"{dname}dec", "", 1)
    else:
        raise ValueError("datadec参数错误")

    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        f"选择下降值，目前全部数值如下：\n{str(card1.data)}", reply_markup=rp_markup)

    return True


def buttonsetdec(query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
    if not card1:
        return errorHandlerQ(query, "找不到卡。")

    dname = args[0][:args[0].find("dec")]
    if dname not in card1.data.alldatanames:
        dicebot.sendtoAdmin("属性名错误，请检查代码")
        return errorHandlerQ(query, "属性名错误，请检查代码")
    if card1.data.datadec is None:
        return errorHandlerQ(query, "该卡无需设置属性降值。")

    decnames = card1.data.datadec[0].split('_')
    decval = int(args[2])

    assert(card1.data.__dict__[dname]-decval >= 1)
    assert(card1.data.datadec[1]+decval <= 0)

    if len(decnames) == 2:
        otherdec = decnames[0] if dname == decnames[1] else decnames[1]
        assert(card1.data.__dict__[otherdec]+card1.data.datadec[1]+decval >= 1)

        card1.data.__dict__[dname] -= decval
        card1.data.__dict__[otherdec] += card1.data.datadec[1]+decval
        card1.data.datadec = None

        card1.generateOtherAttributes()

        query.edit_message_text(
            f"属性下降设置完成，现在基础属性：\n{str(card1.data)}\n请点击 /setjob 设置职业。")
        return True

    if len(decnames) == 3:
        decnames.pop(decnames.index(dname))

        card1.data.__dict__[dname] -= decval
        card1.data.datadec = ('_'.join(decnames), card1.data.datadec[1]+decval)
        card1.write()

        query.edit_message_text(f"请继续设置属性降值，目前全部数值如下：\n{str(card1.data)}")

        rtbuttons = [[]]
        for dname in decnames:
            rtbuttons[0].append(InlineKeyboardButton(
                text=dname, callback_data=dicebot.IDENTIFIER+" choosedec "+dname))

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_reply_markup(reply_markup=rp_markup)
        return True

    dicebot.sendtoAdmin("下降属性参数长度有误")
    return errorHandlerQ(query, "下降属性参数长度有误")


def buttondiscard(query: CallbackQuery, plid: int, args: List[str]) -> bool:
    cdid = int(args[1])

    card = dicebot.getcard(cdid)
    if card is None:
        return errorHandlerQ(query, "找不到这个id的卡。")

    pl = __forcegetplayer(plid)
    if not checkaccess(pl, card) & CANDISCARD:
        return errorHandlerQ(query, "该卡不可删除。")

    cardpop(cdid)

    query.edit_message_text(f"删除了：{card.getname()}。\n该删除操作不可逆。")
    return True


def buttonswitch(query: CallbackQuery, plid: int, args: List[str]) -> bool:
    pl = __forcegetplayer(plid)
    cdid = int(args[1])

    if cdid not in pl.cards:
        return errorHandlerQ(query, "没有找到这个id的卡。")

    pl.controlling = pl.cards[cdid]
    pl.write()

    query.edit_message_text("修改成功，现在操作的卡是："+pl.controlling.getname())
    return True


def buttonswitchgamecard(query: CallbackQuery, kpid: int, args: List[str]) -> bool:
    kp = __forcegetplayer(kpid)
    cdid = int(args[1])
    card = dicebot.getgamecard(cdid)

    if card is None:
        return errorHandlerQ(query, "没有这张卡")
    if card.player != kp:
        return errorHandlerQ(query, "这不是你的卡片")
    if card.group.kp != kp:
        return errorHandlerQ(query, "你不是对应群的kp")

    game = card.group.game if card.group.game is not None else card.group.pausedgame
    assert(game is not None)

    game.kpctrl = card
    game.write()
    query.edit_message_text("修改操纵的npc卡成功，现在正在使用："+card.getname())
    return True


def buttonsetsex(query: CallbackQuery, plid: int,  args: List[str]) -> bool:
    cardi = findcard(plid)
    if cardi is None:
        return errorHandlerQ(query, "找不到卡。")

    sex = args[1]
    if sex == "other":
        addOP(plid, "setsex")
        query.edit_message_text("请输入具体的性别：")
        return True

    cardi.info.sex = sex
    cardi.write()

    rttext = "性别设定为"
    if sex == "male":
        rttext += "男性。"
    else:
        rttext += "女性。"
    query.edit_message_text(rttext)
    return True


def getkpctrl(game: GroupGame) -> Optional[GameCard]:
    for cardi in game.cards.values():
        if cardi.id == game.kpctrl and cardi.playerid == game.kpid:
            return cardi
    return None


def changecardgpid(oldgpid: int, newgpid: int) -> bool:
    """函数`changegroup`的具体实现。"""
    oldcdidlst = list(__forcegetgroup(oldgpid).cards.keys())
    for cdid in oldcdidlst:
        card = cardpop(oldgpid, cdid)
        cardadd(card, newgpid)
    __getgp(oldgpid).write()
    __getgp(newgpid).write()


def groupcopy(oldgpid: int, newgpid: int, copyall: bool) -> bool:
    """copyall为False则只复制NPC卡片"""
    if findexistgame(oldgpid) is not None or findexistgame(newgpid) is not None:
        return False

    oldgp = __forcegetgroup(oldgpid)
    srclist: List[GameCard] = []
    for card in oldgp.cards.values():
        if not copyall and card.type == "PL":
            continue
        srclist.append(card)

    if len(srclist) == 0:
        return False

    newids = getnewids(len(srclist))

    dstlist = [GameCard(card.to_json()) for card in srclist]

    for i in range(len(dstlist)):
        dstlist[i].id = newids[i]

    for card in dstlist:
        cardadd(card, newgpid)

    __getgp(newgpid).write()
    oldgp.write()

    return True


def addskill0(card1: GameCard) -> bool:
    """表示指令/addskill 中没有参数的情况。
    创建技能按钮来完成技能的添加。
    因为兴趣技能过多，使用可以翻页的按钮列表。"""
    rtbuttons = [[]]
    card1.player.renew(dicebot.updater)
    pl = card1.player
    # If card1.skill.points is 0, turn to interest.
    # Then it must be main skill. After all main skills are added, add interest skills.
    if card1.skill.points > 0:
        # Increase skills already added, because sgskill is empty
        if len(list(card1.suggestskill.allskills())) == 0:
            # GOOD TRAP: cgmainskill
            for keys in card1.skill.allskills():
                if keys == "points":
                    continue
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys +
                                                                        ": "+str(card1.skill.get(keys)), callback_data=dicebot.IDENTIFIER+" "+"cgmainskill "+keys))
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            dicebot.sendto(pl, "剩余点数："+str(
                card1.skill.points)+"\n请选择一项主要技能用于增加技能点", rpmarkup=rp_markup)
            return True
        # GOOD TRAP: addsgskill
        for keys in card1.suggestskill.allskills():
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.suggestskill.get(keys)), callback_data=dicebot.IDENTIFIER+" "+"addsgskill "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        dicebot.sendto(pl, "剩余点数："+str(
            card1.skill.points)+"\n请选择一项主要技能", rpmarkup=rp_markup)
        return True
    # turn to interest.
    if card1.interest.points <= 0:  # HIT BAD TRAP
        dicebot.sendto(pl, "你已经没有多余的点数了，如果需要重新设定某项具体技能的点数，用 '/addskill 技能名'")
        return False
    # GOOD TRAP: add interest skill.
    # 显示第一页，每个参数后面带一个当前页码标记
    rttext, rtbuttons = showskillpages(0, card1)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    dicebot.sendto(pl, rttext, rpmarkup=rp_markup)
    return True


def addskill1(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """该函数在`/addskill`接收且仅接收一个参数时调用。制作技能数值表。"""
    # skillname is already checked if in SKILL_DICT
    # First search if args skillname in skill or suggestskill.
    # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
    # Show button for numbers
    skillname = context.args[0]
    m = getskilllevelfromdict(card1, skillname)

    if skillname == "信用" and card1.info.job in dicebot.joblist:
        m = max(m, dicebot.joblist[card1.info.job][0])

    if skillname in card1.skill.allskills():  # GOOD TRAP: cgmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.skill[skillname]), reply_markup=rp_markup)
        return True

    if skillname in card1.suggestskill.allskills():  # GOOD TRAP: addsgskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname, reply_markup=rp_markup)
        return True

    if skillname in card1.interest.allskills():  # GOOD TRAP: cgintskill
        mm = skillmaxval(skillname, card1, False)
        rtbuttons = makeIntButtons(m, mm, "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.interest.get(skillname)), reply_markup=rp_markup)
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


def gamepop(gp: Group) -> Optional[GroupGame]:
    """终止一场游戏。`/abortgame`的具体实现。"""
    ans = gp.game if gp.game is not None else gp.pausedgame
    gp.game = None
    gp.pausedgame = None
    if ans is not None:
        gp.write()
        cdl = list(ans.cards.keys())
        for cdid in cdl:
            dicebot.getgamecard(cdid).delete()
            dicebot.popgamecard(cdid)
        ans.kp.kpgames.pop(ans.group.id)
    return ans


def holdinggamecontinue(gpid: int) -> GroupGame:
    """继续一场暂停的游戏。`/continuegame`的具体实现。"""
    gp = __forcegetgroup(gpid)
    if gp.game is not None and gp.pausedgame is not None:
        raise Exception("群："+str(gp.id)+"存在暂停的游戏和进行中的游戏")
    if gp.pausedgame is not None:
        gp.game, gp.pausedgame = gp.pausedgame, None
    return gp.game


def isholdinggame(gpid: int) -> bool:
    return True if __forcegetgroup(gpid).pausedgame is not None else False


def getgamecardsid(game: GroupGame) -> KeysView[int]:
    return game.cards.keys()


def choosedec(update: Update, card: GameCard):
    datas = card.data.datadec[0].split('_')

    rtbuttons = [[]]
    for dname in datas:
        rtbuttons[0].append(InlineKeyboardButton(
            text=dname, callback_data=dicebot.IDENTIFIER+" choosedec "+dname))

    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("请选择下面一项属性来设置下降值", reply_markup=rp_markup)


def cardsetage(update: Update, cardi: GameCard, age: int) -> bool:
    if cardi.info.age > 0:
        return errorHandler(update, "已经设置过年龄了。")

    if age < 17 or age > 99:
        return errorHandler(update, "年龄应当在17-99岁。")

    cardi.info.age = age

    detailmsg = cardi.generateAgeAttributes()
    update.message.reply_text(
        "年龄设置完成！详细信息如下：\n"+detailmsg+"\n如果年龄不小于40，或小于20，需要设置STR减值。如果需要帮助，使用 /createcardhelp 来获取帮助。")

    if cardi.data.datadec is not None:
        choosedec(update, cardi)
    else:
        cardi.generateOtherAttributes()

    cardi.write()
    return True


def cardsetsex(update: Update, cardi: GameCard, sex: str) -> bool:
    if sex in ["男", "男性", "M", "m", "male", "雄", "雄性", "公", "man"]:
        cardi.info.sex = "male"
        update.message.reply_text("性别设定为男性。")

    elif sex in ["女", "女性", "F", "f", "female", "雌", "雌性", "母", "woman"]:
        cardi.info.sex = "female"
        update.message.reply_text("性别设定为女性。")

    else:
        cardi.info.sex = sex
        update.message.reply_text(
            "性别设定为："+sex+"。")

    return True


def textnewcard(update: Update, cdid: int = -1) -> bool:
    text = update.message.text
    pl = dicebot.forcegetplayer(update)

    if not isint(text) or int(text) >= 0:
        return errorHandler(update, "无效群id。如果你不知道群id，在群里发送 /getid 获取群id。")
    gpid = int(text)
    popOP(pl.id)

    if hascard(pl.id, gpid) and __forcegetgroup(gpid).kp != pl:
        return errorHandler(update, "你在这个群已经有一张卡了！")

    return getnewcard(update.message.message_id, gpid, pl.id, cdid)


def textsetage(update: Update) -> bool:
    text = update.message.text
    plid = getchatid(update)
    if not isint(text):
        return errorHandler(update, "输入无效，请重新输入")
    cardi = findcard(plid)
    if not cardi:
        popOP(plid)
        return errorHandler(update, "找不到卡")

    return (bool(popOP(plid)) or True) if cardsetage(update, cardi, int(text)) else False


def nameset(cardi: GameCard, name: str) -> None:
    cardi.info.name = name
    # cardi.cardcheck["check5"] = True
    cardi.write()


def textsetname(update: Update, plid: int) -> bool:
    if plid == 0:  # 私聊情形
        plid = getchatid(update)

    if getmsgfromid(update) != plid:
        return True  # 不处理

    popOP(getchatid(update))

    text = ' '.join(update.message.text.split())

    cardi = findcard(plid)
    if not cardi:
        return errorHandler(update, "找不到卡。")

    nameset(cardi, text)
    update.message.reply_text("姓名设置完成："+text)
    return True


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
    if cardi.group.kp is None or kpid != cardi.group.kp.id:
        return True

    popOP(update.effective_chat.id)
    if update.message.text != "确认":
        update.message.reply_text("已经取消删除卡片操作。")
    else:
        update.message.reply_text("卡片已删除。")
        dicebot.popcard(cardid)
    return True


def textpassjob(update: Update, plid: int) -> bool:
    t = update.message.text.split()
    if getmsgfromid(update) != ADMIN_ID or (t[0] != "jobcomfirm" and t[0] != "jobreject"):
        return botchat(update)

    if len(t) < 2 or not isint(t[1]):
        return errorHandler(update, "参数无效")

    plid = int(t[1])
    if plid not in dicebot.addjobrequest:
        return errorHandler(update, "没有该id的职业新增申请")

    popOP(ADMIN_ID)
    if t[0] == "jobcomfirm":
        dicebot.joblist[dicebot.addjobrequest[plid]
                        [0]] = dicebot.addjobrequest[plid][1]

        with open(PATH_JOBDICT, 'w', encoding='utf-8') as f:
            json.dump(dicebot.joblist, f, indent=4, ensure_ascii=False)

        dicebot.sendto(plid, "您的新增职业申请已通过。")

    else:
        dicebot.sendto(plid, "您的新增职业申请没有通过。")

    return True


def textpassskill(update: Update, plid: int) -> bool:
    t = update.message.text.split()
    if getmsgfromid(update) != ADMIN_ID or (t[0] != "skillcomfirm" and t[0] != "skillreject"):
        return botchat(update)

    if len(t) < 2 or not isint(t[1]):
        return errorHandler(update, "参数无效")

    plid = int(t[1])
    if plid not in dicebot.addskillrequest:
        return errorHandler(update, "没有该id的技能新增申请")

    popOP(ADMIN_ID)
    if t[0] == "skillcomfirm":
        dicebot.skilllist[dicebot.addskillrequest[plid]
                          [0]] = dicebot.addskillrequest[plid][1]

        with open(PATH_SKILLDICT, 'w', encoding='utf-8') as f:
            json.dump(dicebot.skilllist, f, indent=4, ensure_ascii=False)

        dicebot.sendto(plid, "您的新增技能申请已通过。")

    else:
        dicebot.sendto(plid, "您的新增技能申请没有通过。")

    return True


def getnewcard(msgid: int, gpid: int, plid: int, cdid: int = -1) -> bool:
    """指令`/newcard`的具体实现"""
    gp = __forcegetgroup(gpid)
    new_card, detailmsg = generateNewCard(plid, gpid)
    allids = dicebot.allids
    if cdid >= 0 and cdid not in allids:
        new_card.id = cdid
    else:
        if cdid >= 0 and cdid in allids:
            dicebot.updater.bot.send_message(
                chat_id=plid, reply_to_message_id=msgid, text="输入的ID已经被占用，自动获取ID。之后可以用 /changeid 更换喜欢的id。")
        new_card.id = getoneid()
    dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                     text="角色卡已创建，您的卡id为："+str(new_card.id)+"。详细信息如下：\n"+detailmsg)
    # 如果有3个属性小于50，则discard=true
    if new_card.data.countless50discard():
        new_card.discard = True
        dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                         text="因为有三项属性小于50，如果你愿意的话可以点击 /renewcard 来重置这张角色卡。如果停止创建卡，点击 /discard 来放弃建卡。\n设定年龄后则不能再删除这张卡。")
    dicebot.updater.bot.send_message(chat_id=plid, reply_to_message_id=msgid,
                                     text="长按 /setage 并输入一个数字来设定年龄。如果需要卡片制作帮助，点击 /createcardhelp 来获取帮助。")
    dicebot.addcard(new_card)
    return True


def botchat(update: Update) -> None:
    if isgroupmsg(update) or update.message is None or update.message.text == "":
        return
    text = update.message.text
    try:
        rttext = text+" = "+str(calculator(text))
        update.message.reply_text(rttext)
        return
    except:
        ...
    if text[:1] == "我":
        update.message.reply_text("你"+text[1:])
        return
    if text.find("傻逼") != -1 or text.find("sb") != -1:
        update.message.reply_text("傻逼")
        return


def generateNewCard(userid, groupid) -> Tuple[GameCard, str]:
    """新建玩家卡片"""
    newcard = plainNewCard()
    newcard["playerid"] = userid
    newcard["groupid"] = groupid
    card = GameCard(newcard)
    card.data.randdata(write=False)
    text = card.data.datainfo
    card.interest.points = card.data.INT*2
    return card, text


def generatePoints(card: GameCard) -> bool:
    job = card.info.job
    if job not in dicebot.joblist:
        return False

    ptrule: Dict[str, int] = dicebot.joblist[job][2]
    pt = 0

    for keys in ptrule:
        if keys in card.data.alldatanames:
            pt += card.data.getdata(keys)*ptrule[keys]
        elif len(keys) == 11:
            pt += max(card.data.getdata(keys[:3]), card.data.getdata(keys[4:7]),
                      card.data.getdata(keys[8:]))*ptrule[keys]
        elif keys[:3] in card.data.alldatanames and keys[4:] in card.data.alldatanames:
            pt += max(card.data.getdata(keys[:3]),
                      card.data.getdata(keys[4:]))*ptrule[keys]
        else:
            return False

    card.skill.points = pt
    card.write()
    return True


@overload
def checkaccess(pl: Player, card: GameCard) -> int:
    ...


@overload
def checkaccess(pl: Player, gp: Group) -> int:
    ...


def checkaccess(pl: Player, thing) -> int:
    """用FLAG给出玩家对角色卡或群聊的权限。
    卡片：
    CANREAD = 1
    OWNCARD = 2
    CANSETINFO = 4
    CANDISCARD = 8
    CANMODIFY = 16
    群聊：
    INGROUP = 1
    GROUPKP = 2
    GROUPADMIN = 4
    BOTADMIN = 8
    """
    if isinstance(thing, GameCard):
        card = thing
        f = 0

        if card.id in pl.cards or card.id in pl.gamecards:
            f |= CANREAD | OWNCARD

        if not f & OWNCARD:
            if card.type == "PL" and checkaccess(pl, card.group) & INGROUP:
                f |= CANREAD

        if f & OWNCARD and not card.isgamecard:
            f |= CANSETINFO

        if f & OWNCARD and (card.groupid == -1 or (card.discard and not card.isgamecard and card.id not in dicebot.gamecards)):
            f |= CANDISCARD

        if (card.group.kp is not None and card.group.kp == pl) or pl.id == ADMIN_ID:
            f |= CANMODIFY

        return f

    gp: Group = thing
    f = 0

    if isingroup(gp, pl):
        f |= INGROUP

    if f == 0:
        return BOTADMIN if pl.id == ADMIN_ID else 0

    if gp.kp is not None and gp.kp == pl:
        f |= GROUPKP

    if ispladmin(gp, pl):
        f |= GROUPADMIN

    if pl.id == ADMIN_ID:
        f |= BOTADMIN

    return f
