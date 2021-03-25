# -*- coding:utf-8 -*-
import json
import os
import time
from typing import overload

from telegram.ext import Updater
from telegram import Update

from cfg import *
from gameclass import *


if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
        'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)
updater.idle()

updater.bot


class DiceBot:
    def __init__(self):
        self.IDENTIFIER = str(time.time())
        self.groups: Dict[int, Group] = {}  # readall()赋值
        self.players: Dict[int, Player] = {}  # readall()赋值
        self.cards: Dict[int, GameCard] = {}  # 需要construct()来赋值
        self.gamecards: Dict[int, GameCard] = {}
        self.joblist: dict
        self.skilllist: dict
        self.allids: List[int] = []
        self.updater: Updater = updater
        self.readall()  # 先执行
        self.construct()  # 后执行
        self.operation: Dict[int, str] = {}
        self.readhandlers()

    def readall(self) -> None:
        # groups
        for filename in os.listdir(PATH_GROUPS):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.groups[int(filename[:len(filename)-5])] = Group(d=d)
        for filename in os.listdir(PATH_PLAYERS):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.players[int(filename[:len(filename)-5])] = Player(d=d)

    def construct(self) -> None:
        """创建变量之间的引用"""
        for gp in self.groups.values():
            for card in gp.cards.values():
                self.cards[card.id] = card  # 添加self.cards
                card.player = self.players[card.playerid]  # 添加card.player
                card.player.cards[card.id] = card  # 添加player.cards
                card.group = gp  # 添加card.group
                self.allids.append(card.id)  # 添加self.allids
            if gp.kp is int:
                gp.kp = self.players[gp.kp]
            if gp.chat is int:
                gp.chat = self.updater.bot.get_chat(chat_id=gp.chat)
            if gp.game is not None:
                for card in gp.game.cards.values():
                    self.gamecards[card.id] = card  # 添加self.gamecards
                    # 添加gamecard.player
                    card.player = self.players[card.playerid]
                    card.player.gamecards[card.id] = card  # 添加player.gamecards
                    card.group = gp  # 添加card.group
            if gp.pausedgame is not None:
                for card in gp.pausedgame.cards.values():
                    self.gamecards[card.id] = card  # 添加self.gamecards
                    # 添加gamecard.player
                    card.player = self.players[card.playerid]
                    card.player.gamecards[card.id] = card  # 添加player.gamecards
                    card.group = gp  # 添加card.group
        self.allids.sort()
        for pl in self.players.values():
            if pl.controlling is int:
                pl.controlling = self.cards[pl.controlling]

    def readhandlers(self) -> List[str]:
        """读取全部handlers。
        使用时，先写再读，正常情况下不会有找不到文件的可能"""
        with open(PATH_HANDLERS, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d

    @overload
    def checkconsistency():
        # TODO 检查群名称是否有变化
        # TODO 检查allids是否正确
        # TODO 检查kp对是否完整
        # 如果出现不一致，用assert抛出AssertionError
        pass

    @overload
    def checkconsistency(update: Update):
        # TODO 检查群的升级
        # TODO 检查是否是新群、新玩家
        # 每隔几分钟，做一次该操作
        pass

    @overload
    def writegroup(self, gpid: int):
        try:
            gp = self.groups[gpid]
        except KeyError:
            gp = self.creategp(gpid)
        gp.write()
        # json.dump(gp.to_json(),
        #           f, indent=4, ensure_ascii=False)

    @overload
    def writegroup(self, gp: Group):
        return self.writegroup(gp.id)

    @overload
    def writeplayer(self, plid: int):
        try:
            pl = self.players[plid]
        except KeyError:
            pl = self.createplayer(plid)
        pl.write()

    @overload
    def writeplayer(self, pl: Player):
        return self.writeplayer(pl.id)

    def getgp(self, gpid: int) -> Optional[Group]:
        if gpid not in self.groups:
            return None
        return self.groups[gpid]

    def creategp(self, gpid: int) -> Group:
        self.groups[gpid] = Group(gpid=gpid)

    def getplayer(self, plid) -> Optional[Player]:
        if plid not in self.players:
            return None
        return self.players[plid]

    def createplayer(self, plid) -> Player:
        self.players[plid] = Player(plid=plid)

    """
    def writekpinfo(self) -> None:
        with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
            json.dump(self.kpinfo, f, indent=4, ensure_ascii=False)
    """
    """
    def writecards(self) -> None:
        listofdict: Dict[str, Dict[str, dict]] = {}
        for gpid in listofgamecard:
            if len(listofgamecard[gpid]) == 0:
                listofgamecard.pop(gpid)
                continue
            listofdict[str(gpid)] = {}
            for cdids in listofgamecard[gpid]:
                listofdict[str(gpid)][str(cdids)
                                    ] = listofgamecard[gpid][cdids].__dict__
        with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
            json.dump(listofdict, f, indent=4, ensure_ascii=False)


    def writegameinfo(listofobj: List[GroupGame]) -> None:
        
        savelist: List[dict] = []
        for i in range(len(listofobj)):
            savelist.append(copy.deepcopy(listofobj[i].__dict__))
            tpcards: List[GameCard] = savelist[-1]["cards"]
            savelist[-1]["cards"] = []
            savelist[-1].pop("kpcards")
            for i in tpcards:
                savelist[-1]["cards"].append(i.__dict__)
        with open(PATH_ONGAME, "w", encoding="utf-8") as f:
            json.dump(savelist, f, indent=4, ensure_ascii=False)
    """


"""
def writeholdgameinfo(listofobj: List[GroupGame]) -> None:
    savelist: List[dict] = []
    for i in range(len(listofobj)):
        savelist.append(copy.deepcopy(listofobj[i].__dict__))
        tpcards: List[GameCard] = savelist[-1]["cards"]
        savelist[-1]["cards"] = []
        savelist[-1].pop("kpcards")
        for i in tpcards:
            savelist[-1]["cards"].append(i.__dict__)
    with open(PATH_HOLDGAME, "w", encoding="utf-8") as f:
        json.dump(savelist, f, indent=4, ensure_ascii=False)


def readinfo() -> Tuple[Dict[int, int], Dict[int, Dict[int, GameCard]], List[GroupGame], List[GroupGame]]:
    # 如果文件不存在，则创建新文件
    # group-kp
    try:
        f = open(PATH_GROUP_KP, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_GROUP_KP, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        gpkpdict: Dict[int, int] = {}
    else:
        with open(PATH_GROUP_KP, "r", encoding="utf-8") as f:
            gpkpstrdict: Dict[str, int] = json.load(f)
        gpkpdict: Dict[int, int] = {}
        for keys in gpkpstrdict:
            gpkpdict[int(keys)] = gpkpstrdict[keys]
    print("kp info: passed")
    # cards
    try:
        f = open(PATH_CARDSLIST, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_CARDSLIST, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        cardslist = {}
    else:
        with open(PATH_CARDSLIST, "r", encoding="utf-8") as f:
            cardslist = json.load(f)
    gamecardlist: Dict[int, dict] = {}
    for groupkeys in cardslist:
        gamecardlist[int(groupkeys)] = {}
        for keys in cardslist[groupkeys]:
            gamecardlist[int(groupkeys)][int(keys)] = GameCard(
                cardslist[groupkeys][keys])
    print("card info: passed")
    # games
    try:
        f = open(PATH_ONGAME, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_ONGAME, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        ongamelistdict = []
    else:
        with open(PATH_ONGAME, "r", encoding="utf-8") as f:
            ongamelistdict = json.load(f)
    ongamelist: List[GroupGame] = []
    for i in range(len(ongamelistdict)):
        ongamelist.append(GroupGame(ongamelistdict[i]))
    print("game info: passed")
    # games are holding
    try:
        f = open(PATH_HOLDGAME, "r", encoding="utf-8")
        f.close()
    except FileNotFoundError:
        with open(PATH_HOLDGAME, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        print("File does not exist, create new file")
        holdgamelistdict = []
    else:
        with open(PATH_HOLDGAME, "r", encoding="utf-8") as f:
            holdgamelistdict = json.load(f)
    holdgamelist: List[GroupGame] = []
    for i in range(len(holdgamelistdict)):
        holdgamelist.append(GroupGame(holdgamelistdict[i]))
    return gpkpdict, gamecardlist, ongamelist, holdgamelist
"""


def readskilldict() -> dict:
    """读取SKILL_DICT"""
    with open(PATH_SKILLDICT, 'r', encoding="utf-8") as f:
        d = json.load(f)
    return d


def readjobdict() -> dict:
    """读取JOB_DICT"""
    with open(PATH_JOBDICT, 'r', encoding='utf-8') as f:
        d = json.load(f)
    return d


"""
def readrules() -> Dict[int, GroupRule]:
    d: Dict[str, dict]
    try:
        f = open(PATH_RULES, "r", encoding='utf-8')
        f.close()
    except FileNotFoundError:
        with open(PATH_RULES, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        d = {}
    else:
        with open(PATH_RULES, 'r', encoding='utf-8') as f:
            d = json.load(f)
    d1: Dict[int, GroupRule] = {}
    for key in d:
        d1[int(key)] = GroupRule(d[key])
    return d1
"""


def writehandlers(h: List[str]) -> None:
    """写入Handlers"""
    with open(PATH_HANDLERS, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=4, ensure_ascii=False)


try:
    dicebot = DiceBot()
except:
    updater.bot.send_message(chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
    exit()
