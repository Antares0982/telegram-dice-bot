#!/usr/bin/python3 -O
from telegram.ext import CallbackContext

from basebot import baseBot
from utils import *


class diceBot(baseBot):
    def textHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().textHandler(update, context)

    def photoHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().photoHandler(update, context)

    def buttonHandler(self, update: Update, context: CallbackContext) -> handleStatus:
        return super().buttonHandler(update, context)