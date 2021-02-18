# -*- coding:utf-8 -*-

import asyncio
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, error
from telegram.callbackquery import CallbackQuery
from telegram.ext import CallbackContext, Updater

from createcard import *

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
CURRENT_CARD_DICT: Dict[int, Tuple[int, int]]
OPERATION: Dict[int, str] = {}

SKILL_DICT: dict
JOB_DICT: dict

SKILL_PAGES: List[List[str]]

DETAIL_DICT: Dict[int, str] = {}  # 临时地存储详细信息

IDENTIFIER = str(time.time())  # 在每个按钮的callback加上该标志，如果标志不相等则不处理


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


def getallid() -> List[int]:
    """读取全部卡ID，用于防止卡id重复"""
    idpool: List[int] = []
    for gpids in CARDS_DICT:
        for cdids in CARDS_DICT[gpids]:
            idpool.append(cdids)
            idpool.sort()
    return idpool


def isint(a: str) -> bool:
    try:
        int(a)
    except:
        return False
    return True


def sendtoAdmin(msg: str) -> None:
    updater.bot.send_message(chat_id=ADMIN_ID, text=msg)


# 检测json文件能否正常读取
try:
    GROUP_KP_DICT, CARDS_DICT, ON_GAME = readinfo()
    CURRENT_CARD_DICT = readcurrentcarddict()
    SKILL_DICT = readskilldict()
    SKILL_PAGES = createSkillPages(SKILL_DICT)
    JOB_DICT = JOB_DICT
    GROUP_RULES = readrules()
except:
    sendtoAdmin("读取文件出现问题，请检查json文件！")
    exit()

# 读取完成
updater.bot.send_message(
    chat_id=ADMIN_ID, text="Bot is live!")


def dicemdn(m: int, n: int) -> List[int]:
    if m == 0:
        return []
    if m > 20:
        return []
    ans = np.random.randint(1, n+1, size=m)
    ans = list(map(int, ans))
    return ans


def commondice(dicename) -> str:
    if dicename.find('+') < 0:
        if dicename.find('d') < 0:
            return "Invalid input."
        dices = dicename.split('d')
        if len(dices) != 2 or not isint(dices[0]) or not isint(dices[1]) or int(dices[0]) > 20:
            return "Invalid input."
        ansint = dicemdn(int(dices[0]), int(dices[1]))
        if len(ansint) == 0:
            return "Invalid input."
        if len(ansint) == 1:
            return dicename+" = "+str(ansint[0])
        ans = dicename + " = "
        for i in range(len(ansint)):
            if i < len(ansint)-1:
                ans += str(ansint[i])+'+'
            else:
                ans += str(ansint[i])
        ans += " = "+str(int(sum(ansint)))
        return ans
    dicess = dicename.split('+')
    ansint: List[int] = []
    for i in range(len(dicess)):
        if dicess[i].find('d') < 0 and not isint(dicess[i]):
            return "Invalid input."
        if isint(dicess[i]):
            ansint.append(int(dicess[i]))
        else:
            dices = dicess[i].split('d')
            if len(dices) != 2 or not isint(dices[0]) or not isint(dices[1]) or int(dices[0]) > 20:
                return "Invalid input."
            ansint += dicemdn(int(dices[0]), int(dices[1]))
    ans = dicename + " = "
    for i in range(len(ansint)):
        if i < len(ansint)-1:
            ans += str(ansint[i])+'+'
        else:
            ans += str(ansint[i])
    ans += " = "+str(int(sum(ansint)))
    return ans


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


def hascard(plid: int, gpid: int) -> bool:
    """判断一个群内是否已经有pl的卡"""
    if gpid not in CARDS_DICT:
        return False
    for cdid in CARDS_DICT[gpid]:
        cardi = CARDS_DICT[gpid][cdid]
        if cardi.playerid == plid:
            return True
    return False


def findcardwithid(cdid: int) -> Tuple[GameCard, bool]:
    """输入一个卡id，返回这张卡"""
    for gpid in CARDS_DICT:
        if cdid in CARDS_DICT[gpid]:
            return CARDS_DICT[gpid][cdid], True
    return None, False


def findallplayercards(plid: int) -> List[Tuple[int, int]]:
    """输入一个player的id，返回他的所有卡的`(groupid, id)`对"""
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
    `lower`表示最小值，`upper`表示最大值，均是按钮返回结果的一部分。
    `keystr1`, `keystr2`是`callback_data`的内容，按钮的`callback_data`结构为：
    ```
    keystr1+" "+keystr2+" "+str(integer)
    ```
    `step`参数表示按钮会遍历大于`lower`但小于`upper`的所有按钮的间隔。
    `column`参数表示返回的二维列表每行最多有多少个按钮。"""
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


def findcardfromgame(game: GroupGame, plid: int) -> GameCard:
    """从`game`中返回对应的`plid`的角色卡"""
    for i in game.cards:
        if i.playerid == plid:
            return i
    return None


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
    if not isint(dicename):  # 不是数字，先判断是否有'+'
        if dicename.find("+") == -1:  # 没有'+'，判断是否是单项骰子
            if dicename.find("d") == -1:
                return False
            a, b = dicename.split("d", maxsplit=1)
            if not isint(a) or not isint(b):
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
        try:
            update.message.reply_text(message, parse_mode="MarkdownV2")
        except:
            update.message.reply_text(message)
    return False


def changeplids(gpid: int, oldplid: int, newplid: int) -> None:
    """将某个群中所有`oldid`持有的卡改为`newplid`持有"""
    if gpid not in CARDS_DICT:
        return
    for cdid in CARDS_DICT[gpid]:
        cardi = CARDS_DICT[gpid][cdid]
        if cardi.playerid == oldplid:
            cardi.playerid = newplid
    writecards(CARDS_DICT)
    return


def changeKP(gpid: int, newkpid: int = 0) -> bool:
    """转移KP权限，接收参数：群id，新KP的id。

    会转移所有原KP控制的角色卡，包括正在进行的游戏"""
    if newkpid < 0:
        return False
    oldkpid = getkpid(gpid)
    if oldkpid == newkpid:
        return False
    changeplids(gpid, oldkpid, newkpid)
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


def makejobbutton() -> List[List[InlineKeyboardButton]]:
    """生成全部职业的按钮"""
    rtbuttons = [[]]
    for keys in JOB_DICT:
        if len(rtbuttons[len(rtbuttons)-1]) == 3:
            rtbuttons.append([])
        rtbuttons[len(
            rtbuttons)-1].append(InlineKeyboardButton(keys, callback_data=IDENTIFIER+" "+"job "+keys))
    return rtbuttons


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
    if skillname == "信用":
        if card1.info["job"] in JOB_DICT:
            maxval = min(maxval, JOB_DICT[card1.info["job"]][1])
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


def cgcredit(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    m = 0
    mm = -1
    if card1.info["job"] in JOB_DICT:
        m = JOB_DICT[card1.info["job"]][0]
        mm = JOB_DICT[card1.info["job"]][1]
    aged, ok = skillcantouchmax(card1)
    if aged:
        skillmaxrule = GROUP_RULES[card1.groupid].skillmaxAged
    else:
        skillmaxrule = GROUP_RULES[card1.groupid].skillmax
    if ok:
        mm = skillmaxrule[1]
    else:
        mm = skillmaxrule[0]
    mm = skillmaxval("信用", card1, True)


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
    if not generatePoints(card1, jobname):
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
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill["points"]))
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加主要技能。剩余技能点："+str(card1.skill["points"])+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttoncgmainskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill["points"]))
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "更改主要技能点数。剩余技能点："+str(card1.skill["points"])+" 技能名称："+args[1]+"，当前技能点："+str(card1.skill[args[1]]), reply_markup=rp_markup)
    return True


def buttonaddsgskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, True)
        card1.skill[args[1]] = skvalue
        card1.skill["points"] -= needpt
        query.edit_message_text(
            text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill["points"]))
        card1.suggestskill.pop(args[1])
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, True)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加建议技能。剩余技能点："+str(card1.skill["points"])+" 技能名称："+args[1], reply_markup=rp_markup)
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
        needpt = evalskillcost(args[1], skvalue, card1, False)
        card1.interest[args[1]] = skvalue
        card1.interest["points"] -= needpt
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest["points"]))
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "添加兴趣技能。剩余技能点："+str(card1.interest["points"])+" 技能名称："+args[1], reply_markup=rp_markup)
    return True


def buttoncgintskill(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    if len(args) == 3:
        skvalue = int(args[2])
        needpt = evalskillcost(args[1], skvalue, card1, False)
        card1.interest[args[1]] = skvalue
        card1.interest["points"] -= needpt
        query.edit_message_text(
            text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest["points"]))
        writecards(CARDS_DICT)
        return True
    m = getskilllevelfromdict(card1, args[1])
    mm = skillmaxval(args[1], card1, False)
    rtbuttons = makeIntButtons(m, mm, args[0], args[1])
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    query.edit_message_text(
        "更改兴趣技能点数。剩余技能点："+str(card1.interest["points"])+" 技能名称："+args[1]+"，当前技能点："+str(card1.interest[args[1]]), reply_markup=rp_markup)
    return True


def buttonstrdec(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    strdecval = int(args[2])
    card1, rttext, needcon = choosedec(card1, strdecval)
    if needcon:
        rttext += "\n使用 /setcondec 来设置CON（体质）下降值。"
    else:
        generateOtherAttributes(card1)
    writecards(CARDS_DICT)
    query.edit_message_text(rttext)
    return True


def buttoncondec(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    condecval = int(args[2])
    card1, rttext = choosedec2(card1, condecval)
    generateOtherAttributes(card1)
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
        query.edit_message_text("修改成功，现在操作的卡id是："+str(cdid))
    else:
        query.edit_message_text("修改成功，现在操作的卡是："+cardi.info["name"])
    return True


def buttonswitchkp(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    kpid = update.message.from_user.id
    ctrlid = int(args[1])
    game, ok = findgamewithkpid(kpid)
    if not ok:
        query.edit_message_text("没有找到游戏。")
        return False
    cardi, ok = findcardfromgamewithid(game, ctrlid)
    if not ok or cardi.playerid != kpid:
        query.edit_message_text("没有找到这张npc卡。")
        return False
    game.kpctrl = ctrlid
    writegameinfo(ON_GAME)
    query.edit_message_text("修改操纵的npc卡成功，id为："+str(ctrlid))
    return True


def buttonsetsex(query: CallbackQuery, update: Update, card1: GameCard, args: List[str]) -> bool:
    plid = update.effective_chat.id
    cardi, ok = findcard(plid)
    if not ok:
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


def addskill0(update: Update, context: CallbackContext, card1: GameCard) -> bool:
    """表示指令/addskill 中没有参数的情况。
    创建技能按钮来完成技能的添加。

    因为兴趣技能过多，使用可以翻页的按钮列表。"""
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
            update.message.reply_text("剩余点数："+str(
                card1.skill["points"])+"\n请选择一项主要技能用于增加技能点", reply_markup=rp_markup)
            return True
        # GOOD TRAP: addsgskill
        for keys in card1.suggestskill:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                    str(card1.suggestskill[keys]), callback_data=IDENTIFIER+" "+"addsgskill "+keys))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("剩余点数："+str(
            card1.skill["points"])+"\n请选择一项主要技能", reply_markup=rp_markup)
        return True
    # turn to interest.
    if card1.interest["points"] <= 0:  # HIT BAD TRAP
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
    if skillname == "信用" and card1.info["job"] in JOB_DICT:
        m = max(m, JOB_DICT[card1.info["job"]][0])
    if skillname in card1.skill:  # GOOD TRAP: cgmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "cgmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改主要技能点数。剩余技能点："+str(card1.skill["points"])+" 技能名称："+skillname+"，当前技能点："+str(card1.skill[skillname]), reply_markup=rp_markup)
        return True
    if skillname in card1.suggestskill:  # GOOD TRAP: addsgskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addsgskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "添加建议技能。剩余技能点："+str(card1.skill["points"])+" 技能名称："+skillname, reply_markup=rp_markup)
        return True
    if skillname in card1.interest:  # GOOD TRAP: cgintskill
        mm = skillmaxval(skillname, card1, False)
        rtbuttons = makeIntButtons(m, mm, "cgintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "更改兴趣技能点数。剩余技能点："+str(card1.interest["points"])+" 技能名称："+skillname+"，当前技能点："+str(card1.interest[skillname]), reply_markup=rp_markup)
        return True
    if card1.skill["points"] > 0:  # GOOD TRAP: addmainskill
        mm = skillmaxval(skillname, card1, True)
        rtbuttons = makeIntButtons(m, mm, "addmainskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text(
            "添加主要技能。剩余技能点："+str(card1.skill["points"])+" 技能名称："+skillname, reply_markup=rp_markup)
        return True
    mm = skillmaxval(skillname, card1, False)
    rtbuttons = (m, mm, "addintskill", skillname)
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text(
        "添加兴趣技能。剩余技能点："+str(card1.interest["points"])+" 技能名称："+skillname, reply_markup=rp_markup)
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
            sendmsg = updater.bot.send_message(
                chat_id=gpid, text=msg)
        except error.ChatMigrated as err:
            sendtoAdmin(
                "群id发生变化，原群id："+str(gpid)+"变化为"+str(err.new_chat_id))
            if popallempties(CARDS_DICT):
                writecards(CARDS_DICT)
            _, ok = findgame(err.new_chat_id)
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
    if "name" not in cardi.info or cardi.info["name"] == "":
        return "None"
    return cardi.info["name"]


def cardpop(gpid: int, cdid: int) -> GameCard:
    if gpid not in CARDS_DICT:
        return None
    if cdid not in CARDS_DICT[gpid]:
        return None
    plid = CARDS_DICT[gpid][cdid].playerid
    cgp, cid = CURRENT_CARD_DICT[plid]
    if cgp == gpid and cid == cdid:
        CURRENT_CARD_DICT.pop(plid)
        writecurrentcarddict(CURRENT_CARD_DICT)
    cardi = CARDS_DICT[gpid].pop(cdid)
    writecards(CARDS_DICT)
    return cardi


def cardadd(cardi: GameCard) -> bool:
    gpid = cardi.groupid
    cdid = cardi.id
    if gpid not in CARDS_DICT:
        CARDS_DICT[gpid] = {}
    if cdid in CARDS_DICT[gpid]:
        return False
    CARDS_DICT[gpid][cdid] = cardi
    writecards(CARDS_DICT)
    CURRENT_CARD_DICT[cardi.playerid] = (gpid, cdid)
    writecurrentcarddict(CURRENT_CARD_DICT)
    return True


def cardget(gpid: int, cdid: int) -> GameCard:
    if gpid not in CARDS_DICT:
        return None
    if cdid not in CARDS_DICT[gpid]:
        return None
    return CARDS_DICT[gpid][cdid]


def addOP(chatid: int, op: str) -> None:
    OPERATION[chatid] = op


def popOP(chatid) -> str:
    if chatid not in OPERATION:
        return ""
    return OPERATION.pop(chatid)


def getOP(chatid) -> str:
    if chatid not in OPERATION:
        return ""
    return OPERATION[chatid]


def cardsetage(update: Update, cardi: GameCard, age: int) -> bool:
    if "AGE" in cardi.info and cardi.info["AGE"] > 0:
        popOP(update.effective_chat.id)
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


def textnewcard(update: Update, context: CallbackContext) -> bool:
    text = update.message.text
    plid = update.effective_chat.id
    if not isint(text) or int(text) >= 0:
        return errorHandler(update, "无效群id。如果你不知道群id，在群里发送 /getid 获取群id。")
    gpid = int(text)
    if hascard(plid, gpid) and getkpid(gpid) != plid:
        popOP(plid)
        return errorHandler(update, "你在这个群已经有一张卡了！")
    popOP(plid)
    return getnewcard(update, gpid, plid)


def textsetage(update: Update, context: CallbackContext) -> bool:
    text = update.message.text
    plid = update.effective_chat.id
    if not isint(text):
        return errorHandler(update, "输入无效，请重新输入")
    cardi, ok = findcard(plid)
    if not ok:
        popOP(plid)
        return errorHandler(update, "找不到卡")
    if cardsetage(update, cardi, int(text)):
        popOP(plid)
        return True
    return False


def textsetname(update: Update, plid: int) -> bool:
    if plid == 0:  # 私聊情形
        plid = update.effective_chat.id
    if update.message.from_user.id != plid:
        return True  # 不处理
    popOP(update.effective_chat.id)
    text = update.message.text
    cardi, ok = findcard(plid)
    if not ok:
        return errorHandler(update, "找不到卡。")
    cardi.info["name"] = text
    update.message.reply_text("姓名设置完成："+text)


def textsetsex(update: Update, plid: int) -> bool:
    if plid == 0:  # 私聊情形
        plid = update.effective_chat.id
    if update.message.from_user.id != plid:
        return True
    popOP(update.effective_chat.id)
    text = update.message.text
    cardi, ok = findcard(plid)
    if not ok:
        return errorHandler(update, "找不到卡。")
    return cardsetsex(update, cardi, text)


def countless50discard(cardi: GameCard) -> bool:
    countless50 = 0
    for keys in cardi.data:
        if cardi.data[keys] < 50:
            countless50 += 1
    if countless50 >= 3:
        return True
    return False


def getnewcard(update: Update, gpid: int, plid: int, cdid: int = -1) -> bool:
    """指令`/newcard`的具体实现"""
    if gpid not in CARDS_DICT:
        CARDS_DICT[gpid] = {}
    new_card, detailmsg = generateNewCard(plid, gpid)
    allids = getallid()
    if cdid >= 0 and cdid not in allids:
        new_card.id = cdid
    else:
        if cdid >= 0 and cdid in allids:
            update.message.reply_text(
                "输入的ID已经被占用，自动获取ID。可以用 /changeid 更换喜欢的id。")
        nid = 0
        while nid in allids:
            nid += 1
        new_card.id = nid
    update.message.reply_text(
        "角色卡已创建，您的卡id为："+str(new_card.id)+"。详细信息如下：\n"+detailmsg)
    # 如果有3个属性小于50，则discard=true
    if countless50discard(new_card):
        new_card.discard = True
        update.message.reply_text(
            "因为有三项属性小于50，如果你愿意的话可以使用 /discard 来删除这张角色卡。设定年龄后则不能再删除这张卡。")
    update.message.reply_text(
        "长按 /setage 并输入一个数字来设定年龄。如果需要卡片制作帮助，使用 /createcardhelp 来获取帮助。")
    if plid in CURRENT_CARD_DICT:
        update.message.reply_text(
            "创建新卡时，控制自动切换至新卡。如果需要切换你操作的另一张卡，用 /switch 切换")
    cardadd(new_card)
    return True


def botchat(update: Update) -> None:
    if isgroupmsg(update):
        return
    text = update.message.text
    if text[:1] == "我":
        update.message.reply_text("你"+text[1:])
        return
    if text.find("傻逼"):
        update.message.reply_text("明白了，你是傻逼")
        return
