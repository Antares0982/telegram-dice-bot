# -*- coding:utf-8 -*-
# version: 1.0.1

import logging
import signal
import sys
import os

from telegram.ext import CallbackQueryHandler, MessageHandler, Filters, CommandHandler

from gameclass import *
from botdicts import *
from dicehandlers import *


dispatcher = updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。"""
    if update.message.from_user.id != ADMIN_ID:
        return errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return errorHandler(update, "参数无效", True)
    inst = context.args[0]
    if inst == "stop":
        # 寻找所有群
        gpids: List[int] = []
        for gpid in CARDS_DICT:
            gpids.append(gpid)
        for gpid in GROUP_KP_DICT:
            if gpid not in gpids:
                gpids.append(gpid)
        for gpid in gpids:
            context.bot.send_message(chat_id=gpid, text="Bot程序终止！")
        context.bot.send_message(chat_id=ADMIN_ID, text="进程被指令终止。")
        # 结束进程，先写入所有数据
        writecards(CARDS_DICT)
        writecurrentcarddict(CURRENT_CARD_DICT)
        writekpinfo(GROUP_KP_DICT)
        writegameinfo(ON_GAME)
        pid = os.getpid()
        if sys.platform == "win32":  # windows
            os.kill(pid, signal.CTRL_C_EVENT)
        else:  # Other
            os.kill(pid, signal.SIGKILL)
        return True
    elif inst == "restart":
        return reload(update, context)


def main() -> None:
    dispatcher.add_handler(CommandHandler('bot', bot))

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('addkp', addkp))
    dispatcher.add_handler(CommandHandler('transferkp', transferkp))
    dispatcher.add_handler(CommandHandler('delkp', delkp))
    dispatcher.add_handler(CommandHandler('reload', reload))
    dispatcher.add_handler(CommandHandler('showuserlist', showuserlist))
    dispatcher.add_handler(CommandHandler('getid', getid))
    dispatcher.add_handler(CommandHandler('newcard', newcard))
    dispatcher.add_handler(CommandHandler('discard', discard))
    dispatcher.add_handler(CommandHandler('details', details))
    dispatcher.add_handler(CommandHandler('setage', setage))
    dispatcher.add_handler(CommandHandler('setstrdec', setstrdec))
    dispatcher.add_handler(CommandHandler('setcondec', setcondec))
    dispatcher.add_handler(CommandHandler('setjob', setjob))
    dispatcher.add_handler(CommandHandler('addskill', addskill))
    dispatcher.add_handler(CommandHandler('setname', setname))
    dispatcher.add_handler(CommandHandler('startgame', startgame))
    dispatcher.add_handler(CommandHandler('abortgame', abortgame))
    dispatcher.add_handler(CommandHandler('endgame', endgame))
    dispatcher.add_handler(CommandHandler('switch', switch))
    dispatcher.add_handler(CommandHandler('switchkp', switchkp))
    dispatcher.add_handler(CommandHandler('tempcheck', tempcheck))
    dispatcher.add_handler(CommandHandler('roll', roll))
    dispatcher.add_handler(CommandHandler('show', show))
    dispatcher.add_handler(CommandHandler('showids', showids))
    dispatcher.add_handler(CommandHandler('modify', modify))
    dispatcher.add_handler(CommandHandler(
        'randombackground', randombackground))
    dispatcher.add_handler(CommandHandler('setbkground', setbkground))
    dispatcher.add_handler(CommandHandler('setsex', setsex))
    dispatcher.add_handler(CommandHandler('sancheck', sancheck))
    dispatcher.add_handler(CommandHandler('addcard', addcard))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    updater.start_polling(clean=True)


if __name__ == "__main__":
    pid = os.getpid()
    print(pid)
    main()
