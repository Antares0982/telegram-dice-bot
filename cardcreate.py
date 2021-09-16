from telegram.ext import CallbackContext

from dicebot import BUTTON_DISCARD, diceBot
from gameclass import *
from utils import *


class cardCreate(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

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
        if isgroup(update):
            return self.errorInfo("向我发送私聊消息来添加卡", True)
        if len(context.args) == 0:
            return self.errorInfo("需要参数")
        if (len(context.args)//2)*2 != len(context.args):
            self.reply("参数长度应该是偶数")

        t = templateNewCard()
        # 遍历args获取attr和val
        mem: List[str] = []
        for i in range(0, len(context.args), 2):
            argname: str = context.args[i]
            if argname in mem:
                return self.errorInfo(argname+"属性重复赋值")
            mem.append(argname)
            argval = context.args[i+1]

            if argname == "specialskill":
                skillname, skillval = argval.split(":")
                if not isint(skillval) or int(skillval) <= 0:
                    return self.errorInfo("技能值应该是正整数")
                t["skill"]["skills"][skillname] = int(skillval)
                continue

            if argname == "points":
                return self.errorInfo("points应指明是mainpoints还是intpoints")

            if argname == "mainpoints":
                argname = "points"
                dt = t["skill"]
            elif argname == "intpoints":
                argname = "points"
                dt = t["interest"]

            dt = findattrindict(t, argname)
            if not dt:  # 可能是技能，否则返回
                if argname in self.skilllist or argname == "母语" or argname == "闪避":
                    if not isint(argval) or int(argval) <= 0:
                        return self.errorInfo("技能值应该是正整数")

                    dt: dict = t["skill"]["skills"]
                    dt[argname] = 0  # 这一行是为了防止之后判断类型报错
                else:
                    return self.errorInfo("属性 "+argname+" 在角色卡模板中没有找到")

            if isinstance(dt[argname], dict):
                return self.errorInfo(argname+"是dict类型，不可直接赋值")

            if type(dt[argname]) is bool:
                if argval == "false" or argval == "False":
                    argval = False
                elif argval == "true" or argval == "True":
                    argval = True
                if not type(argval) is bool:
                    return self.errorInfo(argname+"应该为bool类型")
                dt[argname] = argval

            elif type(dt[argname]) is int:
                if not isint(argval):
                    return self.errorInfo(argname+"应该为int类型")
                dt[argname] = int(argval)

            else:
                dt[argname] = argval
        # 参数写入完成
        # 检查groupid是否输入了
        if t["groupid"] == 0:
            return self.errorInfo("需要groupid！")

        # 检查是否输入了以及是否有权限输入playerid
        pl = self.forcegetplayer(update)
        if not self.searchifkp(pl):
            if t["playerid"] != 0 and t["playerid"] != pl.id:
                return self.errorInfo("没有权限设置非自己的playerid")
            t["playerid"] = getchatid(update)
        else:
            if t["groupid"] not in pl.kpgroups and t["playerid"] != 0 and t["playerid"] != pl.id:
                return self.errorInfo("没有权限设置非自己的playerid")
            if t["playerid"] == 0:
                t["playerid"] = pl.id

        # 生成成功
        card1 = GameCard(t)
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

        return True if self.addonecard(card1) else self.errorInfo("卡id重复")

    @commandCallbackMethod
    def createcardhelp(self, update: Update, context: CallbackContext) -> None:

        self.reply(CREATE_CARD_HELP, parse_mode="MarkdownV2")

    @commandCallbackMethod
    def delcard(self, update: Update, context: CallbackContext) -> bool:
        """KP才能使用该指令，删除一张卡片。一次只能删除一张卡。
        `/delcard --cardid`：删除id为cardid的卡。"""

        if len(context.args) == 0:
            return self.errorInfo("需要卡id作为参数", True)
        if not isint(context.args[0]) or int(context.args[0]) < 0:
            return self.errorInfo("参数无效", True)

        cdid = int(context.args[0])
        card = self.getcard(cdid)

        if card is None:
            return self.errorInfo("找不到对应id的卡")

        kp = self.forcegetplayer(update)
        if not self.checkaccess(kp, card) & CANMODIFY:
            return self.errorInfo("没有权限", True)

        # 开始处理
        self.reply(
            f"请确认是否删除卡片\n姓名：{card.getname()}\n如果确认删除，请回复：确认。否则，请回复其他任何文字。")
        self.addOP(getchatid(update), "delcard "+context.args[0])
        return True

    def findAllDiscardCards(self, pl: Player) -> List[GameCard]:
        """返回`plid`对应的所有`discard`为`True`的卡"""
        return [card for card in pl.cards.values() if self.checkaccess(pl, card) & CANDISCARD]

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

        if isgroup(update):
            return self.errorInfo("发送私聊消息删除卡。")

        pl = self.getplayer(update)  # 发送者
        if pl is None:
            return self.errorInfo("找不到可删除的卡。")

        if len(context.args) > 0:
            # 先处理context.args
            if any(not isint(x) for x in context.args):
                return self.errorInfo("参数需要是整数")
            nargs = list(map(int, context.args))

            discards = self.findDiscardCardsWithGpidCdid(pl, nargs)

            # 求args提供的卡id与可删除的卡id的交集

            if len(discards) == 0:  # 交集为空集
                return self.errorInfo("输入的（群/卡片）ID均无效。")

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
            rtbuttons: List[List[InlineKeyboardButton]] = [[]]

            for card in discardgpcdTupleList:
                if len(rtbuttons[len(rtbuttons)-1]) == 4:
                    rtbuttons.append([])
                cardname = card.getname()
                rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(cardname,
                                                                        callback_data="discard "+str(card.id)))

            rp_markup = InlineKeyboardMarkup(rtbuttons)

            self.reply("请点击要删除的卡片：", reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_DISCARD
            return True

        if len(discardgpcdTupleList) == 1:
            card = discardgpcdTupleList[0]

            rttext = "删除卡："+card.getname()
            rttext += "\n删除操作不可逆。"
            self.reply(rttext)

            self.cardpop(card)
            return True

        # 没有可删除的卡
        return self.errorInfo("找不到可删除的卡。")

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

        gpid: int = None
        gp: Optional[Group] = None
        newcdid: Optional[int] = None

        if isgroup(update):
            # 先检查是否有该玩家信息
            rtbutton = [[InlineKeyboardButton(
                text="跳转到私聊", callback_data="None", url="t.me/"+self.bot.username)]]
            rp_markup = InlineKeyboardMarkup(rtbutton)
            if self.getplayer(update) is None:
                self.reply("请先开启与bot的私聊", reply_markup=rp_markup)
                return True

            if len(context.args) > 0:
                if not isint(context.args[0]) or int(context.args[0]) < 0:
                    return self.errorInfo("参数无效")

            gpid = getchatid(update)
            gp = self.forcegetgroup(gpid)
            if len(context.args) > 0:
                newcdid = int(context.args[0])

        elif len(context.args) > 0:
            msg = context.args[0]

            if not isint(msg):
                return self.errorInfo("输入无效")

            if int(msg) >= 0:
                newcdid = int(msg)
            else:
                gpid = int(msg)
                gp = self.forcegetgroup(gpid)
                if len(context.args) > 1:
                    if not isint(context.args[1]) or int(context.args[1]) < 0:
                        return self.errorInfo("输入无效")
                    newcdid = int(context.args[1])

        if gp is None:
            self.reply(
                "准备创建新卡。\n如果你不知道群id，在群里发送 /getid 即可创建角色卡。\n你也可以选择手动输入群id，请发送群id：")
            if newcdid is None:
                self.addOP(getchatid(update), "newcard " +
                           str(update.message.message_id))
            else:
                self.addOP(getchatid(update), "newcard " +
                           str(update.message.message_id)+" "+str(newcdid))
            return True

        # 检查(pl)是否已经有卡
        pl = self.forcegetplayer(update)
        plid = pl.id
        if self.hascard(plid, gpid) and pl != gp.kp:
            return self.errorInfo("你在这个群已经有一张卡了！")

        # 符合建卡条件，生成新卡
        # gp is not None
        assert(gpid is not None)

        remsgid = None
        if isprivate(update):
            remsgid = update.message.message_id
        else:
            assert rp_markup
            self.reply("建卡信息已经私聊发送", reply_markup=rp_markup)

        return self.getnewcard(remsgid, gpid, plid, newcdid)

    @commandCallbackMethod
    def renewcard(self, update: Update, context: CallbackContext) -> bool:
        """如果卡片是可以discard的状态，使用该指令可以将卡片重置。"""

        pl = self.forcegetplayer(update)
        if pl.controlling is None:
            return self.errorInfo("没有操作中的卡")
        f = self.checkaccess(pl, pl.controlling)
        if f & CANDISCARD == 0:
            return self.errorInfo("选中的卡不可重置。如果您使用了 /switch 切换操作中的卡，请使用 /switch 切换回要重置的卡")

        pl.controlling.backtonewcard()
        pl.controlling.interest.points = pl.controlling.data.INT*2
        self.reply(pl.controlling.data.datainfo)
        if pl.controlling.data.countless50discard():
            pl.controlling.discard = True
            self.reply(
                "因为有三项属性小于50，如果你愿意的话可以再次点击 /renewcard 来重置这张角色卡。如果停止创建卡，点击 /discard 来放弃建卡。\n设定年龄后则不能再删除这张卡。")
        else:
            pl.controlling.discard = False
        return True

    @commandCallbackMethod
    def trynewcard(self, update: Update, context: CallbackContext) -> bool:
        """测试建卡，用于熟悉建卡流程。
        测试创建的卡一定可以删除。
        创建新卡指令的帮助见`/help newcard`，
        对建卡过程有疑问，见 `/createcardhelp`。"""

        if isgroup(update):
            return self.errorInfo("发送私聊消息创建角色卡。")

        gp = self.getgp(-1)
        if gp is None:
            gp = self.creategp(-1)
            gp.kp = self.forcegetplayer(ADMIN_ID)

        return self.getnewcard(self.lastmsgid, -1, getchatid(update))

    def buttondiscard(self, query: CallbackQuery, args: List[str]) -> bool:
        cdid = int(args[1])

        card = self.getcard(cdid)
        if card is None:
            return self.errorHandlerQ(query, "找不到这个id的卡。")

        pl = self.forcegetplayer(self.lastchat)
        if not self.checkaccess(pl, card) & CANDISCARD:
            return self.errorHandlerQ(query, "该卡不可删除。")

        self.cardpop(cdid)

        query.edit_message_text(f"删除了：{card.getname()}。\n该删除操作不可逆。")
        return True

    @buttonQueryHandleMethod
    def buttonHandler(self, *args, **kwargs):
        return {
            "discard": (BUTTON_DISCARD, self.buttondiscard)
        }
