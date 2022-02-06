from functools import wraps
from inspect import getfullargspec
from typing import (Any, Callable, Dict, List, Optional, Tuple, TypeVar
                    )

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
    from gameclass import Group, Player

_RT = TypeVar('_RT')

# "Inline" functions for checkers


class baseChecker(object):
    func = None
    active = False

    def __init__(self) -> None:
        self.wrapcheck(type(self).func)

    @classmethod
    def wrapcheck(cls, func):
        if func is None:
            return
        print(f"activating checker: {cls.__name__}")
        def _f(self, u, c, *args, **kwargs): return func(u, c, *args, **kwargs)
        cls.check = _f
        cls.active = False

    def check(self, update: 'Update', context: 'CallbackContext', *args, **kwargs) -> bool:
        raise NotImplementedError


def isgroup(update: 'Update', *args, **kwargs) -> bool:
    return update.effective_chat.type.find("group") != -1

# Checkers


class isgroupCheck(baseChecker):
    func = isgroup


def isprivate(update: 'Update', *args, **kwargs) -> bool:
    return update.effective_chat.type == "private"


class isprivateCheck(baseChecker):
    func = isprivate


def checknoarg(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    """receive: None."""
    return bool(len(context.args))


class noargCheck(baseChecker):
    func = checknoarg


def checkarglength(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    """receive: `length`."""
    return len(context.args) >= kwargs['length']


class arglengthCheck(baseChecker):
    func = checkarglength


def checknonnegativeint(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    index = kwargs['index']
    return len(context.args) > index and isint(context.args[index]) and int(context.args[index]) >= 0


class nonnegativeintCheck(baseChecker):
    func = checknonnegativeint


def checknonpositiveint(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    """receive: `index`."""
    index = kwargs['index']
    return len(context.args) > index and isint(context.args[index]) and int(context.args[index]) <= 0


class nonpositiveintCheck(baseChecker):
    func = checknonpositiveint


def checkiskp(update, context, *args, **kwargs) -> bool:
    """receive: `group`, `player`."""
    group: 'Group' = kwargs['group']
    player: 'Player' = kwargs['player']
    return group is not None and group.kp is not None and group.kp == player


class iskpCheck(baseChecker):
    func = checkiskp


# def checkisgroupmsg(update, context, *args, **kwargs) -> bool:
#     """receive: None."""
#     return isgroup(update)


# def checkisprivatemsg(update, context, *args, **kwargs) -> bool:
#     """receive: None."""
#     return isprivate(update)


def checkisgaming(update, context, *args, **kwargs) -> bool:
    """receive: `group`."""
    group: 'Group' = kwargs['group']
    return group is not None and group.game is not None


class isgamingCheck(baseChecker):
    func = checkisgaming


def checkhasgame(update, context, *args, **kwargs) -> bool:
    """receive: `group`."""
    group: 'Group' = kwargs['group']
    return group is not None and (group.game is not None or group.pausedgame is not None)


class hasgameCheck(baseChecker):
    func = checkhasgame


def checkhascard(update, context, *args, **kwargs) -> bool:
    player: 'Player' = kwargs['player']
    return player is not None and player.controlling is not None


class hascardCheck(baseChecker):
    func = checkhascard


def checkbotadmin(update: 'Update', context, *args, **kwargs) -> bool:
    bot: 'diceBot' = kwargs['bot']
    group: 'Group' = kwargs['group']
    return group is not None and bot.isbotadmin(group.id)


class botadminCheck(baseChecker):
    func = checkbotadmin


def checkadmin(update, context, *args, **kwargs) -> bool:
    player: 'Player' = kwargs['player']
    bot: 'diceBot' = kwargs['bot']
    group: 'Group' = kwargs['group']
    return group is not None and player is not None and bot.isadmin(group.id, player.id)


class adminCheck(baseChecker):
    func = checkadmin


def checkfrommaster(update: 'Update', context, *args, **kwargs) -> bool:
    return update.message.from_user.id == ADMIN_ID


class frommasterCheck(baseChecker):
    func = checkfrommaster


def checkarglengthiseven(update, context: 'CallbackContext', *args, **kwargs) -> bool:
    return len(context.args) & 1 == 0


class arglengthevenCheck(baseChecker):
    func = checkarglengthiseven


def checktargetexist(update, context, *args, **kwargs) -> bool:
    """receive: `target`."""
    target = kwargs['target']
    return target is not None


class targetExistCheck(baseChecker):
    func = checktargetexist

# def checkcardidexist(update, context, *args, **kwargs) -> bool:
#     cardid: int = kwargs['cardid']
#     bot: 'diceBot' = kwargs['bot']
#     return bot.getcard(cardid) is not None


# def checkplayeridexist(update, context, *args, **kwargs) -> bool:
#     """receive: `playerid`, `bot`"""
#     playerid: int = kwargs['playerid']
#     bot: 'diceBot' = kwargs['bot']
#     return bot.getplayer(playerid) is not None


def checkgrouphascard(update, context, *args, **kwargs) -> bool:
    group: 'Group' = kwargs['group']
    return group is not None and group.cards


class grouphascardCheck(baseChecker):
    func = checkgrouphascard

# region pre condition


class basePreCondition(object):
    """
    Call this before each checker.
    If return False, then don't do that check.
    """

    def __call__(self, update: 'Update', context: 'CallbackContext', *args, **kwargs) -> Any:
        return True


class noCondition(basePreCondition):
    """此类的实例调用时永远返回True."""
    ...


class emptyReplyToMsg(basePreCondition):
    def __call__(self, update: 'Update', context: 'CallbackContext', *args, **kwargs) -> Any:
        return update.message.reply_to_message is None
# endregion


class parsingMethod(object):
    def __call__(self, update: 'Update', context: 'CallbackContext', input) -> Any:
        return input


class noParse(parsingMethod):
    ...


class contextArgsToInt(parsingMethod):
    def __call__(self, update: 'Update', context: 'CallbackContext', input) -> int:
        return int(context.args[input])


class parseUpdate(parsingMethod):
    def __call__(self, update: 'Update', context: 'CallbackContext', input) -> 'Update':
        return update


class checkSettings(object):
    def __init__(self, keyword: str, input: Any, preTreat: Optional[Callable] = None, parse_method: 'parsingMethod' = noParse()) -> None:
        self.preTreat = preTreat
        self.parse = parse_method
        self.input = input
        self.keyword = keyword

    def setinfo(self, update, context, botinstance):
        x = self.parse(update, context, self.input)
        if self.preTreat is None:
            return x
        return self.preTreat(botinstance, x) if len(getfullargspec(self.preTreat).args) > 1 else self.preTreat(x)


class CheckSettingsGroup(object):
    def __init__(self, checker: baseChecker, settings: List[checkSettings], errorArgs: Tuple[str, bool]) -> None:
        self.checker = checker
        self.settings = settings
        self.errArgs = errorArgs

    def check(self, update: 'Update', context: 'CallbackContext', botinstance: 'diceBot') -> bool:
        kw = {}
        for setting in self.settings:
            kw[setting.keyword] = setting.setinfo(update, context, botinstance)
        passed = self.checker.check(update, context, **kw)
        if passed:
            return True
        return botinstance.errorInfo(*self.errArgs)


class JudgeCondition(object):
    ...


class ErrorDispatcher(object):
    """help with commandCallbackMethodWithErrorDispatch"""

    def __init__(self, checkingGroups: List[CheckSettingsGroup], preCondition: basePreCondition = noCondition()) -> None:
        self.presatisfy = preCondition
        self.checkingGroups = checkingGroups

    def docheck(self, update: 'Update', context: 'CallbackContext', botinstance: 'diceBot') -> bool:
        print("do checking...", update.effective_chat.id,
              update.message.message_id)
        if not self.presatisfy(update, context):
            return True
        for checks in self.checkingGroups:
            if not checks.check(update, context, botinstance):
                print("check: false")
                return False
        print("check: true")
        return True


class commandCallbackMethod(object):
    """表示一个指令的callback函数，仅限于类的成员方法。
    调用时，会执行一次指令的前置函数。"""

    def __init__(self, func: Callable[[Any, 'Update', 'CallbackContext'], _RT]) -> None:
        wraps(func)(self)
        self.instance: 'diceBot' = None

    def prechecker(self, *args, **kwargs) -> bool:
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
            return False
        return True

    def __call__(self, *args, **kwargs):
        if not self.prechecker(*args, **kwargs):
            return

        return self.__wrapped__(self.instance, *args, **kwargs)

    def preExecute(self, update: 'Update', context: 'CallbackContext') -> None:
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


class commandCallbackMethodWithErrorDispatch(commandCallbackMethod):
    def __init__(
        self,
        func: Callable[[Any, 'Update', 'CallbackContext'], _RT],
        # errorDispatchDict: List[Dict[Union[str, bool], Dict[Callable, Tuple[
        #     Tuple[Optional[Callable], ...],
        #     Tuple[str, ...],
        #     Tuple[Any, ...],
        #     Tuple[str, ...],
        #     Tuple[str, bool]
        # ]
        # ]]]
        errorDispatchDict: List[ErrorDispatcher]
    ) -> None:
        super().__init__(func)
        self.errorDispatchers = errorDispatchDict

        # for dic in self.errorDispatchers:
        #     for _, redic in dic.items():
        #         for detail in redic.values():
        #             alllen = list(map(len, detail[:4]))
        #             if any(x != alllen[0] for x in alllen):
        #                 raise ValueError("ErrorDispatch参数个数不一致")

    def dictErrCheck(self, *args, **kwargs) -> bool:
        try:
            update: 'Update' = args[0] if len(args) > 0 else kwargs['update']
            context: 'CallbackContext' = args[1] \
                if len(args) > 1 else kwargs['context']
        except Exception:
            raise RuntimeError("接收到的参数无效")

        for dic in self.errorDispatchers:
            if not dic.docheck(update, context, self.instance):
                return False

        return True

        # for dic in self.errorDispatchers:
        #     for pre, redic in dic.items():
        #         # if pre == EPRE_REPLY_NONE and update.message.reply_to_message is not None:
        #         if not pre(update, context):
        #             continue

        #         for check, detail in redic.items():
        #             passkwargs = {}
        #             prefuncs, parsemeth, vals, passkw, errargs = detail
        #             for i, v in enumerate(vals):
        #                 # value = v
        #                 # if parsemeth[i] is not None:
        #                 #     if parsemeth[i] == EP_CTX_IND_TOINT:
        #                 #         value = int(context.args[value])
        #                 #     elif parsemeth[i] == EP_UPD:
        #                 #         value = update
        #                 #     else:
        #                 #         ...
        #                 value = parsemeth[i](v)
        #                 if prefuncs[i] is not None:
        #                     if len(getfullargspec(prefuncs[i]).args) > 1:
        #                         value = prefuncs[i](self.instance, value)
        #                     else:
        #                         value = prefuncs[i](value)
        #                 if passkw[i] is not None:
        #                     passkwargs[passkw[i]] = value
        #             if not check(update, context, **passkwargs):
        #                 return self.instance.errorInfo(*errargs)

        # return True

    def prechecker(self, *args, **kwargs) -> bool:
        if not super().prechecker(*args, **kwargs):
            return False
        return self.dictErrCheck(*args, **kwargs)


def commandErrorDispatch(d: Dict[str, Any]) -> Callable:
    return lambda x: commandCallbackMethodWithErrorDispatch(x, d)
