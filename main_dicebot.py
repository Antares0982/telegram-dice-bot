# -*- coding:utf-8 -*-
# version: 1.0.9

import asyncio
import logging
import signal
from inspect import isfunction
from os import getpid, kill
from sys import platform
from typing import List

from telegram import Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler)

import dicehandlers

dispatcher = dicehandlers.utils.dicebot.updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。使用方法：

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。"""
    if dicehandlers.utils.getmsgfromid(update) != dicehandlers.utils.ADMIN_ID:
        return dicehandlers.utils.errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return dicehandlers.utils.errorHandler(update, "参数无效", True)
    inst = context.args[0]
    if inst == "check":
        update.message.reply_text("开始数据自检")
        if not dicehandlers.utils.botcheckdata("bot自检中……"):
            dicehandlers.utils.sendtoAdmin("出现了未知的错误，请检查报错信息")
            return False
        return True
    if inst == "stop":
        if not dicehandlers.utils.botcheckdata("Bot程序终止！", False):
            dicehandlers.utils.sendtoAdmin("出现了未知的错误，请检查报错信息")
        dicehandlers.utils.sendtoAdmin("进程被指令终止。")
        # 结束进程，先写入所有数据
        dicehandlers.utils.writecards(dicehandlers.utils.CARDS_DICT)
        dicehandlers.utils.writecurrentcarddict(
            dicehandlers.utils.CURRENT_CARD_DICT)
        dicehandlers.utils.writekpinfo(dicehandlers.utils.GROUP_KP_DICT)
        dicehandlers.utils.writegameinfo(dicehandlers.utils.ON_GAME)
        pid = getpid()
        if platform == "win32":  # windows
            kill(pid, signal.SIGBREAK)
        else:  # Other
            kill(pid, signal.SIGKILL)
        return dicehandlers.utils.errorHandler(update, "关闭失败！")
    if inst == "restart":
        return dicehandlers.reload(update, context)
    return dicehandlers.utils.errorHandler(update, "没有这一指令", True)


def makehandlerlist() -> List[str]:
    """获得全部handlers同时，写入文件"""
    ans: List[str] = []
    for key in dicehandlers.ALL_HANDLER:
        if isfunction(dicehandlers.ALL_HANDLER[key]):
            if key == "unknown" or key == "button" or key == "textHandler":
                continue
            ans.append(key)
    ans.sort()
    dicehandlers.utils.writehandlers(ans)
    return ans


def main() -> None:
    dispatcher.add_handler(CommandHandler('bot', bot))
    handlerlist = makehandlerlist()
    for key in handlerlist:
        if key == "helper":
            cmdname = "help"
        else:
            cmdname = key
        dispatcher.add_handler(CommandHandler(
            cmdname, dicehandlers.ALL_HANDLER[key]))
    dispatcher.add_handler(CallbackQueryHandler(dicehandlers.button))
    dispatcher.add_handler(MessageHandler(
        Filters.command, dicehandlers.unknown))
    dispatcher.add_handler(MessageHandler(Filters.text & (
        ~Filters.command), dicehandlers.textHandler))
    dicehandlers.utils.updater.start_polling(clean=True)


if __name__ == "__main__":
    main()
    asyncio.run(dicehandlers.utils.timer())
