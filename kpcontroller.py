from dicebot import diceBot
from utils import *
from telegram.ext import CallbackContext
from gameclass import *
class kpController(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    @commandCallbackMethod
    def unbindkp(self, update: Update, context: CallbackContext) -> bool:
        """撤销自己的KP权限。只有当前群内KP可以使用该指令。
        在撤销KP之后的新KP会自动获取原KP的所有NPC的卡片"""
        

        if isprivate(update):
            return self.errorInfo('发群消息撤销自己的KP权限')

        gp = self.forcegetgroup(update)
        if gp.kp is None:
            return self.errorInfo('本群没有KP', True)

        if not self.checkaccess(self.forcegetplayer(update), gp) & GROUPKP:
            return self.errorInfo('你不是KP', True)

        self.changecardsplid(gp, gp.kp, self.forcegetplayer(0))
        self.delkp(gp)

        self.reply('KP已撤销')

        if self.getOP(gp.id).find("delcard") != -1:
            self.popOP(gp.id)

        return True

    @commandCallbackMethod
    def bindkp(self, update: Update, context: CallbackContext) -> bool:
        """添加KP。在群里发送`/bindkp`将自己设置为KP。
        如果这个群已经有一名群成员是KP，则该指令无效。
        若原KP不在群里，该指令可以替换KP。

        如果原KP在群里，需要先发送`/unbindkp`来撤销自己的KP，或者管理员用`/transferkp`来强制转移KP权限。"""
        

        if isprivate(update):
            return self.errorInfo('发送群消息添加KP')

        gp = self.forcegetgroup(update)
        kp = self.forcegetplayer(update)

        # 判断是否已经有KP
        if gp.kp is not None:
            # 已有KP
            if not self.isingroup(gp, kp):
                if not self.changeKP(gp, kp):  # 更新NPC卡拥有者
                    # 不应触发
                    return self.errorInfo("程序错误：不符合添加KP要求，请检查代码")
                return True

            return self.errorInfo("你已经是KP了", True) if gp.kp == kp else self.errorInfo('这个群已经有一位KP了，请先让TA发送 /unbindkp 撤销自己的KP。如果需要强制更换KP，请管理员用\'/transferkp kpid\'添加本群成员为KP，或者 /transferkp 将自己设为KP。')

        # 该群没有KP，可以直接添加KP
        self.addkp(gp, kp)

        # delkp指令会将KP的卡playerid全部改为0，检查如果有id为0的卡，id设为新kp的id
        self.changecardsplid(gp, self.forcegetplayer(0), kp)

        self.reply(
            "绑定群(id): " + gp.getname() + "与KP(id): " + kp.getname())

        return True

    @commandCallbackMethod
    def transferkp(self, update: Update, context: CallbackContext) -> bool:
        """转移KP权限，只有群管理员可以使用这个指令。
        当前群没有KP时或当前群KP为管理员时，无法使用。

        `/transferkp --kpid`：将当前群KP权限转移到某个群成员。
        如果指定的`kpid`不在群内则无法设定。

        `/transferkp`：将当前群KP权限转移到自身。

        `/trasferkp`(reply to someone)：将kp权限转移给被回复者。"""
        if isprivate(update):
            return self.errorInfo("发送群消息强制转移KP权限")

        gp = self.getgp(update)
        pl = self.getplayer(update)
        f = self.checkaccess(pl, gp)

        if not f & GROUPADMIN:
            return self.errorInfo("没有权限", True)

        if gp.kp is None:
            return self.errorInfo("没有KP", True)

        if self.checkaccess(gp.kp, gp) & GROUPADMIN:
            return self.errorInfo("KP是管理员，无法转移")

        # 获取newkp
        newkpid: int
        if len(context.args) != 0:
            if not isint(context.args[0]):
                return self.errorInfo("参数需要是整数", True)
            newkp = self.forcegetplayer(int(context.args[0]))
        else:
            t = self.getreplyplayer(update)
            newkp = t if t is not None else self.forcegetplayer(update)

        if newkp == gp.kp:
            return self.errorInfo("原KP和新KP相同", True)

        if not self.changeKP(gp, newkp):
            return self.errorInfo("程序错误：不符合添加KP要求，请检查代码")  # 不应触发

        return True
