# -*- coding:utf-8 -*-
import copy
import json
import os
from inspect import isfunction
from typing import Any, Dict, Iterator, List, Optional, Tuple

from telegram import Chat
from telegram.ext.updater import Updater

from basicfunc import *
from cfg import *
from dicefunc import *

PLTYPE = "PL"
NPCTYPE = "NPC"

skl: Dict[str, int]

with open(PATH_SKILLDICT, 'r', encoding='utf-8') as f:
    skl = json.load(f)


class datatype:
    """基类"""

    def read_json(self, d: dict, jumpkeys: List[str] = []) -> None:
        """把除了jumpkeys以外的key全部读入self.__dict__"""
        for key in iter(self.__dict__):
            if key in d and key not in jumpkeys:
                self.__dict__[key] = d[key]

    def to_json(self, jumpkey: List[str] = []) -> dict:
        """将值为常量或datatype的子类的成员加入字典d。若成员是类，则需要重新定义该函数"""
        d: Dict[str, Any] = {}
        for key in iter(self.__dict__):
            val = self.__dict__[key]
            if val is None or key in jumpkey or isfunction(val):
                continue
            if isconsttype(val):
                if isinstance(val, dict) and isallkeyint(val):
                    d[key] = turnkeyint(val)
                else:
                    d[key] = val
            elif isinstance(val, datatype):
                d[key] = val.to_json()
        return d

    def show(self, attr: str, jumpkey: List[str] = []) -> str:
        """向下查找成员attr并返回其字符串形式，忽略jumpkey中的成员。如果不是可转换为str的类型则抛出ValueError"""
        if hasattr(self, attr):
            try:
                return str(self.__dict__[attr])
            except Exception:
                raise ValueError("无法转换为str")

        for key in iter(self.__dict__):
            val = self.__dict__[key]
            if key in jumpkey or not isinstance(val, datatype):
                continue

            x = val.show(attr)
            if x != "找不到该属性":
                return x

        return "找不到该属性"

    def modify(self, attr: str, val: str, jumpkey: List[str] = []) -> Tuple[str, bool]:
        """向下查找成员attr并修改其值为val，忽略jumpkey中的成员。如果val类型和原本类型（不是None）不相同，则抛出TypeError"""
        if hasattr(self, attr):
            if not istrueconsttype(self.__dict__[attr]) and not isinstance(self.__dict__[attr], list):
                raise TypeError("成员"+attr+"类型是无法修改的类型")

            if isinstance(self.__dict__[attr], list) and any(not istrueconsttype(x) for x in self.__dict__[attr]):
                raise TypeError("成员"+attr+"类型是无法修改的列表")

            if isinstance(self.__dict__[attr], list):
                # 默认list内所有元素都是相同type
                # 如果list长度为0，不可修改
                if len(self.__dict__[attr]) == 0:
                    raise TypeError("空列表不可以直接修改")

                # 预处理
                a = val.find('[')
                b = val.find(']')
                if a < 0 or b < 0:
                    raise TypeError("输入不是一个合法列表")

                val = val[a+1:b]
                val = ''.join(val.split())
                things = val.split(',')

                if type(self.__dict__[attr][0]) is int:
                    if any(isint(x) for x in things):
                        raise TypeError("输入的列表中存在非int型")
                    things = map(int, things)

                elif type(self.__dict__[attr][0]) is bool:
                    if any(x not in ["F", "false", "False", "假", "T", "true", "True", "真"] for x in things):
                        raise TypeError("输入的列表中存在非bool型，或输入不能识别")
                    things = map(tobool, things)

                ans = str(self.__dict__[attr])
                self.__dict__[attr] = list(things)
                return ans, True

            if attr in jumpkey:
                raise TypeError("该属性不支持修改")

            if type(self.__dict__[attr]) is bool:
                rttext = str(self.__dict__[attr])
                try:
                    self.__dict__[attr] = tobool(val)
                except TypeError as e:
                    raise e

            elif type(self.__dict__[attr]) is int:
                if not isint(val):
                    raise TypeError("给定参数不是int")

                rttext = str(self.__dict__[attr])
                self.__dict__[attr] = int(val)

            else:
                # str
                rttext = self.__dict__[attr]
                self.__dict__[attr] = val

            if hasattr(self, "write") and isfunction(self.write):
                self.write()
            return rttext, True

        # 向下查找递归调用modify()
        for key in iter(self.__dict__):
            if key in jumpkey:
                continue

            v = self.__dict__[key]
            if isinstance(v, datatype):
                rttext, ok = v.modify(attr, val)  # 使用下一级的默认参数
                if ok:
                    if hasattr(self, "write") and isfunction(self.write):
                        self.write()
                    return rttext, True
        return "", False  # 支持重载，返回False不一定代表找不到

    def write(self): ...
    def delete(self): ...


class GameCard(datatype):
    """表示游戏中的卡片。具有属性：id, playerid, player, groupid, group, data, info, skill, interest, suggestskill, 
    attr, background, tempstatus, item, assets, type, discard, status, isgamecard"""

    def __init__(self, carddict: dict = {}):
        self.id: int = None

        self.playerid: int = 0
        self.player: Player = None  # 需要在载入时赋值

        self.groupid: int = 0
        self.group: Group = None  # 需要在载入时赋值

        # 下面六项初始化后不能为None
        self.data: CardData = None
        self.info: CardInfo = None
        self.skill: Skill = None
        self.interest: Skill = None
        self.suggestskill: SgSkill = None
        self.attr: CardAttr = None

        self.background: CardBackground = CardBackground()
        self.tempstatus: CardStatus = CardStatus()

        self.item: List[str] = []
        self.assets: str = ""
        self.type: str = ""
        self.discard: bool = False
        self.status: str = ""

        self.isgamecard: bool = False

        if len(carddict) > 0:
            self.read_json(carddict)
        # 如果有属性没有读到，使用默认初始化
        if self.data is None:
            self.data = CardData()
        if self.info is None:
            self.info = CardInfo()
        if self.skill is None:
            self.skill = Skill()
        if self.interest is None:
            self.interest = Skill()
            self.interest.type = "兴趣"
        if self.suggestskill is None:
            self.suggestskill = SgSkill()
        if self.attr is None:
            self.attr = CardAttr()

        self.cardConstruct()

    def read_json(self, d: dict, jumpkeys: List[str] = []) -> None:
        super().read_json(d, jumpkeys=[
            "data", "info", "skill", "interest", "suggestskill", "attr", "background", "tempstatus"])

        if "data" in d:
            self.data = CardData(d=d["data"])
        if "info" in d:
            self.info = CardInfo(d=d["info"])
        if "skill" in d:
            self.skill = Skill(d=d["skill"])
        if "interest" in d:
            self.interest = Skill(d=d["interest"])
            self.interest.type = "兴趣"
        if "suggestskill" in d:
            self.suggestskill = SgSkill(d=d["suggestskill"])
        if "attr" in d:
            self.attr = CardAttr(d=d["attr"])
        if "background" in d:
            self.background = CardBackground(d=d["background"])
        if "tempstatus" in d:
            self.tempstatus = CardStatus(d=d["tempstatus"])

    def to_json(self, jumpkey: List[str] = ["player", "group"]) -> dict:
        return super().to_json(jumpkey=jumpkey)

    def show(self, attr: str, jumpkey: List[str] = ["group", "player", "tempstatus"]) -> str:
        return super().show(attr, jumpkey=jumpkey)

    def modify(self, attr: str, val: str, jumpkey: List[str] = ["player", "playerid", "group", "groupid", "id", "tempstatus"]) -> Tuple[str, bool]:
        if attr == "points":
            return "需指明为mainpoints或intpoints", False
        if attr == "mainpoints":
            ans = self.skill.modify("points", val)
            self.write()
            return ans
        if attr == "intpoints":
            ans = self.interest.modify("points", val)
            self.write()
            return ans
        ans = super().modify(attr, val, jumpkey=jumpkey)
        self.write()
        return ans

    def generateAgeAttributes(self) -> str:
        if self.info.age < 17 or self.info.age > 99:
            return "年龄尚未设定"

        AGE = self.info.age

        luck = 5*sum(dicemdn(3, 6))

        rttext = ""

        if AGE < 20:
            luck2 = 5*sum(dicemdn(3, 6))
            if luck < luck2:
                self.data.LUCK = luck2
            else:
                self.data.LUCK = luck
            rttext += "年龄低于20，幸运得到奖励骰。结果分别为" + \
                str(luck)+", "+str(luck2)+"。教育减5，力量体型合计减5。"
            self.data.datadec = ("STR_SIZ", -5)
            self.data.EDU -= 5

        elif AGE < 40:
            # self.cardcheck["check2"] = True  # No STR decrease, check2 passes
            rttext += "年龄20-39，得到一次教育增强。"
            rttext += self.EDUenhance(1)
            rttext += "现在教育：" + str(self.data.EDU)+"。"

        elif AGE < 50:
            rttext += "年龄40-49，得到两次教育增强。\n"
            rttext += self.EDUenhance(2)
            rttext += "现在教育："+str(self.data.EDU)+"。\n"
            self.data.datadec = ("STR_CON", -5)
            self.data.APP -= 5
            rttext += "力量体质合计减5，外貌减5。\n"

        elif AGE < 60:
            rttext += "年龄50-59，得到三次教育增强。\n"
            rttext += self.EDUenhance(3)
            rttext += "现在教育："+str(self.data.EDU)+"。\n"
            self.data.datadec = ("STR_CON_DEX", -10)
            self.data.APP -= 10
            rttext += "力量体质敏捷合计减10，外貌减10。\n"

        elif AGE < 70:
            rttext += "年龄60-69，得到四次教育增强。\n"
            rttext += self.EDUenhance(4)
            rttext += "现在教育："+str(self.data.EDU)+"。\n"
            self.data.datadec = ("STR_CON_DEX", -20)
            self.data.APP -= 15
            rttext += "力量体质敏捷合计减20，外貌减15。\n"

        elif AGE < 80:
            rttext += "年龄70-79，得到四次教育增强。\n"
            rttext += self.EDUenhance(4)
            rttext += "现在教育："+str(self.data.EDU)+"。\n"
            self.data.datadec = ("STR_CON_DEX", -40)
            self.data.APP -= 20
            rttext += "力量体质敏捷合计减40，外貌减20。\n"

        else:
            rttext += "年龄80以上，得到四次教育增强。\n"
            rttext += self.EDUenhance(4)
            rttext += "现在教育："+str(self.data.EDU)+"。\n"
            self.data.datadec = ("STR_CON_DEX", -80)
            self.data.APP -= 25
            rttext += "力量体质敏捷合计减80，外貌减25。\n"

        if AGE >= 20:
            self.data.LUCK = luck
            rttext += "幸运："+str(luck)+"\n"

        if self.data.datadec is not None:
            rttext += "使用' /setstrdec STRDEC '来设置因为年龄设定导致的STR减少值，根据所设定的年龄可能还需要设置CON减少值。根据上面的提示减少的数值进行设置。\n"

        rttext += "使用 /setjob 进行职业设定。完成职业设定之后，用'/addskill 技能名 技能点数' 来分配技能点，用空格分隔。"
        return rttext

    def EDUenhance(self, times: int) -> str:
        if times > 4:
            return ""
        rttext = ""
        timelist = ["一", "二", "三", "四"]
        for j in range(times):
            a = dicemdn(1, 100)[0]
            if a > self.data.EDU:
                rttext += "第"+timelist[j]+"次检定增强："+str(a)+"成功，获得"
                a = min(99-self.data.EDU, np.random.randint(1, 11))
                rttext += str(a)+"点提升。\n"
                self.data.EDU += a
            else:
                rttext += "第"+timelist[j]+"次检定增强："+str(a)+"失败。\n"
        return rttext

    def basicinfo(self) -> str:
        rttext: str = ""
        rttext += "角色卡id: "+str(self.id)+"\n"
        rttext += "playerid: "+str(self.playerid)+"\n"
        rttext += "groupid: "+str(self.groupid)+"\n"

        rttext += "基础数值: "+"\n"
        rttext += str(self.data)+"\n"

        rttext += "信息: "+"\n"
        rttext += str(self.info)+"\n"

        rttext += "其他属性: "+"\n"
        rttext += str(self.attr)+"\n"

        return rttext

    def __str__(self) -> str:
        rttext: str = ""

        rttext += "角色卡id: "+str(self.id)+"\n"
        rttext += "playerid: "+str(self.playerid)+"\n"
        rttext += "groupid: "+str(self.groupid)+"\n\n"

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

        rttext += "其他属性: "+"\n"
        rttext += str(self.attr)+"\n"

        rttext += "背景: "+"\n"
        rttext += str(self.background)+"\n"

        rttext += "临时检定加成: "+"\n"
        rttext += str(self.tempstatus)+"\n"

        rttext += "物品: "+'，'.join(self.item)+"\n"

        rttext += "资产: "+self.assets+"\n"

        rttext += "角色类型: "+self.type+"\n"

        rttext += "玩家是否可删除该卡: "
        rttext += "是\n" if self.discard else "否\n"

        rttext += "状态: "+self.status+"\n"

        rttext += "是否为游戏中的角色卡: "
        rttext += "是\n" if self.isgamecard else "否\n"

        return rttext

    def getname(self) -> str:
        """获取角色卡名字信息。
        角色卡没有名字时，返回id的字符串形式"""
        return str(self.id) if self.info.name == "" else self.info.name

    def backtonewcard(self) -> None:
        self.data = CardData()
        self.info = CardInfo()
        self.skill = Skill()
        self.interest = Skill()
        self.interest.type = "兴趣"
        self.suggestskill = SgSkill()
        self.attr = CardAttr()
        self.tempstatus = CardStatus()
        self.item = []
        self.assets: str = ""
        self.write()

    def hasstatus(self, attr: str) -> bool:
        return self.tempstatus.hasstatus(attr)

    def getstatus(self, attr: str) -> bool:
        return self.tempstatus.getstatus(attr)

    def cardConstruct(self):
        self.skill.card = self
        self.interest.card = self
        self.data.card = self
        self.background.card = self

    def generateOtherAttributes(self) -> None:
        """获取到年龄之后，通过年龄计算一些衍生数据。"""
        if self.data.datadec is not None:
            return

        if self.attr.SAN == 0:
            self.attr.SAN = self.data.POW

        if self.attr.MAGIC == 0:
            self.attr.MAGIC = self.data.POW//5

        if self.attr.MAXHP == 0:
            self.attr.MAXHP = (self.data.SIZ+self.data.CON)//10
            self.attr.HP = self.attr.MAXHP

        if self.attr.build < -2:
            if self.data.STR+self.data.SIZ < 65:
                self.attr.build = -2
            elif self.data.STR+self.data.SIZ < 85:
                self.attr.build = -1
            elif self.data.STR+self.data.SIZ < 125:
                self.attr.build = 0
            elif self.data.STR+self.data.SIZ < 165:
                self.attr.build = 1
            elif self.data.STR+self.data.SIZ < 205:
                self.attr.build = 2
            else:
                self.attr.build = 2 + \
                    (self.data.STR+self.data.SIZ-125)//80

        if self.attr.MOV == 0:
            if self.data.DEX < self.data.SIZ and self.data.STR < self.data.SIZ:
                mov = 7
            elif self.data.DEX > self.data.SIZ and self.data.STR > self.data.SIZ:
                mov = 9
            else:
                mov = 8

            if self.info.age < 40:
                self.attr.MOV = mov
            elif self.info.age >= 80:
                self.attr.MOV = mov-5
            else:
                self.attr.MOV = mov - (self.info.age - 30)//10

        if self.attr.DB == "":
            if self.attr.build <= 0:
                self.attr.DB = str(self.attr.build)
            elif self.attr.build == 1:
                self.attr.DB = "1d4"
            else:
                self.attr.DB = str(self.attr.build-1)+"d6"

        self.write()

    def check(self) -> str:
        """如果卡片可以开始游戏，则返回空字符串，否则返回原因"""
        rttext: str = ""

        t = self.data.check()
        if t != "":
            rttext += t+"\n"

        t = self.info.check()
        if t != "":
            rttext += t+"\n"

        t = self.skill.check()
        if t != "":
            rttext += "主要"+t+"\n"

        t = self.interest.check()
        if t != "":
            rttext += "兴趣"+t+"\n"

        t = self.attr.check()
        if t != "":
            rttext += t+"\n"

        t = self.background.check()
        if t != "":
            rttext += t+"\n"

        if len(self.item) == 0:
            rttext += "没有设定随身物品\n"

        if self.assets == "":
            rttext += "没有设定财产"

        if rttext != "":
            rttext = "角色卡(id:"+str(self.id)+")信息不完整，检查到如下问题：\n"+rttext

        return rttext

    def additems(self, item: List[str]) -> None:
        self.item += item
        if len(item) > 0:
            self.write()

    def setassets(self, asset: str) -> None:
        self.assets = asset
        self.write()

    def write(self):
        if self.id is None:
            raise ValueError("写入文件时，GameCard实例没有id")

        if self.isgamecard:
            with open(PATH_GAME_CARDS+str(self.id)+".json", 'w', encoding='utf-8') as f:
                json.dump(self.to_json(), f, indent=4, ensure_ascii=False)
        else:
            with open(PATH_CARDS+str(self.id)+".json", 'w', encoding='utf-8') as f:
                json.dump(self.to_json(), f, indent=4, ensure_ascii=False)

    def delete(self):
        """删除文件"""
        if self.id is None:
            raise ValueError("删除文件时，GameCard实例没有id")
        try:
            if self.isgamecard:
                os.remove(PATH_GAME_CARDS+str(self.id)+".json")
            else:
                os.remove(PATH_CARDS+str(self.id)+".json")
        except Exception:
            ...

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GameCard):
            return False
        return self.id == o.id and self.isgamecard == o.isgamecard


class Player(datatype):
    """表示一个玩家。具有如下属性：id, cards, gamecards, controlling, name, username, kpgroups, kpgames, chat"""

    def __init__(self, plid: Optional[int] = None, d: dict = {}):
        self.cards: Dict[int, GameCard] = {}  # 需要在载入时赋值。存储时：存储卡id。读取时忽略
        self.gamecards: Dict[int, GameCard] = {}  # 需要在载入时赋值。存储时：存储卡id。读取时忽略
        # controlling 需要在载入时赋值。存储时：卡id。正确载入后类型为 GameCard | None
        self.controlling: Optional[GameCard] = None
        self.id: int = plid
        self.name: str = ""  # 读取时忽略
        self.username: str = ""  # 读取时忽略
        self.kpgroups: Dict[int, Group] = {}  # 需要在载入时赋值。存储时：存储int列表。读取时忽略
        self.kpgames: Dict[int, GroupGame] = {}  # 需要在载入时赋值。存储时：存储int列表。读取时忽略
        self.chat: Optional[Chat] = None  # 载入时赋值。存储与读取均忽略
        if len(d) > 0:
            self.read_json(d=d)

    def read_json(self, d: dict, jumpkeys: List[str] = ["cards", "gamecards", "kpgroups", "kpgames", "chat", "name", "username"]) -> None:
        return super().read_json(d, jumpkeys=jumpkeys)

    def to_json(self, jumpkey: List[str] = ["cards", "gamecards", "kpgroups", "kpgames", "controlling", "chat"]) -> dict:
        d = super().to_json(jumpkey=jumpkey)
        # cards
        idlist: List[int] = []
        for card in self.cards.values():
            idlist.append(card.id)
        d["cards"] = idlist
        # gamecards
        idlist: List[int] = []
        for card in self.gamecards.values():
            idlist.append(card.id)
        d["gamecards"] = idlist
        # controlling
        if self.controlling is not None and not type(self.controlling) is int:
            d["controlling"] = self.controlling.id
        elif type(self.controlling) is int:
            d["controlling"] = self.controlling
        # kpgroups
        idlist: List[int] = []
        for key in iter(self.kpgroups):
            idlist.append(key)
        d["kpgroups"] = idlist
        # kpgames
        idlist: List[int] = []
        for key in iter(self.kpgames):
            idlist.append(key)
        d["kpgames"] = idlist
        return d

    def show(self, attr: str, jumpkey: List[str] = []) -> str:
        if hasattr(self, attr):
            try:
                return str(self.__dict__[attr])
            except Exception:
                raise ValueError("无法转换为str")

        return "找不到该属性"

    def modify(self, attr: str, val, jumpkey: List[str]) -> Tuple[str, bool]:
        return "无法修改Player实例", False

    def getname(self) -> str:
        if self.id is None:
            raise TypeError("Player实例没有id")
        if self.chat is None:
            return self.name
        self.username = self.chat.username if self.chat.username is not None else ""
        name = self.chat.full_name
        self.name = name if name is not None else str(self.id)
        return self.name

    def renew(self, updater: Updater) -> None:
        try:
            self.chat = updater.bot.get_chat(chat_id=self.id)
            self.getname()
        except Exception:
            ...
        return None

    def iskp(self, gpid: int) -> bool:
        return gpid in self.kpgroups

    def __str__(self) -> str:
        rttext = "id："+str(self.id)
        rttext += f"昵称：{self.getname()}\n"
        if self.controlling is not None:
            rttext += "当前正在操作的卡片id："+str(self.controlling.id)+"\n"
        rttext += "所有卡片id："+' '.join(map(str, self.cards.keys()))+"\n"
        rttext += "所有游戏中卡片的id："+' '.join(map(str, self.gamecards.keys()))+"\n"
        rttext += "作为kp的群id："+' '.join(map(str, self.kpgroups.keys()))+"\n"
        rttext += "正在进行游戏的群id："+' '.join(map(str, self.kpgames.keys()))+"\n"
        return rttext

    def write(self):
        if not type(self.id) is int:
            raise ValueError("写入文件时，Player实例没有id")
        with open(PATH_PLAYERS+str(self.id)+".json", 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, indent=4, ensure_ascii=False)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Player):
            return False
        return self.id == o.id


class GroupGame(datatype):  # If defined, game is started.
    """表示一个正在进行（或暂停）的游戏。属性：
    group, groupid, kp, cards, kpctrl, tpcheck"""

    def __init__(self, groupid: Optional[int] = None, cards: Dict[int, GameCard] = {}, d: dict = {}):
        if len(d) == 0 and groupid is None:
            raise TypeError("GroupGame的初始化需要groupid或d两个参数中的至少一个")
        # 没有cards也可以进行GroupGame初始化

        self.group: Group = None  # 需要在载入时赋值
        self.groupid: int = None
        self.kp: Optional[Player] = None  # 不需要存储，读取时通过construct()赋值
        self.cards: Dict[int, GameCard] = {}  # 不需要存储，读取时通过construct()赋值
        self.kpctrl: GameCard = None  # 存储时：int，读取时通过construct()赋值
        self.tpcheck: int = 0
        self.memfile: str = ""
        if len(d) > 0:
            self.read_json(d)
            assert(self.groupid is not None)
            return

        self.groupid = groupid
        self.cards: Dict[int, GameCard] = {}

        for i in cards.values():
            ngcard = GameCard(i.to_json())
            ngcard.isgamecard = True
            self.cards[i.id] = ngcard

    def read_json(self, d: dict, jumpkeys: List[str] = ["cards", "kp"]) -> None:
        super().read_json(d, jumpkeys=jumpkeys)

    def to_json(self, jumpkey: List[str] = ["group", "cards", "kp", "kpctrl"]) -> dict:
        d = super().to_json(jumpkey=jumpkey)
        if self.kpctrl is not None:
            d["kpctrl"] = self.kpctrl.id
        return d

    def show(self, attr: str, jumpkey: List[str] = []) -> str:
        if hasattr(self, attr):
            try:
                return str(self.__dict__[attr])
            except Exception:
                raise ValueError("无法转换为str")

        return "找不到该属性"

    def modify(self, attr: str, val, jumpkey: List[str] = []) -> Tuple[str, bool]:
        return "无法修改GroupGame实例", False

    def __str__(self):
        rttext = ""
        for keys in self.__dict__:
            if keys in ["cards", "group", "kp", "kpctrl"]:
                continue
            rttext += keys+": "+str(self.__dict__[keys])+"\n"
        rttext += "游戏中卡共有"+str(len(self.cards)) + \
            "张"
        return rttext

    def write(self):
        if self.group is not None:
            self.group.write()
        for card in self.cards.values():
            card.write()

    def __eq__(self, o: object) -> bool:
        assert(self.group is not None)
        if not isinstance(o, GroupGame):
            return False
        return self.group == o.group


class GroupRule(datatype):
    """一场游戏的规则。

    KP在群里用`/setrule`设置规则。群中如果没有规则，会自动生成默认规则。
    具有如下属性：group, skillmax, skillmaxAged, skillcost, greatsuccess, greatfail"""

    def __init__(self, rules: Dict[str, List[int]] = {}):
        self.group: Group = None  # 用cardConstruct()初始化
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
        if len(rules) > 0:
            self.read_json(rules)

    def to_json(self, jumpkey: List[str] = ["group"]) -> dict:
        return super().to_json(jumpkey=jumpkey)

    def modify(self, attr: str, val, jumpkey: List[str] = []) -> Tuple[str, bool]:
        return "不允许通过modify()修改rule，请使用self.changeRules()", False

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
        self.write()
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

    def write(self):
        if self.group is not None:
            self.group.write()


class Group(datatype):
    """表示一个群。具有如下属性：id, cards, game, pausedgame, rule, name, username, kp, chat"""

    def __init__(self, gpid: Optional[int] = None, d: dict = {}):
        if len(d) == 0 and gpid is None:
            raise TypeError("Group的初始化需要gpid或d两个参数中的至少一个")
        self.id: int = gpid
        self.cards: Dict[int, GameCard] = {}  # 在construct()中赋值。读取时忽略
        self.game: Optional[GroupGame] = None
        self.pausedgame: Optional[GroupGame] = None
        self.rule: GroupRule = GroupRule()
        self.name: str = ""
        self.username: str = ""
        # kp 需要在载入时赋值。读取、存储时为int。经过函数construct()正确载入后类型为 Player | None
        self.kp: Optional[Player] = None
        self.chat: Chat = None  # 需要在载入时赋值。不存储
        if len(d) > 0:
            self.read_json(d)
        self.groupconstruct()

    def read_json(self, d: dict, jumpkeys: List[str] = ["game", "rule", "pausedgame", "cards", "name"]) -> None:
        super().read_json(d, jumpkeys=jumpkeys)
        assert(self.id is not None)

        if "game" in d:
            self.game = GroupGame(d=d["game"])
        elif "rule" in d:
            self.rule.changeRules(d["rule"])
        elif "pausedgame" in d:
            self.pausedgame = GroupGame(d=d["pausedgame"])

    def to_json(self, jumpkey: List[str] = ["chat", "kp"]) -> dict:
        d = super().to_json(jumpkey=jumpkey)
        if self.kp is not None:
            d['kp'] = self.kp.id
        return d

    def show(self, attr: str, jumpkey: List[str] = []) -> str:
        if hasattr(self, attr):
            try:
                return str(self.__dict__[attr])
            except Exception:
                raise ValueError("无法转换为str")

        return "找不到该属性"

    def modify(self, attr: str, val, jumpkey: List[str]) -> Tuple[str, bool]:
        return "无法修改Group实例", False

    def groupconstruct(self):
        if self.game is not None:
            self.game.group = self

        elif self.pausedgame is not None:
            self.pausedgame.group = self

        self.rule.group = self

    def getexistgame(self) -> Optional[GroupGame]:
        return self.game if self.game is not None else self.pausedgame

    def iskp(self, plid: int) -> bool:
        if self.kp and self.kp.id == plid:
            return True
        return False

    def renew(self, updater: Updater) -> None:
        try:
            self.chat = updater.bot.get_chat(chat_id=self.id)
            self.getname()
        except Exception:
            ...
        return None

    def getname(self) -> str:
        if self.id is None:
            raise TypeError("Group实例没有id")

        if self.chat is None:
            return self.name

        self.username = self.chat.username if self.chat.username is not None else ""
        self.name = self.chat.title if self.chat.title is not None else ""

        self.write()

        return self.name

    def getusername(self) -> str:
        self.getname()
        return self.username

    def getcard(self, cardid: int) -> Optional[GameCard]:
        if cardid in self.cards:
            return self.cards[cardid]
        return None

    def write(self):
        if not type(self.id) is int:
            print(type(self.id))
            raise ValueError("写入文件时，Group实例没有id")
        with open(PATH_GROUPS+str(self.id)+".json", 'w', encoding='utf-8') as f:
            json.dump(self.to_json(), f, indent=4, ensure_ascii=False)

    def delete(self):
        if not type(self.id) is int:
            raise ValueError("删除文件时，Group实例没有id")
        try:
            os.remove(PATH_GROUPS+str(self.id)+".json")
        except Exception:
            ...

    def __str__(self) -> str:
        rttext = "群id："+str(self.id)+"\n"
        rttext += "相关卡片id："+', '.join(map(str, self.cards.keys()))+"\n"
        rttext += "群自定义规则："+str(self.rule)+"\n"

        if self.game is not None:
            rttext += "本群正在进行游戏。\n"
        elif self.pausedgame is not None:
            rttext += "本群存在一个暂停的游戏。\n"

        game = self.game if self.game is not None else self.pausedgame
        if game is None:
            return rttext
        rttext += str(game)

        return rttext

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Group):
            return False
        return self.id == o.id


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
        self.datanames: List[str] = ["STR", "SIZ", "CON",
                                     "DEX", "POW", "APP", "INT", "EDU"]
        self.alldatanames: List[str] = copy.copy(
            self.datanames)
        self.alldatanames.append("LUCK")
        self.datadec: Optional[Tuple[str, int]] = None
        self.card: GameCard = None  # 用cardConstruct()赋值
        if len(d) == 0:
            self.randdata()
        else:
            self.read_json(d)

    def read_json(self, d: dict, jumpkeys: List[str] = ["datadec"]) -> None:
        super().read_json(d, jumpkeys=jumpkeys)
        if "datadec" in d:
            self.datadec = (d["datadec"][0], d["datadec"][1])

    def to_json(self, jumpkey: List[str] = ["card", "datanames", "alldatanames", "datadec"]) -> dict:
        d = super().to_json(jumpkey=jumpkey)
        if self.datadec is not None:
            d["datadec"] = [self.datadec[0], self.datadec[1]]
        return d

    def show(self, attr: str, jumpkey: List[str] = ["card"]) -> str:
        return super().show(attr, jumpkey=jumpkey)

    def modify(self, attr: str, val, jumpkey: List[str] = ["card", "TOTAL", "datainfo", "datanames", "alldatanames", "datadec"]) -> Tuple[str, bool]:
        ans = super().modify(attr, val, jumpkey=jumpkey)
        self.total()
        return ans

    def getdata(self, dataname: str) -> int:
        if dataname not in self.alldatanames:
            raise KeyError("CardData没有属性："+dataname)
        return self.__dict__[dataname]

    def total(self) -> int:
        self.TOTAL = 0
        for key in self.alldatanames:
            self.TOTAL += self.__dict__[key]
        if self.datadec is not None:
            self.TOTAL += self.datadec[1]
        self.write()
        return self.TOTAL

    def randdata(self, write: bool = True) -> None:
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
        if write:
            self.write()

    def countless50discard(self) -> bool:
        countless50 = 0
        for key in self.datanames:
            if self.__dict__[key] < 50:
                countless50 += 1
        return countless50 >= 3

    def __str__(self) -> str:
        rttext = "\n".join([x+"："+str(self.__dict__[x])
                            for x in self.alldatanames])
        if self.datadec is not None:
            rttext += "\n"+self.datadec[0]+"下降值" + str(self.datadec[1])
        rttext += "\n总和："+str(self.total())+"\n"
        return rttext

    def check(self) -> str:
        rttext: str = ""

        if any(self.__dict__[x] == 0 for x in self.datanames):
            rttext += "基础7项属性为默认值"
        elif self.LUCK == 0:
            rttext += "幸运未设置，请先设置年龄"
        if self.datadec is not None:
            rttext += "属性下降未设置完成"
        return rttext

    def write(self):
        if self.card is not None:
            self.card.write()


class CardStatus(datatype):
    def __init__(self, d: dict = {}):
        self.GLOBAL: int = 0
        if len(d) > 0:
            self.read_json(d)

    def __str__(self) -> str:
        rttext: str = ""
        for key in iter(self.__dict__):

            if self.__dict__[key] != 0:
                if key == "GLOBAL":
                    if self.GLOBAL == 0:
                        continue
                    rttext += "全局修正："+str(self.GLOBAL)
                else:
                    rttext += key+"修正："+str(self.__dict__[key])

        return rttext if rttext != "" else "没有检定修正"

    def modify(self, attr: str, val, jumpkey: List[str] = []) -> Tuple[str, bool]:
        return "CardStatus实例不可以使用modify()修改一般成员", False

    def hasstatus(self, attr: str) -> bool:
        return hasattr(self, attr) and type(self.__dict__[attr]) is int

    def getstatus(self, attr: str) -> int:
        return self.__dict__[attr]

    def setstatus(self, attr: str, val: int) -> bool:
        if hasattr(self, attr) and not type(self.__dict__[attr]) is int:
            raise TypeError(f"CardStatus属性：{attr}不是可修改的int类型")
        self.__dict__[attr] = val
        return True


class CardInfo(datatype):
    def __init__(self, d={}):
        self.name: str = ""
        self.age: int = -1
        self.sex: str = ""
        self.job: str = ""
        if len(d) > 0:
            self.read_json(d=d)

    def __str__(self) -> str:
        rttext: str = ""
        rttext += "姓名："+self.name+"\n"
        rttext += "年龄："+str(self.age)+"\n"
        rttext += "性别："+self.sex+"\n"
        rttext += "职业："+self.job+"\n"
        return rttext

    def check(self) -> str:
        rttext: str = ""

        if self.job == "":
            rttext += "未设置职业\n"
        if self.name == "":
            rttext += "未设置姓名\n"
        if self.age == -1:
            rttext += "未设置年龄\n"
        if self.sex == "":
            rttext += "未设置性别\n"

        return rttext


class skilltype(datatype):  # skill的基类，只包含一个属性skills
    def __init__(self):
        self.skills: Dict[str, int] = {}

    def get(self, skillname: str) -> int:
        if skillname in self.skills:
            return self.skills[skillname]
        raise KeyError("get("+skillname+"):没有这个技能")

    def set(self, skillname: str, val: int) -> None:
        self.skills[skillname] = val

    def modify(self, attr: str, val: str, jumpkey: List[str] = ["card"]) -> Tuple[str, bool]:
        if attr in skl:
            if not isint(val):
                raise TypeError("技能值不是int")
            ans = (str(self.skills[attr]),
                   True) if attr in self.skills else ("无", True)
            self.skills[attr] = int(val)
            return ans

        return "没有该技能", False

    def allskills(self) -> Iterator[str]:
        return iter(self.skills)


class Skill(skilltype):
    def __init__(self, d: dict = {}):
        super().__init__()
        self.card: GameCard = None  # cardconstruct()赋值
        self.points: int = -1
        self.type: str = "主要"
        if len(d) > 0:
            self.read_json(d=d)

    def to_json(self, jumpkey: List[str] = {"card"}) -> dict:
        return super().to_json(jumpkey=jumpkey)

    def set(self, skillname: str, val: int, costpt: int = 0) -> None:
        super().set(skillname, val)
        self.points -= costpt
        self.write()

    def show(self, attr: str, jumpkey: List[str] = ["card"]) -> str:
        if attr == "points":
            return str(self.points)
        if attr in self.skills:
            return str(self.skills[attr])
        return "找不到该属性"

    def modify(self, attr: str, val: str, jumpkey: List[str] = ["card"]) -> Tuple[str, bool]:
        if attr == "points":
            ans = (str(self.points), True)
            if not isint(val):
                raise TypeError("点数值不是int")
            self.points = int(val)
            return ans

        return super().modify(attr, val, jumpkey=jumpkey)

    def write(self):
        if self.card is not None:
            self.card.write()

    def check(self) -> str:
        if self.points < 0:
            return "技能未开始设置"

        pops = []
        for sk in self.allskills():
            if sk not in skl:
                continue
            if self.get(sk) == skl[sk]:
                pops.append(sk)

        for sk in pops:
            self.skills.pop(sk)

        if len(pops):
            self.write()

        if self.points > 0:
            return "技能点有剩余"
        return ""

    def __str__(self) -> str:
        if self.points == -1:
            return self.type+"技能未开始设置"

        rttext: str = f"{self.type}技能剩余点数：{self.points}\n"
        for key in self.allskills():
            rttext += f"{key}：{self.get(key)}"

        return rttext


class SgSkill(skilltype):
    def __init__(self, d: dict = {}):
        super().__init__()
        if len(d) > 0:
            self.read_json(d=d)

    def show(self, attr: str, jumpkey: List[str] = []) -> str:
        return str(self.skills[attr]) if attr in self.skills else "找不到该属性"

    def pop(self, skillname: str) -> int:
        if skillname not in self.skills:
            raise KeyError("pop("+skillname+"):没有这个技能")
        return self.skills.pop(skillname)

    def __str__(self) -> str:
        rttext: str = "\n"
        for key in self.allskills():
            rttext += f"{key}：{self.get(key)}"

        return rttext


class CardAttr(datatype):
    def __init__(self, d: dict = {}):
        self.sandown: str = "0/0"
        self.DB: str = ""
        self.MOV: int = 0
        self.atktimes: int = 1
        self.build: int = -10
        self.SAN: int = 0
        self.MAXSAN: int = 99
        self.HP: int = 0
        self.MAXHP: int = 0
        self.MAGIC: int = 0
        self.armor: str = ""
        if len(d) > 0:
            self.read_json(d=d)

    def __str__(self) -> str:
        rttext: str = ""
        rttext += "伤害加深："+self.DB
        rttext += "\n移动速度："+str(self.MOV)
        rttext += "\n攻击次数："+str(self.atktimes)
        rttext += "\n体格："+str(self.build)
        rttext += "\nSAN："+str(self.SAN)
        rttext += "\nSAN上限："+str(self.MAXSAN)
        rttext += "\n生命值："+str(self.HP)
        rttext += "\n生命值上限："+str(self.MAXHP)
        rttext += "\n魔法值："+str(self.MAGIC)
        rttext += "\n护甲值："+self.armor
        if self.sandown != "0/0":
            rttext += "\n目击时，san值下降"+self.sandown
        return rttext+"\n"

    def check(self) -> str:
        return "衍生属性未计算" if self.DB == "" or self.MOV == 0 or self.build < -2 or self.MAXHP == 0 else ""


class CardBackground(datatype):
    def __init__(self, d: dict = {}):
        self.card: GameCard = None
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
        if len(d) > 0:
            self.read_json(d=d)

    def to_json(self, jumpkey: List[str] = ["card"]) -> dict:
        return super().to_json(jumpkey=jumpkey)

    def show(self, attr: str, jumpkey: List[str] = ["card"]) -> str:
        return super().show(attr, jumpkey=jumpkey)

    def modify(self, attr: str, val, jumpkey: List[str] = ["card"]) -> Tuple[str, bool]:
        return super().modify(attr, val, jumpkey=jumpkey)

    def check(self) -> str:
        rttext = ""

        if self.description == "":
            rttext += "未设置背景故事\n"
        if self.vip == "":
            rttext += "未设置重要之人\n"
        if self.viplace == "":
            rttext += "未设置重要之地\n"
        if self.faith == "":
            rttext += "未设置信仰\n"
        if self.preciousthing == "":
            rttext += "未设置珍视之物\n"
        if self.speciality == "":
            rttext += "未设置性格特点\n"

        return rttext

    def randbackground(self) -> str:
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
        self.faith = rdfaithlist[dicemdn(1, len(rdfaithlist))[
            0]-1]
        self.vip = rdviplist[dicemdn(1, len(rdviplist))[
            0]-1]
        self.viplace = rdsigplacelist[dicemdn(
            1, len(rdsigplacelist))[0]-1]
        self.preciousthing = rdpreciouslist[dicemdn(
            1, len(rdpreciouslist))[0]-1]
        self.speciality = rdspecialitylist[dicemdn(
            1, len(rdspecialitylist))[0]-1]
        self.write()
        rttext = "信仰: "+self.faith
        rttext += "\n重要之人: "+self.vip
        rttext += "\n重要之地: "+self.viplace
        rttext += "\n珍视之物: "+self.preciousthing
        rttext += "\n性格特点: "+self.speciality
        return rttext

    def __str__(self) -> str:
        rttext: str = ""
        rttext += "背景故事："+self.description+"\n"
        rttext += "重要之人："+self.vip+"\n"
        rttext += "重要之地："+self.viplace+"\n"
        rttext += "信仰："+self.faith+"\n"
        rttext += "珍视之物："+self.preciousthing+"\n"
        rttext += "性格特点："+self.speciality+"\n"
        rttext += "曾受过的伤："+self.dmg+"\n"
        rttext += "恐惧之物："+self.terror+"\n"
        rttext += "神秘学背景："+self.myth + "\n"
        rttext += "第三类接触："+self.thirdencounter + "\n"
        return rttext

    def write(self):
        if self.card is not None:
            self.card.write()
