from dicebot import diceBot
from utils import *
from telegram.ext import CallbackContext
from gameclass import *


class diceCommand(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    @commandCallbackMethod
    def roll(self, update: Update, context: CallbackContext):
        """基本的骰子功能。

        只接受第一个空格前的参数`dicename`。
        `dicename`可能是技能名、属性名（仅限游戏中），可能是`3d6`，可能是`1d4+2d10`。
        骰子环境可能是游戏中，游戏外。

        `/roll`：默认1d100。
        `/roll --mdn`骰一个mdn的骰子。
        `/roll --test`仅限游戏中可以使用。对`test`进行一次检定。
        例如，`/roll 力量`会进行一次STR检定。
        `/roll 射击`进行一次射击检定。
        检定心理学时结果只会发送给kp。
        如果要进行一个暗骰，可以输入
        `/roll 暗骰`进行一次检定为50的暗骰，或者
        `/roll 暗骰60`进行一次检定为60的暗骰。"""

        if len(context.args) == 0:
            self.reply(commondice("1d100"))  # 骰1d100
            return True

        dicename = context.args[0]

        if isprivate(update):
            self.reply(commondice(dicename))
            return True

        gp = self.forcegetgroup(update)

        # 检查输入参数是不是一个基础骰子，如果是则直接计算骰子
        if gp.game is None or dicename.find('d') >= 0 or isint(dicename):
            if isint(dicename) and int(dicename) > 0:
                dicename = "1d"+dicename
            rttext = commondice(dicename)
            if rttext == "Invalid input.":
                return self.errorInfo("输入无效")
            self.reply(rttext)
            return True

        if gp.game is None:
            return self.errorInfo("输入无效")
        # 确认不是基础骰子的计算，转到卡检定
        # 获取临时检定
        tpcheck, gp.game.tpcheck = gp.game.tpcheck, 0
        if tpcheck != 0:
            gp.write()

        pl = self.forcegetplayer(update)

        # 获取卡
        if pl != gp.kp:
            gamecard = self.findcardfromgame(gp.game, pl)
        else:
            gamecard = gp.game.kpctrl
            if gamecard is None:
                return self.errorInfo("请用 /switchgamecard 切换kp要用的卡")
        if not gamecard:
            return self.errorInfo("找不到游戏中的卡。")
        if gamecard.status == STATUS_DEAD:
            return self.errorInfo("角色已死亡")
        if gamecard.status == STATUS_PERMANENTINSANE:
            return self.errorInfo("角色已永久疯狂")

        if dicename.encode('utf-8').isalpha():
            dicename = dicename.upper()

        # 找卡完成，开始检定
        test = 0
        if dicename == "侦察":
            dicename = "侦查"
        if dicename in gamecard.skill.allskills():
            test = gamecard.skill.get(dicename)
        elif dicename in gamecard.interest.allskills():
            test = gamecard.interest.get(dicename)
        elif dicename == "母语":
            test = gamecard.data.EDU
        elif dicename == "闪避":
            test = gamecard.data.DEX//2

        elif dicename in gamecard.data.alldatanames:
            test = gamecard.data.__dict__[dicename]
        elif dicename == "力量":
            dicename = "STR"
            test = gamecard.data.STR
        elif dicename == "体质":
            dicename = "CON"
            test = gamecard.data.CON
        elif dicename == "体型":
            dicename = "SIZ"
            test = gamecard.data.SIZ
        elif dicename == "敏捷":
            dicename = "DEX"
            test = gamecard.data.DEX
        elif dicename == "外貌":
            dicename = "APP"
            test = gamecard.data.APP
        elif dicename == "智力" or dicename == "灵感":
            dicename = "INT"
            test = gamecard.data.INT
        elif dicename == "意志":
            dicename = "POW"
            test = gamecard.data.POW
        elif dicename == "教育":
            dicename = "EDU"
            test = gamecard.data.EDU
        elif dicename == "幸运":
            dicename = "LUCK"
            test = gamecard.data.LUCK

        elif dicename in self.skilllist:
            test = self.skilllist[dicename]

        elif dicename[:2] == "暗骰" and (isint(dicename[2:]) or len(dicename) == 2):
            if len(dicename) != 2:
                test = int(dicename[2:])
            else:
                test = 50

        else:  # HIT BAD TRAP
            return self.errorInfo("输入无效")

        # 将所有检定修正相加
        test += gamecard.tempstatus.GLOBAL
        if gamecard.hasstatus(dicename):
            test += gamecard.getstatus(dicename)
        test += tpcheck

        if test < 1:
            test = 1
        testval = dicemdn(1, 100)[0]
        rttext = dicename+" 检定/出目："+str(test)+"/"+str(testval)+" "

        greatsuccessrule = gp.rule.greatsuccess
        greatfailrule = gp.rule.greatfail

        if (test < 50 and testval >= greatfailrule[2] and testval <= greatfailrule[3]) or (test >= 50 and testval >= greatfailrule[0] and testval <= greatfailrule[1]):
            rttext += "大失败"
        elif (test < 50 and testval >= greatsuccessrule[2] and testval <= greatsuccessrule[3]) or (test >= 50 and testval >= greatsuccessrule[0] and testval <= greatsuccessrule[1]):
            rttext += "大成功"
        elif testval > test:
            rttext += "失败"
        elif testval > test//2:
            rttext += "普通成功"
        elif testval > test//5:
            rttext += "困难成功"
        else:
            rttext += "极难成功"

        if dicename == "心理学" or dicename[:2] == "暗骰":
            if gp.kp is None:
                return self.errorInfo("本群没有KP，请先添加一个KP再试！")

            self.reply(dicename+" 检定/出目："+str(test)+"/???")
            self.sendto(gp.kp, rttext)
        else:
            self.reply(rttext)

        return True

    @commandCallbackMethod
    def sancheck(self, update: Update, context: CallbackContext) -> bool:
        """进行一次sancheck，格式如下：
        `/sancheck checkpass/checkfail`"""

        if isprivate(update):
            return self.errorInfo("在游戏中才能进行sancheck。")

        if len(context.args) == 0:
            return self.errorInfo("需要参数", True)

        checkname = context.args[0]
        if checkname.find("/") == -1:
            return self.errorInfo("将成功和失败的扣除点数用/分开。")

        checkpass, checkfail = checkname.split(sep='/', maxsplit=1)
        if not isadicename(checkpass) or not isadicename(checkfail):
            return self.errorInfo("无效输入")

        gp = self.forcegetgroup(update)

        if gp.game is None:
            return self.errorInfo("找不到游戏", True)

        pl = self.forcegetplayer(update)
        # KP 进行
        if pl == gp.kp:
            card1 = gp.game.kpctrl
            if card1 is None:
                return self.errorInfo("请先用 /switchgamecard 切换到你的卡")
        else:  # 玩家进行
            card1 = self.findcardfromgame(gp.game, pl)
            if card1 is None:
                return self.errorInfo("找不到卡。")

        rttext = "理智：检定/出目 "
        sanity = card1.attr.SAN
        check = dicemdn(1, 100)[0]
        rttext += str(sanity)+"/"+str(check)+" "
        greatfailrule = gp.rule.greatfail
        if (sanity < 50 and check >= greatfailrule[2] and check <= greatfailrule[3]) or (sanity >= 50 and check >= greatfailrule[0] and check <= greatfailrule[1]):  # 大失败
            rttext += "大失败"
            anstype = "大失败"
        elif check > sanity:  # check fail
            rttext += "失败"
            anstype = "失败"
        else:
            rttext += "成功"
            anstype = ""

        rttext += "\n损失理智："
        sanloss, m, n = 0, 0, 0

        if anstype == "大失败":
            if isint(checkfail):
                sanloss = int(checkfail)
            else:
                t = checkfail.split("+")
                for tt in t:
                    if isint(tt):
                        sanloss += int(tt)
                    else:
                        ttt = tt.split('d')
                        sanloss += int(ttt[0])*int(ttt[1])

        elif anstype == "失败":
            if isint(checkfail):
                sanloss = int(checkfail)
            else:
                m, n = checkfail.split("d", maxsplit=1)
                m, n = int(m), int(n)
                sanloss = int(sum(dicemdn(m, n)))

        else:
            if isint(checkpass):
                sanloss = int(checkpass)
            else:
                m, n = checkpass.split("d", maxsplit=1)
                m, n = int(m), int(n)
                sanloss = int(sum(dicemdn(m, n)))

        card1.attr.SAN -= sanloss
        rttext += str(sanloss)+"\n"
        if card1.attr.SAN <= 0:
            card1.attr.SAN = 0
            card1.status = STATUS_PERMANENTINSANE
            rttext += "陷入永久疯狂，快乐撕卡~\n"

        elif sanloss > (card1.attr.SAN+sanloss)//5:
            rttext += "一次损失五分之一以上理智，进入不定性疯狂状态。\n"
            # TODO 处理角色的疯狂状态
        elif sanloss >= 5:
            rttext += "一次损失5点或以上理智，可能需要进行智力（灵感）检定。\n"

        self.reply(rttext)
        card1.write()
        return True
