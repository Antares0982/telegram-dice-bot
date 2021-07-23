#!/usr/bin/python3 -O
from telegram import Message
from telegram.ext import CallbackContext
from telegram.error import ChatMigrated, Unauthorized, BadRequest
from basebot import baseBot
from utils import *

from typing import List, Dict, Union, overload
import time

from gameclass import *


class diceBot(baseBot):
    def __init__(self) -> None:
        super().__init__()

        self.IDENTIFIER = str(time.time())
        self.groups: Dict[int, Group] = {}  # readall()赋值
        self.players: Dict[int, Player] = {}  # readall()赋值
        self.cards: Dict[int, GameCard] = {}  # readall()赋值
        self.gamecards: Dict[int, GameCard] = {}  # readall()赋值
        self.usernametopl: Dict[str, Player] = {}  # construct()赋值
        self.joblist: dict
        self.skilllist: Dict[str, int]
        self.allids: List[int] = []
        self.readall()  # 先执行
        self.construct()  # 后执行
        self.operation: Dict[int, str] = {}
        self.addjobrequest: Dict[int, Tuple[str, list]] = {}
        self.addskillrequest: Dict[int, Tuple[str, int]] = {}
        self.migratefrom: Optional[int] = None
        self.migrateto: Optional[int] = None
        self.skillpages: List[List[str]]
        self.MANUALTEXTS: List[str] = []

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
            if type(gp.kp) is int:
                kp = self.getplayer(gp.kp)
                gp.kp = kp if kp is not None else self.createplayer(gp.kp)
                gp.kp.kpgroups[gp.id] = gp

            if gp.chat is None and gp.id != -1:
                try:
                    gp.chat = self.bot.get_chat(chat_id=gp.id)
                    gp.name = gp.chat.title
                except (BadRequest, Unauthorized):
                    self.sendtoAdmin("群："+str(gp.id)+" " +
                                     gp.name+"telegram chat无法获取")

            game = gp.game if gp.game is not None else gp.pausedgame
            if game is not None:
                if gp.kp is not None:
                    game.kp = gp.kp
                    game.kp.kpgames[gp.id] = game

                if type(game.kpctrl) is int:
                    game.kpctrl = game.cards[game.kpctrl]

        # player
        for pl in self.players.values():
            if pl.chat is None and pl.id != 0:
                try:
                    pl.chat = self.bot.get_chat(chat_id=pl.id)
                    pl.getname()
                    if pl.username != "":
                        self.usernametopl[pl.username] = pl
                except BadRequest:
                    self.sendtoAdmin("用户："+str(pl.id)+" " +
                                     pl.name+"telegram chat无法获取")

            if type(pl.controlling) is int:
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
        self.reply(ADMIN_ID, msg)

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
        if type(update) is int:
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
            gp.chat = self.bot.get_chat(chat_id=gp.id)
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

    def initgroup(self, gpid: int) -> Optional[Group]:
        """若gpid未存储过，创建Group对象并返回，否则返回None"""
        gp = self.getgp(gpid)
        return gp.renew(self.updater) if gp else self.creategp(gpid)

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
        if type(update) is int:
            plid = update
            return None if plid not in self.players else self.players[plid]
        if type(update) is str:
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
            pl.chat = self.bot.get_chat(chat_id=plid)
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

    def initplayer(self, plid: int) -> Optional[Player]:
        """若plid未存储过，创建Player对象并返回，否则返回None"""
        pl = self.getplayer(plid)
        if pl is not None:
            ousn = pl.username
            pl.renew(self.updater)
            if ousn != pl.username:
                self.changeusername(ousn, pl.username, pl)
        else:
            return self.createplayer(plid)

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
    def sendto(self, pl: Player, msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Optional[Message]:
        ...

    @overload
    def sendto(self, gp: Group, msg: str, rpmarkup: None) -> Optional[Message]:
        ...

    @overload
    def sendto(self, id: int, msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Optional[Message]:
        ...

    def sendto(self, pl: Union[Player, Group, int], msg: str, rpmarkup: Optional[InlineKeyboardMarkup] = None) -> Optional[Message]:
        if isinstance(pl, Player) or isinstance(pl, Group):
            chatid = pl.id
        else:
            chatid = pl
        try:
            if chatid >= 0:
                return self.bot.send_message(chat_id=chatid, text=msg, reply_markup=rpmarkup)
            return self.bot.send_message(chat_id=chatid, text=msg)
        except ChatMigrated as e:
            if chatid in self.groups:
                self.groupmigrate(chatid, e.new_chat_id)
                chatid = e.new_chat_id
                self.sendto(chatid, msg)
            else:
                raise e
        except:
            if isinstance(pl, Player) or chatid >= 0:
                if isinstance(pl, Player):
                    name = pl.getname()
                else:
                    if self.getplayer(chatid) is not None:
                        name = self.getplayer(chatid).getname()
                    else:
                        name = str(chatid)
                return self.sendtoAdmin(f"无法向用户{name}发送消息："+msg)
            if isinstance(pl, Group):
                name = pl.getname()
            else:
                if self.getgp(chatid) is not None:
                    name = self.getgp(chatid).getname()
                else:
                    name = str(chatid)
            return self.sendtoAdmin(f"无法向群{name}发送消息："+msg)

    def autoswitchhint(self, plid: int) -> None:
        self.sendto(plid, "创建新卡时，控制自动切换到新卡")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, diceBot):
            return False
        return self.IDENTIFIER == o.IDENTIFIER

    @staticmethod
    def searchifkp(pl: Player) -> bool:
        """判断plid是否至少是一个群的kp"""
        return bool(len(pl.kpgroups))

    def addOP(self, chatid: int, op: str) -> None:
        self.operation[chatid] = op

    def popOP(self, chatid: int) -> str:
        if chatid not in self.operation:
            return ""
        return self.operation.pop(chatid)

    def getOP(self, chatid: int) -> str:
        if chatid not in self.operation:
            return ""
        return self.operation[chatid]

    @commandCallbackMethod
    def addnewjob(self, update: Update, context: CallbackContext) -> bool:
        """向bot数据库中申请添加一个新的职业。
        仅限kp使用这个指令。添加后，请等待bot控制者审核该职业的信息。格式如下：
        `/addnewjob --jobname --creditMin --creditMax --dataname1:ratio --dataname2:ratio/--dataname3_dataname4:ratio...  --skillname1 --skillname2...`
        例如：
        `/addnewjob 刺客 30 60 EDU:2 DEX_STR:2 乔装 电器维修 斗殴 火器 锁匠 机械维修 潜行 心理学`。
        EDU等属性名请使用大写字母。
        审核完成后结果会私聊回复给kp，请开启与bot的私聊。"""
        pl = self.forcegetplayer(update)
        if pl.id in self.addjobrequest:
            return self.errorInfo("已经提交过一个申请了")

        if not self.searchifkp(pl):
            return self.errorInfo("kp才能使用该指令", True)

        if len(context.args) == 0:
            return self.errorInfo("需要参数", True)

        if len(context.args) <= 3:
            return self.errorInfo("参数长度不足")

        if not isint(context.args[1]) or not isint(context.args[2]) or int(context.args[1]) < 0 or int(context.args[1]) > int(context.args[2]):
            return self.errorInfo("信用范围参数无效")

        jobname: str = context.args[0]
        mincre = int(context.args[1])
        maxcre = int(context.args[2])

        i = 3
        ptevalpairs: List[Tuple[str, int]] = []
        while i < len(context.args) and context.args[i].find(':') != -1:
            p = context.args[i].split(':')
            if not isint(p[1]):
                return self.errorInfo("参数无效")

            ptevalpairs.append((p[0], int(p[1])))
            i += 1

        if sum(j for _, j in ptevalpairs) != 4:
            return self.errorInfo("技能点数的乘数总值应该为4")

        skilllist: List[str] = context.args[i:]
        if any(j not in self.skilllist for j in skilllist):
            return self.errorInfo("存在技能表中没有的技能，请先发起技能添加申请或者核阅是否有错别字、使用了同义词")

        ptevald: Dict[str, int] = {}
        for n, j in ptevalpairs:
            ptevald[n] = j

        jobl = [mincre, maxcre, ptevald]
        jobl += skilllist

        ans = (jobname, jobl)
        self.addjobrequest[pl.id, ans]

        pl.renew(self.updater)
        plname = pl.username if pl.username != "" else pl.name
        if plname == "":
            plname = str(pl.id)
        self.sendtoAdmin("有新的职业添加申请："+str(ans) +
                         f"\n来自：@{plname}，id为：{str(pl.id)}")
        self.addOP(ADMIN_ID, "passjob")

        self.reply("申请已经提交，请开启与我的私聊接收审核消息")
        return True

    @commandCallbackMethod
    def addnewskill(self, update: Update, context: CallbackContext) -> bool:
        """向bot数据库中申请添加一个新的技能。
        仅限kp使用这个指令。添加后，请等待bot控制者审核该技能的信息。格式如下：
        `/addnewskill --skillname --basicpoints`
        例如：`/addnewskill 识破 25`。
        审核完成后结果会私聊回复给kp，请开启与bot的私聊。"""
        pl = self.forcegetplayer(update)
        if pl.id in self.addskillrequest:
            return self.errorInfo("已经提交过一个申请了")

        if not self.searchifkp(pl):
            return self.errorInfo("kp才能使用该指令", True)

        if len(context.args) == 0:
            return self.errorInfo("需要参数", True)

        if len(context.args) < 2:
            return self.errorInfo("参数长度不足")

        if not isint(context.args[1]) or int(context.args[1]) < 0 or int(context.args[1]) > 99:
            return self.errorInfo("技能基础点数参数无效")

        skillname: str = context.args[0]
        bspt = int(context.args[1])

        if skillname in self.skilllist:
            return self.errorInfo("该技能已经存在于列表中")

        ans = (skillname, bspt)
        self.addskillrequest[pl.id, ans]

        pl.renew(self.updater)
        plname = pl.username if pl.username != "" else ""
        if plname == "":
            plname = str(pl.id)
        self.sendtoAdmin("有新的技能添加申请："+str(ans) +
                         f"\n来自：@{plname}，id为：{str(pl.id)}")
        self.addOP(ADMIN_ID, "passskill")

        self.reply("申请已经提交，请开启与我的私聊接收审核消息")
        return True


    def getreplyplayer(self, update: Update) -> Optional[Player]:
        """如果有回复的人，调用forcegetplayer获取玩家信息，否则返回None"""
        if isprivatemsg(update):
            return None
        if isgroupmsg(update):
            return self.forcegetplayer(update.message.reply_to_message.from_user.id) if update.message.reply_to_message is not None else None

    @commandCallbackMethod
    def getid(self, update: Update, context: CallbackContext) -> None:
        """获取所在聊天环境的id。
        私聊使用该指令发送用户id，群聊使用该指令则发送群id。
        在创建卡片等待群id时使用该指令，会自动创建卡。"""
        rppl = self.getreplyplayer(update)
        if rppl is not None:
            self.reply("<code>"+str(rppl.id) +
                       "</code> \n点击即可复制", parse_mode='HTML')
            return None

        chatid = getchatid(update)
        pl = self.forcegetplayer(update)
        fromuser = pl.id
        # 检测是否处于newcard状态
        opers = self.getOP(fromuser)

        if opers != "" and isgroup(update):
            opers = opers.split(" ")
            if isgroup(update) and opers[0] == "newcard":
                self.popOP(fromuser)

                if self.hascard(fromuser, chatid) and self.getgp(update).kp is not None and self.getgp(update).kp != pl:
                    context.bot.send_message(
                        chat_id=fromuser, text="你在这个群已经有一张卡了！")
                    return
                if len(opers) >= 3:
                    self.getnewcard(
                        int(opers[1]), chatid, fromuser, int(opers[2]))
                else:
                    self.getnewcard(int(opers[1]), chatid, fromuser)

                rtbutton = [[InlineKeyboardButton(
                    text="跳转到私聊", callback_data="None", url="t.me/"+self.bot.username)]]
                rp_markup = InlineKeyboardMarkup(rtbutton)

                self.reply("<code>"+str(chatid) +
                           "</code> \n点击即可复制", parse_mode='HTML', reply_markup=rp_markup)
                return True

        self.reply("<code>"+str(chatid) +
                   "</code> \n点击即可复制", parse_mode='HTML')

    @commandCallbackMethod
    def manual(self, update: Update, context: CallbackContext) -> bool:
        """显示bot的使用指南"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not isprivate(update):
            return self.errorInfo("请在私聊环境查看手册")

        if len(self.MANUALTEXTS) == 0:
            self.MANUALTEXTS = self.readManual()

        if len(self.MANUALTEXTS) == 0:
            return self.errorInfo("README文件丢失，请联系bot管理者")

        rtbuttons = [[InlineKeyboardButton(
            text="下一页", callback_data=self.IDENTIFIER+" manual 0 next")]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply(
            self.MANUALTEXTS[0], reply_markup=rp_markup, parse_mode="MarkdownV2")
        return

    @commandCallbackMethod
    def msgid(self, update: Update, context: CallbackContext) -> None:
        """输出当前消息的msgid，如果有回复的消息还会返回回复的消息id。仅供调试用"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) > 0:
            self.reply(' '.join(context.args))

        if update.message.reply_to_message is not None:
            if update.message.reply_to_message.link is not None:
                self.reply(update.message.reply_to_message.link)
            else:
                self.reply(
                    f"reply_to message: chat id: {str(getchatid(update))} message id: {str(update.message.reply_to_message.message_id)}")

        if update.message.link is not None:
            self.reply(update.message.link)
        else:
            self.reply(
                f"this message: chat id: {str(getchatid(update))} message id: {str(update.message.message_id)}")
        return

    @commandCallbackMethod
    def start(self, update: Update, context: CallbackContext) -> None:
        """显示bot的帮助信息"""
        self.reply(self.HELP_TEXT)

    @commandCallbackMethod
    def tempcheck(self, update: Update, context: CallbackContext):
        """增加一个临时的检定修正。该指令只能在游戏中使用。
        `/tempcheck --tpcheck`只能用一次的检定修正。使用完后消失
        `/tempcheck --tpcheck --cardid --dicename`对某张卡，持久生效的检定修正。
        如果需要对这张卡全部检定都有修正，dicename参数请填大写单词`GLOBAL`。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            return self.errorInfo("没有参数", True)
        if not isgroup(update):
            return self.errorInfo("在群里设置临时检定")
        if not isint(context.args[0]):
            return self.errorInfo("临时检定修正应当是整数", True)

        gp = self.forcegetgroup(update)
        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorInfo("没有进行中的游戏", True)
        if game.kp != self.forcegetplayer(update):
            return self.errorInfo("KP才可以设置临时检定", True)

        if len(context.args) >= 3 and isint(context.args[1]) and 0 <= int(context.args[1]):
            card = self.getgamecard(int(context.args[1]))
            if card is None or card.group != gp:
                return self.errorInfo("找不到这张卡")

            card.tempstatus.setstatus(context.args[2], int(context.args[0]))
            card.write()
            self.reply(
                "新增了对id为"+context.args[1]+"卡的检定修正\n修正项："+context.args[2]+"，修正值："+context.args[0])
        else:
            game.tpcheck = int(context.args[0])
            self.reply("新增了仅限一次的全局检定修正："+context.args[0])
            game.write()
        return True

    @commandCallbackMethod
    def help(self, update: Update, context: CallbackContext) -> True:
        """查看指令对应函数的说明文档。

        `/help --command`查看指令对应的文档。
        `/help`查看所有的指令。"""
        allfuncs = self.readhandlers()

        if len(context.args) == 0:
            rttext = "单击下面的命令来复制想要查询的指令：\n"
            for funcname in allfuncs:
                if funcname == "helper":
                    funcname = "help"
                rttext += "`/help "+funcname+"`\n"
            update.message.reply_text(rttext, parse_mode="MarkdownV2")
            return True

        glb = globals()

        funcname = context.args[0]
        if funcname == "help":
            funcname = "helper"

        if funcname in allfuncs and glb[funcname].__doc__:
            rttext: str = glb[funcname].__doc__
            ind = rttext.find("    ")
            while ind != -1:
                rttext = rttext[:ind]+rttext[ind+4:]
                ind = rttext.find("    ")
            try:
                update.message.reply_text(rttext, parse_mode="MarkdownV2")
            except:
                update.message.reply_text("Markdown格式parse错误，请联系作者检查并改写文档")
                return False
            return True

        return self.errorInfo("找不到这个指令，或这个指令没有帮助信息。")

    def chatinit(self, update: Update, context: CallbackContext) -> Union[Player, Group, None]:
        """所有指令使用前调用该函数"""
        self.checkconsistency()

        for i in range(len(context.args)):
            if context.args[i][0] == '@':
                pl = self.getplayer(context.args[i][1:])
                if pl is not None:
                    context.args[i] = str(pl.id)

        if isprivatemsg(update):
            return self.initplayer(self.lastchat)
        if isgroupmsg(update):
            self.initplayer(self.lastuser)
            return self.initgroup(self.lastchat)

    def isadmin(self, chatid: int, userid: int):
        admins = self.bot.get_chat(chatid).get_administrators()
        for admin in admins:
            if admin.user.id == userid:
                return True
        return False

    def errorInfo(self, message: str, needrecall: bool = False) -> False:
        """指令无法执行时，调用的函数。
        固定返回`False`，并回复错误信息。
        如果`needrecall`为`True`，在Bot是对应群管理的情况下将删除那条消息。"""

        if needrecall and self.lastchat < 0 and isadmin(self.lastchat, BOT_ID):
            self.delmsg(self.lastchat, self.lastmsgid)
        else:
            if message == "找不到卡。":
                message += "请使用 /switch 切换当前操控的卡再试。"
            elif message.find("参数") != -1:
                message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"

            rp_markup = None
            if message.find("私聊") != -1:
                rtbutton = [[InlineKeyboardButton(
                    "跳转到私聊", callback_data="None", url="t.me/"+self.bot.username)]]
                rp_markup = InlineKeyboardMarkup(rtbutton)

            try:
                self.reply(
                    message, parse_mode="MarkdownV2", reply_markup=rp_markup)
            except:
                self.reply(message, reply_markup=rp_markup)

        return False
