# -*- coding:utf-8 -*-
import copy
import json
import os
import time
from typing import overload

from telegram.ext import Updater

from cfg import ADMIN_ID, DATA_PATH, PROXY, PROXY_URL, TOKEN
from gameclass import *

if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
        'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)


class DiceBot:
    def __init__(self):
        self.IDENTIFIER = str(time.time())
        self.groups: Dict[int, Group] = {}
        self.players: Dict[int, Player] = {}
        self.joblist: dict
        self.skilllist: dict
        self.allids: List[int] = []
        self.updater: Updater = updater
        self.readall()  # 先执行
        self.readcurrent()  # 后执行
        self.construct()
        self.operation: Dict[int, str] = {}
        # self.readhandlers()
        # 代理设置

    def readall(self) -> None:
        for filename in os.listdir(DATA_PATH):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.groups[int(filename[:len(filename)-5])] = Group(d=d)

    def readhandlers(self) -> List[str]:
        """读取全部handlers。

        使用时，先写再读，正常情况下不会有找不到文件的可能"""
        with open(PATH_HANDLERS, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d

    def construct(self) -> None:
        """创建变量引用"""
        pass

    @overload
    def writeplayer(self, plid: int):
        pass

    @overload
    def writeplayer(self, pl: Player):
        pass

    @overload
    def writegroup(self, gpid: int):
        pass

    @overload
    def writegroup(self, gp: Group):
        return self.writegroup(gp.id)

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


def writeholdgameinfo(listofobj: List[GroupGame]) -> None:
    """用于HOLD_GAME写入"""
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
    """读取四个文件的数据：GROUP_KP_DICT, CARDS_DICT, ON_GAME, HOLD_GAME"""
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


def writecurrentcarddict(d: Dict[int, Tuple[int, int]]) -> None:
    """CURRENT_CARD_DICT写入"""
    with open(PATH_CURRENTCARDDICT, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=4, ensure_ascii=False)


def readrules() -> Dict[int, GroupRule]:
    """读取GROUP_RULES"""
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


def writerules(d: Dict[int, GroupRule]) -> None:
    """GROUP_RULES写入"""
    d1: Dict[int, dict] = {}
    for key in d:
        d1[key] = d[key].__dict__
    with open(PATH_RULES, "w", encoding="utf-8") as f:
        json.dump(d1, f, indent=4, ensure_ascii=False)


def writehandlers(h: List[str]) -> None:
    """写入Handlers"""
    with open(PATH_HANDLERS, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=4, ensure_ascii=False)


try:
    dicebot = DiceBot()
except:
    updater.bot.send_message(chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
    exit()
