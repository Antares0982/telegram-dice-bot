import time
from typing import Dict

from telegram import Update
from telegram.ext import CallbackContext

from cfg import ADMIN_ID
from commandCallback import commandCallbackMethod, isgroup, isprivate
from dicebot import diceBot
from diceconstants import BOTADMIN, GROUPKP


class infoShow(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    @commandCallbackMethod
    def showjoblist(self, update: Update, context: CallbackContext) -> None:
        """显示职业列表"""

        if not isprivate(update):
            self.errorInfo("请在私聊中使用该指令")
            return

        rttext = "职业列表："
        counts = 0

        for job in self.joblist:
            jobinfo = self.joblist[job]

            rttext += job+f"：\n信用范围 [{str(jobinfo[0])},{str(jobinfo[1])}]\n"

            rttext += "技能点计算方法："
            calcd: Dict[str, int] = jobinfo[2]
            calcmeth = " 加 ".join("或".join(x.split('_')) +
                                  "乘"+str(calcd[x]) for x in calcd)
            rttext += calcmeth+"\n"

            rttext += "主要技能："+"、".join(x for x in jobinfo[3:])+"\n"

            counts += 1

            if counts == 3:
                self.reply(rttext)
                rttext = ""
                counts = 0
                time.sleep(0.2)

    @commandCallbackMethod
    def showrule(self, update: Update, context: CallbackContext) -> bool:
        """显示当前群内的规则。
        如果想了解群规则的详情，请查阅setrule指令的帮助：
        `/help setrule`"""

        if isprivate(update):
            return self.errorInfo("请在群内查看规则")

        gp = self.forcegetgroup(update)
        rule = gp.rule

        self.reply(str(rule))
        return True

    @commandCallbackMethod
    def showskilllist(self, update: Update, context: CallbackContext) -> None:
        """显示技能列表"""

        rttext = "技能：基础值\n"
        rttext += "母语：等于EDU\n"
        rttext += "闪避：等于DEX的一半\n"

        for skill in self.skilllist:
            rttext += skill+"："+str(self.skilllist[skill])+"\n"

        self.reply(rttext)

    @commandCallbackMethod
    def showuserlist(self, update: Update, context: CallbackContext) -> bool:
        """显示所有信息。非KP无法使用这一指令。
        群聊时不可以使用该指令。
        Bot管理者使用该指令，bot将逐条显示群-KP信息、
        全部的卡信息、游戏信息。KP使用时，只会显示与TA相关的这些消息。"""

        if isgroup(update):  # Group msg: do nothing, even sender is USER or KP
            return self.errorInfo("没有这一指令", True)

        user = self.forcegetplayer(update)

        if not self.searchifkp(user) and user.id != ADMIN_ID:
            return self.errorInfo("没有这一指令")

        # 群
        for gp in self.groups.values():
            if self.checkaccess(user, gp) & (GROUPKP | BOTADMIN) != 0:
                self.reply(str(gp))
                time.sleep(0.2)

        # 玩家
        for pl in self.players.values():
            if pl == user or user.id == ADMIN_ID:
                self.reply(str(pl))
                time.sleep(0.2)

        # 卡片
        for card in self.cards.values():
            if self.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
                self.reply(str(card))
                time.sleep(0.2)

        # 游戏中卡片
        for card in self.gamecards.values():
            if self.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
                self.reply(str(card))
                time.sleep(0.2)

        return True
