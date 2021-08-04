import time

from telegram.ext import CallbackContext
from typing_extensions import TYPE_CHECKING

from dicebot import diceBot
from gameclass import *
from utils import *

if TYPE_CHECKING:
    from main_dicebot import mainBot


class nonCommandHandlers(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    def findcardwithid(self, cdid: int) -> Optional[GameCard]:
        """输入一个卡id，返回这张卡"""
        for gp in self.groups.values():
            if cdid in gp.cards:
                return gp.cards[cdid]
        return None

    def buttonjob(self, query: CallbackQuery, card1: GameCard, args: List[str]) -> bool:
        jobname = args[1]
        if len(args) == 2:
            # 切换至显示职业详情
            jobinfo = self.joblist[jobname]
            rttext = "如果确认选择该职业，请点击下面按钮进行确认。职业信息如下\n信用点范围："
            rttext += str(jobinfo[0])+"至"+str(jobinfo[1])+"\n"
            pointsrule = jobinfo[2]
            sep = ""
            for key in pointsrule:
                if len(key) < 4:
                    rttext += sep+key+"*"+str(pointsrule[key])
                elif len(key) == 7:
                    rttext += sep+key[:3]+"或"+key[4:] + \
                        "之一*"+str(pointsrule[key])
                else:
                    rttext += sep+key[:3]+"或"+key[4:7]+"或" + \
                        key[8:]+"之一*"+str(pointsrule[key])
                sep = "+"
            rttext += "\n推荐技能：\n"
            sep = ""
            for i in range(3, len(jobinfo)):
                rttext += sep+jobinfo[i]
                sep = "，"

            IDENTIFIER = self.IDENTIFIER
            rtbuttons = [[
                InlineKeyboardButton(
                    text="确认", callback_data=IDENTIFIER+" job "+jobname+" True"),
                InlineKeyboardButton(
                    text="返回", callback_data=IDENTIFIER+" job "+jobname+" False")
            ]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text(rttext, reply_markup=rp_markup)
            return True
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        confirm = args[2]  # 只能是True，或False
        if confirm == "False":
            rtbuttons = self.makejobbutton()
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text("请选择职业查看详情：", reply_markup=rp_markup)
            return True
        # 确认完成
        card1.info.job = jobname
        query.edit_message_text(
            "职业设置为："+jobname+"\n现在你可以用指令 /addskill 添加技能，首先需要设置信用点。")
        if not self.generatePoints(card1):
            self.sendtoAdmin("生成技能出错，位置：buttonjob")
            return self.errorHandlerQ(query, "生成技能点出错！")
        for i in range(3, len(self.joblist[jobname])):  # Classical jobs
            card1.suggestskill.set(self.joblist[jobname][i], self.getskilllevelfromdict(
                card1, self.joblist[jobname][i]))   # int
        card1.group.write()
        return True

    def buttonaddmainskill(self, query: CallbackQuery, card1: GameCard, args: List[str]) -> bool:

        if card1 is None:
            return self.errorHandlerQ(query, "找不到卡。")

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        return True

    def buttoncgmainskill(self, query: CallbackQuery,  card1: GameCard, args: List[str]) -> bool:
        if card1 is None:
            return self.errorHandlerQ(query, "找不到卡。")

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.skill.get(args[1])), reply_markup=rp_markup)
        return True

    def buttonaddsgskill(self, query: CallbackQuery,  card1: Optional[GameCard], args: List[str]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.suggestskill.pop(args[1])
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        return True

    def buttonaddintskill(self, query: CallbackQuery,  card1: Optional[GameCard], args: List[str]) -> bool:
        """响应KeyboardButton的addintskill请求。

        因为使用的是能翻页的列表，所以有可能位置1的参数是`page`，
        且位置2的参数是页码。"""
        if args[1] == "page":
            rttext, rtbuttons = self.showskillpages(int(args[2]), card1)
            query.edit_message_text(rttext)
            query.edit_message_reply_markup(InlineKeyboardMarkup(rtbuttons))
            return True

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, False)
            card1.interest.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
            card1.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            else:
                self.sendto(
                    card1.player, "接下来，如果没有设置过的话，请使用 /setname 设置姓名、 /setsex 设置性别、 /setbkg 设置背景信息。")
                self.reply(
                    card1.player.id, "背景设定中必要的部分有：故事、信仰、重要之人、意义非凡之地、珍视之物、性格特质。如果需要帮助，请点击`/help setbkg`并发送给我。", parse_mode="MarkdownV2")
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, False)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加兴趣技能。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        return True

    def buttoncgintskill(self, query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, False)
            card1.interest.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, False)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.interest.get(args[1])), reply_markup=rp_markup)
        return True

    def buttonchoosedec(self, query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")

        if card1.data.datadec is None:
            return self.errorHandlerQ(query, "不需要设置降值。")

        dname = args[1]
        decnames = card1.data.datadec[0].split('_')
        if dname not in decnames:
            return self.errorHandlerQ(query, "无法为该属性设置降值。")

        if len(decnames) == 2:
            anotherdecname = decnames[0] if dname == decnames[1] else decnames[1]
            rtbuttons = self.makeIntButtons(max(0, 1-card1.data.__dict__[anotherdecname]-card1.data.datadec[1]), min(
                card1.data.__dict__[dname]-1, -card1.data.datadec[1]), f"{dname}dec", "", 1)
        elif len(decnames) == 3:
            decnames.pop(decnames.index(dname))
            d1 = decnames[0]
            d2 = decnames[1]
            rtbuttons = self.makeIntButtons(max(0, 2-card1.data.__dict__[d1]-card1.data.__dict__[d2]-card1.data.datadec[1]), min(
                card1.data.__dict__[dname]-1, -card1.data.datadec[1]
            ), f"{dname}dec", "", 1)
        else:
            raise ValueError("datadec参数错误")

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            f"选择下降值，目前全部数值如下：\n{str(card1.data)}", reply_markup=rp_markup)

        return True

    def buttonsetdec(self, query: CallbackQuery, card1: Optional[GameCard], args: List[str]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")

        dname = args[0][:args[0].find("dec")]
        if dname not in card1.data.alldatanames:
            self.sendtoAdmin("属性名错误，请检查代码")
            return self.errorHandlerQ(query, "属性名错误，请检查代码")
        if card1.data.datadec is None:
            return self.errorHandlerQ(query, "该卡无需设置属性降值。")

        decnames = card1.data.datadec[0].split('_')
        decval = int(args[2])

        assert(card1.data.__dict__[dname]-decval >= 1)
        assert(card1.data.datadec[1]+decval <= 0)

        if len(decnames) == 2:
            otherdec = decnames[0] if dname == decnames[1] else decnames[1]
            assert(card1.data.__dict__[otherdec] +
                   card1.data.datadec[1]+decval >= 1)

            card1.data.__dict__[dname] -= decval
            card1.data.__dict__[otherdec] += card1.data.datadec[1]+decval
            card1.data.datadec = None

            card1.generateOtherAttributes()

            query.edit_message_text(
                f"属性下降设置完成，现在基础属性：\n{str(card1.data)}\n请点击 /setjob 设置职业。")
            return True

        if len(decnames) == 3:
            decnames.pop(decnames.index(dname))

            card1.data.__dict__[dname] -= decval
            card1.data.datadec = ('_'.join(decnames),
                                  card1.data.datadec[1]+decval)
            card1.write()

            query.edit_message_text(f"请继续设置属性降值，目前全部数值如下：\n{str(card1.data)}")

            rtbuttons = [[]]
            for dname in decnames:
                rtbuttons[0].append(InlineKeyboardButton(
                    text=dname, callback_data=self.IDENTIFIER+" choosedec "+dname))

            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_reply_markup(reply_markup=rp_markup)
            return True

        self.sendtoAdmin("下降属性参数长度有误")
        return self.errorHandlerQ(query, "下降属性参数长度有误")

    def buttondiscard(self, query: CallbackQuery, plid: int, args: List[str]) -> bool:
        cdid = int(args[1])

        card = self.getcard(cdid)
        if card is None:
            return self.errorHandlerQ(query, "找不到这个id的卡。")

        pl = self.forcegetplayer(plid)
        if not self.checkaccess(pl, card) & CANDISCARD:
            return self.errorHandlerQ(query, "该卡不可删除。")

        self.cardpop(cdid)

        query.edit_message_text(f"删除了：{card.getname()}。\n该删除操作不可逆。")
        return True

    def buttonswitch(self, query: CallbackQuery, plid: int, args: List[str]) -> bool:
        pl = self.forcegetplayer(plid)
        cdid = int(args[1])

        if cdid not in pl.cards:
            return self.errorHandlerQ(query, "没有找到这个id的卡。")

        pl.controlling = pl.cards[cdid]
        pl.write()

        query.edit_message_text("修改成功，现在操作的卡是："+pl.controlling.getname())
        return True

    def buttonswitchgamecard(self, query: CallbackQuery, kpid: int, args: List[str]) -> bool:
        kp = self.forcegetplayer(kpid)
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

    def textnewcard(self, update: Update, cdid: int = -1) -> bool:
        text = update.message.text
        pl = self.forcegetplayer(update)

        if not isint(text) or int(text) >= 0:
            return self.errorInfo("无效群id。如果你不知道群id，在群里发送 /getid 获取群id。")
        gpid = int(text)
        self.popOP(pl.id)

        if self.hascard(pl.id, gpid) and self.forcegetgroup(gpid).kp != pl:
            return self.errorInfo("你在这个群已经有一张卡了！")

        return self.getnewcard(update.message.message_id, gpid, pl.id, cdid)

    def textsetage(self, update: Update) -> bool:
        text = update.message.text
        plid = getchatid(update)
        if not isint(text):
            return self.errorInfo("输入无效，请重新输入")
        cardi = self.findcard(plid)
        if not cardi:
            self.popOP(plid)
            return self.errorInfo("找不到卡")

        return (bool(self.popOP(plid)) or True) if self.cardsetage(update, cardi, int(text)) else False

    def textstartgame(self, update: Update) -> bool:
        gp = self.getgp(update)
        if self.getplayer(update) != gp.kp:
            return True

        if update.message.text == "记录":
            self.reply(
                "开启记录模式。记录时若开头有中英文左小括号，该条消息记录用户的名字；否则记录角色卡的名字。撤回的消息也会被记录，非文本不会被记录。")
            self.atgamestart(gp)
            self.reply("游戏开始！")
            gp.game.memfile = str(time.time())+".txt"
            gp.game.write()
            self.popOP(gp.id)
            self.addOP(gp.id, "textmem")
            return True

        self.atgamestart(gp)
        self.reply("游戏开始！")
        self.popOP(gp.id)
        return True

    def textmem(self, update: Update) -> bool:
        gp = self.getgp(update)

        txt = update.message.text
        if txt == "":
            return True

        if self.getplayer(update) == gp.kp:
            name = f"(KP){gp.kp.getname()}"
            if txt[0] in ["(", "（"]:
                txt = txt[1:]
        elif txt[0] in ["(", "（"]:
            name = self.getplayer(update).getname()
            txt = txt[1:]
        else:
            card = self.findcardfromgame(gp.game, self.getplayer(update))
            if card is not None:
                name = card.getname()
            else:
                name = self.getplayer(update).getname()

        with open(PATH_MEM+gp.game.memfile, "a", encoding='utf-8') as f:
            f.write(f"{name}:{txt}\n")

        return True

    def textpassskill(self, update: Update) -> bool:
        t = update.message.text.split()
        if getmsgfromid(update) != ADMIN_ID or (t[0] != "skillcomfirm" and t[0] != "skillreject"):
            self.botchat(update)
            return True

        if len(t) < 2 or not isint(t[1]):
            return self.errorInfo("参数无效")

        plid = int(t[1])
        if plid not in self.addskillrequest:
            return self.errorInfo("没有该id的技能新增申请")

        self.popOP(ADMIN_ID)
        if t[0] == "skillcomfirm":
            self.skilllist[self.addskillrequest[plid]
                           [0]] = self.addskillrequest[plid][1]

            with open(PATH_SKILLDICT, 'w', encoding='utf-8') as f:
                json.dump(self.skilllist, f, indent=4, ensure_ascii=False)

            self.reply(plid, "您的新增技能申请已通过。")

        else:
            self.reply(plid, "您的新增技能申请没有通过。")

        return True

    def textpassjob(self, update: Update) -> bool:
        t = update.message.text.split()
        if getmsgfromid(update) != ADMIN_ID or (t[0] != "jobcomfirm" and t[0] != "jobreject"):
            self.botchat(update)
            return

        if len(t) < 2 or not isint(t[1]):
            return self.errorInfo("参数无效")

        plid = int(t[1])
        if plid not in self.addjobrequest:
            return self.errorInfo("没有该id的职业新增申请")

        self.popOP(ADMIN_ID)
        if t[0] == "jobcomfirm":
            self.joblist[self.addjobrequest[plid]
                         [0]] = self.addjobrequest[plid][1]

            with open(PATH_JOBDICT, 'w', encoding='utf-8') as f:
                json.dump(self.joblist, f, indent=4, ensure_ascii=False)

            self.reply(plid, "您的新增职业申请已通过。")

        else:
            self.reply(plid, "您的新增职业申请没有通过。")

        return True

    def textdelcard(self, update: Update, cardid: int) -> bool:
        cardi = self.findcardwithid(cardid)
        if not cardi:
            self.popOP(update.effective_chat.id)
            return self.errorInfo("找不到卡。")

        kpid = getmsgfromid(update)
        if cardi.group.kp is None or kpid != cardi.group.kp.id:
            return True

        self.popOP(update.effective_chat.id)
        if update.message.text != "确认":
            self.reply("已经取消删除卡片操作。")
        else:
            self.reply("卡片已删除。")
            self.popcard(cardid)
        return True

    def textsetsex(self, update: Update, plid: int) -> bool:
        if plid == 0:  # 私聊情形
            plid = getchatid(update)

        if getmsgfromid(update) != plid:
            return True

        self.popOP(getchatid(update))
        text = update.message.text

        cardi = self.findcard(plid)
        if not cardi:
            return self.errorInfo("找不到卡。")
        return self.cardsetsex(update, cardi, text)

    def textsetname(self, update: Update, plid: int) -> bool:
        if plid == 0:  # 私聊情形
            plid = getchatid(update)

        if getmsgfromid(update) != plid:
            return True  # 不处理

        self.popOP(getchatid(update))

        text = ' '.join(update.message.text.split())

        cardi = self.findcard(plid)
        if not cardi:
            return self.errorInfo("找不到卡。")

        self.nameset(cardi, text)
        self.reply("姓名设置完成："+text)
        return True

    def botchat(self, update: Update) -> None:
        if isgroupmsg(update) or update.message is None or update.message.text == "":
            return
        text = update.message.text
        try:
            rttext = text+" = "+str(dicecalculator(text))
            self.reply(rttext)
            return
        except Exception:
            ...
        if text[:1] == "我":
            self.reply("你"+text[1:])
            return
        if text.find("傻逼") != -1 or text.find("sb") != -1:
            self.reply("傻逼")
            return

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """信息处理函数，用于无指令的消息处理。
        具体指令处理正常完成时再删除掉当前操作状态`OPERATION[chatid]`，处理出错时不删除。"""

        if update.message is None:
            return handleBlocked(False)

        if isgroup(update):
            gp = self.forcegetgroup(update)
            if gp.game is not None and gp.game.memfile != "":
                self.textmem(update)

        if update.message.text in ["cancel", "取消"]:
            self.reply("操作取消")
            self.popOP(getchatid(update))
            return handleBlocked()

        oper = self.getOP(getchatid(update))
        opers = oper.split(" ")
        if oper == "":
            self.botchat(update)
            return handleBlocked()
        if opers[0] == "newcard":
            return handleBlocked(self.textnewcard(update, int(opers[2])) if len(opers) > 2 else self.textnewcard(update))
        if oper == "setage":
            return handleBlocked(self.textsetage(update))
        if oper == "setname":  # 私聊情形
            return handleBlocked(self.textsetname(update, 0))
        if opers[0] == "setname":  # 群消息情形
            return handleBlocked(self.textsetname(update, int(opers[1])))
        if oper == "setsex":  # 私聊情形
            return handleBlocked(self.textsetsex(update, 0))
        if opers[0] == "setsex":  # 群消息情形
            return handleBlocked(self.textsetsex(update, int(opers[1])))
        if opers[0] == "delcard":
            return handleBlocked(self.textdelcard(update, int(opers[1])))
        if opers[0] == "passjob":
            return handleBlocked(self.textpassjob(update))
        if opers[0] == "passskill":
            return handleBlocked(self.textpassskill(update))
        if oper == "startgame":
            return handleBlocked(self.textstartgame(update))
        return handleBlocked(False)

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """所有按钮请求经该函数处理。功能十分复杂，拆分成多个子函数来处理。
        接收到按钮的参数后，转到对应的子函数处理。"""
        query: CallbackQuery = update.callback_query

        if query.data == "None" or isgroup(update):
            return handleBlocked(False)

        args = query.data.split(" ")
        identifier = args[0]
        if identifier != self.IDENTIFIER:
            if args[1].find("dec") != -1:
                return handleBlocked(self.errorHandlerQ(query, "该请求已经过期，请点击 /choosedec 重新进行操作。"))
            return handleBlocked(self.errorHandlerQ(query, "该请求已经过期。"))

        chatid = getchatid(update)
        pl = self.forcegetplayer(query.from_user.id)
        card1 = pl.controlling
        args = args[1:]

        # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
        if args[0] == "job":  # Job in buttons must be classical
            return handleBlocked(self.buttonjob(query, card1, args))
        # Increase skills already added, because sgskill is none. second arg is skillname
        if args[0] == "addmainskill":
            return handleBlocked(self.buttonaddmainskill(query, card1, args))
        if args[0] == "cgmainskill":
            return handleBlocked(self.buttoncgmainskill(query, card1, args))
        if args[0] == "addsgskill":
            return handleBlocked(self.buttonaddsgskill(query, card1, args))
        if args[0] == "addintskill":
            return handleBlocked(self.buttonaddintskill(query, card1, args))
        if args[0] == "cgintskill":
            return handleBlocked(self.buttoncgintskill(query, card1, args))
        if args[0] == "choosedec":
            return handleBlocked(self.buttonchoosedec(query, card1, args))
        if args[0].find("dec") != -1:
            return handleBlocked(self.buttonsetdec(query, card1, args))
        if args[0] == "discard":
            return handleBlocked(self.buttondiscard(query, chatid, args))
        if args[0] == "switch":
            return handleBlocked(self.buttonswitch(query, chatid, args))
        if args[0] == "switchgamecard":
            return handleBlocked(self.buttonswitchgamecard(query, chatid, args))
        if args[0] == "setsex":
            return handleBlocked(self.buttonsetsex(query, chatid, args))
        if args[0] == "manual":
            return handleBlocked(self.buttonmanual(query, chatid, args))
        # HIT BAD TRAP
        return handleBlocked(False)

    def chatmigrate(self, oldchat: int, newchat: int):
        self.groupmigrate(oldchat, newchat)
        self.reply(ADMIN_ID, f"群`{self.forcegetgroup(newchat).getname()}`升级了。\
            \n原id：`{oldchat}`，现在的id：`{newchat}`。", parse_mode="MarkdownV2")
