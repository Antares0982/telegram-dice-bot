from cfg import ADMIN_ID
from dicefunc import isint

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from telegram.ext import CallbackContext
    from telegram.update import Update

    from dicebot import diceBot
    from gameclass import *
# "Inline" functions for checkers


def isgroup(update: 'Update') -> bool:
    return update.effective_chat.type.find("group") != -1


def isprivate(update: 'Update') -> bool:
    return update.effective_chat.type == "private"

# Checkers


def checknoarg(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    return bool(len(context.args))


def checknonnegativeint(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    index = kwargs['index']
    return len(context.args) > index and isint(context.args[index]) and int(context.args[index] >= 0)


def checkiskp(update, context, *args, **kwargs) -> bool:
    group: 'Group' = kwargs['group']
    player: 'Player' = kwargs['player']
    return group.kp is not None and group.kp == player


def checkisgroupmsg(update, context, *args, **kwargs) -> bool:
    return isgroup(update)


def checkisprivatemsg(update, context, *args, **kwargs) -> bool:
    return isprivate(update)


def checkhasgame(update, context, *args, **kwargs) -> bool:
    group: 'Group' = kwargs['group']
    return group.game is not None or group.pausedgame is not None


def checkhascard(update, context, *args, **kwargs) -> bool:
    player: 'Player' = kwargs['player']
    return player is not None and player.controlling is not None


def checkbotadmin(update: 'Update', context, *args, **kwargs) -> bool:
    bot: 'diceBot' = kwargs['bot']
    group: 'Group' = kwargs['group']
    return group is not None and bot.isbotadmin(group.id)


def checkadmin(update, context, *args, **kwargs) -> bool:
    player: 'Player' = kwargs['player']
    bot: 'diceBot' = kwargs['bot']
    group: 'Group' = kwargs['group']
    return group is not None and player is not None and bot.isadmin(group.id, player.id)


def checkfrommaster(update: 'Update', context, *args, **kwargs) -> bool:
    return update.message.from_user.id == ADMIN_ID


def checkarglengthiseven(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    return len(context.args) & 1 == 0


def checkcardidexist(update, context, *args, **kwargs) -> bool:
    cardid: int = kwargs['cardid']
    bot: 'diceBot' = kwargs['bot']
    return bot.getcard(cardid) is not None


def checkplayeridexist(update, context, *args, **kwargs) -> bool:
    playerid: int = kwargs['playerid']
    bot: 'diceBot' = kwargs['bot']
    return bot.getplayer(playerid) is not None
