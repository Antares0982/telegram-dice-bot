# -*- coding:utf-8 -*-
import json
import os
import time
from typing import overload
from telegram.error import BadRequest

from telegram.ext import Updater
from telegram import Update
from telegram.message import Message

from cfg import *
from gameclass import *

from basicfunc import *

if PROXY:
    updater = Updater(token=TOKEN, request_kwargs={
        'proxy_url': PROXY_URL}, use_context=True)
else:
    updater = Updater(token=TOKEN, use_context=True)


class DiceBot:
    def __init__(self):
        self.IDENTIFIER = str(time.time())
        self.groups: Dict[int, Group] = {}  # readall()赋值
        self.players: Dict[int, Player] = {}  # readall()赋值
        self.cards: Dict[int, GameCard] = {}  # readall()赋值
        self.gamecards: Dict[int, GameCard] = {}  # readall()赋值
        self.joblist: dict
        self.skilllist: Dict[str, int]
        self.allids: List[int] = []
        self.updater: Updater = updater
        self.readall()  # 先执行
        self.construct()  # 后执行
        self.operation: Dict[int, str] = {}
        self.addjobrequest: Dict[int, Tuple[str, list]] = {}
        self.addskillrequest: Dict[int, Tuple[str, int]] = {}
        # self.readhandlers()

    def readall(self) -> None:
        # 初始化
        self.groups = {}
        self.players = {}
        self.cards = {}
        self.gamecards = {}
        # groups
        for filename in os.listdir(PATH_GROUPS):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(PATH_GROUPS+filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.groups[int(filename[:len(filename)-5])] = Group(d=d)
        # players
        for filename in os.listdir(PATH_PLAYERS):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(PATH_PLAYERS+filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.players[int(filename[:len(filename)-5])] = Player(d=d)
        # cards
        for filename in os.listdir(PATH_CARDS):
            if filename == "game" or filename.find(".json") != len(filename)-5:
                continue
            with open(PATH_CARDS+filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.cards[int(filename[:len(filename)-5])] = GameCard(carddict=d)
        # gamecards
        for filename in os.listdir(PATH_GAME_CARDS):
            if filename.find(".json") != len(filename)-5:
                continue
            with open(PATH_GAME_CARDS+filename, "r", encoding='utf-8') as f:
                d = json.load(f)
            self.gamecards[int(filename[:len(filename)-5])
                           ] = GameCard(carddict=d)
        # joblist
        with open(PATH_JOBDICT, 'r', encoding='utf-8') as f:
            self.joblist = json.load(f)
        # skilldict
        with open(PATH_SKILLDICT, 'r', encoding='utf-8') as f:
            self.skilllist = json.load(f)

    def construct(self) -> None:
        """创建变量之间的引用"""
        # card
        for card in self.cards.values():
            card.isgamecard = False

            pl = self.getplayer(card.playerid)
            card.player = pl if pl is not None else self.createplayer(
                card.playerid)  # 添加card.player
            card.player.cards[card.id] = card  # 添加player.cards

            gp = self.getgp(card.groupid)
            card.group = gp if gp is not None else self.creategp(
                card.groupid)  # 添加card.group
            card.group.cards[card.id] = card  # 添加group.cards

            self.allids.append(card.id)

        # gamecard
        for card in self.gamecards.values():
            card.isgamecard = True

            assert(self.getplayer(card.id) is not None)
            card.player = self.getplayer(card.id)  # 添加gamecard.player
            card.player.gamecards[card.id] = card  # 添加player.gamecards

            assert(self.getgp(card.groupid) is not None)
            card.group = self.getgp(card.groupid)  # 添加card.group

            assert(bool(card.group.game) != bool(card.group.pausedgame))
            game = card.group.game if card.group.game is not None else card.group.pausedgame
            game.cards[card.id] = card  # 添加game.cards

        # group
        for gp in self.groups.values():
            if isinstance(gp.kp, int):
                kp = self.getplayer(gp.kp)
                gp.kp = kp if kp is not None else self.createplayer(gp.kp)
                gp.kp.kpgroups[gp.id] = gp

            if gp.chat is None:
                try:
                    gp.chat = self.updater.bot.get_chat(chat_id=gp.id)
                    gp.name = gp.chat.title
                except BadRequest:
                    self.sendtoAdmin("群："+str(gp.id)+" " +
                                     gp.name+"telegram chat无法获取")

            game = gp.game if gp.game is not None else gp.pausedgame
            if game is not None:
                if gp.kp is not None:
                    game.kp = gp.kp
                    game.kp.kpgames[gp.id] = game

                if isinstance(game.kpctrl, int):
                    game.kpctrl = game.cards[game.kpctrl]

        # player
        for pl in self.players.values():
            if pl.chat is None:
                try:
                    pl.chat = self.updater.bot.get_chat(chat_id=pl.id)
                    pl.getname()
                except BadRequest:
                    self.sendtoAdmin("用户："+str(pl.id)+" " +
                                     pl.name+"telegram chat无法获取")

            if isinstance(pl.controlling, int):
                assert(self.cards[pl.controlling].player == pl)
                pl.controlling = self.cards[pl.controlling]

        # ids
        self.allids.sort()

    def readhandlers(self) -> List[str]:
        """读取全部handlers。
        使用时，先写再读，正常情况下不会有找不到文件的可能"""
        with open(PATH_HANDLERS, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d

    def sendtoAdmin(self, msg: str) -> None:
        self.updater.bot.send_message(chat_id=ADMIN_ID, text=msg)

    @overload
    def checkconsistency():
        # TODO 检查群名称是否有变化
        # TODO 检查allids是否正确
        # TODO 检查kp对是否完整
        # kp对如果出现不一致，用assert抛出AssertionError
        pass

    @overload
    def checkconsistency(update: Update):
        # TODO 检查是否是新群、新玩家
        # 每隔几分钟，做一次该操作
        pass

    def writegroup(self) -> None:
        for gp in self.groups.values():
            gp.write()

    def writeplayer(self) -> None:
        for pl in self.players.values():
            pl.write()

    def writecard(self) -> None:
        for card in self.cards.values():
            assert(not card.isgamecard)
            card.write()
        for card in self.gamecards.values():
            assert(card.isgamecard)
            card.write()

    @overload
    def getgp(self, gpid: int) -> Optional[Group]:
        return None if gpid not in self.groups else self.groups[gpid]

    @overload
    def getgp(self, update: Update) -> Optional[Group]:
        assert(isgroupmsg(update))
        return self.getgp(getchatid(update))

    @overload
    def creategp(self, gpid: int) -> Group:
        assert(gpid not in self.groups)

        gp = Group(gpid=gpid)
        self.groups[gpid] = gp

        try:
            gp.chat = self.updater.bot.get_chat(chat_id=gp.id)
            gp.getname()
        except:
            self.sendtoAdmin("无法获取群"+str(gp.id)+" chat信息")

        gp.write()

    @overload
    def creategp(self, update: Update) -> Group:
        assert(isgroupmsg(update))
        return self.creategp(getchatid(update))

    @overload
    def forcegetgroup(self, gpid: int) -> Group:
        return self.getgp(gpid) if gpid in self.groups else self.creategp(gpid)

    @overload
    def forcegetgroup(self, update: Update) -> Group:
        assert(isgroupmsg(update))
        return self.forcegetgroup(getchatid(update))

    @overload
    def getplayer(self, plid: int) -> Optional[Player]:
        return None if plid not in self.players else self.players[plid]

    @overload
    def getplayer(self, update: Update) -> Optional[Player]:
        return self.getplayer(getmsgfromid(update))

    @overload
    def createplayer(self, plid: int) -> Player:
        assert(plid not in self.players)

        pl = Player(plid=plid)
        self.players[plid] = pl

        try:
            pl.chat = self.updater.bot.get_chat(chat_id=plid)
            pl.getname()
        except:
            self.sendtoAdmin("无法获取玩家"+str(pl.id)+" chat信息")

        pl.write()

    @overload
    def createplayer(self, update: Update) -> Player:
        return self.createplayer(getmsgfromid(update))

    @overload
    def forcegetplayer(self, plid: int) -> Player:
        return self.getplayer(plid) if plid in self.players else self.createplayer(plid)

    @overload
    def forcegetplayer(self, update: Update) -> Player:
        return self.forcegetplayer(getmsgfromid(update))

    def getcard(self, cdid: int) -> Optional[GameCard]:
        return self.cards[cdid] if cdid in self.cards else None

    def getgamecard(self, cdid: int) -> Optional[GameCard]:
        return self.gamecards[cdid] if cdid in self.gamecards else None

    def addcard(self, card: GameCard) -> bool:
        """添加一张游戏外的卡，当卡id重复时返回False"""
        assert(not card.isgamecard)

        if card.id in self.allids:
            raise ValueError("添加卡时，id重复")

        # 维护dicebot
        self.cards[card.id] = card
        # 增加id
        self.allids.append(card.id)
        self.allids.sort()
        # 增加群索引
        gp = self.forcegetgroup(card.groupid)
        card.group = gp
        gp.cards[card.id] = card
        gp.write()
        # 增加pl索引
        pl = self.forcegetplayer(card.playerid)
        pl.cards[card.id] = card
        card.player = pl

        if pl.controlling:
            self.autoswitchhint(pl.id)
        pl.controlling = card

        pl.write()
        card.write()
        return True

    def popcard(self, cdid: int) -> GameCard:
        """删除一张游戏外的卡片"""
        if self.getcard(cdid) is None:
            raise KeyError("找不到id为"+str(cdid)+"的卡")

        card = self.cards.pop(cdid)

        # 维护groups
        card.group.cards.pop(cdid)
        card.group.write()

        # 维护players
        card.player.cards.pop(cdid)
        if card.player.controlling == card:
            card.player.controlling = None
        card.player.write()

        # 维护allids
        self.allids.pop(self.allids.index(cdid))
        card.delete()
        return card

    def addgamecard(self, card: GameCard) -> bool:
        # 排查
        assert(card.isgamecard)

        if card.id in self.gamecards:
            raise ValueError("添加游戏卡时，id重复")

        gp = self.forcegetgroup(card.groupid)
        if gp.game is None and gp.pausedgame is None:
            raise ValueError("没有对应的游戏")

        assert(gp.game is None or gp.pausedgame is None)

        # 维护dicebot
        self.gamecards[card.id] = card
        # 不考虑allids的问题
        # 维护群、游戏
        game = gp.game if gp.game is not None else gp.pausedgame
        game.cards[card.id] = card
        card.group = gp
        gp.write()
        # 维护Player
        pl = self.forcegetplayer(card.playerid)
        card.player = pl
        pl.gamecards[card.id] = card

        pl.write()
        card.write()

    def popgamecard(self, cdid: int) -> GameCard:
        if self.getgamecard(cdid) is None:
            raise KeyError("找不到id为"+str(cdid)+"的游戏中的卡")

        card = self.gamecards.pop(cdid)

        # 维护groups及games
        assert(card.group.game is not None or card.group.pausedgame is not None)
        assert(card.group.game is None or card.group.pausedgame is None)
        game = card.group.game if card.group.game is not None else card.group.pausedgame
        game.cards.pop(cdid)
        card.group.write()

        # 维护players
        card.player.gamecards.pop(cdid)
        card.delete()
        card.player.write()
        return card

    def cardtransferto(self, card: GameCard, newpl: Player) -> bool:
        """转移一张卡所属权，游戏进行中则无法转移"""
        if card.player == newpl or card.id in card.player.gamecards or card.isgamecard:
            return False

        card.player.cards.pop(card.id)

        if card.player.controlling == card:
            card.player.controlling = None
            self.sendto(card.player, "卡片所有权被转换")

        card.player.write()

        card.player = newpl
        card.playerid = newpl.id
        newpl.cards[card.id] = card

        return True

    def addkp(self, gp: Group, pl: Player) -> None:
        """如果要更新kp，需要先执行delkp"""
        gp.kp = pl
        pl.kpgroups[gp.id] = gp
        game = gp.game if gp.game is not None else gp.pausedgame
        if game is not None:
            game.kp = pl
            pl.kpgames[gp.id] = game

        gp.write()
        pl.write()

    def delkp(self, gp: Group) -> Optional[Player]:
        """仅删除kp。"""
        if gp.kp is None:
            return None
        kp = gp.kp
        kp.kpgroups.pop(gp.id)
        gp.kp = None
        game = gp.game if gp.game is not None else gp.pausedgame
        if game is not None:
            game.kp = None
            kp.kpgames.pop(gp.id)

        gp.write()
        kp.write()

    def groupmigrate(self, oldid: int, newid: int) -> None:
        gp = self.getgp(oldid)
        assert(gp is not None)
        for card in gp.cards.values():
            card.groupid = newid
            card.write()
        if gp.game is not None:
            gp.game.groupid = newid
            for card in gp.game.cards.values():
                card.groupid = newid
                card.write()
        gp.id = newid
        gp.renew(self.updater)
        gp.write()

    @overload
    def sendto(self, pl: Player, msg: str) -> Message:
        try:
            return self.updater.bot.send_message(chat_id=pl.id, text=msg)
        except:
            return self.sendtoAdmin(f"无法向用户{pl.getname()}发送消息："+msg)

    @overload
    def sendto(self, plid: int, msg: str) -> Message:
        try:
            return self.updater.bot.send_message(chat_id=plid, text=msg)
        except:
            return self.sendtoAdmin(f"无法向用户{self.forcegetplayer(plid).getname()}发送消息："+msg)

    def autoswitchhint(self, plid: int) -> None:
        self.sendto(plid, "创建新卡时，控制自动切换到新卡")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, DiceBot):
            return False
        return self.IDENTIFIER == o.IDENTIFIER
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


dicebot = DiceBot()

# try:
#     dicebot = DiceBot()
# except:
#     updater.bot.send_message(chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
#     print("出现问题")
#     exit()
