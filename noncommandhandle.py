import time

from telegram.ext import CallbackContext

from dicebot import BUTTON_MANUAL, diceBot
from gameclass import *
from utils import *


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
        query: CallbackQuery = update.callback_query

        args = query.data.split(" ")

        workingmethod = self.workingMethod[self.lastchat]

        matchdict = {
            "manual": BUTTON_MANUAL
        }

        if args[0] not in matchdict:
            return handlePassed

        if workingmethod != matchdict[args[0]]:
            return handleBlocked(self.queryError(query))

        if args[0] == "manual":
            return handleBlocked(self.buttonmanual(query, args))
        # HIT BAD TRAP
        return handleBlocked(False)

    def chatmigrate(self, oldchat: int, newchat: int):
        self.groupmigrate(oldchat, newchat)
        self.reply(ADMIN_ID, f"群`{self.forcegetgroup(newchat).getname()}`升级了。\
            \n原id：`{oldchat}`，现在的id：`{newchat}`。", parse_mode="MarkdownV2")
