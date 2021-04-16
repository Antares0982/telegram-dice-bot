# -*- coding:utf-8 -*-
import json
import os
import time
from typing import List, Optional, Tuple, Union, overload

from telegram import Update
from telegram.error import BadRequest, ChatMigrated
from telegram.ext import Updater
from telegram.message import Message

from basicfunc import *
from cfg import *
from gameclass import *

# 初始化updater
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
        self.usernametopl: Dict[str, Player] = {}  # construct()赋值
        self.joblist: dict
        self.skilllist: Dict[str, int]
        self.allids: List[int] = []
        self.updater: Updater = updater
        self.readall()  # 先执行
        self.construct()  # 后执行
        self.operation: Dict[int, str] = {}
        self.addjobrequest: Dict[int, Tuple[str, list]] = {}
        self.addskillrequest: Dict[int, Tuple[str, int]] = {}
        self.migratefrom: Optional[int] = None
        self.migrateto: Optional[int] = None
        self.skillpages: List[List[str]]

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

        self.skillpages = self.createSkillPages()

    def construct(self) -> None:
        """创建变量之间的引用"""
        self.allids = []
        self.usernametopl = {}
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

            assert(self.getplayer(card.playerid) is not None)
            card.player = self.getplayer(card.playerid)  # 添加gamecard.player
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

            if gp.chat is None and gp.id != -1:
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
            if pl.chat is None and pl.id != 0:
                try:
                    pl.chat = self.updater.bot.get_chat(chat_id=pl.id)
                    pl.getname()
                    if pl.username != "":
                        self.usernametopl[pl.username] = pl
                except BadRequest:
                    self.sendtoAdmin("用户："+str(pl.id)+" " +
                                     pl.name+"telegram chat无法获取")

            if isinstance(pl.controlling, int):
                assert(self.cards[pl.controlling].player == pl)
                pl.controlling = self.cards[pl.controlling]

        # ids
        self.allids.sort()

    def createSkillPages(self) -> List[List[str]]:
        """创建技能的分页列表，用于添加兴趣技能"""
        # 一页16个
        skillPaged: List[List[str]] = [["母语", "闪避"]]
        for key in self.skilllist:
            if key == "克苏鲁神话":
                continue
            if len(skillPaged[len(skillPaged)-1]) == 16:
                skillPaged.append([])
            skillPaged[len(skillPaged)-1].append(key)
        return skillPaged

    def readhandlers(self) -> List[str]:
        """读取全部handlers。
        使用时，先写再读，正常情况下不会有找不到文件的可能"""
        with open(PATH_HANDLERS, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return d

    def sendtoAdmin(self, msg: str) -> None:
        self.updater.bot.send_message(chat_id=ADMIN_ID, text=msg)

    def checkconsistency(self):
        for card in self.cards.values():
            if card.player is None or card.player.id != card.playerid:
                card.player = self.forcegetplayer(card.playerid)
                self.sendtoAdmin("card.player出现问题")

            if card.id not in card.player.cards:
                card.player.cards[card.id] = card
                self.sendtoAdmin("player.cards出现问题")

            if card.group is None or card.group.id != card.groupid:
                card.group = self.forcegetgroup(card.groupid)
                self.sendtoAdmin("card.group出现问题")

        for card in self.gamecards.values():
            if card.player is None or card.player.id != card.playerid:
                card.player = self.forcegetplayer(card.playerid)
                self.sendtoAdmin("gamecard.player出现问题")

            if card.id not in card.player.gamecards:
                card.player.gamecards[card.id] = card
                self.sendtoAdmin("player.gamecards出现问题")

            if card.group.getexistgame() is None:
                self.sendtoAdmin("Game未开始却拥有gamecard")
            else:
                game = card.group.getexistgame()
                if card.group != game.group:
                    self.sendtoAdmin("card.gamegroup出现问题")

        self.allids.sort()
        t = list(self.cards.keys())
        t.sort()
        if self.allids != t:
            self.sendtoAdmin("id出现不一致")

        for gp in self.groups.values():
            if gp.kp is not None:
                if gp.id not in gp.kp.kpgroups:
                    self.sendtoAdmin("kp对出现不一致")
                    gp.kp[gp.id] = gp

            game = gp.getexistgame()
            if game is not None:
                if game.kp != gp.kp:
                    self.sendtoAdmin("game kp和group不一致")
                    game.kp = gp.kp
                if game.group.id not in game.kp.kpgames:
                    game.kp.kpgames[game.group.id] = game
                    self.sendtoAdmin("kp.kpgames出现不一致")

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
        ...

    @overload
    def getgp(self, update: Update) -> Optional[Group]:
        ...

    def getgp(self, update: Union[int, Update]):
        if isinstance(update, Update):
            assert(isgroupmsg(update))
            return None if getchatid(update) not in self.groups else self.groups[getchatid(update)]
        if isinstance(update, int):
            gpid = update
            return None if gpid not in self.groups else self.groups[gpid]

    @overload
    def creategp(self, gpid: int) -> Group:
        ...

    @overload
    def creategp(self, update: Update) -> Group:
        ...

    def creategp(self, update: Union[int, Update]) -> Group:
        if isinstance(update, Update):
            assert(isgroupmsg(update))
            return self.creategp(getchatid(update))
        gpid: int = update
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
    def forcegetgroup(self, gpid: int) -> Group:
        ...

    @overload
    def forcegetgroup(self, update: Update) -> Group:
        ...

    def forcegetgroup(self, update: Union[int, Update]) -> Group:
        if isinstance(update, Update):
            assert(isgroupmsg(update))
            return self.forcegetgroup(getchatid(update))
        gpid: int = update
        return self.getgp(gpid) if gpid in self.groups else self.creategp(gpid)

    @overload
    def getplayer(self, plid: int) -> Optional[Player]:
        ...

    @overload
    def getplayer(self, update: Update) -> Optional[Player]:
        ...

    @overload
    def getplayer(self, username: str) -> Optional[Player]:
        ...

    def getplayer(self, update: Union[int, Update, str]) -> Optional[Player]:
        if isinstance(update, Update):
            return None if getmsgfromid(update) not in self.players else self.players[getmsgfromid(update)]
        if isinstance(update, int):
            plid = update
            return None if plid not in self.players else self.players[plid]
        if isinstance(update, str):
            username = update
            return self.usernametopl[username] if username in self.usernametopl else None

    @overload
    def createplayer(self, plid: int) -> Player:
        ...

    @overload
    def createplayer(self, update: Update) -> Player:
        ...

    def createplayer(self, update: Union[int, Update]) -> Player:
        if isinstance(update, Update):
            return self.createplayer(getmsgfromid(update))
        plid: int = update
        assert(plid not in self.players)

        pl = Player(plid=plid)
        self.players[plid] = pl

        try:
            pl.chat = self.updater.bot.get_chat(chat_id=plid)
            pl.getname()
            if pl.username != "":
                self.usernametopl[pl.username] = pl
        except:
            self.sendtoAdmin("无法获取玩家"+str(pl.id)+" chat信息")

        pl.write()

        return pl

    @overload
    def forcegetplayer(self, plid: int) -> Player:
        ...

    @overload
    def forcegetplayer(self, update: Update) -> Player:
        ...

    def forcegetplayer(self, update: Union[int, Update]) -> Player:
        if isinstance(update, Update):
            return self.forcegetplayer(getmsgfromid(update))
        plid: int = update
        return self.getplayer(plid) if plid in self.players else self.createplayer(plid)

    def getcard(self, cdid: int) -> Optional[GameCard]:
        return self.cards[cdid] if cdid in self.cards else None

    def getgamecard(self, cdid: int) -> Optional[GameCard]:
        return self.gamecards[cdid] if cdid in self.gamecards else None

    def addcard(self, card: GameCard, dontautoswitch: bool = False, givekphint: bool = True) -> bool:
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

        if not dontautoswitch:
            if pl.controlling is not None:
                self.autoswitchhint(pl.id)
            pl.controlling = card

        pl.write()
        card.write()
        if card.group.kp is not None and givekphint:
            self.sendto(
                card.group.kp, f"您的群 {card.group.getname()} 新增了一张卡片，玩家是 {card.player.getname()} ，卡id：{str(card.id)}")
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

    def changeusername(self, ousn: str, nusn: str, pl: Player) -> None:
        if ousn in self.usernametopl:
            if nusn != "":
                assert(pl == self.usernametopl[ousn])
                self.usernametopl[nusn] = self.usernametopl.pop(ousn)
            else:
                self.usernametopl.pop(ousn)
        else:
            if nusn != "":
                self.usernametopl[nusn] = pl

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
        gp.delete()
        assert(gp is not None)
        # 维护dicebot
        self.groups[newid] = self.groups.pop(oldid)
        # 维护card
        for card in gp.cards.values():
            card.groupid = newid
            card.write()
        # 维护game, gamecard
        if gp.game is not None:
            gp.game.groupid = newid
            for card in gp.game.cards.values():
                card.groupid = newid
                card.write()
        # 维护Player
        if gp.kp is not None:
            gp.kp.kpgroups[newid] = gp.kp.kpgroups.pop(oldid)
            if oldid in gp.kp.kpgames:
                gp.kp.kpgames[newid] = gp.kp.kpgames.pop(oldid)
            gp.kp.write()

        gp.id = newid
        gp.renew(self.updater)
        gp.write()

    @overload
    def sendto(self, pl: Player, msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Message:
        ...

    @overload
    def sendto(self, plid: int, msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Message:
        ...

    def sendto(self, pl: Union[Player, int], msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Message:
        try:
            if rpmarkup is not None:
                if isinstance(pl, Player):
                    return self.updater.bot.send_message(chat_id=pl.id, text=msg, reply_markup=rpmarkup)
                if pl >= 0:
                    return self.updater.bot.send_message(chat_id=pl, text=msg, reply_markup=rpmarkup)
                self.sendtoAdmin("群聊不发送按钮")
                return self.updater.bot.send_message(chat_id=pl, text=msg)
            if isinstance(pl, Player):
                return self.updater.bot.send_message(chat_id=pl.id, text=msg)
            return self.updater.bot.send_message(chat_id=pl, text=msg)
        except ChatMigrated as e:
            raise e
        except:
            if isinstance(pl, Player):
                return self.sendtoAdmin(f"无法向用户{pl.getname()}发送消息："+msg)
            return self.sendtoAdmin(f"无法向用户{self.forcegetplayer(pl).getname()}发送消息："+msg)

    def autoswitchhint(self, plid: int) -> None:
        self.sendto(plid, "创建新卡时，控制自动切换到新卡")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, DiceBot):
            return False
        return self.IDENTIFIER == o.IDENTIFIER


try:
    dicebot = DiceBot()
except:
    updater.bot.send_message(chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
    print("出现问题")
    exit()
