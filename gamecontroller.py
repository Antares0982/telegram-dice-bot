from dicebot import diceBot
from utils import *
from telegram.ext import CallbackContext
from gameclass import *


class gameController(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    @commandCallbackMethod
    def startgame(self, update: Update, context: CallbackContext) -> bool:
        """开始一场游戏。

        这一指令将拷贝本群内所有卡，之后将用拷贝的卡片副本进行游戏，修改属性将不会影响到游戏外的原卡属性。
        如果要正常结束游戏，使用`/endgame`可以将游戏的角色卡数据覆写到原本的数据上。
        如果要放弃这些游戏内进行的修改，使用`/abortgame`会直接删除这些副本副本。
        `/startgame`：正常地开始游戏，对所有玩家的卡片（type为PL）进行卡片检查。
        `/startgame ignore`跳过开始游戏的检查，直接开始游戏。

        开始后，bot会询问是否保存聊天文本数据。此时回复cancel或者取消，即可取消开始游戏。"""
        

        if isprivate(update):
            return self.errorInfo("游戏需要在群里进行")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorInfo("游戏只能由KP发起", True)
        if gp.game is not None:
            return self.errorInfo("游戏已经在进行中")

        if gp.pausedgame is not None:
            return self.continuegame(update, context)  # 检测到游戏暂停中，直接继续

        # 开始验证
        if not(len(context.args) > 0 and context.args[0] == "ignore"):
            if len(gp.cards) == 0:
                return self.errorInfo("本群没有任何卡片，无法开始游戏")
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
    def abortgame(self, update: Update, context: CallbackContext) -> bool:
        """放弃游戏。只有KP能使用该指令。这还将导致放弃在游戏中做出的所有修改，包括hp，SAN等。"""
        

        if not isgroup(update):
            return self.errorInfo("发送群聊消息来中止游戏")
        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorInfo("只有KP可以中止游戏", True)

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is not None:
            mempath = game.memfile
            if mempath != "":
                with open(PATH_MEM+mempath, 'r', encoding='utf-8') as f:
                    update.message.reply_document(
                        f, filename=gp.getname()+".txt", timeout=120)

        if self.gamepop(gp) is None:
            return self.errorInfo("没有找到游戏", True)

        self.reply("游戏已终止！")
        return True

    @commandCallbackMethod
    def pausegame(self, update: Update, context: CallbackContext) -> bool:
        """暂停游戏。
        游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
        当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
        可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
        继续游戏后会覆盖游戏中的这些属性。"""
        

        if not isgroup(update):
            return self.errorInfo("发送群消息暂停游戏")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorInfo("只有KP可以暂停游戏", True)
        if gp.game is None:
            return self.errorInfo("没有进行中的游戏", True)

        gp.pausedgame = gp.game
        gp.game = None
        gp.write()

        self.reply("游戏暂停，用 /continuegame 恢复游戏")
        return True

    @commandCallbackMethod
    def endgame(self, update: Update, context: CallbackContext) -> bool:
        """结束游戏。

        这一指令会导致所有角色卡的所有权转移给KP，之后玩家无法再操作这张卡片。
        同时，游戏外的卡片会被游戏内的卡片覆写。
        如果还没有准备好进行覆写，就不要使用这一指令。"""
        

        if not isgroup(update):
            return self.errorInfo("群聊才能使用该指令")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorInfo("只有KP可以结束游戏。")

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorInfo("没找到进行中的游戏。")

        mempath = game.memfile

        self.atgameending(game)

        if mempath != "":
            with open(PATH_MEM+mempath, 'r', encoding='utf-8') as f:
                update.message.reply_document(
                    f, filename=gp.getname()+".txt", timeout=120)

        self.reply("游戏结束！")
        return True

    @commandCallbackMethod
    def continuegame(self, update: Update, context: CallbackContext) -> bool:
        """继续游戏。必须在`/pausegame`之后使用。
        游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
        当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
        可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
        继续游戏后会覆盖游戏中的这些属性。"""
        

        if not isgroup(update):
            return self.errorInfo("发送群消息暂停游戏")

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        if gp.kp != kp:
            return self.errorInfo("只有KP可以暂停游戏", True)
        if gp.pausedgame is None:
            return self.errorInfo("没有进行中的游戏", True)

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
