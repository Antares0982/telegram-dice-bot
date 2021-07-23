from dicebot import diceBot
from utils import *
from telegram.ext import CallbackContext
from gameclass import *

class nonCommandHandlers(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)
    

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """信息处理函数，用于无指令的消息处理。
        具体指令处理正常完成时再删除掉当前操作状态`OPERATION[chatid]`，处理出错时不删除。"""
        
        if update.message is None:
            return True

        if update.message.migrate_from_chat_id is not None:
            # 触发migrate
            oldid = update.message.migrate_from_chat_id
            if self.migrateto is not None:
                newid = self.migrateto
                self.migrateto = None
                self.groupmigrate(oldid, newid)
                self.sendtoAdmin(f"群{str(oldid)}迁移了，新的id：{str(newid)}")
                self.sendto(newid, "本群迁移了，原id"+str(oldid)+"新的id"+str(newid))
                return True

            # 等待获取migrateto
            self.migratefrom = oldid
            return True

        if update.message.migrate_to_chat_id is not None:
            # 触发migrate
            newid = update.message.migrate_to_chat_id
            if self.migratefrom is not None:
                oldid = self.migratefrom
                self.migratefrom = None
                self.groupmigrate(oldid, newid)
                self.sendtoAdmin(f"群{str(oldid)}迁移了，新的id：{str(newid)}")
                self.sendto(newid, "本群迁移了，原id"+str(oldid)+"新的id"+str(newid))
                return True

            # 等待获取migratefrom
            self.migrateto = newid
            return True

        if isgroup(update):
            gp = self.forcegetgroup(update)
            if gp.game is not None and gp.game.memfile != "":
                self.textmem(update)

        if update.message.text in ["cancel", "取消"]:
            update.message.reply_text("操作取消")
            self.popOP(getchatid(update))
            return True

        oper = self.getOP(getchatid(update))
        opers = oper.split(" ")
        if oper == "":
            self.botchat(update)
            return True
        if opers[0] == "newcard":
            return self.textnewcard(update, int(opers[2])) if len(opers) > 2 else self.textnewcard(update)
        if oper == "setage":
            return self.textsetage(update)
        if oper == "setname":  # 私聊情形
            return self.textsetname(update, 0)
        if opers[0] == "setname":  # 群消息情形
            return self.textsetname(update, int(opers[1]))
        if oper == "setsex":  # 私聊情形
            return self.textsetsex(update, 0)
        if opers[0] == "setsex":  # 群消息情形
            return self.textsetsex(update, int(opers[1]))
        if opers[0] == "delcard":
            return self.textdelcard(update, int(opers[1]))
        if opers[0] == "passjob":
            return self.textpassjob(update)
        if opers[0] == "passskill":
            return self.textpassskill(update)
        if oper == "startgame":
            return self.textstartgame(update)
        return False

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """所有按钮请求经该函数处理。功能十分复杂，拆分成多个子函数来处理。
        接收到按钮的参数后，转到对应的子函数处理。"""
        query: CallbackQuery = update.callback_query
        query.answer()

        if query.data == "None":
            return False
        if isgroup(update):
            return False

        args = query.data.split(" ")
        identifier = args[0]
        if identifier != self.IDENTIFIER:
            if args[1].find("dec") != -1:
                return self.errorHandlerQ(query, "该请求已经过期，请点击 /choosedec 重新进行操作。")
            return self.errorHandlerQ(query, "该请求已经过期。")

        chatid = getchatid(update)
        pl = self.forcegetplayer(query.from_user.id)
        card1 = pl.controlling
        args = args[1:]

        # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
        if args[0] == "job":  # Job in buttons must be classical
            return self.buttonjob(query, card1, args)
        # Increase skills already added, because sgskill is none. second arg is skillname
        if args[0] == "addmainskill":
            return self.buttonaddmainskill(query, card1, args)
        if args[0] == "cgmainskill":
            return self.buttoncgmainskill(query, card1, args)
        if args[0] == "addsgskill":
            return self.buttonaddsgskill(query, card1, args)
        if args[0] == "addintskill":
            return self.buttonaddintskill(query, card1, args)
        if args[0] == "cgintskill":
            return self.buttoncgintskill(query, card1, args)
        if args[0] == "choosedec":
            return self.buttonchoosedec(query, card1, args)
        if args[0].find("dec") != -1:
            return self.buttonsetdec(query, card1, args)
        if args[0] == "discard":
            return self.buttondiscard(query, chatid, args)
        if args[0] == "switch":
            return self.buttonswitch(query, chatid, args)
        if args[0] == "switchgamecard":
            return self.buttonswitchgamecard(query, chatid, args)
        if args[0] == "setsex":
            return self.buttonsetsex(query, chatid, args)
        if args[0] == "manual":
            return self.buttonmanual(query, chatid, args)
        # HIT BAD TRAP
        return False