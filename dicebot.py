import time
from typing import Dict, KeysView, List, Union, overload

from telegram import Message
from telegram.error import BadRequest, ChatMigrated, Unauthorized
from telegram.ext import CallbackContext

from basebot import baseBot
from gameclass import *
from utils import *


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

        self.operation: Dict[int, str] = {}
        self.addjobrequest: Dict[int, Tuple[str, list]] = {}
        self.addskillrequest: Dict[int, Tuple[str, int]] = {}
        self.migratefrom: Optional[int] = None
        self.migrateto: Optional[int] = None
        self.skillpages: List[List[str]]
        self.MANUALTEXTS: List[str] = []

    def botstart(self) -> None:
        self.readall()  # 先执行
        self.construct()  # 后执行
        super().botstart()

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

    @staticmethod
    def isingroup(gp: Group, pl: Player) -> bool:
        """查询某个pl是否在群里"""
        if gp.chat is None:
            return False
        try:
            gp.chat.get_member(user_id=pl.id)
        except Exception:
            return False
        return True

    @staticmethod
    def ispladmin(gp: Group, pl: Player) -> bool:
        """检测pl是不是gp的管理员"""
        for i in range(5):
            try:
                admins = gp.chat.get_administrators()
            except Exception:
                continue
            break
        for admin in admins:
            if admin.user.id == pl.id:
                return True
        return False

    def findcard(self, plid: int) -> Optional[GameCard]:
        """输入一个player的id，返回该player当前选择中的卡"""
        pl = self.getplayer(plid)
        if not pl:
            return None
        return pl.controlling

    def getskilllevelfromdict(self, card1: GameCard, key: str) -> int:
        """从技能表中读取的技能初始值。

        如果是母语和闪避这样的与卡信息相关的技能，用卡信息来计算初始值"""
        if key in self.skilllist:
            return self.skilllist[key]
        if key == "母语":
            return card1.data.EDU
        if key == "闪避":
            return card1.data.DEX//2
        return -1

    def makeIntButtons(self, lower: int, upper: int, keystr1: str, keystr2: str, step: int = 5, column: int = 4) -> List[list]:
        """返回一个InlineKeyboardButton组成的二维列表。按钮的显示文本是整数。
        `lower`表示最小值，`upper`表示最大值，均是按钮返回结果的一部分。
        `keystr1`, `keystr2`是`callback_data`的内容，按钮的`callback_data`结构为：
        ```
        keystr1+" "+keystr2+" "+str(integer)
        ```
        `step`参数表示按钮会遍历大于`lower`但小于`upper`的所有按钮的间隔。
        `column`参数表示返回的二维列表每行最多有多少个按钮。"""
        if lower > upper:
            upper = lower

        IDENTIFIER = self.IDENTIFIER
        rtbuttons = [[]]
        if (lower//step)*step != lower:
            rtbuttons[0].append(InlineKeyboardButton(
                str(lower), callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(lower)))
            t = step+(lower//step)*step
        else:
            t = lower
        for i in range(t, upper, step):
            if len(rtbuttons[len(rtbuttons)-1]) == column:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(i),
                                                                    callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(i)))
        if len(rtbuttons[len(rtbuttons)-1]) == column:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(str(upper),
                                                                callback_data=IDENTIFIER+" "+keystr1+" "+keystr2+" "+str(upper)))
        return rtbuttons

    # def findgame(self, gpid: int) -> Optional[GroupGame]:
    #     """接收一个groupid，返回对应的GroupGame对象"""
    #     gp = self.getgp(gpid)
    #     if not gp:
    #         return None
    #     return gp.game

    @staticmethod
    def findcardfromgame(game: GroupGame, pl: Player) -> GameCard:
        """从`game`中返回对应的`plid`的角色卡"""
        for i in pl.gamecards.values():
            if i.group == game.group:
                return i
        return None

    @staticmethod
    def findcardfromgroup(pl: Player, gp: Group) -> Optional[GameCard]:
        """返回pl在gp中的其中一张卡，无法返回多张卡"""
        for i in pl.cards.values():
            if i.group == gp:
                return i
        return None

    # @staticmethod
    # def findcardfromgamewithid(game: GroupGame, cdid: int) -> GameCard:
    #     """从`game`中返回`id`为`cdid`的角色卡"""
    #     return game.cards[cdid] if cdid in game.cards else None

    def addskill0(self, card1: GameCard) -> bool:
        """表示指令/addskill 中没有参数的情况。
        创建技能按钮来完成技能的添加。
        因为兴趣技能过多，使用可以翻页的按钮列表。"""
        rtbuttons = [[]]
        card1.player.renew(self.updater)
        pl = card1.player
        # If card1.skill.points is 0, turn to interest.
        # Then it must be main skill. After all main skills are added, add interest skills.
        if card1.skill.points > 0:
            # Increase skills already added, because sgskill is empty
            if len(list(card1.suggestskill.allskills())) == 0:
                # GOOD TRAP: cgmainskill
                for keys in card1.skill.allskills():
                    if keys == "points":
                        continue
                    if len(rtbuttons[len(rtbuttons)-1]) == 4:
                        rtbuttons.append([])
                    rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys +
                                                                            ": "+str(card1.skill.get(keys)), callback_data=self.IDENTIFIER+" "+"cgmainskill "+keys))
                rp_markup = InlineKeyboardMarkup(rtbuttons)
                self.sendto(pl, "剩余点数："+str(
                    card1.skill.points)+"\n请选择一项主要技能用于增加技能点", rpmarkup=rp_markup)
                return True
            # GOOD TRAP: addsgskill
            for keys in card1.suggestskill.allskills():
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(keys+": " +
                                                                        str(card1.suggestskill.get(keys)), callback_data=self.IDENTIFIER+" "+"addsgskill "+keys))
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.sendto(pl, "剩余点数："+str(
                card1.skill.points)+"\n请选择一项主要技能", rpmarkup=rp_markup)
            return True
        # turn to interest.
        if card1.interest.points <= 0:  # HIT BAD TRAP
            self.sendto(pl, "你已经没有多余的点数了，如果需要重新设定某项具体技能的点数，用 '/addskill 技能名'")
            return False
        # GOOD TRAP: add interest skill.
        # 显示第一页，每个参数后面带一个当前页码标记
        rttext, rtbuttons = self.showskillpages(0, card1)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.sendto(pl, rttext, rpmarkup=rp_markup)
        return True

    @overload
    def checkaccess(self, pl: Player, card: GameCard) -> int:
        ...

    @overload
    def checkaccess(self, pl: Player, gp: Group) -> int:
        ...

    def checkaccess(self, pl: Player, thing: Union[GameCard, Group]) -> int:
        """用FLAG给出玩家对角色卡或群聊的权限。
        卡片：
        CANREAD = 1
        OWNCARD = 2
        CANSETINFO = 4
        CANDISCARD = 8
        CANMODIFY = 16
        群聊：
        INGROUP = 1
        GROUPKP = 2
        GROUPADMIN = 4
        BOTADMIN = 8
        """
        if isinstance(thing, GameCard):
            card = thing
            f = 0

            if card.id in pl.cards or card.id in pl.gamecards:
                f |= CANREAD | OWNCARD

            if not f & OWNCARD:
                if card.group.id == -1 or (card.type == "PL" and self.checkaccess(pl, card.group) & INGROUP):
                    f |= CANREAD

            if f & OWNCARD and not card.isgamecard:
                f |= CANSETINFO

            if f & OWNCARD and (card.groupid == -1 or (card.discard and not card.isgamecard and card.id not in self.gamecards)):
                f |= CANDISCARD

            if (card.group.kp is not None and card.group.kp == pl) or pl.id == ADMIN_ID:
                f |= CANMODIFY | CANREAD

            return f

        gp: Group = thing
        f = 0

        if self.isingroup(gp, pl):
            f |= INGROUP

        if f == 0:
            return BOTADMIN if pl.id == ADMIN_ID else 0

        if gp.kp is not None and gp.kp == pl:
            f |= GROUPKP

        if self.ispladmin(gp, pl):
            f |= GROUPADMIN

        if pl.id == ADMIN_ID:
            f |= BOTADMIN

        return f

    @staticmethod
    def readManual() -> List[str]:
        try:
            with open(os.path.join(os.path.dirname(__file__), "README.md"), 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return []

        text = text[text.find("## 指南")+3:]
        texts = text.split("\n### ")

        return texts

    def atgamestart(self, gp: Group) -> None:
        # 开始执行
        kp = gp.kp
        gp.game = GroupGame(gp.id, gp.cards)
        # 构建数据关联
        gp.game.group = gp
        gp.game.kp = gp.kp
        kp.kpgames[gp.id] = gp.game

        kpcardcount = 0
        kpcardptr: GameCard = None
        for card in gp.game.cards.values():
            self.gamecards[card.id] = card
            card.group = gp
            card.player = self.getcard(card.id).player
            card.player.gamecards[card.id] = card

            if card.player == kp:
                kpcardcount += 1
                kpcardptr = card

        if kpcardcount == 1:
            gp.game.kpctrl = kpcardptr
            self.sendto(kp, "在游戏中只有一张卡，操作的卡片自动切换到该卡：" +
                        gp.game.kpctrl.getname())
        elif kpcardcount > 1:
            self.sendto(
                kp, f"NPC卡片多于1张，在需要使用NPC卡片进行对抗前，请使用指令：\n`/switchgamecard {gp.id}`")

        gp.game.write()

    def atgameending(self, game: GroupGame) -> None:
        kp = game.kp
        gp = game.group

        idl = list(game.cards.keys())  # 在迭代过程中改变键会抛出错误，复制键

        for x in idl:
            self.popcard(x)
            nocard = self.popgamecard(x)
            nocard.isgamecard = False
            nocard.playerid = kp.id
            self.addonecard(nocard, dontautoswitch=True, givekphint=False)

        gp.game = None
        gp.pausedgame = None
        gp.kp.kpgames.pop(gp.id)

    def atidchanging(self, msg: Message, oldid: int, newid: int) -> None:
        gamecard = self.getgamecard(oldid)
        if gamecard is not None:
            gamecard = self.popgamecard(oldid)
            gamecard.id = newid
            self.addgamecard(gamecard)

        card = self.popcard(oldid)
        card.id = newid
        self.addonecard(card, dontautoswitch=True, givekphint=False)
        rttext = "修改卡片的id：从"+str(oldid)+"修改为"+str(newid)
        if gamecard is not None:
            rttext += "\n游戏内卡片id同步修改完成。"

        msg.reply_text(rttext)

    def holdinggamecontinue(self, gpid: int) -> GroupGame:
        """继续一场暂停的游戏。`/continuegame`的具体实现。"""
        gp = self.forcegetgroup(gpid)
        if gp.game is not None and gp.pausedgame is not None:
            raise Exception("群："+str(gp.id)+"存在暂停的游戏和进行中的游戏")
        if gp.pausedgame is not None:
            gp.game, gp.pausedgame = gp.pausedgame, None
        return gp.game

    def isholdinggame(self, gpid: int) -> bool:
        return True if self.forcegetgroup(gpid).pausedgame is not None else False

    @staticmethod
    def getgamecardsid(game: GroupGame) -> KeysView[int]:
        return game.cards.keys()

    def choosedec(self, update: Update, card: GameCard):
        datas = card.data.datadec[0].split('_')

        rtbuttons = [[]]
        for dname in datas:
            rtbuttons[0].append(InlineKeyboardButton(
                text=dname, callback_data=self.IDENTIFIER+" choosedec "+dname))

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply("请选择下面一项属性来设置下降值", reply_markup=rp_markup)

    @overload
    def cardpop(self, card: GameCard) -> Optional[GameCard]:
        ...

    @overload
    def cardpop(self, id: int) -> Optional[GameCard]:
        ...

    def cardpop(self, id: Union[GameCard, int]) -> Optional[GameCard]:
        """删除一张卡并返回其数据。返回None则删除失败"""
        if type(id) is int:
            return self.popcard(id) if self.getcard(id) is not None else None
        card = id
        if card.isgamecard:
            return self.popgamecard(card.id)
        return self.popcard(card.id)

    def findDiscardCardsWithGpidCdid(self, pl: Player, cardslist: List[int]) -> List[GameCard]:
        ans: List[int] = []

        for id in cardslist:
            if id < 0:  # 群id
                gp = self.getgp(id)
                if gp is None:
                    continue
                for card in gp.cards.values():
                    if self.checkaccess(pl, card) & CANDISCARD:
                        ans.append(card.id)
            else:
                card = self.getcard(id)
                if card is None:
                    continue
                if self.checkaccess(pl, card) & CANDISCARD:
                    ans.append(card.id)

        ans = list(set(ans))

        return [self.getcard(x) for x in ans]

    @staticmethod
    def showcardinfo(card1: GameCard) -> str:  # show full card
        """调用`GameCard.__str__`返回`card1`的信息"""
        return str(card1)

    @staticmethod
    def iskeyconstval(d: dict, keyname: str) -> bool:
        if type(d[keyname], bool) or type(d[keyname]) is str or isinstance(d[keyname]) is int:
            return True
        return False

    @classmethod
    def showvalwithkey(cls, d: dict, keyname: str) -> Optional[str]:
        """输入字典和键，格式化其值为字符串并输出"""
        if keyname not in d:
            return None
        val = d[keyname]
        rttext: str = ""
        if isinstance(val, dict):
            for key in val:
                rttext += key+": "+str(val[key])+"\n"
        elif not cls.iskeyconstval(d, keyname):
            return None
        else:
            rttext = str(val)
        if rttext == "":
            rttext = "None"
        return rttext

    def showattrinfo(self, update: Update, card1: GameCard, attrname: str) -> bool:
        """显示卡中某项具体的数据，并直接由`update`输出到用户。
        不能输出属性`tempstatus`下的子属性。
        如果获取不到`attrname`这个属性，返回False。"""
        rttext = self.showvalwithkey(card1.__dict__, attrname)
        if rttext is not None:
            self.reply(rttext)
            return True
        # 没有在最外层找到
        for keys in card1.__dict__:
            if not isinstance(card1.__dict__[keys], dict) or (keys == "tempstatus" and attrname != "global"):
                continue
            rttext = self.showvalwithkey(card1.__dict__[keys], attrname)
            if rttext is None:
                continue
            self.reply(rttext)
            return True
        self.reply("找不到这个属性！")
        return False

    @staticmethod
    def modifythisdict(d: dict, attrname: str, val: str) -> Tuple[str, bool]:
        """修改一个字典`d`。`d`的键为`str`类型，值为`bool`, `int`, `str`其中之一。

        寻找`attrname`是否在字典中，如果不在字典中或键对应的值是`dict`类型，返回不能修改的原因以及`False`。
        否则，返回True的同时返回修改前的值的格式化。"""
        if isinstance(d[attrname], dict):
            return "不能修改dict类型", False
        if type(d[attrname]) is bool:
            rtmsg = "False"
            if d[attrname]:
                rtmsg = "True"
            if val in ["F", "false", "False", "假"]:
                d[attrname] = False
                val = "False"
            elif val in ["T", "true", "True", "真"]:
                d[attrname] = True
                val = "True"
            else:
                return "无效的值", False
            return rtmsg, True
        if type(d[attrname]) is int:
            if not isint(val):
                return "无效的值", False
            rtmsg = str(d[attrname])
            d[attrname] = int(val)
            return rtmsg, True
        if type(d[attrname]) is str:
            rtmsg: str = d[attrname]
            d[attrname] = val
            return rtmsg, True
        # 对应的值不是可修改的三个类型之一，也不是dict类型
        return "类型错误！", False

    @classmethod
    def findattrindict(cls, d: dict, key: str) -> dict:
        """从字典（键为字符串，值为字典或`int`, `str`, `bool`类型）中找到某个键所在的那层字典并返回。
        搜索子字典时，如果`key`不是`global`，忽略`tempstatus`对应的字典。"""
        if key in d:
            return d

        for k1 in d:
            if not isinstance(d[k1], dict) or (k1 == "tempstatus" and key != "GLOBAL"):
                continue
            t = cls.findattrindict(d[k1], key)
            if t:
                return t
        return None

    @classmethod
    def modifycardinfo(cls, card1: GameCard, attrname: str, val: str) -> Tuple[str, bool]:
        """修改`card1`的某项属性。

        因为`card1`的属性中有字典，`attrname`可能是其属性里的某项，
        所以可能还要遍历`card1`的所有字典。"""
        if attrname in card1.__dict__:
            rtmsg, ok = cls.modifythisdict(card1.__dict__, attrname, val)
            if not ok:
                return rtmsg, ok
            return "卡id："+str(card1.id)+"的属性："+attrname+"从"+rtmsg+"修改为"+val, True
        for key in card1.__dict__:
            if not isinstance(card1.__dict__[key], dict) or key == "tempstatus":
                continue
            if attrname in card1.__dict__[key]:
                rtmsg, ok = cls.modifythisdict(
                    card1.__dict__[key], attrname, val)
                if not ok:
                    return rtmsg, ok
                return "卡id："+str(card1.id)+"的属性："+attrname+"从"+rtmsg+"修改为"+val, True
        return "找不到该属性", False

    def findkpcards(self, kpid) -> List[GameCard]:
        """查找`kpid`作为kp，所控制的NPC卡片，并做成列表全部返回"""
        ans = []
        kp = self.getplayer(kpid)
        if not kp:
            return ans
        for card in kp.cards.values():
            if card.group.kp.id == kp.id:
                ans.append(card)
        return ans

    @staticmethod
    def changecardsplid(gp: Group, oldpl: Player, newpl: Player) -> None:
        """将某个群中所有`oldplid`持有的卡改为`newplid`持有。"""
        oplk = list(oldpl.cards.keys())
        for key in oplk:

            card = oldpl.cards[key]
            if card.group != gp:
                continue

            card.playerid = newpl.id
            card.player = newpl
            newpl.cards[key] = oldpl.cards.pop(key)

        for key in oldpl.gamecards.keys():

            card = oldpl.gamecards[key]
            if card.group != gp:
                continue

            card.playerid = newpl.id
            card.player = newpl
            newpl.gamecards[key] = oldpl.gamecards.pop(key)

        if oldpl.controlling is not None and oldpl.controlling.group == gp:
            oldpl.controlling = None

        oldpl.write()
        newpl.write()
        return

    def changeKP(self, gp: Group, newkp: Player) -> bool:
        """转移KP权限，接收参数：群id，新KP的id。
        会转移所有原KP控制的角色卡，包括正在进行的游戏。"""
        kp = gp.kp
        if not kp:
            return False
        if kp == newkp:
            return False

        self.changecardsplid(gp, kp, newkp)

        self.delkp(kp)
        self.addkp(gp, newkp)

        gp.write()
        kp.write()
        newkp.write()
        return True

    def makejobbutton(self) -> List[List[InlineKeyboardButton]]:
        """生成全部职业的按钮"""
        rtbuttons = [[]]
        for keys in self.joblist:
            if len(rtbuttons[len(rtbuttons)-1]) == 3:
                rtbuttons.append([])
            rtbuttons[len(
                rtbuttons)-1].append(InlineKeyboardButton(keys, callback_data=self.IDENTIFIER+" job "+keys))
        return rtbuttons

    def skillcantouchmax(self, card1: GameCard, jumpskill: Optional[str] = None) -> Tuple[bool, bool]:
        """判断一张卡当前是否可以新增一个专精技能。

        第一个返回值描述年龄是否符合Aged标准。第二个返回值描述在当前年龄下能否触摸到专精等级"""
        rules = card1.group.rule
        if card1.info.age > rules.skillmaxAged[3]:
            ans1 = True
            skillmaxrule = rules.skillmaxAged
        else:
            ans1 = False
            skillmaxrule = rules.skillmax

        countSpecialSkill = 0

        card1.skill.check()

        for skill in card1.skill.allskills():
            if (skill == "母语" or skill == "闪避") and self.getskilllevelfromdict(card1, skill) == card1.skill.get(skill):
                continue
            if jumpskill is not None and skill == jumpskill:
                continue
            if card1.skill.get(skill) > skillmaxrule[0]:
                countSpecialSkill += 1

        for skill in card1.interest.allskills():
            if (skill == "母语" or skill == "闪避") and self.getskilllevelfromdict(card1, skill) == card1.interest.get(skill):
                continue
            if jumpskill is not None and skill == jumpskill:
                continue
            if card1.interest.get(skill) > skillmaxrule[0]:
                countSpecialSkill += 1

        return (ans1, True) if countSpecialSkill < skillmaxrule[2] else (ans1, False)

    def skillmaxval(self, skillname: str, card1: GameCard, ismainskill: bool) -> int:
        """通过cost规则，返回技能能达到的最高值。"""
        aged, ok = self.skillcantouchmax(card1, skillname)
        gp = self.forcegetgroup(card1.groupid)

        if aged:
            skillrule = gp.rule.skillmaxAged
        else:
            skillrule = gp.rule.skillmax

        if ok:
            maxval = skillrule[1]
        else:
            maxval = skillrule[0]

        if skillname == "信用":
            if card1.info.job in self.joblist:
                maxval = min(maxval, self.joblist[card1.info.job][1])

        basicval = -1

        if ismainskill:
            pts = card1.skill.points
            if skillname in card1.skill.allskills():
                basicval = card1.skill.get(skillname)
        else:
            pts = card1.interest.points
            if skillname in card1.interest.allskills():
                basicval = card1.interest.get(skillname)

        costrule = gp.rule.skillcost

        if basicval == -1:
            basicval = self.getskilllevelfromdict(card1, skillname)

        if len(costrule) <= 2:
            skillmax = (pts+basicval*costrule[0])//costrule[0]
            return min(maxval, skillmax)

        # 有非默认的规则，长度不为2
        i = 1
        skillmax = basicval

        while i < len(costrule):
            if (costrule[i]-skillmax)*costrule[i-1] <= pts:
                pts -= (costrule[i]-skillmax)*costrule[i-1]
                skillmax = costrule[i]
                i += 2
            else:
                return min(maxval, (pts+skillmax*costrule[i-1])//costrule[i-1])

        return min(maxval, skillmax)

    def evalskillcost(self, skillname: str, skillval: int, card1: GameCard, ismainskill: bool) -> int:
        """返回由当前技能值增加到目标值需要消耗多少点数。如果目标技能值低于已有值，返回负数"""
        if skillval > 99:
            return 10000  # HIT BAD TRAP
        basicval = -1
        if ismainskill:
            if skillname in card1.skill.allskills():
                basicval = card1.skill.get(skillname)
        else:
            if skillname in card1.interest.allskills():
                basicval = card1.interest.get(skillname)
        if basicval == -1:
            basicval = self.getskilllevelfromdict(card1, skillname)
        if skillval == basicval:
            return 0
        gp = card1.group
        costrule = gp.rule.skillcost
        if skillval < basicval:
            # 返还技能点，返回负数
            if len(costrule) <= 2:
                return (skillval-basicval)*costrule[0]
            i = len(costrule)-1
            while i >= 0 and costrule[i] >= basicval:
                i -= 2
            if i < 0:
                return (skillval-basicval)*costrule[0]
            if skillval >= costrule[i]:
                return (skillval-basicval)*costrule[i+1]
            ans = 0
            while i >= 0 and skillval < costrule[i]:
                ans += (basicval-costrule[i])*costrule[i+1]
                basicval = costrule[i]
                i -= 2
            return -(ans+(basicval-skillval)*costrule[i+1])
        # 增加点数，返回值为正
        if skillval <= costrule[1]:
            return (skillval-basicval)*costrule[0]
        i = 1
        ans = 0
        while skillval > costrule[i]:
            ans += costrule[i-1]*(costrule[i]-basicval)
            basicval = costrule[i]
            i += 2
        return ans + costrule[i-1]*(costrule[i]-basicval)

    def generatePoints(self, card: GameCard) -> bool:
        job = card.info.job
        if job not in self.joblist:
            return False

        ptrule: Dict[str, int] = self.joblist[job][2]
        pt = 0

        for keys in ptrule:
            if keys in card.data.alldatanames:
                pt += card.data.getdata(keys)*ptrule[keys]
            elif len(keys) == 11:
                pt += max(card.data.getdata(keys[:3]), card.data.getdata(keys[4:7]),
                          card.data.getdata(keys[8:]))*ptrule[keys]
            elif keys[:3] in card.data.alldatanames and keys[4:] in card.data.alldatanames:
                pt += max(card.data.getdata(keys[:3]),
                          card.data.getdata(keys[4:]))*ptrule[keys]
            else:
                return False

        card.skill.points = pt
        card.write()
        return True

    def isfromkp(self, update: Update) -> bool:
        """判断消息发送者是否是kp。
        如果是私聊消息，只需要发送者是某群KP即返回True。如果是群聊消息，当发送者是本群KP才返回True"""
        if isprivatemsg(update):  # 私聊消息，搜索所有群判断是否是kp
            return self.searchifkp(self.forcegetplayer(update))

        # 如果是群消息，判断该指令是否来自本群kp
        gp = self.forcegetgroup(update)
        return gp.kp is not None and gp.kp == self.forcegetplayer(update)

    def addcardoverride(self, card: GameCard, id: int, dontautoswitch: bool = False) -> bool:
        """添加一张游戏外的卡，当卡id重复时返回False。该函数忽略原本card.groupid或者card.playerid"""
        if id < 0:
            card.groupid = id
        else:
            card.playerid = id

        return self.addonecard(card, dontautoswitch)

    def changecardgpid(self, oldgpid: int, newgpid: int) -> bool:
        """函数`changegroup`的具体实现。"""
        oldcdidlst = list(self.forcegetgroup(oldgpid).cards.keys())
        for cdid in oldcdidlst:
            card = self.cardpop(oldgpid, cdid)
            self.addcardoverride(card, newgpid)
        self.getgp(oldgpid).write()
        self.getgp(newgpid).write()

    @staticmethod
    def getkpctrl(game: GroupGame) -> Optional[GameCard]:
        for cardi in game.cards.values():
            if cardi.id == game.kpctrl and cardi.playerid == game.kpid:
                return cardi
        return None

    def buttonmanual(self, query: CallbackQuery, plid: int, args: List[str]) -> bool:
        pagereq = args[2]
        thispage = int(args[1])

        if pagereq == "pre":
            page = thispage-1
            if page == 0:
                rtbuttons = [[InlineKeyboardButton(
                    text="下一页", callback_data=self.IDENTIFIER+" manual 0 next")]]
            else:
                rtbuttons = [[
                    InlineKeyboardButton(
                        text="上一页", callback_data=self.IDENTIFIER+f" manual {page} pre"),
                    InlineKeyboardButton(
                        text="下一页", callback_data=self.IDENTIFIER+f" manual {page} next")
                ]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text(
                text=self.MANUALTEXTS[page], parse_mode="MarkdownV2", reply_markup=rp_markup)

        else:
            page = thispage+1
            if page == len(self.MANUALTEXTS)-1 or (page == len(self.MANUALTEXTS)-2 and plid != ADMIN_ID):
                rtbuttons = [[InlineKeyboardButton(
                    text="上一页", callback_data=self.IDENTIFIER+f" manual {page} pre")]]
            else:
                rtbuttons = [[
                    InlineKeyboardButton(
                        text="上一页", callback_data=self.IDENTIFIER+f" manual {page} pre"),
                    InlineKeyboardButton(
                        text="下一页", callback_data=self.IDENTIFIER+f" manual {page} next")
                ]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text(
                text=self.MANUALTEXTS[page], parse_mode="MarkdownV2", reply_markup=rp_markup)

        return True

    def buttonsetsex(self, query: CallbackQuery, plid: int,  args: List[str]) -> bool:
        cardi = self.findcard(plid)
        if cardi is None:
            return self.errorHandlerQ(query, "找不到卡。")

        sex = args[1]
        if sex == "other":
            self.addOP(plid, "setsex")
            query.edit_message_text("请输入具体的性别：")
            return True

        cardi.info.sex = sex
        cardi.write()

        rttext = "性别设定为"
        if sex == "male":
            rttext += "男性。"
        else:
            rttext += "女性。"
        query.edit_message_text(rttext)
        return True

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
        except Exception:
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
        except Exception:
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

    def addonecard(self, card: GameCard, dontautoswitch: bool = False, givekphint: bool = True) -> bool:
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
        """该方法维护时请务必注意。
        在方法被调用时，`oldid`对应的群已经消失了。
        这时候不可以调用`getname`等方法，因为`chat`对象为`None`。"""
        gp = self.getgp(oldid)
        if gp is None:
            return
        gp.delete()
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
                return self.reply(chat_id=chatid, text=msg, reply_markup=rpmarkup)
            return self.reply(chat_id=chatid, text=msg)
        except ChatMigrated as e:
            if chatid in self.groups:
                self.groupmigrate(chatid, e.new_chat_id)
                chatid = e.new_chat_id
                self.sendto(chatid, msg)
            else:
                raise e
        except Exception:
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

    def cardsetsex(self, update: Update, cardi: GameCard, sex: str) -> bool:
        if sex in ["男", "男性", "M", "m", "male", "雄", "雄性", "公", "man"]:
            cardi.info.sex = "male"
            self.reply("性别设定为男性。")

        elif sex in ["女", "女性", "F", "f", "female", "雌", "雌性", "母", "woman"]:
            cardi.info.sex = "female"
            self.reply("性别设定为女性。")

        else:
            cardi.info.sex = sex
            self.reply("性别设定为："+sex+"。")

        return True

    def cardsetage(self, update: Update, cardi: GameCard, age: int) -> bool:
        if cardi.info.age > 0:
            return self.errorInfo("已经设置过年龄了。")

        if age < 17 or age > 99:
            return self.errorInfo("年龄应当在17-99岁。")

        cardi.info.age = age

        detailmsg = cardi.generateAgeAttributes()
        update.message.reply_text(
            "年龄设置完成！详细信息如下：\n"+detailmsg+"\n如果年龄不小于40，或小于20，需要设置STR减值。如果需要帮助，使用 /createcardhelp 来获取帮助。")

        if cardi.data.datadec is not None:
            self.choosedec(update, cardi)
        else:
            cardi.generateOtherAttributes()

        cardi.write()
        return True

    @staticmethod
    def nameset(cardi: GameCard, name: str) -> None:
        cardi.info.name = name
        # cardi.cardcheck["check5"] = True
        cardi.write()

    def atcardtransfer(self, msg: Message, cdid: int, tpl: Player) -> None:
        gamecard = self.getgamecard(cdid)
        if gamecard is not None:
            gamecard = self.popgamecard(cdid)
            gamecard.playerid = tpl.id
            self.addgamecard(gamecard)

        card = self.popcard(cdid)
        opl = card.player
        card.playerid = tpl.id

        if card.group.kp is not None and msg.from_user.id == card.group.kp.id:
            self.addonecard(card, dontautoswitch=False, givekphint=False)
            self.sendto(tpl, "玩家："+opl.getname() +
                        "的一张卡"+card.getname()+"被KP转移给您")
        else:
            self.addonecard(card, dontautoswitch=False, givekphint=True)
            self.sendto(tpl, "玩家："+opl.getname() +
                        "将自己的一张卡"+card.getname()+"转移给您")

        rttext = "卡id"+str(cdid)+"拥有者从"+str(opl.id)+"修改为"+str(tpl.id)+"。"
        if gamecard is not None:
            rttext += "游戏内数据也被同步修改了。"

        msg.reply_text(rttext)

    def gamepop(self, gp: Group) -> Optional[GroupGame]:
        """终止一场游戏。`/abortgame`的具体实现。"""
        ans = gp.game if gp.game is not None else gp.pausedgame

        if ans is not None:
            cdl = list(ans.cards.keys())  # 迭代过程中不能改变字典，复制键
            for cdid in cdl:
                self.popgamecard(cdid)

            if ans.kp is not None:
                ans.kp.kpgames.pop(ans.group.id)

            gp.game = None
            gp.pausedgame = None
            gp.write()

        return ans

    def showskillpages(self, page: int, card1: GameCard) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        IDENTIFIER = self.IDENTIFIER
        thispageskilllist = self.skillpages[page]
        rttext = f"添加/修改兴趣技能，剩余点数：{str(card1.interest.points)}。目前的数值/基础值如下："
        rtbuttons = [[]]
        for key in thispageskilllist:
            if key in card1.skill.allskills() or key in card1.suggestskill.allskills():
                continue
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            if key in card1.interest.allskills():
                rttext += "（已有技能）"+key+"："+str(card1.interest.get(key))+"\n"
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(text=key,
                                                                        callback_data=IDENTIFIER+" cgintskill "+key))
                continue
            rttext += key+"："+str(self.getskilllevelfromdict(card1, key))+"\n"
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(text=key,
                                                                    callback_data=IDENTIFIER+" addintskill "+key))
        if page == 0:
            rtbuttons.append([InlineKeyboardButton(
                text="下一页", callback_data=IDENTIFIER+" addintskill page 1")])
        elif page == len(self.skillpages)-1:
            rtbuttons.append([InlineKeyboardButton(
                text="上一页", callback_data=IDENTIFIER+" addintskill page "+str(page-1))])
        else:
            rtbuttons.append([InlineKeyboardButton(text="上一页", callback_data=IDENTIFIER+" addintskill page "+str(
                page-1)), InlineKeyboardButton(text="下一页", callback_data=IDENTIFIER+" addintskill page "+str(page+1))])
        return rttext, rtbuttons

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

    def hascard(self, plid: int, gpid: int) -> bool:
        """判断一个群内是否已经有pl的卡"""
        pl = self.getplayer(plid)
        if not pl:
            pl = self.initplayer(plid)
            return False

        return any(card.group.id == gpid for card in pl.cards.values())

    @staticmethod
    def generateNewCard(userid, groupid) -> Tuple[GameCard, str]:
        """新建玩家卡片"""
        newcard = plainNewCard()
        newcard["playerid"] = userid
        newcard["groupid"] = groupid
        card = GameCard(newcard)
        card.data.randdata(write=False)
        text = card.data.datainfo
        card.interest.points = card.data.INT*2
        return card, text

    def getoneid(self) -> int:
        return self.getnewids(1)[0]

    def getnewids(self, n: int) -> List[int]:
        """获取n个新的卡id，这些id尽可能小"""
        ids = self.allids
        ans: List[int] = []
        nid = 0
        for _ in range(n):
            while nid in ids:
                nid += 1
            ans.append(nid)
            nid += 1
        return ans

    def getnewcard(self, msgid: Optional[int], gpid: int, plid: int, cdid: Optional[int] = None) -> bool:
        """指令`/newcard`的具体实现"""
        gp = self.forcegetgroup(gpid)
        new_card, detailmsg = self.generateNewCard(plid, gpid)
        allids = self.allids
        if cdid is not None and cdid not in allids:
            new_card.id = cdid
        else:
            if cdid is not None and cdid in allids:
                self.reply(
                    chat_id=plid, text="输入的ID已经被占用，自动获取ID。之后可以用 /changeid 更换喜欢的id。", reply_to_message_id=msgid)
            new_card.id = self.getoneid()
        self.reply(chat_id=plid, reply_to_message_id=msgid,
                   text="角色卡已创建，您的卡id为："+str(new_card.id)+"。详细信息如下：\n"+detailmsg)
        # 如果有3个属性小于50，则discard=true
        if new_card.data.countless50discard():
            new_card.discard = True
            self.reply(chat_id=plid, reply_to_message_id=msgid,
                       text="因为有三项属性小于50，如果你愿意的话可以点击 /renewcard 来重置这张角色卡。如果停止创建卡，点击 /discard 来放弃建卡。\n设定年龄后则不能再删除这张卡。")
        self.reply(chat_id=plid, reply_to_message_id=msgid,
                   text="长按 /setage 并输入一个数字来设定年龄。如果需要卡片制作帮助，点击 /createcardhelp 来获取帮助。")
        self.addonecard(new_card)
        return True

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
        if isprivate(update):
            self.reply(HELP_TEXT)
        else:
            self.reply("")

    @commandCallbackMethod
    def tempcheck(self, update: Update, context: CallbackContext):
        """增加一个临时的检定修正。该指令只能在游戏中使用。
        `/tempcheck --tpcheck`只能用一次的检定修正。使用完后消失
        `/tempcheck --tpcheck --cardid --dicename`对某张卡，持久生效的检定修正。
        如果需要对这张卡全部检定都有修正，dicename参数请填大写单词`GLOBAL`。"""

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
            except Exception:
                update.message.reply_text("Markdown格式parse错误，请联系作者检查并改写文档")
                return False
            return True

        return self.errorInfo("找不到这个指令，或这个指令没有帮助信息。")

    def unknown(self, update: Update, context: CallbackContext) -> False:
        return self.errorInfo("没有这一指令", True)

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
            except Exception:
                self.reply(message, reply_markup=rp_markup)

        return False

    @staticmethod
    def errorHandlerQ(query: CallbackQuery,  message: str) -> False:
        if message == "找不到卡。":
            message += "请使用 /switch 切换当前操控的卡再试。"
        elif message.find("参数") != -1:
            message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"

        try:
            query.edit_message_text(message, parse_mode="MarkdownV2")
        except Exception:
            query.edit_message_text(message)

        return False
