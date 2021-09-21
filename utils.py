from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, TypeVar

from telegram import (CallbackQuery, InlineKeyboardButton,
                      InlineKeyboardMarkup, Update)

from cfg import *

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from telegram.ext import CallbackContext

    from dicebot import diceBot

_RT = TypeVar('_RT')
# FLAGS

CANREAD = 1
OWNCARD = 2
CANSETINFO = 4
CANDISCARD = 8
CANMODIFY = 16

INGROUP = 1
GROUPKP = 2
GROUPADMIN = 4
BOTADMIN = 8

STATUS_DEAD = "dead"
STATUS_ALIVE = "alive"
STATUS_SERIOUSLYWOUNDED = "seriously wounded"
STATUS_NEARDEATH = "near-death"
STATUS_TEMPSTABLE = "temporarily stable"
STATUS_PERMANENTINSANE = "permanently insane"


def isfromme(update: Update) -> bool:
    """检查是否来自`ADMIN_ID`"""
    return getchatid(update) == ADMIN_ID


def getfromid(update: Update) -> int:
    """返回`from_user.id`"""
    return update.message.from_user.id


def getchatid(update: Update) -> int:
    """返回`chat_id`"""
    return update.effective_chat.id


def getmsgid(update: Update) -> int:
    """返回message_id"""
    return update.message.message_id


def isprivate(update: Update) -> bool:
    return update.effective_chat.type == "private"


def isgroup(update: Update) -> bool:
    return update.effective_chat.type.find("group") != -1


def ischannel(update: Update) -> bool:
    return update.effective_chat.type == "channel"


class handleStatus(object):
    __slots__ = ['block', 'normal']

    def __init__(self, normal: bool, block: bool) -> None:
        self.block: bool = block
        self.normal: bool = normal

    def __bool__(self):
        ...

    def blocked(self):
        return self.block


handlePassed = handleStatus(True, False)


class handleBlocked(handleStatus):
    __slots__ = []

    def __init__(self, normal: bool = True) -> None:
        super().__init__(normal=normal, block=True)

    def __bool__(self):
        return self.normal


class commandCallbackMethod(object):
    """表示一个指令的callback函数，仅限于类的成员方法。
    调用时，会执行一次指令的前置函数。"""

    def __init__(self, func: Callable[[Any, Update, 'CallbackContext'], _RT]) -> None:
        wraps(func)(self)
        self.instance: 'diceBot' = None

    def __call__(self, *args, **kwargs):
        numOfArgs = len(args)+len(kwargs.keys())
        if numOfArgs != 2:
            raise RuntimeError(
                f"指令{self.__name__}的callback function参数个数应为2，但接受到{numOfArgs}个")
        if len(args) == 2:
            self.preExecute(*args)
        elif len(args) == 1:
            self.preExecute(args[0], **kwargs)
        else:
            self.preExecute(**kwargs)

        inst = self.instance
        if any(x in inst.blacklist for x in (inst.lastchat, inst.lastuser)):
            inst.errorInfo("你在黑名单中，无法使用任何功能")
            return

        return self.__wrapped__(self.instance, *args, **kwargs)

    def preExecute(self, update: Update, context: 'CallbackContext') -> None:
        """在每个command Handler前调用，是指令的前置函数"""
        if self.instance is None:
            raise RuntimeError("command callback method还未获取实例")
        self.instance.renewStatus(update)
        self.instance.chatinit(update, context)

    def __get__(self, instance, cls):
        if instance is None:
            raise TypeError("该装饰器仅适用于方法")
        if self.instance is None:
            self.instance = instance
        return self


class buttonQueryHandleMethod(object):
    """
    用于响应按钮请求分发的装饰器。
    被装饰的方法必须通过`class.buttonHandler(self, ...)`的方式调用，并且只返回`matchdict`.
    `matchdict`结构如下：
        `key:(workingmethod, dispatched_method)`
    解释如下：
        key (:obj:`str`): 是callback query data经过split之后的第一个字符串。也就是说，将要相应以`key`
            开头的callback data对应的按钮。
        workingmethod (:obj:`str`): 是bot对该用户当前的工作状态，与
            `instance.workingMethod[instance.lastchat]`比较，这是保证当前该按钮确实处于活跃阶段，否则
            可能造成隐患。如果不同，说明当前不是处于应该相应用户这一按钮请求的时机。如果相同，将参数传给
            `dispatched_method`进行处理。
        dispatched_method (:method:`(CallbackQuery, List[str])->bool`): 实际的响应method。对于对应
            callback data和working method进行具体的处理。`query`与`query.data.split()`两个参数将被传入。
    """

    def __init__(
        self,
        func: Callable[[Any], dict]
    ) -> None:
        wraps(func)(self)
        self.matchdict: Dict[
            str,
            Tuple[str, Callable[[CallbackQuery, List[str]], bool]]
        ] = {}

    def __call__(self, instance: 'diceBot', update: Update, context: 'CallbackContext', **kwargs) -> handleStatus:
        query: CallbackQuery = update.callback_query

        args = query.data.split(" ")

        workingmethod = instance.workingMethod[instance.lastchat]

        callback = args[0]

        if not self.matchdict:
            self.matchdict = self.__wrapped__(instance)

        if callback not in self.matchdict:
            return handlePassed

        if workingmethod != self.matchdict[callback][0]:
            return handleBlocked(instance.queryError(query))

        utilfunc = self.matchdict[callback][1]

        return handleBlocked(utilfunc(query, args))
