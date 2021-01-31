# -*- coding:utf-8 -*-
# version: 1.0.1

import logging

from telegram.ext import CallbackQueryHandler, MessageHandler, Filters, CommandHandler

from gameclass import *
from botdicts import *
from dicehandlers import *


dispatcher = updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def main() -> None:
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
    main()
