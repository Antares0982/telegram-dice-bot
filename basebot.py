import os
import sqlite3
import time
import traceback
from signal import SIGINT
from typing import Dict, List, Optional

from telegram import Bot, CallbackQuery, Update
from telegram.error import BadRequest, NetworkError, TimedOut
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler, Updater)

from utils import *


class baseBot(object):
    def __init__(self) -> None:
        if PROXY:
            self.updater = Updater(token=TOKEN, use_context=True, request_kwargs={
                                   "proxy_url": PROXY_URL})
        else:
            self.updater = Updater(token=TOKEN, use_context=True)

        self.bot: Bot = self.updater.bot
        self.workingMethod: Dict[int, str] = {}  # key为chat_id，而非user.id

        self.lastchat: int = ADMIN_ID
        self.lastuser: int = ADMIN_ID
        self.lastmsgid: int = -1  # 默认-1，如果是按钮响应需要调整到-1
        self.blacklist: List[int] = []
        self.readblacklist()

    def botstart(self) -> None:
        self.importHandlers()
        self.reply(ADMIN_ID, "Bot is live!")
        self.updater.start_polling(drop_pending_updates=True)
        self.updater.idle()

    def readblacklist(self):
        self.blacklist = []
        conn = sqlite3.connect(blacklistdatabase)
        c = conn.cursor()
        cur = c.execute("SELECT * FROM BLACKLIST;")
        ans = cur.fetchall()
        conn.close()
        for tgid in ans:
            self.blacklist.append(tgid)

    def addblacklist(self, id: int):
        if id in self.blacklist:
            return
        self.blacklist.append(id)
        conn = sqlite3.connect(blacklistdatabase)
        c = conn.cursor()
        c.execute(f"""INSERT INTO BLACKLIST(TGID)
        VALUES({id});""")
        conn.commit()
        conn.close()

    def renewStatus(self, update: Update) -> None:
        """在每个command Handler前调用，是指令的前置函数"""
        self.lastchat = getchatid(update)

        if update.callback_query is None:
            if ischannel(update):
                self.lastuser = -1
            else:
                self.lastuser = getfromid(update)
            self.lastmsgid = getmsgid(update)

        else:
            self.lastuser = update.callback_query.from_user.id
            self.lastmsgid = -1

    def reply(self, *args, **kwargs) -> int:
        """调用send_message方法，回复或发送消息。
        支持telegram bot中`send_message`方法的keyword argument，
        如`reply_markup`，`reply_to_message_id`，`parse_mode`，`timeout`。
        返回值是message id"""
        assert len(args) <= 2
        ans = None
        chat_id: Optional[int] = None
        text: str = None
        if len(args) > 0:
            if type(args[0]) is int:
                chat_id = args[0]
                kwargs["chat_id"] = chat_id
            elif type(args[0]) is str:
                text = args[0]
                kwargs["text"] = text

            if len(args) > 1:
                assert type(args[0]) is int
                assert type(args[1]) is str
                text = args[1]
                kwargs["text"] = text

        if chat_id is None and "chat_id" in kwargs:
            chat_id = kwargs["chat_id"]

        if text is None and "text" in kwargs:
            text = kwargs["text"]

        if not text:
            raise ValueError("发生错误：发送消息时没有文本")

        if chat_id is None:
            kwargs["chat_id"] = self.lastchat
            if self.lastmsgid >= 0 and "reply_to_message_id" not in kwargs:
                kwargs["reply_to_message_id"] = self.lastmsgid

        txts = text.split("\n")

        if len(txts) > 10 and len(text) >= 1024:
            while len(txts) > 10:
                kwargs["text"] = "\n".join(txts[:10])
                txts = txts[10:]
                for i in range(5):
                    try:
                        ans = self.bot.send_message(**kwargs).message_id
                        if "reply_markup" in kwargs:
                            kwargs.pop("reply_markup")
                    except Exception as e:
                        if i == 4:
                            raise e
                        time.sleep(5)
                    else:
                        break

        if len(txts) > 0:
            kwargs["text"] = "\n".join(txts)
            for i in range(5):
                try:
                    ans = self.bot.send_message(**kwargs).message_id
                except Exception as e:
                    if i == 4:
                        raise e
                    time.sleep(5)
                else:
                    break

        if ans is None:
            raise ValueError("没有成功发送消息")
        return ans

    def delmsg(self, chat_id: int, msgid: int, maxTries: int = 5) -> bool:
        """尝试删除消息`maxTries`次，该方法的目的是防止网络原因删除失败时导致执行出现失误"""
        assert maxTries > 0

        for i in range(maxTries):
            try:
                self.bot.delete_message(
                    chat_id=chat_id, message_id=msgid)
            except Exception:
                if i == 4:
                    return False
                continue
            break

        return True

    # def errorInfo(self, msg: str) -> False:
    #     self.reply(text=msg)
    #     return False

    def remove_job_if_exists(self, name: str) -> bool:
        """Remove job with given name. Returns whether job was removed."""

        current_jobs = self.updater.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True

    @staticmethod
    def queryError(query: CallbackQuery) -> False:
        try:
            query.edit_message_text(
                text="这个按钮请求已经无效了", reply_markup=None)
        except BadRequest:
            query.delete_message()
        return False

    def importHandlers(self) -> None:
        for key in self.__dir__():
            func = getattr(self, key)
            if type(func) is commandCallbackMethod:
                print(f"Handler added: {key}")
                self.updater.dispatcher.add_handler(CommandHandler(key, func))

        self.updater.dispatcher.add_handler(
            MessageHandler((Filters.text | Filters.status_update) & (~Filters.command) & (~Filters.video) & (
                ~Filters.photo) & (~Filters.sticker) & (~Filters.chat_type.channel), self.textHandler))

        self.updater.dispatcher.add_handler(MessageHandler(
            Filters.chat_type.channel, self.channelHandler))

        self.updater.dispatcher.add_handler(MessageHandler(
            (Filters.photo | Filters.sticker) & (~Filters.chat_type.channel), self.photoHandler))

        self.updater.dispatcher.add_handler(
            CallbackQueryHandler(self.buttonHandler))

        self.updater.dispatcher.add_error_handler(self.errorHandler)

        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.command, self.unknowncommand))

    # 指令
    @commandCallbackMethod
    def cancel(self, update: Update, context: CallbackContext) -> bool:
        if self.lastuser in self.workingMethod:
            self.workingMethod.pop(self.lastuser)
            self.reply(text="操作取消～")
            return True
        return False

    @commandCallbackMethod
    def stop(self, update: Update, context: CallbackContext) -> bool:
        if not isfromme(update):
            self.reply("你没有权限")
            return False
        try:
            self.beforestop()
        except Exception:
            ...
        self.reply(text="主人再见QAQ")
        pid = os.getpid()
        os.kill(pid, SIGINT)
        return True

    # @commandCallbackMethod
    # def getid(self, update: Update, context: CallbackContext) -> None:
    #     if ischannel(update):
    #         return
    #     if isgroup(update) and update.message.reply_to_message is not None:
    #         self.reply(
    #             text=f"群id：`{self.lastchat}`\n回复的消息的用户id：`{update.message.reply_to_message.from_user.id}`", parse_mode="MarkdownV2")
    #     elif isgroup(update):
    #         self.reply(
    #             text=f"群id：`{self.lastchat}`\n您的id：`{self.lastuser}`", parse_mode="MarkdownV2")
    #     elif isprivate(update):
    #         self.reply(text=f"您的id：\n{self.lastchat}", parse_mode="MarkdownV2")

    # 非指令的handlers，供重载用。如果需要定义别的类型的handlers，务必在此处创建虚函数

    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def channelHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def editedChannelHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        """Override"""
        return handlePassed

    # 错误处理
    def errorHandler(self, update: object, context: CallbackContext):
        err = context.error
        if err.__class__ in [NetworkError, OSError, TimedOut]:
            raise err

        self.reply(
            chat_id=ADMIN_ID,
            text=f"哎呀，出现了未知的错误呢……\n{err.__class__}\n\
                {err}\ntraceback:{traceback.format_exc()}")

    # 未知指令
    def unknowncommand(self, update: Update, context: CallbackContext):
        self.renewStatus(update)
        try:
            if not isfromme(update):
                self.reply("没有这个指令")
            else:
                self.reply("似乎没有这个指令呢……")
        except Exception:
            ...

    # 聊天迁移
    def chatmigrate(self, oldchat: int, newchat: int):
        """这里仅更新blacklist名单，其他需求请Override，不会影响本函数被调用"""
        conn = sqlite3.connect(blacklistdatabase)
        c = conn.cursor()
        c.execute(f"""UPDATE BLACKLIST
        SET TGID={newchat} WHERE TGID={oldchat}""")
        if oldchat in self.blacklist:
            self.blacklist[self.blacklist.index(oldchat)] = newchat

    # 关闭前执行
    def beforestop(self):
        """Override"""
        return
