from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar

from telegram import CallbackQuery, Update

from cfg import ADMIN_ID

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from telegram.ext import CallbackContext

    from dicebot import diceBot
    from gameclass import datatype

_RT = TypeVar('_RT')
# FLAGS


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


class commandCallbackMethodWithErrorDispatch(commandCallbackMethod):
    def __init__(
        self,
        func: Callable[[Any, Update, 'CallbackContext'], _RT],
        errorDispatchDict: Dict[str, Any]
    ) -> None:
        super().__init__(func)
        self.errorDispatcher = errorDispatchDict

    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


def commandErrorDispatch(d: Dict[str, Any]) -> Callable:
    return lambda x: commandCallbackMethodWithErrorDispatch(x, d)


class buttonQueryHandleMethod(object):
    """
    用于响应按钮请求分发的装饰器。
    被装饰的方法必须通过`klass.methodname(self, ...)`的方式调用，并且只返回`matchdict`.
    `matchdict`结构如下：
        `key:(workingmethod, dispatched_method [, args, errorInfoString])`
    解释如下：
        key (:obj:`str`): 是callback query data经过split之后的第一个字符串。也就是说，将要相应以`key`
            开头的callback data对应的按钮。这一key必须是固定的，请保证不在运行时修改。
        workingmethod (:obj:`str`): 是bot对该用户当前的工作状态，与
            `instance.workingMethod[instance.lastchat]`比较，这是保证当前该按钮确实处于活跃阶段，否则
            可能造成隐患。如果不同，说明当前不是处于应该响应用户这一按钮请求的时机，并返回。如果相同，将参数传给
            `dispatched_method`进行处理。
        dispatched_method (:method:`(CallbackQuery, List[str])->bool`): 实际的响应method。对于对应
            callback data和working method进行具体的处理。`query`与`query.data.split()`两个参数将被传入。
            之后的参数在args里传入。
        args (Optional, :object:`Tuple[Any]`): 如果存在这些参数，那么它们将会被按顺序传递给
            `dispatched_method`。
        errorInfoString (Optional, :object:`str`): match工作状态失败时给用户的提示。不定义的话就显示
            默认的错误提示。必须在第四个位置，如果不需要args但是需要`errorInfoString`，请在args的位置填入
            `tuple()`。
    """

    def __init__(
        self,
        func: Callable[[Any], dict]
    ) -> None:
        self.matchkeys: Set[str] = set()
        wraps(func)(self)

    def memKeysAndGetDict(self, instance) -> Dict[
        str, Tuple[
            str,
            Callable[[CallbackQuery, List[str], Any], bool],
            Tuple[Any],
            Optional[str]
        ]
    ]:
        if not self.matchkeys:
            matchdict = self.__wrapped__(instance)
            self.matchkeys = set(matchdict.keys())
        else:
            matchdict = self.__wrapped__(instance)
        return matchdict

    def __call__(self, instance: 'diceBot', update: Update, context: 'CallbackContext', **kwargs) -> handleStatus:
        query: CallbackQuery = update.callback_query

        args = query.data.split(" ")

        workingmethod = instance.workingMethod[instance.lastchat]

        callback = args[0]

        # 如果不在此处响应，不应该调用wrapped，因为这可能导致无意义的耗时
        matchdict = None
        if not self.matchkeys:
            matchdict = self.memKeysAndGetDict(instance)
        if callback not in self.matchkeys:
            return handlePassed

        if not matchdict:
            matchdict = self.memKeysAndGetDict(instance)

        dispatchinfo = matchdict[callback]

        if workingmethod != dispatchinfo[0]:
            if len(dispatchinfo) > 3:
                return handleBlocked(instance.errorHandlerQ(query, dispatchinfo[3]))
            return handleBlocked(instance.queryError(query))

        orderArgs = tuple() if len(dispatchinfo) < 3 else dispatchinfo[2]
        utilfunc = dispatchinfo[1]
        return handleBlocked(utilfunc(query, args, *orderArgs))


# class diceDataTask(object):
#     """
#     表示一个dicebot任务，用于自动化管理数据。
#     将task和相应的arguments传入，执行后再对数据进行读、写、删除操作。
#     """
#     # flags
#     DONOTHING = 0
#     READ = 1
#     WRITE = 2
#     REMOVE = 3

#     def __init__(
#             self,
#             tasks: Tuple[Callable[[Any], bool]],
#             args: Tuple[tuple],
#             afterwardTaskTarget: List['datatype'],
#             signals: List[int]) -> None:
#         if len(tasks) != len(args):
#             raise ValueError("任务个数和argument个数不一致")
#         if len(afterwardTaskTarget) != len(signals):
#             raise ValueError("执行后目标个数和signal个数不一致")
#         self.tasks = tasks
#         self.args = args
#         self.afterTarget = afterwardTaskTarget
#         self.signals = signals

#     def run(self):
#         for i in range(len(self.tasks)):
#             ans = self.tasks[i](*self.args[i])
#             if not ans:
#                 return False

#         for i in range(len(self.afterTarget)):
#             sig = self.signals[i]
#             if not sig:
#                 continue
#             if sig == self.READ:
#                 self.afterTarget[i].read()  # TODO(Antares): To be implemented
#             elif sig == self.WRITE:
#                 self.afterTarget[i].write()
#             elif sig == self.REMOVE:
#                 self.afterTarget[i].delete()
#             else:
#                 raise ValueError("无效的信号值")
#         return True
