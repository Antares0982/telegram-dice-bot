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
from dicehandlers import dicebot

dispatcher = dicebot.updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def botexec(s: str, needreturn: bool = False):
    if not needreturn:
        try:
            exec(s)
        except:
            dicebot.sendtoAdmin("执行失败")
        return

    try:
        exec("t="+s)
    except:
        dicebot.sendtoAdmin("执行失败")
        return 
    return locals()["t"]


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。使用方法：

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。

    `/bot exec --command`执行python代码，仅限bot控制者使用"""
    if dicehandlers.utils.getmsgfromid(update) != dicehandlers.utils.ADMIN_ID:
        return dicehandlers.utils.errorHandler(update, "没有权限", True)

    if len(context.args) == 0:
        return dicehandlers.utils.errorHandler(update, "参数无效", True)

    inst = context.args[0]
    if inst == "check":
        update.message.reply_text("开始数据自检")
        return True if dicehandlers.utils.botcheckdata("bot自检中……") else bool(dicehandlers.utils.sendtoAdmin("出现了未知的错误，请检查报错信息"))

    if inst == "stop":

        dicebot.sendtoAdmin("进程被指令终止。")

        # 结束进程，先写入所有数据
        dicebot.writegroup()
        dicebot.writeplayer()
        dicebot.writecard()

        pid = getpid()
        if platform == "win32":  # windows
            kill(pid, signal.SIGBREAK)
        else:  # Other
            kill(pid, signal.SIGKILL)

        return dicehandlers.utils.errorHandler(update, "关闭失败！")

    if inst == "restart":
        return dicehandlers.reload(update, context)

    if inst == "exec":
        if context.args[1] == 'r' and len(context.args) > 2:
            return botexec(context.args[2:], True)
        if len(context.args) > 1:
            ans = str(botexec(context.args[1:]))
            dicebot.sendtoAdmin(ans)

        return dicehandlers.utils.errorHandler(update, "参数无效")

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
        ~Filters.command) & (~Filters.audio) & (~Filters.video) & (~Filters.photo) & (~Filters.sticker), dicehandlers.textHandler))

    dicehandlers.utils.updater.start_polling(clean=True)
    dicehandlers.utils.updater.idle()


if __name__ == "__main__":
    main()

    asyncio.run(dicehandlers.utils.timer())
