# -*- coding:utf-8 -*-

import json
import logging
import signal
from inspect import isfunction
from os import getpid, kill
from typing import List

from telegram import Update
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler)
from telegram.ext.dispatcher import Dispatcher

import dicehandlers
from cfg import *
from dicehandlers import dicebot
from utils import *

dispatcher: Dispatcher = dicebot.updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def writehandlers(h: List[str]) -> None:
    """写入Handlers"""
    with open(PATH_HANDLERS, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=4, ensure_ascii=False)


def botexec(s: str, needreturn: bool = False):
    if not needreturn:
        try:
            exec(s)
        except Exception as e:
            return "执行失败"+str(e)
        return "执行成功"

    try:
        exec("t="+s)
    except Exception as e:
        dicebot.sendtoAdmin("执行失败"+str(e))
        return
    return locals()["t"]


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。使用方法：

    `/bot check`将检查数据的一致性。

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。

    `/bot exec --command`执行python代码，如果第一个参数是小写字母r，则计算后面的代码结果并返回"""
    if ischannel(update):
        return False
    chatinit(update, context)

    if dicebot.forcegetplayer(update).id != ADMIN_ID:
        return errorHandler(update, "没有权限", True)

    if len(context.args) == 0:
        return errorHandler(update, "需要参数", True)

    inst = context.args[0]
    if inst == "check":
        update.message.reply_text("开始数据维护")
        dicebot.checkconsistency()
        return True

    if inst == "stop":

        # 结束进程，先写入所有数据
        dicebot.writegroup()
        dicebot.writeplayer()
        dicebot.writecard()

        pid = getpid()
        dicebot.sendtoAdmin("进程被指令终止。")
        kill(pid, signal.SIGINT)  # 发送SIGINT，由updater.idle()接收信号结束bot。
        return True

    if inst == "restart":
        return dicehandlers.reload(update, context)

    if inst == "exec":
        if context.args[1] == 'r' and len(context.args) > 2:
            dicebot.sendtoAdmin(str(botexec(' '.join(context.args[2:]), True)))
            return True
        if len(context.args) > 1:
            ans = str(botexec(' '.join(context.args[1:])))
            dicebot.sendtoAdmin(ans)
            return True

        return errorHandler(update, "参数无效")

    return errorHandler(update, "没有这一指令", True)


def makehandlerlist() -> List[str]:
    """获得全部handlers同时，写入文件。忽略几个特殊的handlers"""
    ans: List[str] = []

    for key in dicehandlers.ALL_HANDLER:
        if isfunction(dicehandlers.ALL_HANDLER[key]):
            if key == "unknown" or key == "button" or key == "textHandler":
                continue
            ans.append(key)

    ans.sort()

    writehandlers(ans)

    return ans


def addhandlers() -> None:
    """自动地读取dicehandlers.py中的所有函数作为handlers，忽略几个特殊用途的handlers"""
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
    dispatcher.add_handler(MessageHandler(
        (Filters.text | Filters.status_update.migrate)
        & (~Filters.command)
        & (~Filters.audio)
        & (~Filters.video)
        & (~Filters.photo)
        & (~Filters.sticker), dicehandlers.textHandler))


def main() -> None:
    dispatcher.add_handler(CommandHandler('bot', bot))

    addhandlers()

    dicebot.updater.start_polling(drop_pending_updates=True)
    dicebot.updater.idle()


if __name__ == "__main__":
    main()
