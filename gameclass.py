# -*- coding:utf-8 -*-
import copy
from io import TextIOWrapper
from typing import Any, Dict, List, Optional, Tuple, Union
from telegram import Chat
from dicefunc import *

# 卡信息存储于群中


def isconsttype(val) -> bool:
    if val is int or val is str or val is bool:
        return True
    if isinstance(val, list):
        for e in val:
            if not isconsttype(e):
                return False
        return True
    return False

# 基类


class datatype:
    def to_json(self, jumpkey: List[str] = []) -> dict:
        d: Dict[str, Any] = {}
        for key in self.__dict__:
            if self.__dict__[key] is None or key in jumpkey or self.__dict__[key] is function:
                continue
            if isconsttype(self.__dict__[key]):
                d[key] = self.__dict__[key]
            elif isinstance(self.__dict__[key], datatype):
                try:
                    d[key] = self.__dict__[key].to_json()
                except AttributeError:
                    pass
        return d

    def modify(self, attr: str, val, jumpkey: List[str] = []) -> Tuple[str, bool]:
        if attr in self.__dict__ and isconsttype(val) and type(val) == type(self.__dict__[attr]):
            rttext = str(self.__dict__[attr])
            self.__dict__[attr] = val
            return rttext, True
        for key in self.__dict__:
            if key in jumpkey or self.__dict__[key] is function:
                continue
            if isinstance(self.__dict__[key], datatype):
                try:
                    rttext, ok = self.__dict__[key].modify(attr, val)
                    if ok:
                        return rttext, True
                except AttributeError:
                    pass

    def read_json(self, d: dict, jumpkeys: List[str] = []) -> None:
        for key in self.__dict__:
            if key in d and key not in jumpkeys:
                self.__dict__[key] = d[key]
        return


class GameCard(datatype):
    def __init__(self, carddict: dict = {}):
        self.id: int = 0
        self.playerid: int = 0
        self.player: Optional[Player] = None  # 需要在载入时赋值
        self.groupid: int = 0
        self.group: Optional[Group] = None  # 需要在载入时赋值
        self.data: CardData
        self.info: CardInfo
        self.skill: Skill
        self.interest: Skill
        self.suggestskill: SgSkill
        self.attr: CardAttr
        self.background: CardBackground = CardBackground()
        self.tempstatus: CardStatus = CardStatus()
        self.item: List[str] = []
        self.assets: str = ""
        self.type: str = ""
        self.discard: bool = False
        self.status: str = ""
        if len(carddict) > 0:
            self.read_json(carddict)

    def read_json(self, d: dict, jumpkeys: List[str] = []) -> None:
        super().read_json(d, jumpkeys=[
            "data", "info", "skill", "interest", "suggestskill", "attr", "background", "tempstatus"])
        for key in d:
            if key == "data":
                self.data = CardData(d[key])
            elif key == "info":
                self.info = CardInfo(d[key])
            elif key == "skill":
                self.skill = Skill(d[key])
            elif key == "interest":
                self.interest = Skill(d[key])
            elif key == "suggestskill":
                self.suggestskill = SgSkill(d[key])
            elif key == "attr":
                self.attr = CardAttr(d[key])
            elif key == "background":
                self.background = CardBackground(d[key])
            elif key == "tempstatus":
                self.tempstatus = CardStatus(d[key])

    def __str__(self):
        rttext: str = ""
        rttext += "id: "+str(self.id)+"\n"
        rttext += "playerid: "+str(self.playerid)+"\n"
        rttext += "groupid: "+str(self.groupid)+"\n"
        rttext += "基础数值: "+"\n"
        rttext += str(self.data)+"\n"
        rttext += "信息: "+"\n"
        rttext += str(self.info)+"\n"
        rttext += "技能: "+"\n"
        rttext += str(self.skill)+"\n"
        rttext += "兴趣技能: "+"\n"
        rttext += str(self.interest)+"\n"
        rttext += "建议技能: "+"\n"
        rttext += str(self.suggestskill)+"\n"
        # rttext += "角色卡检查: "+"\n"
        # for keys in self.cardcheck:
        #     rttext += keys+": "+str(self.cardcheck[keys])+"\n"
        rttext += "其他属性: "+"\n"
        rttext += str(self.attr)+"\n"
        rttext += "背景故事: "+"\n"
        rttext += str(self.background)+"\n"
        rttext += "临时检定加成: "+"\n"
        rttext += str(self.tempstatus)+"\n"
        rttext += "物品: "+'，'.join(self.item)+"\n"
        rttext += "资产: "+self.assets+"\n"
        rttext += "角色类型: "+self.type+"\n"
        rttext += "玩家是否可删除该卡: "
        if self.discard:
            rttext += "是\n"
        else:
            rttext += "否\n"
        rttext += "状态: "+self.status+"\n"
        return rttext

    def check(self) -> bool:
        pass
        return True

    def additem(self, item: str) -> None:
        self.item.append(item)

    def modify(self, attr: str, val) -> Tuple[str, bool]:
        if attr == "GLOBAL":
            self.tempstatus.modify(attr, val)
        return super().modify(attr, val, jumpkey="tempstatus")


class Player(datatype):
    def __init__(self, plid: Optional[int] = None, d: dict = {}):
        self.cards: Dict[int, GameCard] = {}  # 需要在载入时赋值。存储时：存储群-卡id对
        self.gamecards: Dict[int, GameCard] = {}  # 需要在载入时赋值。存储时：存储群-卡id对
        # 需要在载入时赋值。存储时：卡id
        self.controlling: Optional[Union[GameCard, int]] = None
        self.id = plid
        self.kpgroups: Dict[int, Group] = {}
        self.kpgames: Dict[int, GroupGame] = {}
        for key in d:
            pass

    def iskp(self, gpid: int) -> bool:
        if gpid in self.kpgroups:
            return True
        return False

    def write(self, f: Optional[TextIOWrapper] = None):
        if f is None:
            return
        pass

    def to_json(self) -> dict:
        d = {}
        for key in self.__dict__:
            if isconsttype(self.__dict__[key]):
                d[key] = self.__dict__[key]
        # cards
        idlist: List[int] = []
        for key in self.cards:
            idlist.append(key)
        d["cards"] = idlist
        # gamecards
        idlist: List[int] = []
        for key in self.gamecards:
            idlist.append(key)
        d["gamecards"] = idlist
        # controlling
        if self.controlling is not None and self.controlling is not int:
            d["controlling"] = self.controlling.id
        return d


class Group(datatype):
    def __init__(self, gpid: Optional[int] = None, d: dict = {}):
        self.id: Optional[int] = gpid
        self.cards: Dict[int, GameCard] = {}
        self.game: Optional[GroupGame] = None
        self.rule: GroupRule = GroupRule()
        self.pausedgame: Optional[GroupGame] = None
        self.kp: Optional[Union[Player, int]] = None  # 需要在载入时赋值
        self.chat: Union[Chat, int] = None  # 需要在载入时赋值
        for key in d:
            if key == "game":
                self.game = GroupGame(d[key])
            elif key == "rule":
                self.rule.changeRules(d[key])
            elif key == "pausedgame":
                self.holdinggame = GroupGame(d[key])
            elif key == "cards":
                for key2 in d[key]:
                    self.cards[int(key2)] = GameCard(d[key][key2])
                    self.cards[int(key2)].group = self
            else:
                self.__dict__[key] = d[key]

    def iskp(self, plid: int) -> bool:
        if self.kp and self.kp.id == plid:
            return True
        return False

    def getkp(self) -> Optional[Player]:
        return self.kp

    def write(self, f: Optional[TextIOWrapper] = None):
        if f is None:
            return
        pass

    def getcard(self, cardid: int) -> Optional[GameCard]:
        if cardid in self.cards:
            return self.cards[cardid]
        return None

    def to_json(self) -> dict:
        d = super().to_json(["kp", "chat"])
        if self.kp is not None:
            d['kp'] = self.kp.id
        d['chat'] = self.chat.id
        return d


class CardData(datatype):
    def __init__(self, d: dict = {}):
        self.STR: int = 0
        self.SIZ: int = 0
        self.CON: int = 0
        self.DEX: int = 0
        self.APP: int = 0
        self.POW: int = 0
        self.INT: int = 0
        self.EDU: int = 0
        self.LUCK: int = 0
        self.TOTAL: int = 0
        self.datainfo: str = ""
        self.__datanames: List[str] = ["STR", "SIZ", "CON",
                                       "DEX", "POW", "APP", "INT", "EDU"]
        self.__alldatanames: List[str] = copy.copy(
            self.__datanames).append("LUCK")
        if not d:
            self.randdata()
        else:
            for key in d:
                self.__dict__[key] = d[key]

    def total(self) -> int:
        self.TOTAL = 0
        for key in self.__datanames:
            self.TOTAL += self.__dict__[key]
        self.TOTAL += self.LUCK
        return self.TOTAL

    def randdata(self) -> None:
        text = ""
        a, b, c = dicemdn(3, 6)
        self.STR = 5*(a+b+c)
        text += get3d6str("STR", a, b, c)
        a, b, c = dicemdn(3, 6)
        self.CON = 5*(a+b+c)
        text += get3d6str("CON", a, b, c)
        a, b = dicemdn(2, 6)
        self.SIZ = 5*(a+b+6)
        text += get2d6_6str("SIZ", a, b)
        a, b, c = dicemdn(3, 6)
        self.DEX = 5*(a+b+c)
        text += get3d6str("DEX", a, b, c)
        a, b, c = dicemdn(3, 6)
        self.APP = 5*(a+b+c)
        text += get3d6str("APP", a, b, c)
        a, b = dicemdn(2, 6)
        self.INT = 5*(a+b+6)
        text += get2d6_6str("INT", a, b)
        a, b, c = dicemdn(3, 6)
        self.POW = 5*(a+b+c)
        text += get3d6str("POW", a, b, c)
        a, b = dicemdn(2, 6)
        self.EDU = 5*(a+b+6)
        text += get2d6_6str("EDU", a, b)
        self.datainfo = text

    def countless50discard(self) -> bool:
        countless50 = 0
        for key in self.__datanames:
            if self.__dict__[key] < 50:
                countless50 += 1
        if countless50 >= 3:
            return True
        return False

    def modify(self, attr: str, val: int) -> bool:
        pass
        return True


class CardStatus(datatype):
    def __init__(self):
        self.STR: int = 0
        self.SIZ: int = 0
        self.CON: int = 0
        self.DEX: int = 0
        self.POW: int = 0
        self.INT: int = 0
        self.EDU: int = 0
        self.LUCK: int = 0
        self.GLOBAL: int = 0

    def modify(self, attr: str, val) -> bool:
        pass
        return True


class CardInfo(datatype):
    def __init__(self):
        self.name: str = ""
        self.age: int = ""
        self.sex: str = ""
        self.job: str = ""

    def modify(self, attr: str, val) -> bool:
        pass
        return True


class Skill(datatype):
    def __init__(self):
        self.points: int = -1
        self.skills: Dict[str, int] = {}
        self.card: Optional[GameCard] = None  # 需要在载入时赋值

    def modify(self, attr: str, val) -> bool:
        pass
        return True

    def get(self, skillname: str) -> int:
        if skillname in self.skills:
            return self.skills[skillname]
        return -1

    def set(self, skillname: str, val: int) -> None:
        self.skills[skillname] = val


class SgSkill(datatype):
    def __init__(self):
        self.skills: Dict[str, int] = {}


class CardAttr(datatype):
    def __init__(self, card: GameCard):
        self.DB: str
        self.MOV: str
        self.atktimes: str
        self.physique: int
        self.SAN: int
        self.MAXSAN: int
        self.LP: int
        self.MAXLP: int

    def modify(self, attr: str, val) -> bool:
        pass
        return True


class CardBackground(datatype):
    def __init__(self):
        self.description: str = ""
        self.vip: str = ""
        self.viplace: str = ""
        self.faith: str = ""
        self.preciousthing: str = ""
        self.speciality: str = ""
        self.dmg: str = ""
        self.terror: str = ""
        self.myth: str = ""
        self.thirdencounter: str = ""

    def modify(self, attr: str, val) -> bool:
        pass
        return True

# 保存在群中


class GroupGame(datatype):  # If defined, game is started.
    def __init__(self, groupid, cards: Dict[int, dict] = {}, kpid: int = None):
        self.group: Group = None  # 需要在载入时赋值
        if isinstance(groupid, dict):
            self.groupid: int = groupid["groupid"]
            self.kpid: int = groupid["kpid"]
            self.kpctrl: int = groupid["kpctrl"]
            self.tpcheck: int = groupid["tpcheck"]
            tpcardslist = groupid["cards"]
            self.cards: Dict[int, GameCard] = {}
            for i in tpcardslist:
                t = GameCard(tpcardslist[i])
                self.cards[t.id] = t
            del tpcardslist, t
        else:
            self.groupid: int = groupid  # Unique, should not be edited after initializing
            self.kpid: int = kpid  # Can be edited
            self.cards: Dict[int, GameCard] = {}  # list of GameCard
            for i in cards:
                self.cards[i] = GameCard(cards[i])
            self.kpctrl: int = -1
            self.tpcheck: int = 0
        self.kpcards: Dict[int, GameCard] = {}
        for i in self.cards:
            if self.cards[i].playerid == self.kpid:
                self.kpcards[i] = self.cards[i]

    def __str__(self):
        rttext = ""
        for keys in self.__dict__:
            if keys == "cards" or keys == "kpcards":
                continue
            rttext += keys+": "+str(self.__dict__[keys])+"\n"
        rttext += "游戏中卡共有"+str(len(self.cards)) + \
            "张，其中kp所持卡共有"+str(len(self.kpcards))+"张"
        return rttext


class GroupRule(datatype):
    """一场游戏的规则。

    KP在群里用`/setrule`设置规则。群中如果没有规则，会自动生成默认规则。"""

    def __init__(self, rules: Dict[str, List[int]] = {}):  # 不允许用户调用
        # 0位参数描述一般技能上限，1位参数描述专精技能上限，2位参数描述专精技能个数。上限<=99
        self.skillmax: List[int] = [80, 90, 1]
        # 0位描述一般技能上限，1位描述专精技能上限，2位描述专精技能个数，3位描述至少到什么年龄才能使用此设置，如果没有设置的话默认100
        self.skillmaxAged: List[int] = [80, 90, 1, 100]
        # 1,3,5……位描述技能分段位置，单调递增，最后一个数必须是100。在大于skillcost[2*i-1]但小于等于skillcost[2*i+1]时，每一技能点花费skillcost[2*i]
        self.skillcost: List[int] = [1, 100]
        # 在检定需要骰出大于等于50时，greatsuccess[0]~greatsuccess[1]算大成功，否则greatsuccess[2]~greatsuccess[3]算大成功
        self.greatsuccess: List[int] = [1, 1, 1, 1]
        # 在检定需要骰出大于等于50时，greatfail[0]~greatfail[1]算大失败，否则greatfail[2]~greatfail[3]算大失败
        self.greatfail: List[int] = [100, 100, 96, 100]
        for key in rules:
            self.__dict__[key] = rules[key]

    def changeRules(self, cgrules: Dict[str, List[int]]) -> Tuple[str, bool]:
        rttext: str = ""
        for key in cgrules:
            if key == "skillmax":
                if len(cgrules[key]) != 3:
                    return rttext+"skillmax 参数长度有误", False
                if cgrules[key][2] > 20:
                    return rttext+"skillmax 专精技能个数太多", False
                if cgrules[key][0] < 0 or cgrules[key][1] <= cgrules[key][0] or cgrules[key][1] >= 100 or cgrules[key][2] < 0:
                    return rttext+"skillmax 参数有误", False
                rttext += "skillmax设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "skillmaxAged":
                if len(cgrules[key]) != 4:
                    return rttext+"skillmaxAged 参数长度有误", False
                if cgrules[key][2] > 20:
                    return rttext+"skillmaxAged 专精技能个数太多", False
                if cgrules[key][0] < 0 or cgrules[key][1] <= cgrules[key][0] or cgrules[key][1] >= 100 or cgrules[key][2] < 0 or cgrules[key][3] < 17 or cgrules[key][3] > 100:
                    return rttext+"skillmaxAged 参数有误", False
                rttext += "skillmaxAged设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "skillcost":
                if len(cgrules[key]) & 1 != 0 or len(cgrules[key]) == 0:
                    return rttext+"skillcost 参数长度应当是偶数", False
                i = 0
                while i+2 < len(cgrules[key]):
                    if cgrules[key][i+2] <= cgrules[key][i]:
                        return rttext+"skillcost 参数有误", False
                    i += 2
                i = 1
                while i+2 < len(cgrules[key]):
                    if cgrules[key][i+2] <= cgrules[key][i]:
                        return rttext+"skillcost 参数有误，技能点数低时应该消耗更少", False
                    i += 2
                del i
                if cgrules[key][0] <= 0 or cgrules[key][1] <= 0:
                    return rttext+"skillcost 参数有误", False
                if cgrules[key][len(cgrules[key])-1] != 100:
                    return rttext+"skillcost 最后一个参数应该是100", False
                rttext += "skillcost设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "greatsuccess":
                if len(cgrules[key]) != 4:
                    return rttext+"greatsuccess 参数长度有误", False
                if cgrules[key][0] > cgrules[key][1] or cgrules[key][2] > cgrules[key][3]:
                    return rttext+"greatsuccess 参数有误", False
                if cgrules[key][0] <= 0 or cgrules[key][1] > 100 or cgrules[key][2] <= 0 or cgrules[key][1] > 100:
                    return rttext+"greatsuccess 参数有误", False
                rttext += "greatsuccess设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "greatfail":
                if len(cgrules[key]) != 4:
                    return rttext+"greatfail 参数长度有误", False
                if cgrules[key][0] > cgrules[key][1] or cgrules[key][2] > cgrules[key][3]:
                    return rttext+"greatfail 参数有误", False
                if cgrules[key][0] <= 0 or cgrules[key][1] > 100 or cgrules[key][2] <= 0 or cgrules[key][1] > 100:
                    return rttext+"greatfail 参数有误", False
                rttext += "greatfail设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            else:
                rttext += "无法识别的key："+key
                continue
        return rttext, True

    def __str__(self):
        rttext = ""
        rttext += "通常技能上限："+str(self.skillmax[0])+"\n"
        if self.skillmax[2] != 0:
            rttext += "有"+str(self.skillmax[2]) + \
                "项技能上限为"+str(self.skillmax[1])+"\n"
        if self.skillmaxAged[3] == 100:
            rttext += "高年龄段的技能上限增强：关闭\n"
        else:
            rttext += "高年龄段的技能上限增强：开启\n"
            rttext += "年龄大于等于" + \
                str(self.skillmaxAged[3])+"时技能上限为" + \
                str(self.skillmaxAged[0])+"\n"
            if self.skillmaxAged[2] != 0:
                rttext += "有" + \
                    str(self.skillmaxAged[2])+"项技能上限为" + \
                    str(self.skillmaxAged[1])+"\n"
        rttext += "技能点数消耗规则：\n"
        for i in range(0, len(self.skillcost), 2):
            rttext += "当点数小于等于" + \
                str(self.skillcost[i+1])+"时，消耗"+str(self.skillcost[i])+"点\n"
        rttext += "大成功范围：\n"
        if self.greatsuccess[0] == self.greatsuccess[2] and self.greatsuccess[1] == self.greatsuccess[3]:
            if self.greatsuccess[0] == self.greatsuccess[1]:
                rttext += "骰出"+str(self.greatsuccess[0])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatsuccess[0])+"至" + \
                    str(self.greatsuccess[1])+"点\n"
        else:
            rttext += "当检定点数大于等于50时，"
            if self.greatsuccess[0] == self.greatsuccess[1]:
                rttext += "骰出"+str(self.greatsuccess[0])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatsuccess[0])+"至" + \
                    str(self.greatsuccess[1])+"点\n"
            rttext += "当检定点数低于50时，"
            if self.greatsuccess[2] == self.greatsuccess[3]:
                rttext += "骰出"+str(self.greatsuccess[2])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatsuccess[2])+"至" + \
                    str(self.greatsuccess[3])+"点\n"
        rttext += "大失败范围：\n"
        if self.greatfail[0] == self.greatfail[2] and self.greatfail[1] == self.greatfail[3]:
            if self.greatfail[0] == self.greatfail[1]:
                rttext += "骰出"+str(self.greatfail[0])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatfail[0])+"至"+str(self.greatfail[1])+"点\n"
        else:
            rttext += "当检定点数大于等于50时，"
            if self.greatfail[0] == self.greatfail[1]:
                rttext += "骰出"+str(self.greatfail[0])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatfail[0])+"至"+str(self.greatfail[1])+"点\n"
            rttext += "当检定点数低于50时，"
            if self.greatfail[2] == self.greatfail[3]:
                rttext += "骰出"+str(self.greatfail[2])+"点\n"
            else:
                rttext += "骰出" + \
                    str(self.greatfail[2])+"至"+str(self.greatfail[3])+"点\n"
        return rttext
