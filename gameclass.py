from typing import List
import copy


class GameCard:
    def __init__(self, cardinfo: dict):
        self.id: int = 0
        self.playerid: int = 0
        self.groupid: int = 0
        self.data: dict = {}
        self.info: dict = {}
        self.skill: dict = {}
        self.interest: dict = {}
        self.suggestskill: dict = {}
        self.cardcheck: dict = {}
        self.attr: dict = {}
        self.background: dict = {}
        self.tempstatus: dict = {}
        self.item: str = ""
        self.assets: str = ""
        self.type: str = ""
        self.discard: bool = False
        self.status: str = ""
        self.__dict__ = copy.deepcopy(cardinfo)

    def __str__(self):
        rttext: str = ""
        rttext += "id: "+str(self.id)+"\n"
        rttext += "playerid: "+str(self.playerid)+"\n"
        rttext += "groupid: "+str(self.groupid)+"\n"
        rttext += "基础数值: "+"\n"
        for keys in self.data:
            rttext += keys+": "+str(self.data[keys])+"\n"
        rttext += "信息: "+"\n"
        for keys in self.info:
            rttext += keys+": "+str(self.info[keys])+"\n"
        rttext += "技能: "+"\n"
        for keys in self.skill:
            rttext += keys+": "+str(self.skill[keys])+"\n"
        rttext += "兴趣技能: "+"\n"
        for keys in self.interest:
            rttext += keys+": "+str(self.interest[keys])+"\n"
        rttext += "建议技能: "+"\n"
        for keys in self.suggestskill:
            rttext += keys+": "+str(self.suggestskill[keys])+"\n"
        rttext += "角色卡检查: "+"\n"
        for keys in self.cardcheck:
            rttext += keys+": "+str(self.cardcheck[keys])+"\n"
        rttext += "其他属性: "+"\n"
        for keys in self.attr:
            rttext += keys+": "+str(self.attr[keys])+"\n"
        rttext += "背景故事: "+"\n"
        for keys in self.background:
            rttext += keys+": "+str(self.background[keys])+"\n"
        rttext += "临时检定加成: "+"\n"
        for keys in self.tempstatus:
            rttext += keys+": "+str(self.tempstatus[keys])+"\n"
        rttext += "物品: "+self.item+"\n"
        rttext += "资产: "+self.assets+"\n"
        rttext += "角色类型: "+self.type+"\n"
        rttext += "可删除: "
        if self.discard:
            rttext += "是\n"
        else:
            rttext += "否\n"
        rttext += "状态: "+self.status+"\n"
        return rttext


class GroupGame:  # If defined, game is started.
    def __init__(self, groupid, cards: List[dict] = None, kpid: int = None):
        if isinstance(groupid, dict):
            self.groupid: int = groupid["groupid"]
            self.kpid: int = groupid["kpid"]
            self.kpctrl: int = groupid["kpctrl"]
            self.tpcheck: int = groupid["tpcheck"]
            tpcardslist = groupid["cards"]
            self.cards = []
            for i in tpcardslist:
                self.cards.append(GameCard(i))
            del tpcardslist
        else:
            self.groupid: int = groupid  # Unique, should not be edited after initializing
            self.kpid: int = kpid  # Can be edited
            self.cards: List[GameCard] = []  # list of GameCard
            for i in cards:
                self.cards.append(GameCard(i))
            self.kpctrl: int = -1
            self.tpcheck: int = 0
        self.kpcards: List[GameCard] = []
        for i in self.cards:
            if i.playerid == self.kpid:
                self.kpcards.append(i)

    def __str__(self):
        rttext = ""
        for keys in self.__dict__:
            if keys == "cards" or keys == "kpcards":
                continue
            rttext += keys+": "+str(self.__dict__[keys])+"\n"
        rttext += "游戏中卡共有"+str(len(self.cards)) + \
            "张，其中kp所持卡共有"+str(len(self.kpcards))+"张"
        return rttext
