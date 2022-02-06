#!/usr/bin/python3

import logging
from typing import List

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext.filters import Filters

from admincommand import adminCommand
from basebot import baseBot
from cardcreate import cardCreate
from cardhelper import cardHelper
from cardshowbot import cardShowBot
from cfg import ADMIN_ID
from commandCallback import commandCallbackMethod, isgroup
from dicecommand import diceCommand
from gamecontroller import gameController
from infoshow import infoShow
from kpcontroller import kpController
from noncommandhandle import nonCommandHandlers
from utils import getchatid, handleStatus, isfromme


class mainBot(
    adminCommand,
    cardCreate,
    cardHelper,
    cardShowBot,
    diceCommand,
    gameController,
    infoShow,
    kpController,
    nonCommandHandlers
):
    def __init__(self) -> None:
        print("subclass init")
        for cls in self.__class__.__bases__:
            cls.__init__(self)
        print("all subclasses init finished")

    @commandCallbackMethod
    def exec(self, update: Update, context: CallbackContext) -> None:
        if not isfromme(update):
            self.errorInfo("没有权限")
            return

        if len(context.args) == 0:
            self.errorInfo("没有接收到命令诶")
            return
        try:
            needReturn = False
            txt = update.message.text
            if context.args[0] == 'r':
                needReturn = True
                command = txt[txt.find("r ")+2:]
            else:
                command = ' '.join(context.args)

            if not command:
                raise ValueError

            if not needReturn:
                try:
                    exec(command)
                except Exception as e:
                    self.reply(text="执行失败……")
                    raise e
                self.reply(text="执行成功～")
            else:
                try:
                    exec("t="+command)
                    ans = locals()['t']
                except Exception as e:
                    self.reply(text="执行失败……")
                    raise e
                self.reply(text=f"执行成功，返回值：{ans}")
        except (TypeError, ValueError):
            self.reply(text="唔……似乎参数不对呢")
        except Exception as e:
            raise e

    def textHandler(self, update: Update, context: CallbackContext) -> bool:
        if update.message.migrate_to_chat_id is not None:
            self.chatmigrate(
                getchatid(update), update.message.migrate_to_chat_id)
            return True

        if Filters.status_update(update):
            return True

        self.renewStatus(update)
        if any(x in self.blacklist for x in (self.lastuser, self.lastchat)):
            return self.errorInfo("你在黑名单中，无法使用任何功能")

        for cls in self.__class__.__bases__:
            status: handleStatus = cls.textHandler(self, update, context)
            if status.blocked():
                return status.normal

        return False

    def buttonHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        update.callback_query.answer()

        if any(x in self.blacklist for x in (self.lastuser, self.lastchat)):
            return self.queryError(update.callback_query)

        if self.lastchat not in self.workingMethod or not self.workingMethod[self.lastchat]:
            return self.queryError(update.callback_query)

        if update.callback_query.data == "None" or isgroup(update):
            return False

        for cls in self.__class__.__bases__:
            status: handleStatus = cls.buttonHandler(self, update, context)
            if status.blocked():
                return status.normal

        return self.queryError(update.callback_query)

    def photoHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if self.lastchat in self.blacklist:
            return self.errorInfo("你在黑名单中，无法使用任何功能")

        for cls in self.__class__.__bases__:
            status: handleStatus = cls.photoHandler(self, update, context)
            if status.blocked():
                return status.normal

        return False

    def channelHandler(self, update: Update, context: CallbackContext) -> bool:
        self.renewStatus(update)
        if self.lastchat in self.blacklist:
            return False

        if update.channel_post is not None:
            for cls in self.__class__.__bases__:
                status: handleStatus = cls.channelHandler(
                    self, update, context)
                if status.blocked():
                    return status.normal

        elif update.edited_channel_post is not None:
            for cls in self.__class__.__bases__:
                status = cls.editedChannelHandler(
                    self, update, context)
                if status.blocked():
                    return status.normal

        return False

    def chatmigrate(self, oldchat: int, newchat: int):
        errs: List[Exception] = []
        try:
            baseBot.chatmigrate(self, oldchat, newchat)
        except Exception as e:
            errs.append(e)

        for kls in self.__class__.__bases__:
            try:
                kls.chatmigrate(self, oldchat, newchat)
            except Exception as e:
                errs.append(e)

        if len(errs) != 0:
            if len(errs) > 1:
                errstr = '\n'.join(str(x) for x in errs)
                raise RuntimeError(f"聊天迁移时抛出多于一个错误：{errstr}")
            raise errs[0]

    def beforestop(self):
        for cls in self.__class__.__bases__:
            cls.beforestop(self)


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    global mainbot

    pass
    mainbot = mainBot()
    try:
        mainbot.botstart()
    except Exception as e:
        mainbot.reply(
            chat_id=ADMIN_ID, text="读取文件出现问题，请检查json文件！")
        print("出现问题")
        raise e


if __name__ == "__main__":
    main()
