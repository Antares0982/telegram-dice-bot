from dicebot import diceBot
from utils import *
from telegram.ext import CallbackContext
from gameclass import *

import time


class cardShowBot(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    @commandCallbackMethod
    def showkp(self, update: Update, context: CallbackContext) -> bool:
        """这一指令是为KP设计的。不能在群聊中使用。

        `/showkp game --groupid`: 显示发送者在某个群主持的游戏中所有的卡
        `/showkp card`: 显示发送者作为KP控制的所有卡
        `/showkp group --groupid`: 显示发送者是KP的某个群内的所有卡"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        if isgroup(update):
            return self.errorInfo("使用该指令请发送私聊消息", True)

        if len(context.args) == 0:
            return self.errorInfo("需要参数")

        arg = context.args[0]
        if arg == "group":
            kp = self.forcegetplayer(update)
            # args[1] should be group id
            if len(context.args) < 2:
                return self.errorInfo("需要群ID")
            gpid = context.args[1]
            if not self.isint(gpid) or int(gpid) >= 0:
                return self.errorInfo("无效ID")

            gpid = int(gpid)
            if gpid < 0 or self.getgp(gpid) is None or self.getgp(gpid).kp != kp:
                return self.errorInfo("这个群没有卡或没有权限")

            gp: Group = self.getgp(gpid)
            ans: List[GameCard] = []
            for card in kp.cards.values():
                if card.group != gp:
                    continue
                ans.append(card)

            if len(ans) == 0:
                return self.errorInfo("该群没有你的卡")

            for i in ans:
                self.reply(str(i))
                time.sleep(0.2)
            return True

        if arg == "game":
            kp = self.forcegetplayer(update)

            if len(context.args) < 2:
                return self.errorInfo("需要群ID")
            gpid = context.args[1]
            if not self.isint(gpid) or int(gpid) >= 0:
                return self.errorInfo("无效群ID")

            gp = self.getgp(gpid)
            if gp is None or (gp.game is None and gp.pausedgame is None):
                return self.errorInfo("没有找到游戏")

            if gp.kp != kp:
                return self.errorInfo("你不是这个群的kp")

            game = gp.game if gp.game is not None else gp.pausedgame

            hascard = False
            for i in game.cards.values():
                if i.player != kp:
                    continue
                hascard = True
                self.reply(str(i))
                time.sleep(0.2)

            return True if hascard else self.errorInfo("你没有控制的游戏中的卡")

        if arg == "card":
            kp = self.forcegetplayer(update)

            hascard = False
            for card in kp.cards.values():
                if card.group.kp != kp:
                    continue
                hascard = True
                self.reply(str(card))
                time.sleep(0.2)

            return True if hascard else self.errorInfo("你没有控制NPC卡片")

        return self.errorInfo("无法识别的参数")

    @commandCallbackMethod
    def showmycards(self, update: Update, context: CallbackContext) -> bool:
        """显示自己所持的卡。群聊时发送所有在本群可显示的卡片。私聊时发送所有卡片。"""
        if self.ischannel(update):
            return False
        self.chatinit(update, context)

        pl = self.forcegetplayer(update)
        if len(pl.cards) == 0:
            return self.errorInfo("你没有任何卡。")

        if isgroup(update):
            # 群消息，只发送本群的卡
            gp = self.forcegetgroup(update)
            rttexts: List[str] = []

            for card in pl.cards.values():
                if card.group != gp or card.type != PLTYPE:
                    continue
                rttexts.append(str(card))

            if len(rttexts) == 0:
                return self.errorInfo("找不到本群的卡。")

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
                return self.errorInfo("该玩家在本群没有卡")

        card = rpcard if rpcard is not None else None
        if card is None:
            if isgroup(update):
                gp = self.forcegetgroup(update)
                card = self.findcardfromgroup(pl, gp)
                if card is None:
                    return self.errorInfo("请先在本群创建卡")
            else:
                card = pl.controlling
                if card is None:
                    return self.errorInfo("请先创建卡，或者使用 /switch 选中一张卡")

        game = card.group.game if card.group.game is not None else card.group.pausedgame

        rttext = ""

        if game is not None and isgroup(update):
            if card.id in game.cards:
                rttext = "显示游戏中的卡：\n"
                card = game.cards[card.id]

        if rttext == "":
            rttext = "显示游戏外的卡：\n"

        if not self.checkaccess(pl, card) & CANREAD:
            return self.errorInfo("没有权限")

        if card.type != PLTYPE and isgroup(update):
            return self.errorInfo("非玩家卡片不可以在群内显示")

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
            return self.errorInfo("请用mainpoints或intpoints来显示")
        else:
            ans = card.show(context.args[0])

        if ans == "找不到该属性":
            return self.errorInfo("找不到该属性")

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
            return self.errorInfo("需要参数")
        if not self.isint(context.args[0]) or int(context.args[0]) < 0:
            return self.errorInfo("卡id参数无效", True)
        cdid = int(context.args[0])

        rttext: str = ""
        cardi: Optional[GameCard] = None

        if isgroup(update):
            cardi = self.getgamecard(cdid)
            if cardi is not None:
                rttext = "显示游戏内的卡片\n"

        if cardi is None:
            cardi = self.getcard(cdid)

            if cardi is None:
                return self.errorInfo("找不到这张卡")

        if rttext == "":
            rttext = "显示游戏外的卡片\n"

        # 检查是否有权限
        if isprivate(update):

            pl = self.forcegetplayer(update)

            if self.checkaccess(pl, cardi) & CANREAD == 0:
                return self.errorInfo("没有权限")
        else:
            if (cardi.groupid != -1 and cardi.group != self.forcegetgroup(update)) or cardi.type != PLTYPE:
                return self.errorInfo("没有权限", True)

        # 开始处理
        if len(context.args) >= 2:
            if context.args[1] == "card":
                self.reply(rttext+str(cardi))
            else:
                ans = cardi.show(context.args[1])
                if ans == "找不到该属性":
                    return self.errorInfo(ans)

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

        if isgroup(update):
            gp = self.forcegetgroup(update)

            out = bool(len(context.args) == 0) or bool(
                context.args[0] != "game")

            if not out and gp.game is None and gp.pausedgame is None:
                return self.errorInfo("没有进行中的游戏")

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
                return self.errorInfo("本群没有卡")

            self.reply(rttext)
            return True

        # 下面处理私聊消息
        kp = self.forcegetplayer(update)
        if not self.searchifkp(kp):
            return self.errorInfo("没有权限")

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
            return self.errorInfo("没有可显示的卡。")

        return True
