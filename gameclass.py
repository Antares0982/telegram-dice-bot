from typing import List


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
        self.__dict__ = cardinfo


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
