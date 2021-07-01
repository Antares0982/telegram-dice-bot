#!/usr/bin/python3 -O
from telegram import Message
from telegram.ext import CallbackContext
from telegram.error import ChatMigrated, Unauthorized, BadRequest
from basebot import baseBot
from utils import *

from typing import List, Dict, Union, overload
import time

from gameclass import *

# FLAGS

CANREAD = 1
OWNCARD = 2
CANSETINFO = 4
CANDISCARD = 8
CANMODIFY = 16

INGROUP = 1
GROUPKP = 2
GROUPADMIN = 4
BOTADMIN = 8

STATUS_DEAD = "dead"
STATUS_ALIVE = "alive"
STATUS_SERIOUSLYWOUNDED = "seriously wounded"
STATUS_NEARDEATH = "near-death"
STATUS_TEMPSTABLE = "temporarily stable"
STATUS_PERMANENTINSANE = "permanently insane"


class diceBot(baseBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
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
                    gp.chat = self.updater.bot.get_chat(chat_id=gp.id)
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
                    pl.chat = self.updater.bot.get_chat(chat_id=pl.id)
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
                return self.updater.bot.send_message(chat_id=chatid, text=msg, reply_markup=rpmarkup)
            return self.updater.bot.send_message(chat_id=chatid, text=msg)
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

    @commandCallbackMethod
    def abortgame(self, update: Update, context: CallbackContext) -> bool:
        """放弃游戏。只有KP能使用该指令。这还将导致放弃在游戏中做出的所有修改，包括hp，SAN等。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isgroupmsg(update):
            return self.errorHandler(update, "发送群聊消息来中止游戏")
        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorHandler(update, "只有KP可以中止游戏", True)

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is not None:
            mempath = game.memfile
            if mempath != "":
                with open(PATH_MEM+mempath, 'r', encoding='utf-8') as f:
                    update.message.reply_document(
                        f, filename=gp.getname()+".txt", timeout=120)

        if self.gamepop(gp) is None:
            return self.errorHandler(update, "没有找到游戏", True)

        self.reply("游戏已终止！")
        return True

    @commandCallbackMethod
    def addcard(self, update: Update, context: CallbackContext) -> bool:
        """使用已有信息添加一张卡片，模板使用的是NPC/怪物模板。指令格式如下：

        `/addcard --attr_1 --val_1 --attr_2 --val_2 …… --attr_n -- val_n`，
        其中`attr`是卡的直接属性或子属性。

        卡的属性只有三种类型的值：`int`, `str`, `bool`，其他类型暂不支持用本指令。
        函数会自动判断对应的属性是什么类型，其中`bool`类型`attr`对应的`val`只能是`true`, `True`, `false`, `False`之一。

        不可以直接添加tempstatus这个属性。

        如果需要添加主要技能点数，用mainpoints作为`attr`，兴趣技能点则用intpoints，清不要使用points。

        如果要添加特殊技能，比如怪物的技能，请令`attr`为`specialskill`，`val`为`特殊技能名:技能值`。
        技能值是正整数，技能名和技能值用英文冒号分开。

        `name`和背景信息不支持空格，如果要设置这一项信息，需要之后用`/setbkg`来修改，所以尽量不要用该指令设置背景信息。

        如果遇到无法识别的属性，将无法创建卡片。
        参数中，必须的`attr`之一为`groupid`，如果找不到`groupid`将无法添加卡片。
        `playerid`会自动识别为发送者，无需填写`playerid`。
        指令使用者是KP的情况下，才可以指定`playerid`这个属性，否则卡片无效。
        给定`id`属性的话，在指定的卡id已经被占用的时候，会重新自动选取。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "向我发送私聊消息来添加卡", True)
        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数")
        if (len(context.args)//2)*2 != len(context.args):
            self.reply("参数长度应该是偶数")

        t = self.templateNewCard()
        # 遍历args获取attr和val
        mem: List[str] = []
        for i in range(0, len(context.args), 2):
            argname: str = context.args[i]
            if argname in mem:
                return self.errorHandler(update, argname+"属性重复赋值")
            mem.append(argname)
            argval = context.args[i+1]

            if argname == "specialskill":
                skillname, skillval = argval.split(":")
                if not self.isint(skillval) or int(skillval) <= 0:
                    return self.errorHandler(update, "技能值应该是正整数")
                t["skill"]["skills"][skillname] = int(skillval)
                continue

            if argname == "points":
                return self.errorHandler(update, "points应指明是mainpoints还是intpoints")

            if argname == "mainpoints":
                argname = "points"
                dt = t["skill"]
            elif argname == "intpoints":
                argname = "points"
                dt = t["interest"]

            dt = self.findattrindict(t, argname)
            if not dt:  # 可能是技能，否则返回
                if argname in self.skilllist or argname == "母语" or argname == "闪避":
                    if not self.isint(argval) or int(argval) <= 0:
                        return self.errorHandler(update, "技能值应该是正整数")

                    dt = t["skill"]["skills"]
                    dt[argname] = 0  # 这一行是为了防止之后判断类型报错
                else:
                    return self.errorHandler(update, "属性 "+argname+" 在角色卡模板中没有找到")

            if isinstance(dt[argname], dict):
                return self.errorHandler(update, argname+"是dict类型，不可直接赋值")

            if type(dt[argname]) is bool:
                if argval == "false" or argval == "False":
                    argval = False
                elif argval == "true" or argval == "True":
                    argval = True
                if not type(argval) is bool:
                    return self.errorHandler(update, argname+"应该为bool类型")
                dt[argname] = argval

            elif type(dt[argname]) is int:
                if not self.isint(argval):
                    return self.errorHandler(update, argname+"应该为int类型")
                dt[argname] = int(argval)

            else:
                dt[argname] = argval
        # 参数写入完成
        # 检查groupid是否输入了
        if t["groupid"] == 0:
            return self.errorHandler(update, "需要groupid！")

        # 检查是否输入了以及是否有权限输入playerid
        pl = self.forcegetplayer(update)
        if not self.searchifkp(pl):
            if t["playerid"] != 0 and t["playerid"] != pl.id:
                return self.errorHandler(update, "没有权限设置非自己的playerid")
            t["playerid"] = self.getchatid(update)
        else:
            if t["groupid"] not in pl.kpgroups and t["playerid"] != 0 and t["playerid"] != pl.id:
                return self.errorHandler(update, "没有权限设置非自己的playerid")
            if t["playerid"] == 0:
                t["playerid"] = pl.id

        # 生成成功
        card1 = self.GameCard(t)
        # 添加id

        if "id" not in context.args or card1.id < 0 or card1.id in self.allids:
            self.reply("输入了已被占用的id，或id未设置，或id无效。自动获取id")
            card1.id = self.getoneid()
        # 生成衍生数值
        card1.generateOtherAttributes()
        # 卡检查
        rttext = card1.check()
        if rttext != "":
            self.reply(
                "卡片添加成功，但没有通过开始游戏的检查。")
            self.reply(rttext)
        else:
            self.reply("卡片添加成功")

        return True if self.addcard(card1) else self.errorHandler(update, "卡id重复")

    @commandCallbackMethod
    def additem(self, update: Update, context: CallbackContext) -> bool:
        """为你的人物卡添加一些物品。用空格，制表符或回车来分隔不同物品。
        `/additem --item1 --item2...`"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        card = self.forcegetplayer(update).controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。")

        card.additems(context.args)
        self.reply(f"添加了{str(len(context.args))}件物品。")
        return True

    @commandCallbackMethod
    def addkp(self, update: Update, context: CallbackContext) -> bool:
        """添加KP。在群里发送`/addkp`将自己设置为KP。
        如果这个群已经有一名群成员是KP，则该指令无效。
        若原KP不在群里，该指令可以替换KP。

        如果原KP在群里，需要先发送`/delkp`来撤销自己的KP，或者管理员用`/transferkp`来强制转移KP权限。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, '发送群消息添加KP')

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        # 判断是否已经有KP
        if gp.kp is not None:
            # 已有KP
            if not self.isingroup(gp, kp):
                if not self.changeKP(gp, kp):  # 更新NPC卡拥有者
                    # 不应触发
                    return self.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")
                return True

            return self.errorHandler(update, "你已经是KP了", True) if gp.kp == kp else self.errorHandler(update, '这个群已经有一位KP了，请先让TA发送 /delkp 撤销自己的KP。如果需要强制更换KP，请管理员用\'/transferkp kpid\'添加本群成员为KP，或者 /transferkp 将自己设为KP。')

        # 该群没有KP，可以直接添加KP
        self.addkp(gp, kp)

        # delkp指令会将KP的卡playerid全部改为0，检查如果有id为0的卡，id设为新kp的id
        self.changecardsplid(gp, self.forcegetplayer(0), kp)

        self.reply(
            "绑定群(id): " + gp.getname() + "与KP(id): " + kp.getname())

        return True

    @commandCallbackMethod
    def addnewjob(self, update: Update, context: CallbackContext) -> bool:
        """向bot数据库中申请添加一个新的职业。
        仅限kp使用这个指令。添加后，请等待bot控制者审核该职业的信息。格式如下：
        `/addnewjob --jobname --creditMin --creditMax --dataname1:ratio --dataname2:ratio/--dataname3_dataname4:ratio...  --skillname1 --skillname2...`
        例如：
        `/addnewjob 刺客 30 60 EDU:2 DEX_STR:2 乔装 电器维修 斗殴 火器 锁匠 机械维修 潜行 心理学`。
        EDU等属性名请使用大写字母。
        审核完成后结果会私聊回复给kp，请开启与bot的私聊。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if pl.id in self.addjobrequest:
            return self.errorHandler(update, "已经提交过一个申请了")

        if not self.searchifkp(pl):
            return self.errorHandler(update, "kp才能使用该指令", True)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数", True)

        if len(context.args) <= 3:
            return self.errorHandler(update, "参数长度不足")

        if not self.isint(context.args[1]) or not self.isint(context.args[2]) or int(context.args[1]) < 0 or int(context.args[1]) > int(context.args[2]):
            return self.errorHandler(update, "信用范围参数无效")

        jobname: str = context.args[0]
        mincre = int(context.args[1])
        maxcre = int(context.args[2])

        i = 3
        ptevalpairs: List[Tuple[str, int]] = []
        while i < len(context.args) and context.args[i].find(':') != -1:
            p = context.args[i].split(':')
            if not self.isint(p[1]):
                return self.errorHandler(update, "参数无效")

            ptevalpairs.append((p[0], int(p[1])))
            i += 1

        if sum(j for _, j in ptevalpairs) != 4:
            return self.errorHandler(update, "技能点数的乘数总值应该为4")

        skilllist: List[str] = context.args[i:]
        if any(j not in self.skilllist for j in skilllist):
            return self.errorHandler(update, "存在技能表中没有的技能，请先发起技能添加申请或者核阅是否有错别字、使用了同义词")

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
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if pl.id in self.addskillrequest:
            return self.errorHandler(update, "已经提交过一个申请了")

        if not self.searchifkp(pl):
            return self.errorHandler(update, "kp才能使用该指令", True)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数", True)

        if len(context.args) < 2:
            return self.errorHandler(update, "参数长度不足")

        if not self.isint(context.args[1]) or int(context.args[1]) < 0 or int(context.args[1]) > 99:
            return self.errorHandler(update, "技能基础点数参数无效")

        skillname: str = context.args[0]
        bspt = int(context.args[1])

        if skillname in self.skilllist:
            return self.errorHandler(update, "该技能已经存在于列表中")

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

    @commandCallbackMethod
    def addskill(self, update: Update, context: CallbackContext) -> bool:
        """该函数用于增加/修改技能。

        `/addskill`：生成按钮，玩家按照提示一步步操作。
        `/addskill 技能名`：修改某项技能的点数。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "发私聊消息来增改技能", True)

        pl = self.forcegetplayer(update)
        card1 = pl.controlling
        if card1 is None:
            return self.errorHandler(update, "找不到卡。")

        if card1.skill.points == -1:
            return self.errorHandler(update, "信息不完整，无法添加技能")

        if card1.skill.points == 0 and card1.interest.points == 0:
            if len(context.args) == 0 or (context.args[0] not in card1.skill.allskills() and context.args[0] not in card1.interest.allskills()):
                return self.errorHandler(update, "你已经没有技能点了，请添加参数来修改具体的技能！")

        if card1.info.job == "":
            return self.errorHandler(update, "请先设置职业")

        if len(context.args) > 1:
            return self.errorHandler(update, "该指令只能接收一个参数：技能名")

        # 开始处理
        if "信用" not in card1.skill.allskills():
            return self.addcredit(update, card1)

        if len(context.args) == 0:
            return self.addskill0(card1)

        if context.args[0] == "信用" or context.args[0] == "credit":
            return self.addcredit(update, card1) if "信用" not in card1.skill.allskills() else self.cgcredit(update, card1)

        skillname = context.args[0]

        if skillname != "母语" and skillname != "闪避" and (skillname not in self.skilllist or skillname == "克苏鲁神话"):
            return self.errorHandler(update, "无法设置这个技能")

        # This function only returns True
        return self.addskill1(update, context, card1)

    @commandCallbackMethod
    def cardtransfer(self, update: Update, context: CallbackContext) -> bool:
        """转移卡片所有者。格式为
        `/cardtransfer --cardid --playerid`：将卡转移给playerid。
        回复某人`/cardtransfer --cardid`：将卡转移给被回复的人。要求参数有且仅有一个。
        只有卡片拥有者或者KP有权使用该指令。
        如果对方不是KP且对方已经在本群有卡，则无法转移。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数", True)
        if len(context.args) == 1 and self.getreplyplayer(update) is None:
            return self.errorHandler(update, "参数不足", True)
        if not self.isint(context.args[0]) or (len(context.args) > 1 and not self.isint(context.args[1])):
            return self.errorHandler(update, "参数无效", True)
        if int(context.args[0]) < 0 or (len(context.args) > 1 and int(context.args[1]) < 0):
            return self.errorHandler(update, "负数参数无效", True)

        cdid = int(context.args[0])
        card = self.getcard(cdid)
        if card is None:
            return self.errorHandler(update, "找不到这张卡")

        operationer = self.forcegetplayer(update)
        if len(context.args) == 1:
            tpl: Player = self.getreplyplayer(update)
        else:
            tpl = self.forcegetplayer(int(context.args[1]))

        if not self.checkaccess(operationer, card) & (OWNCARD | CANMODIFY):
            return self.errorHandler(update, "没有权限", True)

        if tpl != card.group.kp:
            for c in tpl.cards.values():
                if c.group == card.group:
                    return self.errorHandler(update, "目标玩家已经在对应群有一张卡了")

        # 开始处理
        self.atcardtransfer(update.message, cdid, tpl)
        return True

    @commandCallbackMethod
    def changegroup(self, update: Update, context: CallbackContext) -> bool:
        """修改卡片的所属群。
        一般只用于卡片创建时输入了错误的群id。
        比较特殊的情形：
        如果需要将某个群的所有卡片全部转移到另一个群，
        第一个参数写为负数的`groupid`即可。这一操作需要原群的kp权限。
        在原群进行游戏时，这个指令无效。

        指令格式：
        `/changegroup --groupid/--cardid --newgroupid`
        """
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) < 2:
            return self.errorHandler(update, "至少需要2个参数", True)
        if not self.isint(context.args[0]) or not self.isint(context.args[1]):
            return self.errorHandler(update, "参数无效", True)

        newgpid = int(context.args[1])
        if newgpid >= 0:
            return self.errorHandler(update, "转移的目标群id应该是负数", True)

        if int(context.args[0]) < 0:  # 转移全部群卡片
            ogpid = int(context.args[0])

            oldgp = self.getgp(ogpid)
            if oldgp is None or len(oldgp.cards) == 0:
                return self.errorHandler(update, "该群没有卡")

            newgp = self.forcegetgroup(newgpid)
            kp = self.forcegetgroup(update)
            if ((kp != oldgp.kp and oldgp.id != -1) or kp != newgp.kp) and kp.id != ADMIN_ID:
                return self.errorHandler(update, "没有权限", True)

            if oldgp.getexistgame() is not None:
                return self.errorHandler(update, "游戏进行中，无法转移")

            # 检查权限通过
            numofcards = len(oldgp.cards)
            self.changecardgpid(ogpid, newgpid)
            self.reply(
                "操作成功，已经将"+str(numofcards)+"张卡片从群："+str(ogpid)+"移动到群："+str(newgpid))
            return True

        # 转移一张卡片
        cdid = int(context.args[0])
        card = self.getcard(cdid)
        if card is None:
            return self.errorHandler(update, "找不到这个id的卡片", True)

        oldgp = card.group
        if oldgp.getexistgame():
            return self.errorHandler(update, "游戏正在进行，无法转移")

        pl = self.forcegetplayer(update)
        if not self.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
            return self.errorHandler(update, "没有权限")

        # 开始执行
        card = self.popcard(cdid)
        self.addcardoverride(card, newgpid)
        cardname = card.getname()
        self.reply(
            "操作成功，已经将卡片"+cardname+"从群："+str(oldgp.id)+"移动到群："+str(newgpid))
        return True

    @commandCallbackMethod
    def changeid(self, update: Update, context: CallbackContext) -> bool:
        """修改卡片id。卡片的所有者或者KP均有使用该指令的权限。

        指令格式：
        `/changeid --cardid --newid`

        如果`newid`已经被占用，则指令无效。
        这一行为将同时改变游戏内以及游戏外的卡id。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) < 2:
            return self.errorHandler(update, "至少需要两个参数。")

        if not self.isint(context.args[0]) or not self.isint(context.args[1]):
            return self.errorHandler(update, "参数无效", True)

        oldid = int(context.args[0])
        newid = int(context.args[1])

        if newid < 0:
            return self.errorHandler(update, "卡id不能为负数", True)
        if newid == oldid:
            return self.errorHandler(update, "前后id相同", True)
        if newid in self.allids:
            return self.errorHandler(update, "该ID已经被占用")

        card = self.getcard(oldid)
        if card is None:
            return self.errorHandler(update, "找不到该ID对应的卡")

        pl = self.forcegetplayer(update)
        if not self.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
            return self.errorHandler(update, "没有权限")

        # 开始处理
        self.atidchanging(update.message, oldid, newid)
        return True

    @commandCallbackMethod
    def choosedec(self, update: Update, context: CallbackContext) -> bool:
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "私聊使用该指令")

        pl = self.forcegetplayer(update)

        if pl.controlling is None:
            return self.errorHandler(update, "请先使用 /switch 切换回要设定降值的卡。")

        if pl.controlling.data.datadec is None:
            return self.errorHandler(update, "该卡不需要进行降值设定。请先使用 /switch 切换回要设定降值的卡。")

        self.choosedec(update, pl.controlling)
        return True

    @commandCallbackMethod
    def continuegame(self, update: Update, context: CallbackContext) -> bool:
        """继续游戏。必须在`/pausegame`之后使用。
        游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
        当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
        可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
        继续游戏后会覆盖游戏中的这些属性。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isgroupmsg(update):
            return self.errorHandler(update, "发送群消息暂停游戏")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorHandler(update, "只有KP可以暂停游戏", True)
        if gp.pausedgame is None:
            return self.errorHandler(update, "没有进行中的游戏", True)

        for card in gp.pausedgame.cards.values():
            outcard = gp.getcard(card.id)
            assert(outcard is not None)
            card.info.name = outcard.info.name
            card.info.sex = outcard.info.sex
            card.item = copy.copy(outcard.item)
            card.assets = outcard.assets
            card.background = CardBackground(d=outcard.background.to_json())

        for card in gp.cards.values():
            if card.id not in gp.pausedgame.cards:
                ngcard = GameCard(card.to_json())
                ngcard.isgamecard = True
                self.addgamecard(ngcard)

        gp.game = gp.pausedgame
        gp.pausedgame = None
        gp.write()
        self.reply("游戏继续！")
        return True

    @commandCallbackMethod
    def copygroup(self, update: Update, context: CallbackContext) -> bool:
        """复制一个群的所有数据到另一个群。
        新的卡片id将自动从小到大生成。

        格式：
        `/copygroup --oldgroupid --newgroupid (kp)`
        将`oldgroupid`群中数据复制到`newgroupid`群中。
        如果有第三个参数kp，则仅复制kp的卡片。

        使用者需要同时是两个群的kp。
        任何一个群在进行游戏的时候，该指令都无法使用。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        try:
            oldgpid, newgpid = int(context.args[0]), int(context.args[1])
        except (IndexError, ValueError):
            return self.errorHandler(update, "输入无效", True)

        ogp = self.getgp(oldgpid)
        if ogp is None or len(ogp.cards) == 0:
            return self.errorHandler(update, "该群没有卡", True)

        kp = self.forcegetplayer(update)
        ngp = self.getgp(newgpid)
        if ngp is None or kp != ogp.kp or ngp.kp != kp:
            return self.errorHandler(update, "没有权限", True)

        copyall = True
        if len(context.args) >= 3 and context.args[2] == "kp":
            copyall = False

        if not self.groupcopy(oldgpid, newgpid, copyall):
            return self.errorHandler(update, "无法复制")

        self.reply("复制成功")
        return True

    @commandCallbackMethod
    def createcardhelp(self, update: Update, context: CallbackContext) -> None:
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        self.reply(self.CREATE_CARD_HELP, parse_mode="MarkdownV2")

    @commandCallbackMethod
    def delcard(self, update: Update, context: CallbackContext) -> bool:
        """KP才能使用该指令，删除一张卡片。一次只能删除一张卡。
        `/delcard --cardid`：删除id为cardid的卡。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要卡id作为参数", True)
        if not self.isint(context.args[0]) or int(context.args[0]) < 0:
            return self.errorHandler(update, "参数无效", True)

        cdid = int(context.args[0])
        card = self.getcard(cdid)

        if card is None:
            return self.errorHandler(update, "找不到对应id的卡")

        kp = self.forcegetplayer(update)
        if not self.checkaccess(kp, card) & CANMODIFY:
            return self.errorHandler(update, "没有权限", True)

        # 开始处理
        self.reply(
            f"请确认是否删除卡片\n姓名：{card.getname()}\n如果确认删除，请回复：确认。否则，请回复其他任何文字。")
        self.addOP(self.getchatid(update), "delcard "+context.args[0])
        return True

    @commandCallbackMethod
    def delkp(self, update: Update, context: CallbackContext) -> bool:
        """撤销自己的KP权限。只有当前群内KP可以使用该指令。
        在撤销KP之后的新KP会自动获取原KP的所有NPC的卡片"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, '发群消息撤销自己的KP权限')

        gp = self.forcegetgroup(update)
        if gp.kp is None:
            return self.errorHandler(update, '本群没有KP', True)

        if not self.checkaccess(self.forcegetplayer(update), gp) & GROUPKP:
            return self.errorHandler(update, '你不是KP', True)

        self.changecardsplid(gp, gp.kp, self.forcegetplayer(0))
        self.delkp(gp)

        self.reply('KP已撤销')

        if self.getOP(gp.id).find("delcard") != -1:
            self.popOP(gp.id)

        return True

    @commandCallbackMethod
    def delmsg(self, update: Update, context: CallbackContext) -> bool:
        """用于删除消息，清空当前对话框中没有用的消息。
        bot可以删除任意私聊消息，无论是来自用户还是bot。
        如果是群内使用该指令，需要管理员或KP权限，
        以及bot是管理员，此时可以删除群内的任意消息。

        当因为各种操作产生了过多冗杂消息的时候，使用
        `/delmsg --msgnumber`将会删除：delmsg指令的消息
        以及该指令上面的msgnumber条消息。例如：
        `/delmsg 2`将删除包含delmsg指令在内的3条消息。
        没有参数的时候，`/delmsg`默认删除指令和指令的上一条消息。

        因为要进行连续的删除请求，删除的时间会稍微有些滞后，
        请不要重复发送该指令，否则可能造成有用的消息丢失。
        如果感觉删除没有完成，请先随意发送一条消息来拉取删除情况，
        而不是继续用`/delmsg`删除。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        delnum = 1
        chatid = self.getchatid(update)

        if self.isgroupmsg(update) and not self.isadmin(update, BOT_ID):
            return self.errorHandler(update, "Bot没有管理权限")

        if self.isgroupmsg(update) and self.checkaccess(self.forcegetplayer(update), self.forcegetgroup(update)) & (GROUPKP | GROUPADMIN) == 0:
            return self.errorHandler(update, "没有权限", True)

        if len(context.args) >= 1:
            if not self.isint(context.args[0]) or int(context.args[0]) <= 0:
                return self.errorHandler(update, "参数错误", True)
            delnum = int(context.args[0])
            if delnum > 10:
                return self.errorHandler(update, "一次最多删除10条消息")

        lastmsgid = update.message.message_id
        while delnum >= 0:  # 这是因为要连同delmsg指令的消息也要删掉
            if lastmsgid < -100:
                break
            try:
                context.bot.delete_message(
                    chat_id=chatid, message_id=lastmsgid)
            except:
                lastmsgid -= 1
            else:
                delnum -= 1
                lastmsgid -= 1

        update.effective_chat.send_message("删除完成").delete()
        return True

    @commandCallbackMethod
    def discard(self, update: Update, context: CallbackContext) -> bool:
        """该指令用于删除角色卡。
        通过识别卡中`discard`是否为`True`来判断是否可以删除这张卡。
        如果`discard`为`False`，需要玩家向KP申请，让KP修改`discard`属性为`True`。

        指令格式如下：
        `/discard (--groupid_1/--cardid_1 --groupid_2/--cardid_2 ...)`。
        可以一次输入多个群或卡id来批量删除。

        无参数时，如果只有一张卡可以删除，自动删除那张卡。
        否则，会创建一组按钮来让玩家选择要删除哪张卡。

        有参数时，
        若其中一个参数为群id（负数），则删除该群内所有可删除的卡。
        若其中一个参数为卡id，删除对应的那张卡。
        找不到参数对应的卡时，该参数会被忽略。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "发送私聊消息删除卡。")

        pl = self.getplayer(update)  # 发送者
        if pl is None:
            return self.errorHandler(update, "找不到可删除的卡。")

        if len(context.args) > 0:
            # 先处理context.args
            if any(not self.isint(x) for x in context.args):
                return self.errorHandler(update, "参数需要是整数")
            nargs = list(map(int, context.args))

            discards = self.findDiscardCardsWithGpidCdid(pl, nargs)

            # 求args提供的卡id与可删除的卡id的交集

            if len(discards) == 0:  # 交集为空集
                return self.errorHandler(update, "输入的（群/卡片）ID均无效。")

            if len(discards) == 1:
                card = discards[0]
                rttext = "删除卡："+str(card.getname())
                rttext += "删除操作不可逆。"
                self.reply(rttext)
            else:
                self.reply(
                    "删除了"+str(len(discards))+"张卡片。\n删除操作不可逆。")

            for card in discards:
                self.cardpop(card)
            return True

        # 计算可以discard的卡有多少
        discardgpcdTupleList = self.findAllDiscardCards(pl)
        if len(discardgpcdTupleList) > 1:  # 创建按钮，接下来交给按钮完成
            rtbuttons: List[List[str]] = [[]]

            for card in discardgpcdTupleList:
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                cardname = card.getname()
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(cardname,
                                                                        callback_data=self.IDENTIFIER+" "+"discard "+str(card.id)))

            rp_markup = InlineKeyboardMarkup(rtbuttons)

            self.reply("请点击要删除的卡片：", reply_markup=rp_markup)
            return True

        if len(discardgpcdTupleList) == 1:
            card = discardgpcdTupleList[0]

            rttext = "删除卡："+card.getname()
            rttext += "\n删除操作不可逆。"
            self.reply(rttext)

            self.cardpop(card)
            return True

        # 没有可删除的卡
        return self.errorHandler(update, "找不到可删除的卡。")

    @commandCallbackMethod
    def endgame(self, update: Update, context: CallbackContext) -> bool:
        """结束游戏。

        这一指令会导致所有角色卡的所有权转移给KP，之后玩家无法再操作这张卡片。
        同时，游戏外的卡片会被游戏内的卡片覆写。
        如果还没有准备好进行覆写，就不要使用这一指令。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isgroupmsg(update):
            return self.errorHandler(update, "群聊才能使用该指令")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorHandler("只有KP可以结束游戏。")

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorHandler(update, "没找到进行中的游戏。")

        mempath = game.memfile

        self.atgameending(game)

        if mempath != "":
            with open(PATH_MEM+mempath, 'r', encoding='utf-8') as f:
                update.message.reply_document(
                    f, filename=gp.getname()+".txt", timeout=120)

        self.reply("游戏结束！")
        return True

    @commandCallbackMethod
    def getid(self, update: Update, context: CallbackContext) -> None:
        """获取所在聊天环境的id。
        私聊使用该指令发送用户id，群聊使用该指令则发送群id。
        在创建卡片等待群id时使用该指令，会自动创建卡。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        rppl = self.getreplyplayer(update)
        if rppl is not None:
            self.reply("<code>"+str(rppl.id) +
                       "</code> \n点击即可复制", parse_mode='HTML')
            return None

        chatid = self.getchatid(update)
        pl = self.forcegetplayer(update)
        fromuser = pl.id
        # 检测是否处于newcard状态
        opers = self.getOP(fromuser)

        if opers != "" and self.isgroupmsg(update):
            opers = opers.split(" ")
            if self.isgroupmsg(update) and opers[0] == "newcard":
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
                    text="跳转到私聊", callback_data="None", url="t.me/"+self.updater.bot.username)]]
                rp_markup = InlineKeyboardMarkup(rtbutton)

                self.reply("<code>"+str(chatid) +
                           "</code> \n点击即可复制", parse_mode='HTML', reply_markup=rp_markup)
                return True

        self.reply("<code>"+str(chatid) +
                   "</code> \n点击即可复制", parse_mode='HTML')

    @commandCallbackMethod
    def hp(self, update: Update, context: CallbackContext) -> bool:
        """修改HP。KP通过回复某位PL消息并在回复消息中使用本指令即可修改对方卡片的HP。
        回复自己的消息，则修改kp当前选中的游戏卡。
        或者，也可以使用@用户名以及用玩家id的方法选中某名PL，但请不要同时使用回复和用户名。
        使用范例：
        `/hp +1d3`：恢复1d3点HP。
        `/hp -2`：扣除2点HP。
        `/hp 10`：将HP设置为10。
        `/hp @username 12`：将用户名为username的玩家HP设为12。
        下面的例子是无效输入：
        `/hp 1d3`：无法将HP设置为一个骰子的结果，恢复1d3生命请在参数前加上符号`+`，扣除同理。
        在生命变动的情况下，角色状态也会同步地变动。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "游戏中才可以修改HP。")
        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorHandler(update, "没有权限", True)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要指定扣除的HP", True)

        chp: str = context.args[0]
        game = gp.game
        if game is None:
            return self.errorHandler(update, "找不到进行中的游戏", True)

        rppl = self.getreplyplayer(update)

        if rppl is None:
            if len(context.args) < 2:
                return self.errorHandler(update, "请用回复或@用户名的方式来选择玩家改变HP")
            if not self.isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorHandler(update, "参数无效")
            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorHandler(update, "指定的用户无效")
            chp = context.args[1]

        if rppl != kp:
            cardi = self.findcardfromgame(game, rppl)
        else:
            cardi = game.kpctrl

        if cardi is None:
            return self.errorHandler(update, "找不到这名玩家的卡。")

        if chp[0] == "+" or chp[0] == "-":
            if len(chp) == 1:
                return self.errorHandler(update, "参数无效", True)

            # 由dicecalculator()处理。减法时，检查可能的括号导致的输入错误
            if chp[0] == '-' and chp[1] != '(' and (chp[1:].find('+') != -1 or chp[1:].find('-') != -1):
                return self.errorHandler(update, "当第一个减号的后面是可计算的骰子，且存在加减法时，请在第一个符号之后使用括号")

            try:
                diceans = self.dicecalculator(chp[1:])
            except:
                return self.errorHandler(update, "参数无效", True)

            if diceans < 0:
                return self.errorHandler(update, "骰子的结果为0，生命值不修改")

            chp = chp[0]+str(diceans)
        else:
            # 直接修改生命为目标值的情形。不支持dicecalculator()，仅支持整数
            if not self.isint(chp) or int(chp) > 100 or int(chp) < 0:
                return self.errorHandler(update, "参数无效", True)

        if cardi.status == STATUS_DEAD:
            return self.errorHandler(update, "该角色已死亡")

        originhp = cardi.attr.HP
        if chp[0] == "+":
            cardi.attr.HP += int(chp[1:])
        elif chp[0] == "-":
            cardi.attr.HP -= int(chp[1:])
        else:
            cardi.attr.HP = int(chp)

        hpdiff = cardi.attr.HP - originhp
        if hpdiff == 0:
            return self.errorHandler(update, "HP不变，目前HP："+str(cardi.attr.HP))

        if hpdiff < 0:
            # 承受伤害描述。分类为三种状态
            takedmg = -hpdiff
            if takedmg < cardi.attr.MAXHP//2:
                # 轻伤，若生命不降到0，不做任何事
                if takedmg >= originhp:
                    update.message.reply_to_message.reply_text("HP归0，角色昏迷")
            elif takedmg > cardi.attr.MAXHP:
                update.message.reply_to_message.reply_text("致死性伤害，角色死亡")
                cardi.status = STATUS_DEAD
            else:
                update.message.reply_to_message.reply_text(
                    "角色受到重伤，请进行体质检定以维持清醒")
                cardi.status = STATUS_SERIOUSLYWOUNDED
                if originhp <= takedmg:
                    update.message.reply_to_message.reply_text("HP归0，进入濒死状态")
                    cardi.status = STATUS_NEARDEATH

            if cardi.attr.HP < 0:
                cardi.attr.HP = 0

        else:
            # 恢复生命，可能脱离某种状态
            if cardi.attr.HP >= cardi.attr.MAXHP:
                cardi.attr.HP = cardi.attr.MAXHP
                update.message.reply_to_message.reply_text("HP达到最大值")

            if hpdiff > 1 and originhp <= 1 and cardi.status == STATUS_NEARDEATH:
                self.reply("脱离濒死状态")
                cardi.status = STATUS_SERIOUSLYWOUNDED
        cardi.write()

        self.reply("生命值从"+str(originhp)+"修改为"+str(cardi.attr.HP))
        return True

    @commandCallbackMethod
    def kill(self, update: Update, context: CallbackContext) -> bool:
        """使角色死亡。使用回复或者`@username`作为参数来选择对象撕卡。
        回复的优先级高于参数。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorHandler(update, "没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorHandler(update, "没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorHandler(update, "使用回复或@username指定恢复者")
            if not self.isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorHandler(update, "参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorHandler(update, "玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorHandler(update, "找不到该玩家的卡。")

        if card.status == STATUS_DEAD:
            return self.errorHandler(update, "角色已死亡")

        card.status = STATUS_DEAD
        self.reply("已撕卡")
        card.write()
        return True

    @commandCallbackMethod
    def link(self, update: Update, context: CallbackContext) -> bool:
        """获取群邀请链接，并私聊发送给用户。

        使用该指令必须要满足两个条件：指令发送者和bot都是该群管理员。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isgroupmsg(update):
            return self.errorHandler(update, "在群聊使用该指令。")
        if not self.isadmin(update, self.BOT_ID):
            return self.errorHandler(update, "Bot没有权限")
        if not self.isadmin(update, update.message.from_user.id):
            return self.errorHandler(update, "没有权限", True)

        adminid = update.message.from_user.id
        gpid = update.effective_chat.id
        chat = context.bot.get_chat(chat_id=gpid)
        ivlink = chat.invite_link
        if not ivlink:
            ivlink = context.bot.export_chat_invite_link(chat_id=gpid)

        try:
            context.bot.send_message(
                chat_id=adminid, text="群："+chat.title+"的邀请链接：\n"+ivlink)
        except:
            return self.errorHandler(update, "邀请链接发送失败！")

        rtbutton = [[InlineKeyboardButton(
            text="跳转到私聊", callback_data="None", url="t.me/"+self.updater.bot.username)]]
        rp_markup = InlineKeyboardMarkup(rtbutton)

        self.reply("群邀请链接已经私聊发送。", reply_markup=rp_markup)
        return True

    @commandCallbackMethod
    def mad(self, update: Update, context: CallbackContext) -> bool:
        """使角色陷入永久疯狂。使用回复或者`@username`作为参数来选择对象撕卡。
        回复的优先级高于参数。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorHandler(update, "没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorHandler(update, "没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorHandler(update, "使用回复或@username指定恢复者")
            if not self.isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorHandler(update, "参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorHandler(update, "玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorHandler(update, "找不到该玩家的卡。")

        if card.status == STATUS_DEAD:
            return self.errorHandler(update, "角色已死亡")

        if card.status == STATUS_PERMANENTINSANE:
            return self.errorHandler(update, "角色已永久疯狂")

        card.status = STATUS_PERMANENTINSANE
        card.write()
        self.reply("已撕卡")
        return True

    @commandCallbackMethod
    def manual(self, update: Update, context: CallbackContext) -> bool:
        """显示bot的使用指南"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isprivatemsg(update):
            return self.errorHandler(update, "请在私聊环境查看手册")

        if len(self.MANUALTEXTS) == 0:
            self.MANUALTEXTS = self.readManual()

        if len(self.MANUALTEXTS) == 0:
            return self.errorHandler(update, "README文件丢失，请联系bot管理者")

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
                    f"reply_to message: chat id: {str(self.getchatid(update))} message id: {str(update.message.reply_to_message.message_id)}")

        if update.message.link is not None:
            self.reply(update.message.link)
        else:
            self.reply(
                f"this message: chat id: {str(self.getchatid(update))} message id: {str(update.message.message_id)}")
        return

    @commandCallbackMethod
    def modify(self, update: Update, context: CallbackContext) -> bool:
        """强制修改某张卡某个属性的值。
        需要注意可能出现的问题，使用该指令前，请三思。

        `/modify --cardid --arg --value (game)`: 修改id为cardid的卡的value，要修改的参数是arg。
        带game时修改的是游戏内卡片数据，不指明时默认游戏外
        （对于游戏中与游戏外卡片区别，参见 `/help startgame`）。
        修改对应卡片的信息必须要有对应的KP权限，或者是BOT的管理者。
        如果要修改主要技能点和兴趣技能点，请使用`mainpoints`, `intpoints`作为`arg`，而不要使用points。
        id, playerid, groupid这三个属性不可以修改。
        想要修改id，请使用指令
        `/changeid --cardid --newid`
        （参考`/help changeid`）。
        想要修改所属群，使用指令
        `/changegroup --cardid --newgroupid`
        （参考`/help changegroup`）。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if not self.searchifkp(pl) and pl.id != ADMIN_ID:
            return self.errorHandler(update, "没有权限", True)

        # need 3 args, first: card id, second: attrname, third: value
        if len(context.args) < 3:
            return self.errorHandler(update, "需要至少3个参数", True)

        card_id = context.args[0]
        if not self.isint(card_id) or int(card_id) < 0:
            return self.errorHandler(update, "无效ID", True)

        card_id = int(card_id)
        if len(context.args) > 3 and context.args[3] == "game":
            card = self.getgamecard(card_id)
            rttext = "修改了游戏内的卡片：\n"
        else:
            card = self.getcard(card_id)
            rttext = "修改了游戏外的卡片：\n"

        if card is None:
            return self.errorHandler(update, "找不到这张卡")

        if not self.checkaccess(pl, card) & CANMODIFY:
            return self.errorHandler(update, "没有权限", True)

        try:
            if context.args[1] == "mainpoints":
                ans, ok = card.skill.modify("points", context.args[2])
            elif context.args[1] == "intpoints":
                ans, ok = card.interest.modify("points", context.args[2])
            else:
                ans, ok = card.modify(context.args[1], context.args[2])
        except TypeError as e:
            return self.errorHandler(update, str(e))

        if not ok:
            return self.errorHandler(update, "修改失败。"+ans)

        rttext += context.args[1]+"从"+ans+"变为"+context.args[2]
        self.reply(rttext)
        return True

    @commandCallbackMethod
    def newcard(self, update: Update, context: CallbackContext) -> bool:
        """随机生成一张新的角色卡。需要一个群id作为参数。
        只接受私聊消息。

        如果发送者不是KP，那么只能在一个群内拥有最多一张角色卡。

        如果不知道群id，请先发送`/getid`到群里获取id。

        `/newcard`提交创建卡请求，bot会等待你输入`groupid`。
        `/newcard --groupid`新建一张卡片，绑定到`groupid`对应的群。
        `/newcard --cardid`新建一张卡片，将卡片id设置为`cardid`，`cardid`必须是非负整数。
        `/newcard --groupid --cardid`新建一张卡片，绑定到`groupid`对应的群的同时，将卡片id设置为`cardid`。

        当指定的卡id已经被别的卡占用的时候，将自动获取未被占用的id。

        当生成时有至少三项基础属性低于50时，可以使用`/discard`来放弃并删除这张角色卡。
        创建新卡之后，当前控制卡片会自动切换到新卡，详情参见
        `/help switch`。

        角色卡说明
        一张角色卡具有：
        `groupid`，`id`，`playerid`基本信息。
        STR，CON，SIZ，DEX，APP，INT，EDU，LUCK基本属性；
        职业、姓名、性别、年龄；
        技能信息；
        背景故事（描述，重要之人，重要之地，珍视之物，特质，受过的伤，恐惧之物，神秘学物品，第三类接触）；
        检定修正值；
        物品，财产；
        角色类型（PL，NPC）；
        是否可以被删除；
        状态（存活，死亡，疯狂等）。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        gpid: int = None
        gp: Optional[Group] = None
        newcdid: Optional[int] = None

        if self.isgroupmsg(update):
            # 先检查是否有该玩家信息
            rtbutton = [[InlineKeyboardButton(
                text="跳转到私聊", callback_data="None", url="t.me/"+self.updater.bot.username)]]
            rp_markup = InlineKeyboardMarkup(rtbutton)
            if self.getplayer(update) is None:
                self.reply("请先开启与bot的私聊", reply_markup=rp_markup)
                return True

            if len(context.args) > 0:
                if not self.isint(context.args[0]) or int(context.args[0]) < 0:
                    return self.errorHandler(update, "参数无效")

            gpid = self.getchatid(update)
            gp = self.forcegetgroup(gpid)
            if len(context.args) > 0:
                newcdid = int(context.args[0])

        elif len(context.args) > 0:
            msg = context.args[0]

            if not self.isint(msg):
                return self.errorHandler(update, "输入无效")

            if int(msg) >= 0:
                newcdid = int(msg)
            else:
                gpid = int(msg)
                gp = self.forcegetgroup(gpid)
                if len(context.args) > 1:
                    if not self.isint(context.args[1]) or int(context.args[1]) < 0:
                        return self.errorHandler(update, "输入无效")
                    newcdid = int(context.args[1])

        if gp is None:
            self.reply(
                "准备创建新卡。\n如果你不知道群id，在群里发送 /getid 即可创建角色卡。\n你也可以选择手动输入群id，请发送群id：")
            if newcdid is None:
                self.addOP(self.getchatid(update), "newcard " +
                           str(update.message.message_id))
            else:
                self.addOP(self.getchatid(update), "newcard " +
                           str(update.message.message_id)+" "+str(newcdid))
            return True

        # 检查(pl)是否已经有卡
        pl = self.forcegetplayer(update)
        plid = pl.id
        if self.hascard(plid, gpid) and pl != gp.kp:
            return self.errorHandler(update, "你在这个群已经有一张卡了！")

        # 符合建卡条件，生成新卡
        # gp is not None
        assert(gpid is not None)

        remsgid = None
        if self.isprivatemsg(update):
            remsgid = update.message.message_id
        else:
            assert(rp_markup)
            self.reply("建卡信息已经私聊发送", reply_markup=rp_markup)

        return self.getnewcard(remsgid, gpid, plid, newcdid)

    @commandCallbackMethod
    def pausegame(self, update: Update, context: CallbackContext) -> bool:
        """暂停游戏。
        游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
        当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
        可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
        继续游戏后会覆盖游戏中的这些属性。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isgroupmsg(update):
            return self.errorHandler(update, "发送群消息暂停游戏")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorHandler(update, "只有KP可以暂停游戏", True)
        if gp.game is None:
            return self.errorHandler(update, "没有进行中的游戏", True)

        gp.pausedgame = gp.game
        gp.game = None
        gp.write()

        self.reply("游戏暂停，用 /continuegame 恢复游戏")
        return True

    @commandCallbackMethod
    def randombkg(self, update: Update, context: CallbackContext) -> bool:
        """生成随机的背景故事。

        获得当前发送者选中的卡，生成随机的背景故事并写入。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。")

        self.reply(card.background.randbackground())
        return True

    @commandCallbackMethod
    def recover(self, update: Update, context: CallbackContext) -> bool:
        """将重伤患者的状态恢复。使用回复或者`@username`作为参数来选择对象恢复。
        回复的优先级高于参数。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorHandler(update, "没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorHandler(update, "没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorHandler(update, "使用回复或@username指定恢复者")
            if not self.isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorHandler(update, "参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorHandler(update, "玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorHandler(update, "找不到该玩家的卡。")

        if card.status != STATUS_SERIOUSLYWOUNDED:
            return self.errorHandler(update, "该角色没有重伤")

        card.status = STATUS_ALIVE
        self.reply("角色已恢复")
        card.write()
        return True

    @commandCallbackMethod
    def reload(self, update: Update, context: CallbackContext) -> bool:
        """重新读取所有文件，只有bot管理者可以使用"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.getmsgfromid(update) != self.ADMIN_ID:
            return self.errorHandler(update, "没有权限", True)

        try:
            self.readall()
            self.construct()
        except:
            return self.errorHandler(update, "读取文件出现问题，请检查json文件！")

        self.reply('重新读取文件成功。')
        return True

    @commandCallbackMethod
    def renewcard(self, update: Update, context: CallbackContext) -> bool:
        """如果卡片是可以discard的状态，使用该指令可以将卡片重置。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if pl.controlling is None:
            return self.errorHandler(update, "没有操作中的卡")
        f = self.checkaccess(pl, pl.controlling)
        if f & CANDISCARD == 0:
            return self.errorHandler(update, "选中的卡不可重置。如果您使用了 /switch 切换操作中的卡，请使用 /switch 切换回要重置的卡")

        pl.controlling.backtonewcard()
        self.reply(pl.controlling.data.datainfo)
        if pl.controlling.data.countless50discard():
            pl.controlling.discard = True
            self.reply(
                "因为有三项属性小于50，如果你愿意的话可以再次点击 /renewcard 来重置这张角色卡。如果停止创建卡，点击 /discard 来放弃建卡。\n设定年龄后则不能再删除这张卡。")
        else:
            pl.controlling.discard = False
        return True

    @commandCallbackMethod
    def roll(self, update: Update, context: CallbackContext):
        """基本的骰子功能。

        只接受第一个空格前的参数`dicename`。
        `dicename`可能是技能名、属性名（仅限游戏中），可能是`3d6`，可能是`1d4+2d10`。
        骰子环境可能是游戏中，游戏外。

        `/roll`：默认1d100。
        `/roll --mdn`骰一个mdn的骰子。
        `/roll --test`仅限游戏中可以使用。对`test`进行一次检定。
        例如，`/roll 力量`会进行一次STR检定。
        `/roll 射击`进行一次射击检定。
        检定心理学时结果只会发送给kp。
        如果要进行一个暗骰，可以输入
        `/roll 暗骰`进行一次检定为50的暗骰，或者
        `/roll 暗骰60`进行一次检定为60的暗骰。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            self.reply(self.commondice("1d100"))  # 骰1d100
            return True

        dicename = context.args[0]

        if self.isprivatemsg(update):
            self.reply(self.commondice(dicename))
            return True

        gp = self.forcegetgroup(update)

        # 检查输入参数是不是一个基础骰子，如果是则直接计算骰子
        if gp.game is None or dicename.find('d') >= 0 or self.isint(dicename):
            if self.isint(dicename) and int(dicename) > 0:
                dicename = "1d"+dicename
            rttext = self.commondice(dicename)
            if rttext == "Invalid input.":
                return self.errorHandler(update, "输入无效")
            self.reply(rttext)
            return True

        if gp.game is None:
            return self.errorHandler(update, "输入无效")
        # 确认不是基础骰子的计算，转到卡检定
        # 获取临时检定
        tpcheck, gp.game.tpcheck = gp.game.tpcheck, 0
        if tpcheck != 0:
            gp.write()

        pl = self.forcegetplayer(update)

        # 获取卡
        if pl != gp.kp:
            gamecard = self.findcardfromgame(gp.game, pl)
        else:
            gamecard = gp.game.kpctrl
            if gamecard is None:
                return self.errorHandler(update, "请用 /switchgamecard 切换kp要用的卡")
        if not gamecard:
            return self.errorHandler(update, "找不到游戏中的卡。")
        if gamecard.status == STATUS_DEAD:
            return self.errorHandler(update, "角色已死亡")
        if gamecard.status == STATUS_PERMANENTINSANE:
            return self.errorHandler(update, "角色已永久疯狂")

        if dicename.encode('utf-8').isalpha():
            dicename = dicename.upper()

        # 找卡完成，开始检定
        test = 0
        if dicename == "侦察":
            dicename = "侦查"
        if dicename in gamecard.skill.allskills():
            test = gamecard.skill.get(dicename)
        elif dicename in gamecard.interest.allskills():
            test = gamecard.interest.get(dicename)
        elif dicename == "母语":
            test = gamecard.data.EDU
        elif dicename == "闪避":
            test = gamecard.data.DEX//2

        elif dicename in gamecard.data.alldatanames:
            test = gamecard.data.__dict__[dicename]
        elif dicename == "力量":
            dicename = "STR"
            test = gamecard.data.STR
        elif dicename == "体质":
            dicename = "CON"
            test = gamecard.data.CON
        elif dicename == "体型":
            dicename = "SIZ"
            test = gamecard.data.SIZ
        elif dicename == "敏捷":
            dicename = "DEX"
            test = gamecard.data.DEX
        elif dicename == "外貌":
            dicename = "APP"
            test = gamecard.data.APP
        elif dicename == "智力" or dicename == "灵感":
            dicename = "INT"
            test = gamecard.data.INT
        elif dicename == "意志":
            dicename = "POW"
            test = gamecard.data.POW
        elif dicename == "教育":
            dicename = "EDU"
            test = gamecard.data.EDU
        elif dicename == "幸运":
            dicename = "LUCK"
            test = gamecard.data.LUCK

        elif dicename in self.skilllist:
            test = self.skilllist[dicename]

        elif dicename[:2] == "暗骰" and (self.isint(dicename[2:]) or len(dicename) == 2):
            if len(dicename) != 2:
                test = int(dicename[2:])
            else:
                test = 50

        else:  # HIT BAD TRAP
            return self.errorHandler(update, "输入无效")

        # 将所有检定修正相加
        test += gamecard.tempstatus.GLOBAL
        if gamecard.hasstatus(dicename):
            test += gamecard.getstatus(dicename)
        test += tpcheck

        if test < 1:
            test = 1
        testval = self.dicemdn(1, 100)[0]
        rttext = dicename+" 检定/出目："+str(test)+"/"+str(testval)+" "

        greatsuccessrule = gp.rule.greatsuccess
        greatfailrule = gp.rule.greatfail

        if (test < 50 and testval >= greatfailrule[2] and testval <= greatfailrule[3]) or (test >= 50 and testval >= greatfailrule[0] and testval <= greatfailrule[1]):
            rttext += "大失败"
        elif (test < 50 and testval >= greatsuccessrule[2] and testval <= greatsuccessrule[3]) or (test >= 50 and testval >= greatsuccessrule[0] and testval <= greatsuccessrule[1]):
            rttext += "大成功"
        elif testval > test:
            rttext += "失败"
        elif testval > test//2:
            rttext += "普通成功"
        elif testval > test//5:
            rttext += "困难成功"
        else:
            rttext += "极难成功"

        if dicename == "心理学" or dicename[:2] == "暗骰":
            if gp.kp is None:
                return self.errorHandler(update, "本群没有KP，请先添加一个KP再试！")

            self.reply(dicename+" 检定/出目："+str(test)+"/???")
            self.sendto(gp.kp, rttext)
        else:
            self.reply(rttext)

        return True

    @commandCallbackMethod
    def sancheck(self, update: Update, context: CallbackContext) -> bool:
        """进行一次sancheck，格式如下：
        `/sancheck checkpass/checkfail`"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "在游戏中才能进行sancheck。")

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数", True)

        checkname = context.args[0]
        if checkname.find("/") == -1:
            return self.errorHandler(update, "将成功和失败的扣除点数用/分开。")

        checkpass, checkfail = checkname.split(sep='/', maxsplit=1)
        if not self.isadicename(checkpass) or not self.isadicename(checkfail):
            return self.errorHandler(update, "无效输入")

        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorHandler(update, "找不到游戏", True)

        pl = self.forcegetplayer(update)
        # KP 进行
        if pl == gp.kp:
            card1 = gp.game.kpctrl
            if card1 is None:
                return self.errorHandler(update, "请先用 /switchgamecard 切换到你的卡")
        else:  # 玩家进行
            card1 = self.findcardfromgame(gp.game, pl)
            if card1 is None:
                return self.errorHandler(update, "找不到卡。")

        rttext = "理智：检定/出目 "
        sanity = card1.attr.SAN
        check = self.dicemdn(1, 100)[0]
        rttext += str(sanity)+"/"+str(check)+" "
        greatfailrule = gp.rule.greatfail
        if (sanity < 50 and check >= greatfailrule[2] and check <= greatfailrule[3]) or (sanity >= 50 and check >= greatfailrule[0] and check <= greatfailrule[1]):  # 大失败
            rttext += "大失败"
            anstype = "大失败"
        elif check > sanity:  # check fail
            rttext += "失败"
            anstype = "失败"
        else:
            rttext += "成功"
            anstype = ""

        rttext += "\n损失理智："
        sanloss, m, n = 0, 0, 0

        if anstype == "大失败":
            if self.isint(checkfail):
                sanloss = int(checkfail)
            else:
                t = checkfail.split("+")
                for tt in t:
                    if self.isint(tt):
                        sanloss += int(tt)
                    else:
                        ttt = tt.split('d')
                        sanloss += int(ttt[0])*int(ttt[1])

        elif anstype == "失败":
            if self.isint(checkfail):
                sanloss = int(checkfail)
            else:
                m, n = checkfail.split("d", maxsplit=1)
                m, n = int(m), int(n)
                sanloss = int(sum(self.dicemdn(m, n)))

        else:
            if self.isint(checkpass):
                sanloss = int(checkpass)
            else:
                m, n = checkpass.split("d", maxsplit=1)
                m, n = int(m), int(n)
                sanloss = int(sum(self.dicemdn(m, n)))

        card1.attr.SAN -= sanloss
        rttext += str(sanloss)+"\n"
        if card1.attr.SAN <= 0:
            card1.attr.SAN = 0
            card1.status = STATUS_PERMANENTINSANE
            rttext += "陷入永久疯狂，快乐撕卡~\n"

        elif sanloss > (card1.attr.SAN+sanloss)//5:
            rttext += "一次损失五分之一以上理智，进入不定性疯狂状态。\n"
            # TODO 处理角色的疯狂状态
        elif sanloss >= 5:
            rttext += "一次损失5点或以上理智，可能需要进行智力（灵感）检定。\n"

        self.reply(rttext)
        card1.write()
        return True

    @commandCallbackMethod
    def setage(self, update: Update, context: CallbackContext):
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "发送私聊消息设置年龄。", True)

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。")

        if card.info.age >= 17 and card.info.age <= 99:
            return self.errorHandler(update, "已经设置过年龄了。")

        if len(context.args) == 0:
            self.reply("请输入年龄：")
            self.addOP(self.getchatid(update), "setage")
            return True

        age = context.args[0]
        if not self.isint(age):
            return self.errorHandler(update, "输入无效")

        age = int(age)
        return self.cardsetage(update, card, age)

    @commandCallbackMethod
    def setasset(self, update: Update, context: CallbackContext) -> bool:
        """设置你的角色卡的资金或财产，一段文字描述即可。`/setasset`"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        card = self.forcegetplayer(update).controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。")

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数")

        card.setassets(' '.join(context.args))
        self.reply("设置资金成功")
        return True

    @commandCallbackMethod
    def setbkg(self, update: Update, context: CallbackContext) -> bool:
        """设置背景信息。

        指令格式如下：
        `/setbkg --bkgroundname --bkgroudinfo...`

        其中第一个参数是背景的名称，只能是下面几项之一：
        `description`故事、
        `faith`信仰、
        `vip`重要之人、
        `viplace`意义非凡之地、
        `preciousthing`珍视之物、
        `speciality`性格特质、
        `dmg`曾经受过的伤、
        `terror`恐惧之物、
        `myth`神秘学相关物品、
        `thirdencounter`第三类接触。

        第二至最后一个参数将被空格连接成为一段文字，填入背景故事中。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if len(context.args) <= 1:
            return self.errorHandler(update, "参数不足", True)

        card = pl.controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。", True)

        if context.args[0] not in card.background.__dict__ or not type(card.background.__dict__[context.args[0]]) is str:
            rttext = "找不到这项背景属性，背景属性只支持以下参数：\n"
            for keys in card.background.__dict__:
                if not type(card.background.__dict__[keys]) is str:
                    continue
                rttext += keys+"\n"
            return self.errorHandler(update, rttext)

        card.background.__dict__[context.args[0]] = ' '.join(context.args[1:])
        card.write()
        self.reply("背景故事添加成功")
        return True

    @commandCallbackMethod
    def setjob(self, update: Update, context: CallbackContext) -> bool:
        """设置职业。

        `/setjob`生成按钮来设定职业。点击职业将可以查看对应的推荐技能，
        以及对应的信用范围和主要技能点计算方法。再点击确认即可确认选择该职业。
        确认了职业就不能再更改。

        `/setjob --job`将职业直接设置为给定职业。
        如果允许非经典职业，需要参数`self.IGNORE_JOB_DICT`为`True`，
        否则不能设置。如果设置了非经典职业，技能点计算方法为教育乘4。

        在力量、体质等属性减少值计算完成后才可以设置职业。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "发送私聊消息设置职业。")

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorHandler(update, "找不到卡。")
        if card.info.age == -1:
            return self.errorHandler(update, "年龄未设置")
        if card.data.datadec is not None:
            return self.errorHandler(update, "属性下降未设置完成")
        if card.info.job != "":
            return self.errorHandler(update, "职业已经设置过了")

        if len(context.args) == 0:
            rtbuttons = self.makejobbutton()
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            # 设置职业的任务交给函数buttonjob
            self.reply(
                "请选择职业查看详情：", reply_markup=rp_markup)
            return True

        jobname = context.args[0]
        if not IGNORE_JOB_DICT and jobname not in self.self.joblist:
            return self.errorHandler("该职业无法设置")

        card.info.job = jobname
        if jobname not in self.self.joblist:
            self.reply(
                "这个职业不在职业表内，你可以用'/addskill 技能名 点数 (main/interest)'来选择技能！如果有interest参数，该技能将是兴趣技能并消耗兴趣技能点。")
            card.skill.points = int(card.data.EDU*4)
            card.write()
            return True

        for skillname in self.joblist[jobname][3:]:
            card.suggestskill.set(skillname, self.getskilllevelfromdict(
                card, skillname))
        self.reply("用 /addskill 来添加技能。")
        # This trap should not be hit
        if not self.generatePoints(card):
            return self.errorHandler(update, "生成主要技能点出现错误")
        return True

    @commandCallbackMethod
    def setname(self, update: Update, context: CallbackContext) -> bool:
        """设置角色卡姓名。

        `/setname --name`：直接设定姓名。
        `/setname`：bot将等待输入姓名。
        设置的姓名可以带有空格等字符。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        card1 = self.forcegetplayer(update).controlling
        if card1 is None:
            return self.errorHandler(update, "找不到卡。")

        if len(context.args) == 0:
            if self.isprivatemsg(update):
                self.addOP(self.getchatid(update), "setname")
            else:
                self.addOP(self.getchatid(update),
                           "setname "+str(card1.playerid))
            self.reply("请输入姓名：")
            return True

        self.nameset(card1, ' '.join(context.args))
        self.reply("角色的名字已经设置为"+card1.info.name+"。")
        return True

    @commandCallbackMethod
    def setrule(self, update: Update, context: CallbackContext) -> bool:
        """设置游戏的规则。
        一个群里游戏有自动生成的默认规则，使用本指令可以修改这些规则。

        `/setrule --args`修改规则。`--args`格式如下：

        `rulename1:str --rules1:List[int] rulename2:str --rule2:List[int] ...`

        一次可以修改多项规则。
        有可能会出现部分规则设置成功，但部分规则设置失败的情况，
        查看返回的信息可以知道哪些部分已经成功修改。

        规则的详细说明：

        skillmax：接收长度为3的数组，记为r。`r[0]`是一般技能上限，
        `r[1]`是个别技能的上限，`r[2]`表示个别技能的个数。

        skillmaxAged：年龄得到的技能上限增加设定。
        接收长度为4的数组，记为r。`r[0]`至`r[2]`同上，
        但仅仅在年龄大于`r[3]`时开启该设定。`r[3]`等于100代表不开启该设定。

        skillcost：技能点数分配时的消耗。接收长度为偶数的数组，记为r。
        若i为偶数（或0），`r[i]`表示技能点小于`r[i+1]`时，
        需要分配`r[i]`点点数来获得1点技能点。r的最后一项必须是100。
        例如：`r=[1, 80, 2, 100]`，则从10点升至90点需要花费`1*70+2*10=90`点数。

        greatsuccess：大成功范围。接收长度为4的数组，记为r。
        `r[0]-r[1]`为检定大于等于50时大成功范围，否则是`r[2]-r[3]`。

        greatfail：大失败范围。同上。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "请在群内用该指令设置规则")

        gp = self.forcegetgroup(update)

        if not self.isfromkp(update):
            return self.errorHandler(update, "没有权限", True)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数", True)

        gprule = gp.rule

        ruledict: Dict[str, List[int]] = {}

        i = 0
        while i < len(context.args):
            j = i+1
            tplist: List[int] = []
            while j < len(context.args):
                if self.isint(context.args[j]):
                    tplist.append(int(context.args[j]))
                    j += 1
                else:
                    break
            ruledict[context.args[i]] = tplist
            i = j
        del i, j

        msg, ok = gprule.changeRules(ruledict)
        if not ok:
            return self.errorHandler(update, msg)

        self.reply(msg)
        return True

    @commandCallbackMethod
    def setsex(self, update: Update, context: CallbackContext) -> bool:
        """设置性别。比较明显的性别词汇会被自动分类为男性或女性，其他的性别也可以设置。
        `/setsex 性别`：直接设置。
        `/setsex`：使用交互式的方法设置性别。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if pl.controlling is None:
            return self.errorHandler(update, "找不到卡。", True)
        if len(context.args) == 0:
            if self.isgroupmsg(update):
                gpid = self.getchatid(update)
                self.addOP(gpid, "setsex "+str(pl.id))
                self.reply("请输入性别：")
                return True

            rtbuttons = [[InlineKeyboardButton("男性", callback_data=self.IDENTIFIER+" setsex male"), InlineKeyboardButton(
                "女性", callback_data=self.IDENTIFIER+" setsex female"), InlineKeyboardButton("其他", callback_data=self.IDENTIFIER+" setsex other")]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply("请选择性别：", reply_markup=rp_markup)
            return True

        card = pl.controlling
        self.cardsetsex(update, card, context.args[0])
        return True

    @commandCallbackMethod
    def show(self, update: Update, context: CallbackContext) -> bool:
        """显示目前操作中的卡片的信息。私聊时默认显示游戏外的卡，群聊时优先显示游戏内的卡。
        （如果有多张卡，用`/switch`切换目前操作的卡。）
        `/show`：显示最基础的卡片信息；
        `/show card`：显示当前操作的整张卡片的信息；
        `/show --attrname`：显示卡片的某项具体属性。
        （回复某人消息）`/show card或--attrname`：同上，但显示的是被回复者的卡片的信息。

        例如，`/show skill`显示主要技能，
        `/show interest`显示兴趣技能。
        如果要显示主要技能点和兴趣技能点，请使用`mainpoints`, `intpoints`作为`arg`，而不要使用points。
        如果当前卡中没有这个属性，则无法显示。
        可以显示的属性例子：
        `STR`,`description`,`SAN`,`MAGIC`,`name`,`item`,`job`"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        rppl = self.getreplyplayer(update)
        rpcard: Optional[GameCard] = None

        if rppl is None and len(context.args) > 0:
            if self.isint(context.args[0]):
                rppl = self.getplayer(int(context.args[0]))
            if rppl is not None:
                context.args = context.args[1:]

        if rppl is not None:
            gp = self.forcegetgroup(update)
            rpcard = self.findcardfromgroup(rppl, gp)
            if rpcard is None:
                return self.errorHandler(update, "该玩家在本群没有卡")

        card = rpcard if rpcard is not None else None
        if card is None:
            if self.isgroupmsg(update):
                gp = self.forcegetgroup(update)
                card = self.findcardfromgroup(pl, gp)
                if card is None:
                    return self.errorHandler(update, "请先在本群创建卡")
            else:
                card = pl.controlling
                if card is None:
                    return self.errorHandler(update, "请先创建卡，或者使用 /switch 选中一张卡")

        game = card.group.game if card.group.game is not None else card.group.pausedgame

        rttext = ""

        if game is not None and self.isgroupmsg(update):
            if card.id in game.cards:
                rttext = "显示游戏中的卡：\n"
                card = game.cards[card.id]

        if rttext == "":
            rttext = "显示游戏外的卡：\n"

        if not self.checkaccess(pl, card) & CANREAD:
            return self.errorHandler(update, "没有权限")

        if card.type != PLTYPE and self.isgroupmsg(update):
            return self.errorHandler(update, "非玩家卡片不可以在群内显示")

        if len(context.args) == 0:
            self.reply(card.basicinfo())
            return True

        if context.args[0] == "card":
            self.reply(str(card))
            return True

        if context.args[0] == "mainpoints":
            ans = card.skill.show("points")
        elif context.args[0] == "intpoints":
            ans = card.interest.show("points")
        elif context.args[0] == "points":
            return self.errorHandler(update, "请用mainpoints或intpoints来显示")
        else:
            ans = card.show(context.args[0])

        if ans == "找不到该属性":
            return self.errorHandler(update, "找不到该属性")

        if ans == "":
            self.reply(rttext+"无")
        else:
            self.reply(rttext+ans)
        return True

    @commandCallbackMethod
    def showcard(self, update: Update, context: CallbackContext) -> bool:
        """显示某张卡的信息。

        `/showcard --cardid (card/--attrname)`: 显示卡id为`cardid`的卡片的信息。
        如果第二个参数是`card`，显示整张卡；否则，显示这一项数据。
        如果第二个参数不存在，显示卡片基本信息。
        群聊时使用该指令，优先查看游戏内的卡片。

        显示前会检查发送者是否有权限显示这张卡。在这些情况下，无法显示卡：

        群聊环境：显示非本群的卡片，或者显示本群的type不为PL的卡片；

        私聊环境：显示没有查看权限的卡片。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数")
        if not self.isint(context.args[0]) or int(context.args[0]) < 0:
            return self.errorHandler(update, "卡id参数无效", True)
        cdid = int(context.args[0])

        rttext: str = ""
        cardi: Optional[GameCard] = None

        if self.isgroupmsg(update):
            cardi = self.getgamecard(cdid)
            if cardi is not None:
                rttext = "显示游戏内的卡片\n"

        if cardi is None:
            cardi = self.getcard(cdid)

            if cardi is None:
                return self.errorHandler(update, "找不到这张卡")

        if rttext == "":
            rttext = "显示游戏外的卡片\n"

        # 检查是否有权限
        if self.isprivatemsg(update):

            pl = self.forcegetplayer(update)

            if self.checkaccess(pl, cardi) & CANREAD == 0:
                return self.errorHandler(update, "没有权限")
        else:
            if (cardi.groupid != -1 and cardi.group != self.forcegetgroup(update)) or cardi.type != PLTYPE:
                return self.errorHandler(update, "没有权限", True)

        # 开始处理
        if len(context.args) >= 2:
            if context.args[1] == "card":
                self.reply(rttext+str(cardi))
            else:
                ans = cardi.show(context.args[1])
                if ans == "找不到该属性":
                    return self.errorHandler(update, ans)

                self.reply(rttext+ans)
            return True

        # 显示基本属性
        self.reply(rttext+cardi.basicinfo())
        return True

    @commandCallbackMethod
    def showids(self, update: Update, context: CallbackContext) -> bool:
        """用于显示卡的名字-id对。群聊时使用只能显示游戏中PL的卡片id。

        `showids`: 显示游戏外的卡id。

        `showids game`: 显示游戏中的卡id。

        私聊时，只有KP可以使用该指令，显示的是该玩家作为KP的所有群的id对，按群分开。
        两个指令同上，但结果将更详细，结果会包括KP主持游戏的所有群的卡片。
        KP使用时有额外的一个功能：

        `showids kp`: 返回KP游戏中控制的所有卡片id"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            gp = self.forcegetgroup(update)

            out = bool(len(context.args) == 0) or bool(
                context.args[0] != "game")

            if not out and gp.game is None and gp.pausedgame is None:
                return self.errorHandler(update, "没有进行中的游戏")

            hascard = False
            if out:
                cdd = gp.cards
            else:
                game = gp.game if gp.game is not None else gp.pausedgame
                cdd = game.cards

            rttext = "卡id：卡名\n"
            for card in cdd.values():
                if card.type != PLTYPE:
                    continue
                hascard = True
                rttext += str(card.id)+"："+card.getname()+"\n"

            if not hascard:
                return self.errorHandler(update, "本群没有卡")

            self.reply(rttext)
            return True

        # 下面处理私聊消息
        kp = self.forcegetplayer(update)
        if not self.searchifkp(kp):
            return self.errorHandler(update, "没有权限")

        searchtype = 0
        if len(context.args) > 0:
            if context.args[0] == "game":
                searchtype = 1
            elif context.args[0] == "kp":
                searchtype = 2
        allempty = True
        for gp in kp.kpgroups.values():
            game = gp.game if gp.game is not None else gp.pausedgame
            if game is None and searchtype > 0:
                continue

            if searchtype > 0:
                cdd = game.cards
            else:
                cdd = gp.cards

            hascard = False
            rttext = "群id："+str(gp.id)+"，群名："+gp.getname()+"，id信息如下\n"
            rttext += "卡id：卡名\n"
            for card in cdd.values():
                if searchtype == 2 and card.player != kp:
                    continue
                allempty = False
                hascard = True
                rttext += str(card.id)+"："+card.getname()+"\n"

            if not hascard:
                continue

            self.reply(rttext)
            time.sleep(0.2)

        if allempty:
            return self.errorHandler(update, "没有可显示的卡。")

        return True

    @commandCallbackMethod
    def showjoblist(self, update: Update, context: CallbackContext) -> None:
        """显示职业列表"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if not self.isprivatemsg(update):
            return self.errorHandler(update, "请在私聊中使用该指令")

        rttext = "职业列表："
        counts = 0

        for job in self.joblist:
            jobinfo = self.joblist[job]

            rttext += job+f"：\n信用范围 [{str(jobinfo[0])},{str(jobinfo[1])}]\n"

            rttext += "技能点计算方法："
            calcd: Dict[str, int] = jobinfo[2]
            calcmeth = " 加 ".join("或".join(x.split('_')) +
                                  "乘"+str(calcd[x]) for x in calcd)
            rttext += calcmeth+"\n"

            rttext += "主要技能："+"、".join(x for x in jobinfo[3:])+"\n"

            counts += 1

            if counts == 3:
                self.reply(rttext)
                rttext = ""
                counts = 0
                time.sleep(0.2)

    @commandCallbackMethod
    def showkp(self, update: Update, context: CallbackContext) -> bool:
        """这一指令是为KP设计的。不能在群聊中使用。

        `/showkp game --groupid`: 显示发送者在某个群主持的游戏中所有的卡
        `/showkp card`: 显示发送者作为KP控制的所有卡
        `/showkp group --groupid`: 显示发送者是KP的某个群内的所有卡"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "使用该指令请发送私聊消息", True)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数")

        arg = context.args[0]
        if arg == "group":
            kp = self.forcegetplayer(update)
            # args[1] should be group id
            if len(context.args) < 2:
                return self.errorHandler(update, "需要群ID")
            gpid = context.args[1]
            if not self.isint(gpid) or int(gpid) >= 0:
                return self.errorHandler(update, "无效ID")

            gpid = int(gpid)
            if gpid < 0 or self.getgp(gpid) is None or self.getgp(gpid).kp != kp:
                return self.errorHandler(update, "这个群没有卡或没有权限")

            gp: Group = self.getgp(gpid)
            ans: List[GameCard] = []
            for card in kp.cards.values():
                if card.group != gp:
                    continue
                ans.append(card)

            if len(ans) == 0:
                return self.errorHandler(update, "该群没有你的卡")

            for i in ans:
                self.reply(str(i))
                time.sleep(0.2)
            return True

        if arg == "game":
            kp = self.forcegetplayer(update)

            if len(context.args) < 2:
                return self.errorHandler(update, "需要群ID")
            gpid = context.args[1]
            if not self.isint(gpid) or int(gpid) >= 0:
                return self.errorHandler(update, "无效群ID")

            gp = self.getgp(gpid)
            if gp is None or (gp.game is None and gp.pausedgame is None):
                return self.errorHandler(update, "没有找到游戏")

            if gp.kp != kp:
                return self.errorHandler(update, "你不是这个群的kp")

            game = gp.game if gp.game is not None else gp.pausedgame

            hascard = False
            for i in game.cards.values():
                if i.player != kp:
                    continue
                hascard = True
                self.reply(str(i))
                time.sleep(0.2)

            return True if hascard else self.errorHandler(update, "你没有控制的游戏中的卡")

        if arg == "card":
            kp = self.forcegetplayer(update)

            hascard = False
            for card in kp.cards.values():
                if card.group.kp != kp:
                    continue
                hascard = True
                self.reply(str(card))
                time.sleep(0.2)

            return True if hascard else self.errorHandler(update, "你没有控制NPC卡片")

        return self.errorHandler(update, "无法识别的参数")

    @commandCallbackMethod
    def showmycards(self, update: Update, context: CallbackContext) -> bool:
        """显示自己所持的卡。群聊时发送所有在本群可显示的卡片。私聊时发送所有卡片。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if len(pl.cards) == 0:
            return self.errorHandler(update, "你没有任何卡。")

        if self.isgroupmsg(update):
            # 群消息，只发送本群的卡
            gp = self.forcegetgroup(update)
            rttexts: List[str] = []

            for card in pl.cards.values():
                if card.group != gp or card.type != PLTYPE:
                    continue
                rttexts.append(str(card))

            if len(rttexts) == 0:
                return self.errorHandler(update, "找不到本群的卡。")

            for x in rttexts:
                self.reply(x)
                time.sleep(0.2)
            return True

        # 私聊消息，发送全部卡
        for card in pl.cards.values():
            self.reply(str(card))
            time.sleep(0.2)
        return True

    @commandCallbackMethod
    def showrule(self, update: Update, context: CallbackContext) -> bool:
        """显示当前群内的规则。
        如果想了解群规则的详情，请查阅setrule指令的帮助：
        `/help setrule`"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "请在群内查看规则")

        gp = self.forcegetgroup(update)
        rule = gp.rule

        self.reply(str(rule))
        return True

    @commandCallbackMethod
    def showskilllist(self, update: Update, context: CallbackContext) -> None:
        """显示技能列表"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        rttext = "技能：基础值\n"
        rttext += "母语：等于EDU\n"
        rttext += "闪避：等于DEX的一半\n"

        for skill in self.skilllist:
            rttext += skill+"："+str(self.skilllist[skill])+"\n"

        self.reply(rttext)

    @commandCallbackMethod
    def showuserlist(self, update: Update, context: CallbackContext) -> bool:
        """显示所有信息。非KP无法使用这一指令。
        群聊时不可以使用该指令。
        Bot管理者使用该指令，bot将逐条显示群-KP信息、
        全部的卡信息、游戏信息。KP使用时，只会显示与TA相关的这些消息。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):  # Group msg: do nothing, even sender is USER or KP
            return self.errorHandler(update, "没有这一指令", True)

        user = self.forcegetplayer(update)

        if not self.searchifkp(user) and user.id != ADMIN_ID:
            return self.errorHandler(update, "没有这一指令")

        # 群
        for gp in self.groups.values():
            if self.checkaccess(user, gp) & (GROUPKP | BOTADMIN) != 0:
                self.reply(str(gp))
                time.sleep(0.2)

        # 玩家
        for pl in self.players.values():
            if pl == user or user.id == ADMIN_ID:
                self.reply(str(pl))
                time.sleep(0.2)

        # 卡片
        for card in self.cards.values():
            if self.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
                self.reply(str(card))
                time.sleep(0.2)

        # 游戏中卡片
        for card in self.gamecards.values():
            if self.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
                self.reply(str(card))
                time.sleep(0.2)

        return True

    @commandCallbackMethod
    def start(self, update: Update, context: CallbackContext) -> None:
        """显示bot的帮助信息"""
        self.reply(self.HELP_TEXT)

    @commandCallbackMethod
    def startgame(self, update: Update, context: CallbackContext) -> bool:
        """开始一场游戏。

        这一指令将拷贝本群内所有卡，之后将用拷贝的卡片副本进行游戏，修改属性将不会影响到游戏外的原卡属性。
        如果要正常结束游戏，使用`/endgame`可以将游戏的角色卡数据覆写到原本的数据上。
        如果要放弃这些游戏内进行的修改，使用`/abortgame`会直接删除这些副本副本。
        `/startgame`：正常地开始游戏，对所有玩家的卡片（type为PL）进行卡片检查。
        `/startgame ignore`跳过开始游戏的检查，直接开始游戏。

        开始后，bot会询问是否保存聊天文本数据。此时回复cancel或者取消，即可取消开始游戏。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "游戏需要在群里进行")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorHandler(update, "游戏只能由KP发起", True)
        if gp.game is not None:
            return self.errorHandler(update, "游戏已经在进行中")

        if gp.pausedgame is not None:
            return self.continuegame(update, context)  # 检测到游戏暂停中，直接继续

        # 开始验证
        if not(len(context.args) > 0 and context.args[0] == "ignore"):
            if len(gp.cards) == 0:
                return self.errorHandler(update, "本群没有任何卡片，无法开始游戏")
            canstart = True
            for card in gp.cards.values():
                card.generateOtherAttributes()
                if card.type != PLTYPE:
                    continue
                ck = card.check()
                if ck != "":
                    canstart = False
                    self.reply(ck)

            if not canstart:
                return False

        self.reply(
            "准备开始游戏，是否需要记录聊天文本？如果需要记录文本，请回复'记录'。回复'cancel'或者'取消'来取消游戏。")
        self.addOP(gp.id, "startgame")
        return True

    @commandCallbackMethod
    def switch(self, update: Update, context: CallbackContext):
        """切换目前操作的卡。
        注意，这不是指kp在游戏中的多张卡之间切换，如果kp要切换游戏中骰骰子的卡，请参见指令`/switchgamecard`。
        玩家只能修改目前操作的卡的基本信息，例如：年龄、性别、背景、技能点数等。
        `/switch`：生成按钮来切换卡。
        `/switch --cdid`切换至id为`cdid`的卡。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "对bot私聊来切换卡。")

        pl = self.forcegetplayer(update)

        if len(pl.cards) == 0:
            return self.errorHandler(update, "你没有任何卡。")

        if len(pl.cards) == 1:
            if pl.controlling is not None:
                return self.errorHandler(update, "你只有一张卡，无需切换。")

            for card in pl.cards.values():
                pl.controlling = card
                break
            pl.write()

            self.reply(
                f"你只有一张卡，自动控制这张卡。现在操作的卡：{pl.controlling.getname()}")
            return True

        if len(context.args) > 0:
            if not self.isint(context.args[0]):
                return self.errorHandler(update, "输入无效。")
            cdid = int(context.args[0])
            if cdid < 0:
                return self.errorHandler(update, "卡片id为正数。")
            if cdid not in pl.cards:
                return self.errorHandler(update, "找不到这个id的卡。")

            pl.controlling = pl.cards[cdid]
            pl.write()

            self.reply(
                f"现在操作的卡：{pl.controlling.getname()}")
            return True

        # 多个选项。创建按钮
        rtbuttons = [[]]
        for card in pl.cards.values():
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])

            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
                card.getname(), callback_data=self.IDENTIFIER+" switch "+str(card.id)))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply("请选择要切换控制的卡：", reply_markup=rp_markup)
        # 交给按钮来完成
        return True

    @commandCallbackMethod
    def switchgamecard(self, update: Update, context: CallbackContext):
        """用于KP切换游戏中进行对抗时使用的NPC卡片。

        （仅限私聊时）`/switchgamecard --groupid`：创建按钮，让KP选择要用的卡。
        （私聊群聊皆可）`/switchgamecard --cardid`：切换到id为cardid的卡并控制。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if len(context.args) == 0:
            return self.errorHandler(update, "需要参数")

        if not self.isint(context.args[0]):
            return self.errorHandler(update, "参数无效")

        pl = self.forcegetplayer(update)
        iid = int(context.args[0])
        if iid >= 0:
            cdid = iid
            if cdid not in pl.gamecards:
                return self.errorHandler(update, "你没有这个id的游戏中的卡")

            card = pl.gamecards[cdid]
            game: GroupGame = card.group.game if card.group.game is not None else card.group.pausedgame
            assert(game is not None)
            if game.kp != pl:
                return self.errorHandler(update, "你不是该卡对应群的kp")
            game.kpctrl = card
            game.write()
            return True

        gpid = iid

        if self.isgroupmsg(update):
            return self.errorHandler(update, "请直接指定要切换的卡id，或者向bot发送私聊消息切换卡！")

        gp = self.getgp(gpid)
        if gp is None:
            return self.errorHandler(update, "找不到该群")

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorHandler(update, "该群没有在进行游戏")
        if game.kp != pl:
            return self.errorHandler(update, "你不是kp")

        rtbuttons = [[]]
        for card in game.cards.values():
            if card.player != pl:
                continue

            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])

            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
                card.getname(), callback_data=self.IDENTIFIER+" switchgamecard "+str(card.id)))

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply("请选择要切换控制的卡：", reply_markup=rp_markup)
        # 交给按钮来完成
        return True

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
            return self.errorHandler(update, "没有参数", True)
        if not self.isgroupmsg(update):
            return self.errorHandler(update, "在群里设置临时检定")
        if not self.isint(context.args[0]):
            return self.errorHandler(update, "临时检定修正应当是整数", True)

        gp = self.forcegetgroup(update)
        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorHandler(update, "没有进行中的游戏", True)
        if game.kp != self.forcegetplayer(update):
            return self.errorHandler(update, "KP才可以设置临时检定", True)

        if len(context.args) >= 3 and self.isint(context.args[1]) and 0 <= int(context.args[1]):
            card = self.getgamecard(int(context.args[1]))
            if card is None or card.group != gp:
                return self.errorHandler(update, "找不到这张卡")

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
    def transferkp(self, update: Update, context: CallbackContext) -> bool:
        """转移KP权限，只有群管理员可以使用这个指令。
        当前群没有KP时或当前群KP为管理员时，无法使用。

        `/transferkp --kpid`：将当前群KP权限转移到某个群成员。
        如果指定的`kpid`不在群内则无法设定。

        `/transferkp`：将当前群KP权限转移到自身。

        `/trasferkp`(reply to someone)：将kp权限转移给被回复者。"""

        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isprivatemsg(update):
            return self.errorHandler(update, "发送群消息强制转移KP权限")

        gp = self.getgp(update)
        pl = self.getplayer(update)
        f = self.checkaccess(pl, gp)

        if not f & GROUPADMIN:
            return self.errorHandler(update, "没有权限", True)

        if gp.kp is None:
            return self.errorHandler(update, "没有KP", True)

        if self.checkaccess(gp.kp, gp) & GROUPADMIN:
            return self.errorHandler(update, "KP是管理员，无法转移")

        # 获取newkp
        newkpid: int
        if len(context.args) != 0:
            if not self.isint(context.args[0]):
                return self.errorHandler(update, "参数需要是整数", True)
            newkp = self.forcegetplayer(int(context.args[0]))
        else:
            t = self.getreplyplayer(update)
            newkp = t if t is not None else self.forcegetplayer(update)

        if newkp == gp.kp:
            return self.errorHandler(update, "原KP和新KP相同", True)

        if not self.changeKP(gp, newkp):
            return self.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发

        return True

    @commandCallbackMethod
    def trynewcard(self, update: Update, context: CallbackContext) -> bool:
        """测试建卡，用于熟悉建卡流程。
        测试创建的卡一定可以删除。
        创建新卡指令的帮助见`/help newcard`，
        对建卡过程有疑问，见 `/createcardhelp`。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if self.isgroupmsg(update):
            return self.errorHandler(update, "发送私聊消息创建角色卡。")

        gp = self.getgp(-1)
        if gp is None:
            gp = self.creategp(-1)
            gp.kp = self.forcegetplayer(ADMIN_ID)

        return self.getnewcard(update.message.message_id, -1, self.getchatid(update))

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().textHandler(update, context)

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().photoHandler(update, context)

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().buttonHandler(update, context)
