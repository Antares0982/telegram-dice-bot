from telegram.ext import CallbackContext

from dicebot import BUTTON_SWITCHGAMECARD, diceBot
from gameclass import *
from utils import *


class adminCommand(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    def findexistgame(self, gpid: int) -> Optional[GroupGame]:
        gp = self.getgp(gpid)
        if not gp:
            return None
        return gp.getexistgame()

    def groupcopy(self, oldgpid: int, newgpid: int, copyall: bool) -> bool:
        """copyall为False则只复制NPC卡片"""
        if self.findexistgame(oldgpid) is not None or self.findexistgame(newgpid) is not None:
            return False

        oldgp = self.forcegetgroup(oldgpid)
        srclist: List[GameCard] = []
        for card in oldgp.cards.values():
            if not copyall and card.type == "PL":
                continue
            srclist.append(card)

        if len(srclist) == 0:
            return False

        newids = self.getnewids(len(srclist))

        dstlist = [GameCard(card.to_json()) for card in srclist]

        for i in range(len(dstlist)):
            dstlist[i].id = newids[i]

        for card in dstlist:
            self.addcardoverride(card, newgpid)

        self.getgp(newgpid).write()
        oldgp.write()

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

        try:
            oldgpid, newgpid = int(context.args[0]), int(context.args[1])
            assert oldgpid < 0 and newgpid < 0
        except (IndexError, ValueError, AssertionError):
            return self.errorInfo("输入无效", True)

        ogp = self.getgp(oldgpid)
        if ogp is None or len(ogp.cards) == 0:
            return self.errorInfo("该群没有卡", True)

        kp = self.forcegetplayer(update)
        ngp = self.getgp(newgpid)
        if ngp is None or kp != ogp.kp or ngp.kp != kp:
            return self.errorInfo("没有权限", True)

        copyall = True
        if len(context.args) >= 3 and context.args[2] == "kp":
            copyall = False

        if not self.groupcopy(oldgpid, newgpid, copyall):
            return self.errorInfo("无法复制")

        self.reply("复制成功")
        return True

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

        if isprivate(update):
            return self.errorInfo("游戏中才可以修改HP。")
        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)
        if gp.kp != kp:
            return self.errorInfo("没有权限", True)

        if len(context.args) == 0:
            return self.errorInfo("需要指定扣除的HP", True)

        chp: str = context.args[0]
        game = gp.game
        if game is None:
            return self.errorInfo("找不到进行中的游戏", True)

        rppl = self.getreplyplayer(update)
        if update.message.reply_to_message is not None:
            rpmsgid = update.message.reply_to_message.message_id
        else:
            rpmsgid = update.message.message_id

        if rppl is None:
            if len(context.args) < 2:
                return self.errorInfo("请用回复或@用户名的方式来选择玩家改变HP")
            if not isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorInfo("参数无效")
            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorInfo("指定的用户无效")
            chp = context.args[1]

        if rppl != kp:
            cardi = self.findcardfromgame(game, rppl)
        else:
            cardi = game.kpctrl

        if cardi is None:
            return self.errorInfo("找不到这名玩家的卡。")

        if chp[0] == "+" or chp[0] == "-":
            if len(chp) == 1:
                return self.errorInfo("参数无效", True)

            # 由dicecalculator()处理。减法时，检查可能的括号导致的输入错误
            if chp[0] == '-' and chp[1] != '(' and (chp[1:].find('+') != -1 or chp[1:].find('-') != -1):
                return self.errorInfo("当第一个减号的后面是可计算的骰子，且存在加减法时，请在第一个符号之后使用括号")

            try:
                diceans = dicecalculator(chp[1:])
            except Exception:
                return self.errorInfo("参数无效", True)

            if diceans < 0:
                return self.errorInfo("骰子的结果为0，生命值不修改")

            chp = chp[0]+str(diceans)
        else:
            # 直接修改生命为目标值的情形。不支持dicecalculator()，仅支持整数
            if not isint(chp) or int(chp) > 100 or int(chp) < 0:
                return self.errorInfo("参数无效", True)

        if cardi.status == STATUS_DEAD:
            return self.errorInfo("该角色已死亡")

        originhp = cardi.attr.HP
        if chp[0] == "+":
            cardi.attr.HP += int(chp[1:])
        elif chp[0] == "-":
            cardi.attr.HP -= int(chp[1:])
        else:
            cardi.attr.HP = int(chp)

        hpdiff = cardi.attr.HP - originhp
        if hpdiff == 0:
            return self.errorInfo("HP不变，目前HP："+str(cardi.attr.HP))

        if hpdiff < 0:
            # 承受伤害描述。分类为三种状态
            takedmg = -hpdiff
            if takedmg < cardi.attr.MAXHP//2:
                # 轻伤，若生命不降到0，不做任何事
                if takedmg >= originhp:
                    self.reply(
                        text="HP归0，角色昏迷", reply_to_message_id=rpmsgid)
            elif takedmg > cardi.attr.MAXHP:
                self.reply(
                    text="致死性伤害，角色死亡", reply_to_message_id=rpmsgid)
                cardi.status = STATUS_DEAD
            else:
                self.reply(text="角色受到重伤，请进行体质检定以维持清醒",
                           reply_to_message_id=rpmsgid)
                cardi.status = STATUS_SERIOUSLYWOUNDED
                if originhp <= takedmg:
                    self.reply(
                        text="HP归0，进入濒死状态", reply_to_message_id=rpmsgid)
                    cardi.status = STATUS_NEARDEATH

            if cardi.attr.HP < 0:
                cardi.attr.HP = 0

        else:
            # 恢复生命，可能脱离某种状态
            if cardi.attr.HP >= cardi.attr.MAXHP:
                cardi.attr.HP = cardi.attr.MAXHP
                self.reply(text="HP达到最大值", reply_to_message_id=rpmsgid)

            if hpdiff > 1 and originhp <= 1 and cardi.status == STATUS_NEARDEATH:
                self.reply(text="脱离濒死状态", reply_to_message_id=rpmsgid)
                cardi.status = STATUS_SERIOUSLYWOUNDED
        cardi.write()

        self.reply(text="生命值从"+str(originhp)+"修改为" +
                   str(cardi.attr.HP), reply_to_message_id=rpmsgid)
        return True

    @commandCallbackMethod
    def kill(self, update: Update, context: CallbackContext) -> bool:
        """使角色死亡。使用回复或者`@username`作为参数来选择对象撕卡。
        回复的优先级高于参数。"""

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorInfo("没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorInfo("没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorInfo("使用回复或@username指定恢复者")
            if not isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorInfo("参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorInfo("玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorInfo("找不到该玩家的卡。")

        if card.status == STATUS_DEAD:
            return self.errorInfo("角色已死亡")

        card.status = STATUS_DEAD
        self.reply("已撕卡")
        card.write()
        return True

    @commandCallbackMethod
    def link(self, update: Update, context: CallbackContext) -> bool:
        """获取群邀请链接，并私聊发送给用户。

        使用该指令必须要满足两个条件：指令发送者和bot都是该群管理员。"""

        if not isgroup(update):
            return self.errorInfo("在群聊使用该指令。")
        if not self.isadmin(self.lastchat, BOT_ID):
            return self.errorInfo("Bot没有权限")
        if not self.isadmin(self.lastchat, self.lastuser):
            return self.errorInfo("没有权限", True)

        adminid = self.lastuser
        gpid = update.effective_chat.id
        chat = context.bot.get_chat(chat_id=gpid)
        ivlink = chat.invite_link
        if not ivlink:
            ivlink = context.bot.export_chat_invite_link(chat_id=gpid)

        try:
            self.reply(
                chat_id=adminid, text="群："+chat.title+"的邀请链接：\n"+ivlink)
        except Exception:
            return self.errorInfo("邀请链接发送失败！")

        rtbutton = [[InlineKeyboardButton(
            text="跳转到私聊", callback_data="None", url="t.me/"+self.bot.username)]]
        rp_markup = InlineKeyboardMarkup(rtbutton)

        self.reply("群邀请链接已经私聊发送。", reply_markup=rp_markup)
        return True

    @commandCallbackMethod
    def mad(self, update: Update, context: CallbackContext) -> bool:
        """使角色陷入永久疯狂。使用回复或者`@username`作为参数来选择对象撕卡。
        回复的优先级高于参数。"""

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorInfo("没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorInfo("没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorInfo("使用回复或@username指定恢复者")
            if not isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorInfo("参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorInfo("玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorInfo("找不到该玩家的卡。")

        if card.status == STATUS_DEAD:
            return self.errorInfo("角色已死亡")

        if card.status == STATUS_PERMANENTINSANE:
            return self.errorInfo("角色已永久疯狂")

        card.status = STATUS_PERMANENTINSANE
        card.write()
        self.reply("已撕卡")
        return True

    @commandCallbackMethod
    def deletemsg(self, update: Update, context: CallbackContext) -> bool:
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

        delnum = 1
        chatid = getchatid(update)

        if isgroup(update) and not self.isadmin(self.lastchat, BOT_ID):
            return self.errorInfo("Bot没有管理权限")

        if isgroup(update) and self.checkaccess(self.forcegetplayer(update), self.forcegetgroup(update)) & (GROUPKP | GROUPADMIN) == 0:
            return self.errorInfo("没有权限", True)

        if len(context.args) >= 1:
            if not isint(context.args[0]) or int(context.args[0]) <= 0:
                return self.errorInfo("参数错误", True)
            delnum = int(context.args[0])
            if delnum > 10:
                return self.errorInfo("一次最多删除10条消息")

        lastmsgid = self.lastmsgid
        while delnum >= 0:  # 这是因为要连同delmsg指令的消息也要删掉
            if lastmsgid < -100:
                break
            try:
                context.bot.delete_message(
                    chat_id=chatid, message_id=lastmsgid)
            except Exception as e:
                if str(e).find("can't be deleted for everyone") != -1:
                    self.errorInfo("消息删除失败，发送时间较久的消息无法删除")
                    break
                lastmsgid -= 1
            else:
                delnum -= 1
                lastmsgid -= 1

        update.effective_chat.send_message("删除完成").delete()
        return True

    @commandCallbackMethod
    def recover(self, update: Update, context: CallbackContext) -> bool:
        """将重伤患者的状态恢复。使用回复或者`@username`作为参数来选择对象恢复。
        回复的优先级高于参数。"""

        kp = self.forcegetplayer(update)
        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorInfo("没有进行中的游戏", True)

        if kp != gp.kp:
            return self.errorInfo("没有权限", True)

        rppl = self.getreplyplayer(update)
        if rppl is None:
            if len(context.args) == 0:
                return self.errorInfo("使用回复或@username指定恢复者")
            if not isint(context.args[0]) or int(context.args[0]) < 0:
                return self.errorInfo("参数无效", True)

            rppl = self.getplayer(int(context.args[0]))
            if rppl is None:
                return self.errorInfo("玩家无效")

        card = self.findcardfromgame(gp.game, rppl)
        if card is None:
            return self.errorInfo("找不到该玩家的卡。")

        if card.status != STATUS_SERIOUSLYWOUNDED:
            return self.errorInfo("该角色没有重伤")

        card.status = STATUS_ALIVE
        self.reply("角色已恢复")
        card.write()
        return True

    @commandCallbackMethod
    def reload(self, update: Update, context: CallbackContext) -> bool:
        """重新读取所有文件，只有bot管理者可以使用"""

        if self.lastuser != ADMIN_ID:
            return self.errorInfo("没有权限", True)

        try:
            self.readall()
            self.construct()
        except Exception:
            return self.errorInfo("读取文件出现问题，请检查json文件！")

        self.reply('重新读取文件成功。')
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

        if isprivate(update):
            return self.errorInfo("请在群内用该指令设置规则")

        gp = self.forcegetgroup(update)

        if not self.isfromkp(update):
            return self.errorInfo("没有权限", True)

        if len(context.args) == 0:
            return self.errorInfo("需要参数", True)

        gprule = gp.rule

        ruledict: Dict[str, List[int]] = {}

        i = 0
        while i < len(context.args):
            j = i+1
            tplist: List[int] = []
            while j < len(context.args):
                if isint(context.args[j]):
                    tplist.append(int(context.args[j]))
                    j += 1
                else:
                    break
            ruledict[context.args[i]] = tplist
            i = j
        del i, j

        msg, ok = gprule.changeRules(ruledict)
        if not ok:
            return self.errorInfo(msg)

        self.reply(msg)
        return True

    def buttonswitchgamecard(self, query: CallbackQuery, args: List[str]) -> bool:
        kp = self.forcegetplayer(self.lastchat)
        cdid = int(args[1])
        card = self.getgamecard(cdid)

        if card is None:
            return self.errorHandlerQ(query, "没有这张卡")
        if card.player != kp:
            return self.errorHandlerQ(query, "这不是你的卡片")
        if card.group.kp != kp:
            return self.errorHandlerQ(query, "你不是对应群的kp")

        game = card.group.game if card.group.game is not None else card.group.pausedgame
        assert(game is not None)

        game.kpctrl = card
        game.write()
        query.edit_message_text("修改操纵的npc卡成功，现在正在使用："+card.getname())
        return True

    @buttonQueryHandleMethod
    def buttonHandler(self, *args, **kwargs):
        return {
            "switchgamecard": (BUTTON_SWITCHGAMECARD, self.buttonswitchgamecard)
        }
