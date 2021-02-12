# -*- coding:utf-8 -*-
# version: 1.0.1

import logging
import signal
import sys
import os
from telegram import Update
from telegram.ext import CallbackQueryHandler, MessageHandler, Filters, CommandHandler, CallbackContext

from gameclass import *
from botdicts import *
import dicehandlers


dispatcher = dicehandlers.updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。使用方法：

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。"""
    if update.message.from_user.id != ADMIN_ID:
        return dicehandlers.errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return dicehandlers.errorHandler(update, "参数无效", True)
    inst = context.args[0]
    if inst == "stop":
        # 寻找所有群
        gpids: List[int] = []
        for gpid in dicehandlers.CARDS_DICT:
            gpids.append(gpid)
        for gpid in dicehandlers.GROUP_KP_DICT:
            if gpid not in gpids:
                gpids.append(gpid)
        for gpid in gpids:
            context.bot.send_message(chat_id=gpid, text="Bot程序终止！")
        dicehandlers.sendtoAdmin("进程被指令终止。")
        # 结束进程，先写入所有数据
        writecards(dicehandlers.CARDS_DICT)
        writecurrentcarddict(dicehandlers.CURRENT_CARD_DICT)
        writekpinfo(dicehandlers.GROUP_KP_DICT)
        writegameinfo(dicehandlers.ON_GAME)
        pid = os.getpid()
        if sys.platform == "win32":  # windows
            os.kill(pid, signal.SIGBREAK)
        else:  # Other
            os.kill(pid, signal.SIGKILL)
        return dicehandlers.errorHandler(update, "关闭失败！")
    if inst == "restart":
        return dicehandlers.reload(update, context)
    return dicehandlers.errorHandler(update, "没有这一指令", True)


def main() -> None:
    dispatcher.add_handler(CommandHandler('bot', bot))

    dispatcher.add_handler(CommandHandler('start', dicehandlers.start))
    dispatcher.add_handler(CommandHandler('addkp', dicehandlers.addkp))
    dispatcher.add_handler(CommandHandler(
        'transferkp', dicehandlers.transferkp))
    dispatcher.add_handler(CommandHandler('delkp', dicehandlers.delkp))
    dispatcher.add_handler(CommandHandler('reload', dicehandlers.reload))
    dispatcher.add_handler(CommandHandler(
        'showuserlist', dicehandlers.showuserlist))
    dispatcher.add_handler(CommandHandler('getid', dicehandlers.getid))
    dispatcher.add_handler(CommandHandler('showrule', dicehandlers.showrule))
    dispatcher.add_handler(CommandHandler('setrule', dicehandlers.setrule))
    dispatcher.add_handler(CommandHandler(
        'createcardhelp', dicehandlers.createcardhelp))
    dispatcher.add_handler(CommandHandler('newcard', dicehandlers.newcard))
    dispatcher.add_handler(CommandHandler('discard', dicehandlers.discard))
    dispatcher.add_handler(CommandHandler('details', dicehandlers.details))
    dispatcher.add_handler(CommandHandler('setage', dicehandlers.setage))
    dispatcher.add_handler(CommandHandler('setstrdec', dicehandlers.setstrdec))
    dispatcher.add_handler(CommandHandler('setcondec', dicehandlers.setcondec))
    dispatcher.add_handler(CommandHandler('setjob', dicehandlers.setjob))
    dispatcher.add_handler(CommandHandler(
        'showjoblist', dicehandlers.showjoblist))
    dispatcher.add_handler(CommandHandler('addskill', dicehandlers.addskill))
    dispatcher.add_handler(CommandHandler(
        'showskilllist', dicehandlers.showskilllist))
    dispatcher.add_handler(CommandHandler('setname', dicehandlers.setname))
    dispatcher.add_handler(CommandHandler('startgame', dicehandlers.startgame))
    dispatcher.add_handler(CommandHandler('abortgame', dicehandlers.abortgame))
    dispatcher.add_handler(CommandHandler('endgame', dicehandlers.endgame))
    dispatcher.add_handler(CommandHandler('switch', dicehandlers.switch))
    dispatcher.add_handler(CommandHandler('switchkp', dicehandlers.switchkp))
    dispatcher.add_handler(CommandHandler('tempcheck', dicehandlers.tempcheck))
    dispatcher.add_handler(CommandHandler('roll', dicehandlers.roll))
    dispatcher.add_handler(CommandHandler('show', dicehandlers.show))
    dispatcher.add_handler(CommandHandler('showkp', dicehandlers.showkp))
    dispatcher.add_handler(CommandHandler('showcard', dicehandlers.showcard))
    dispatcher.add_handler(CommandHandler('showids', dicehandlers.showids))
    dispatcher.add_handler(CommandHandler('modify', dicehandlers.modify))
    dispatcher.add_handler(CommandHandler('changeid', dicehandlers.changeid))
    dispatcher.add_handler(CommandHandler(
        'changegroup', dicehandlers.changegroup))
    dispatcher.add_handler(CommandHandler(
        'randombackground', dicehandlers.randombackground))
    dispatcher.add_handler(CommandHandler(
        'setbkground', dicehandlers.setbkground))
    dispatcher.add_handler(CommandHandler('setsex', dicehandlers.setsex))
    dispatcher.add_handler(CommandHandler('sancheck', dicehandlers.sancheck))
    dispatcher.add_handler(CommandHandler('addcard', dicehandlers.addcard))
    dispatcher.add_handler(CommandHandler('help', dicehandlers.helper))
    dispatcher.add_handler(CallbackQueryHandler(dicehandlers.button))
    dispatcher.add_handler(MessageHandler(
        Filters.command, dicehandlers.unknown))
    dicehandlers.updater.start_polling(clean=True)


if __name__ == "__main__":
    main()
