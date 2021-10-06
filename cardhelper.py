from telegram.ext import CallbackContext

from dicebot import (BUTTON_ADDINTSKILL, BUTTON_ADDMAINSKILL,
                     BUTTON_ADDSGSKILL, BUTTON_CGINTSKILL, BUTTON_CGMAINSKILL,
                     BUTTON_CHOOSEDEC, BUTTON_JOB, BUTTON_SETDEC,
                     BUTTON_SETSEX, BUTTON_SWITCH, BUTTON_SWITCHGAMECARD,
                     diceBot)
from gameclass import *
from utils import *


class cardHelper(diceBot):
    def __init__(self) -> None:
        if not hasattr(self, "updater"):
            diceBot.__init__(self)

    def addskill1(self, update: Update, context: CallbackContext, card1: GameCard) -> bool:
        """该函数在`/addskill`接收且仅接收一个参数时调用。制作技能数值表。"""
        # skillname is already checked if in SKILL_DICT
        # First search if args skillname in skill or suggestskill.
        # Otherwise, if (not suggestskill) and main points>0, should add main skill. Else should add Interest skill
        # Show button for numbers
        skillname = context.args[0]
        m = self.getskilllevelfromdict(card1, skillname)

        if skillname == "信用" and card1.info.job in self.joblist:
            m = max(m, self.joblist[card1.info.job][0])

        if skillname in card1.skill.allskills():  # GOOD TRAP: cgmainskill
            mm = self.skillmaxval(skillname, card1, True)
            rtbuttons = self.makeIntButtons(m, mm, "cgmainskill", skillname)
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply(
                "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.skill.get(skillname)), reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_CGMAINSKILL
            return True

        if skillname in card1.suggestskill.allskills():  # GOOD TRAP: addsgskill
            mm = self.skillmaxval(skillname, card1, True)
            rtbuttons = self.makeIntButtons(m, mm, "addsgskill", skillname)
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply(
                "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname, reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_ADDSGSKILL
            return True

        if skillname in card1.interest.allskills():  # GOOD TRAP: cgintskill
            mm = self.skillmaxval(skillname, card1, False)
            rtbuttons = self.makeIntButtons(m, mm, "cgintskill", skillname)
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply(
                "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+skillname+"，当前技能点："+str(card1.interest.get(skillname)), reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_CGINTSKILL
            return True

        if card1.skill.points > 0:  # GOOD TRAP: addmainskill
            mm = self.skillmaxval(skillname, card1, True)
            rtbuttons = self.makeIntButtons(m, mm, "addmainskill", skillname)
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply(
                "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+skillname, reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_ADDMAINSKILL
            return True

        mm = self.skillmaxval(skillname, card1, False)
        rtbuttons = self.makeIntButtons(m, mm, "addintskill", skillname)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply(
            "添加兴趣技能。剩余技能点："+str(card1.interest.points)+" 技能名称："+skillname, reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_ADDINTSKILL
        return True

    def addmainskill(self, skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
        """该函数对没有`skillname`这项技能的卡使用。将主要技能值设置为`skillvalue`。"""
        if card1.skill.points == 0:
            return self.errorInfo("你已经没有剩余点数了")
        if skillvalue < self.getskilllevelfromdict(card1, skillname) or skillvalue > self.skillmaxval(skillname, card1, True):
            return self.errorInfo("目标技能点太高或太低")
        # 计算点数消耗
        costval = self.evalskillcost(skillname, skillvalue, card1, True)
        self.reply(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
        card1.skill.set(skillname, skillvalue, costval)
        card1.write()
        return True

    def addsgskill(self, skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
        """添加一个建议的技能。直接调用`addmainskill`完成。"""
        if not self.addmainskill(skillname, skillvalue, card1, update):
            return False
        card1.suggestskill.pop(skillname)
        card1.write()
        return True

    def addintskill(self, skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
        """该函数对没有`skillname`这项技能的卡使用。将兴趣技能值设置为`skillvalue`。"""
        if card1.interest.points == 0:
            return self.errorInfo("你已经没有剩余点数了")
        if skillvalue < self.getskilllevelfromdict(card1, skillname) or skillvalue > self.skillmaxval(skillname, card1, False):
            return self.errorInfo("目标技能点太高或太低")
        # 计算点数消耗
        costval = self.evalskillcost(skillname, skillvalue, card1, False)
        self.reply(
            "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
        card1.interest.set(skillname, skillvalue, costval)
        card1.write()
        return True

    # Change main skill level
    def cgmainskill(self, skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
        """修改主要技能的值。如果将技能点调低，返还技能点数。"""
        if skillvalue < self.getskilllevelfromdict(card1, skillname) or skillvalue > self.skillmaxval(skillname, card1, True):
            return self.errorInfo("目标技能点太高或太低")
        costval = self.evalskillcost(skillname, skillvalue, card1, True)
        if costval >= 0:
            self.reply(
                "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
        else:
            self.reply(
                "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
        card1.skill.set(skillname, skillvalue, costval)
        card1.write()
        return True

    def cgintskill(self, skillname: str, skillvalue: int, card1: GameCard, update: Update) -> bool:
        """修改兴趣技能的值。如果将技能点调低，返还技能点数。"""
        if skillvalue < self.getskilllevelfromdict(card1, skillname) or skillvalue > self.skillmaxval(skillname, card1, False):
            return self.errorInfo("目标技能点太高或太低")
        costval = self.evalskillcost(skillname, skillvalue, card1, False)
        if costval >= 0:
            self.reply(
                "技能设置成功："+skillname+" "+str(skillvalue)+"，消耗点数："+str(costval))
        else:
            self.reply(
                "技能设置成功："+skillname+" "+str(skillvalue)+"，返还点数："+str(-costval))
        card1.interest.set(skillname, skillvalue, costval)
        card1.group.write()
        return True

    def addcredit(self, update: Update, card1: GameCard) -> bool:
        self.reply("请先设置信用！")
        gp = card1.group
        if card1.info.job in self.joblist:
            m = self.joblist[card1.info.job][0]
            mm = self.joblist[card1.info.job][1]
        else:
            aged, ok = self.skillcantouchmax(card1, "信用")
            if aged:
                skillmaxrule = gp.rule.skillmaxAged
            else:
                skillmaxrule = gp.rule.skillmax
            m = 0
            if ok:
                mm = skillmaxrule[1]
            else:
                mm = skillmaxrule[0]
        rtbuttons = self.makeIntButtons(m, mm, "addmainskill", "信用")
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply(
            "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称：信用", reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_ADDMAINSKILL
        return True

    def cgcredit(self, update: Update, card1: GameCard) -> bool:
        m = 0
        mm = -1
        if card1.info.job in self.joblist:
            m = self.joblist[card1.info.job][0]
            mm = self.joblist[card1.info.job][1]
            mm = min(mm, self.skillmaxval("信用", card1, True))
        else:
            mm = self.skillmaxval("信用", card1, True)

        rtbutton = self.makeIntButtons(m, mm, "cgmainskill", "信用")
        rp_markup = InlineKeyboardMarkup(rtbutton)
        self.reply(text="修改信用，现在还剩"+str(card1.skill.points)+"点，当前信用："+str(
            card1.skill.get("信用")), reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_CGMAINSKILL
        return True

    @commandCallbackMethod
    def randombkg(self, update: Update, context: CallbackContext) -> bool:
        """生成随机的背景故事。

        获得当前发送者选中的卡，生成随机的背景故事并写入。"""

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorInfo("找不到卡。")

        self.reply(card.background.randbackground())
        return True

    @commandCallbackMethod
    def setbkg(self, update: Update, context: CallbackContext) -> bool:
        """设置背景信息。

        指令格式如下：
        `/setbkg --bkgroundname --bkgroudinfo...`

        其中第一个参数是背景的名称，只能是下面几项之一：
        `description`故事、
        `faith`信仰、
        `vip`重要之人、
        `viplace`意义非凡之地、
        `preciousthing`珍视之物、
        `speciality`性格特质、
        `dmg`曾经受过的伤、
        `terror`恐惧之物、
        `myth`神秘学相关物品、
        `thirdencounter`第三类接触。

        第二至最后一个参数将被空格连接成为一段文字，填入背景故事中。"""

        pl = self.forcegetplayer(update)
        if len(context.args) <= 1:
            return self.errorInfo("参数不足", True)

        card = pl.controlling
        if card is None:
            return self.errorInfo("找不到卡。", True)

        if context.args[0] not in card.background.__dict__ or not type(card.background.__dict__[context.args[0]]) is str:
            rttext = "找不到这项背景属性，背景属性只支持以下参数：\n"
            for keys in card.background.__dict__:
                if not type(card.background.__dict__[keys]) is str:
                    continue
                rttext += keys+"\n"
            return self.errorInfo(rttext)

        card.background.__dict__[context.args[0]] = ' '.join(context.args[1:])
        card.write()
        self.reply("背景故事添加成功")
        return True

    @commandCallbackMethod
    def setname(self, update: Update, context: CallbackContext) -> bool:
        """设置角色卡姓名。

        `/setname --name`：直接设定姓名。
        `/setname`：bot将等待输入姓名。
        设置的姓名可以带有空格等字符。"""

        card1 = self.forcegetplayer(update).controlling
        if card1 is None:
            return self.errorInfo("找不到卡。")

        if len(context.args) == 0:
            if isprivate(update):
                self.addOP(getchatid(update), "setname")
            else:
                self.addOP(getchatid(update),
                           "setname "+str(card1.playerid))
            self.reply("请输入姓名：")
            return True

        self.nameset(card1, ' '.join(context.args))
        self.reply("角色的名字已经设置为"+card1.info.name+"。")
        return True

    @commandCallbackMethod
    def setsex(self, update: Update, context: CallbackContext) -> bool:
        """设置性别。比较明显的性别词汇会被自动分类为男性或女性，其他的性别也可以设置。
        `/setsex 性别`：直接设置。
        `/setsex`：使用交互式的方法设置性别。"""

        pl = self.forcegetplayer(update)
        if pl.controlling is None:
            return self.errorInfo("找不到卡。", True)
        if len(context.args) == 0:
            if isgroup(update):
                gpid = getchatid(update)
                self.addOP(gpid, "setsex "+str(pl.id))
                self.reply("请输入性别：")
                return True

            rtbuttons = [[InlineKeyboardButton("男性", callback_data="setsex male"), InlineKeyboardButton(
                "女性", callback_data="setsex female"), InlineKeyboardButton("其他", callback_data="setsex other")]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            self.reply("请选择性别：", reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_SETSEX
            return True

        card = pl.controlling
        self.cardsetsex(update, card, context.args[0])
        return True

    @commandCallbackMethod
    def changeid(self, update: Update, context: CallbackContext) -> bool:
        """修改卡片id。卡片的所有者或者KP均有使用该指令的权限。

        指令格式：
        `/changeid --cardid --newid`

        如果`newid`已经被占用，则指令无效。
        这一行为将同时改变游戏内以及游戏外的卡id。"""

        if len(context.args) < 2:
            return self.errorInfo("至少需要两个参数。")

        if not isint(context.args[0]) or not isint(context.args[1]):
            return self.errorInfo("参数无效", True)

        oldid = int(context.args[0])
        newid = int(context.args[1])

        if newid < 0:
            return self.errorInfo("卡id不能为负数", True)
        if newid == oldid:
            return self.errorInfo("前后id相同", True)
        if newid in self.allids:
            return self.errorInfo("该ID已经被占用")

        card = self.getcard(oldid)
        if card is None:
            return self.errorInfo("找不到该ID对应的卡")

        pl = self.forcegetplayer(update)
        if not self.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
            return self.errorInfo("没有权限")

        # 开始处理
        self.atidchanging(update.message, oldid, newid)
        return True

    @commandCallbackMethod
    def addskill(self, update: Update, context: CallbackContext) -> bool:
        """该函数用于增加/修改技能。

        `/addskill`：生成按钮，玩家按照提示一步步操作。
        `/addskill 技能名`：修改某项技能的点数。"""

        if isgroup(update):
            return self.errorInfo("发私聊消息来增改技能", True)

        pl = self.forcegetplayer(update)
        card1 = pl.controlling
        if card1 is None:
            return self.errorInfo("找不到卡。")

        if card1.skill.points == -1:
            return self.errorInfo("信息不完整，无法添加技能")

        if card1.skill.points == 0 and card1.interest.points == 0:
            if len(context.args) == 0 or (context.args[0] not in card1.skill.allskills() and context.args[0] not in card1.interest.allskills()):
                return self.errorInfo("你已经没有技能点了，请添加参数来修改具体的技能！")

        if card1.info.job == "":
            return self.errorInfo("请先设置职业")

        if len(context.args) > 1:
            return self.errorInfo("该指令只能接收一个参数：技能名")

        # 开始处理
        if "信用" not in card1.skill.allskills():
            return self.addcredit(update, card1)

        if len(context.args) == 0:
            return self.addskill0(card1)

        if context.args[0] == "信用" or context.args[0] == "credit":
            return self.addcredit(update, card1) if "信用" not in card1.skill.allskills() else self.cgcredit(update, card1)

        skillname = context.args[0]

        if skillname != "母语" and skillname != "闪避" and (skillname not in self.skilllist or skillname == "克苏鲁神话"):
            return self.errorInfo("无法设置这个技能")

        # This function only returns True
        return self.addskill1(update, context, card1)

    @commandCallbackMethod
    def additem(self, update: Update, context: CallbackContext) -> bool:
        """为你的人物卡添加一些物品。用空格，制表符或回车来分隔不同物品。
        `/additem --item1 --item2...`"""

        card = self.forcegetplayer(update).controlling
        if card is None:
            return self.errorInfo("找不到卡。")

        card.additems(context.args)
        self.reply(f"添加了{str(len(context.args))}件物品。")
        return True

    @commandCallbackMethod
    def cardtransfer(self, update: Update, context: CallbackContext) -> bool:
        """转移卡片所有者。格式为
        `/cardtransfer --cardid --playerid`：将卡转移给playerid。
        回复某人`/cardtransfer --cardid`：将卡转移给被回复的人。要求参数有且仅有一个。
        只有卡片拥有者或者KP有权使用该指令。
        如果对方不是KP且对方已经在本群有卡，则无法转移。"""

        if len(context.args) == 0:
            return self.errorInfo("需要参数", True)
        if len(context.args) == 1 and self.getreplyplayer(update) is None:
            return self.errorInfo("参数不足", True)
        if not isint(context.args[0]) or (len(context.args) > 1 and not isint(context.args[1])):
            return self.errorInfo("参数无效", True)
        if int(context.args[0]) < 0 or (len(context.args) > 1 and int(context.args[1]) < 0):
            return self.errorInfo("负数参数无效", True)

        cdid = int(context.args[0])
        card = self.getcard(cdid)
        if card is None:
            return self.errorInfo("找不到这张卡")

        operationer = self.forcegetplayer(update)
        if len(context.args) == 1:
            tpl: Player = self.getreplyplayer(update)
        else:
            tpl = self.forcegetplayer(int(context.args[1]))

        if not self.checkaccess(operationer, card) & (OWNCARD | CANMODIFY):
            return self.errorInfo("没有权限", True)

        if tpl != card.group.kp:
            for c in tpl.cards.values():
                if c.group == card.group:
                    return self.errorInfo("目标玩家已经在对应群有一张卡了")

        # 开始处理
        self.atcardtransfer(update.message, cdid, tpl)
        return True

    @commandCallbackMethod
    def changegroup(self, update: Update, context: CallbackContext) -> bool:
        """修改卡片的所属群。
        一般只用于卡片创建时输入了错误的群id。
        比较特殊的情形：
        如果需要将某个群的所有卡片全部转移到另一个群，
        第一个参数写为负数的`groupid`即可。这一操作需要原群的kp权限。
        在原群进行游戏时，这个指令无效。

        指令格式：
        `/changegroup --groupid/--cardid --newgroupid`
        """

        if len(context.args) < 2:
            return self.errorInfo("至少需要2个参数", True)
        if not isint(context.args[0]) or not isint(context.args[1]):
            return self.errorInfo("参数无效", True)

        newgpid = int(context.args[1])
        if newgpid >= 0:
            return self.errorInfo("转移的目标群id应该是负数", True)

        if int(context.args[0]) < 0:  # 转移全部群卡片
            ogpid = int(context.args[0])

            oldgp = self.getgp(ogpid)
            if oldgp is None or len(oldgp.cards) == 0:
                return self.errorInfo("该群没有卡")

            newgp = self.forcegetgroup(newgpid)
            kp = self.forcegetgroup(update)
            if ((kp != oldgp.kp and oldgp.id != -1) or kp != newgp.kp) and kp.id != ADMIN_ID:
                return self.errorInfo("没有权限", True)

            if oldgp.getexistgame() is not None:
                return self.errorInfo("游戏进行中，无法转移")

            # 检查权限通过
            numofcards = len(oldgp.cards)
            self.changecardgpid(ogpid, newgpid)
            self.reply(
                "操作成功，已经将"+str(numofcards)+"张卡片从群："+str(ogpid)+"移动到群："+str(newgpid))
            return True

        # 转移一张卡片
        cdid = int(context.args[0])
        card = self.getcard(cdid)
        if card is None:
            return self.errorInfo("找不到这个id的卡片", True)

        oldgp = card.group
        if oldgp.getexistgame():
            return self.errorInfo("游戏正在进行，无法转移")

        pl = self.forcegetplayer(update)
        if not self.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
            return self.errorInfo("没有权限")

        # 开始执行
        card = self.popcard(cdid)
        self.addcardoverride(card, newgpid)
        cardname = card.getname()
        self.reply(
            "操作成功，已经将卡片"+cardname+"从群："+str(oldgp.id)+"移动到群："+str(newgpid))
        return True

    @commandCallbackMethod
    def choosedec(self, update: Update, context: CallbackContext) -> bool:

        if isgroup(update):
            return self.errorInfo("私聊使用该指令")

        pl = self.forcegetplayer(update)

        if pl.controlling is None:
            return self.errorInfo("请先使用 /switch 切换回要设定降值的卡。")

        if pl.controlling.data.datadec is None:
            return self.errorInfo("该卡不需要进行降值设定。请先使用 /switch 切换回要设定降值的卡。")

        self.choosedec(update, pl.controlling)
        return True

    @commandCallbackMethod
    def modify(self, update: Update, context: CallbackContext) -> bool:
        """强制修改某张卡某个属性的值。
        需要注意可能出现的问题，使用该指令前，请三思。

        `/modify --cardid --arg --value (game)`: 修改id为cardid的卡的value，要修改的参数是arg。
        带game时修改的是游戏内卡片数据，不指明时默认游戏外
        （对于游戏中与游戏外卡片区别，参见 `/help startgame`）。
        修改对应卡片的信息必须要有对应的KP权限，或者是BOT的管理者。
        如果要修改主要技能点和兴趣技能点，请使用`mainpoints`, `intpoints`作为`arg`，而不要使用points。
        id, playerid, groupid这三个属性不可以修改。
        想要修改id，请使用指令
        `/changeid --cardid --newid`
        （参考`/help changeid`）。
        想要修改所属群，使用指令
        `/changegroup --cardid --newgroupid`
        （参考`/help changegroup`）。"""

        pl = self.forcegetplayer(update)
        if not self.searchifkp(pl) and pl.id != ADMIN_ID:
            return self.errorInfo("没有权限", True)

        # need 3 args, first: card id, second: attrname, third: value
        if len(context.args) < 3:
            return self.errorInfo("需要至少3个参数", True)

        card_id = context.args[0]
        if not isint(card_id) or int(card_id) < 0:
            return self.errorInfo("无效ID", True)

        card_id = int(card_id)
        if len(context.args) > 3 and context.args[3] == "game":
            card = self.getgamecard(card_id)
            rttext = "修改了游戏内的卡片：\n"
        else:
            card = self.getcard(card_id)
            rttext = "修改了游戏外的卡片：\n"

        if card is None:
            return self.errorInfo("找不到这张卡")

        if not self.checkaccess(pl, card) & CANMODIFY:
            return self.errorInfo("没有权限", True)

        try:
            if context.args[1] == "mainpoints":
                ans, ok = card.skill.modify("points", context.args[2])
            elif context.args[1] == "intpoints":
                ans, ok = card.interest.modify("points", context.args[2])
            else:
                ans, ok = card.modify(context.args[1], context.args[2])
        except TypeError as e:
            return self.errorInfo(str(e))

        if not ok:
            return self.errorInfo("修改失败。"+ans)

        rttext += context.args[1]+"从"+ans+"变为"+context.args[2]
        self.reply(rttext)
        return True

    @commandCallbackMethod
    def setage(self, update: Update, context: CallbackContext):
        if isgroup(update):
            return self.errorInfo("发送私聊消息设置年龄。", True)

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorInfo("找不到卡。")

        if card.info.age >= 17 and card.info.age <= 99:
            return self.errorInfo("已经设置过年龄了。")

        if len(context.args) == 0:
            self.reply("请输入年龄：")
            self.addOP(getchatid(update), "setage")
            return True

        age = context.args[0]
        if not isint(age):
            return self.errorInfo("输入无效")

        age = int(age)
        return self.cardsetage(update, card, age)

    @commandCallbackMethod
    def setasset(self, update: Update, context: CallbackContext) -> bool:
        """设置你的角色卡的资金或财产，一段文字描述即可。`/setasset`"""

        card = self.forcegetplayer(update).controlling
        if card is None:
            return self.errorInfo("找不到卡。")

        if len(context.args) == 0:
            return self.errorInfo("需要参数")

        card.setassets(' '.join(context.args))
        self.reply("设置资金成功")
        return True

    @commandCallbackMethod
    def setjob(self, update: Update, context: CallbackContext) -> bool:
        """设置职业。

        `/setjob`生成按钮来设定职业。点击职业将可以查看对应的推荐技能，
        以及对应的信用范围和主要技能点计算方法。再点击确认即可确认选择该职业。
        确认了职业就不能再更改。

        `/setjob --job`将职业直接设置为给定职业。
        如果允许非经典职业，需要参数`self.IGNORE_JOB_DICT`为`True`，
        否则不能设置。如果设置了非经典职业，技能点计算方法为教育乘4。

        在力量、体质等属性减少值计算完成后才可以设置职业。"""

        if isgroup(update):
            return self.errorInfo("发送私聊消息设置职业。")

        pl = self.forcegetplayer(update)
        card = pl.controlling
        if card is None:
            return self.errorInfo("找不到卡。")
        if card.info.age == -1:
            return self.errorInfo("年龄未设置")
        if card.data.datadec is not None:
            return self.errorInfo("属性下降未设置完成")
        if card.info.job != "":
            return self.errorInfo("职业已经设置过了")

        if len(context.args) == 0:
            rtbuttons = self.makejobbutton()
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            # 设置职业的任务交给函数buttonjob
            self.reply(
                "请选择职业查看详情：", reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_JOB
            return True

        jobname = context.args[0]
        if not IGNORE_JOB_DICT and jobname not in self.joblist:
            return self.errorInfo("该职业无法设置")

        card.info.job = jobname
        if jobname not in self.joblist:
            self.reply(
                "这个职业不在职业表内，你可以用'/addskill 技能名 点数 (main/interest)'来选择技能！如果有interest参数，该技能将是兴趣技能并消耗兴趣技能点。")
            card.skill.points = int(card.data.EDU*4)
            card.write()
            return True

        for skillname in self.joblist[jobname][3:]:
            card.suggestskill.set(skillname, self.getskilllevelfromdict(
                card, skillname))
        self.reply("用 /addskill 来添加技能。")
        # This trap should not be hit
        if not self.generatePoints(card):
            return self.errorInfo("生成主要技能点出现错误")
        return True

    @commandCallbackMethod
    def switch(self, update: Update, context: CallbackContext):
        """切换目前操作的卡。
        注意，这不是指kp在游戏中的多张卡之间切换，如果kp要切换游戏中骰骰子的卡，请参见指令`/switchgamecard`。
        玩家只能修改目前操作的卡的基本信息，例如：年龄、性别、背景、技能点数等。
        `/switch`：生成按钮来切换卡。
        `/switch --cdid`切换至id为`cdid`的卡。"""

        if isgroup(update):
            return self.errorInfo("对bot私聊来切换卡。")

        pl = self.forcegetplayer(update)

        if len(pl.cards) == 0:
            return self.errorInfo("你没有任何卡。")

        if len(pl.cards) == 1:
            if pl.controlling is not None:
                return self.errorInfo("你只有一张卡，无需切换。")

            for card in pl.cards.values():
                pl.controlling = card
                break
            pl.write()

            self.reply(
                f"你只有一张卡，自动控制这张卡。现在操作的卡：{pl.controlling.getname()}")
            return True

        if len(context.args) > 0:
            if not isint(context.args[0]):
                return self.errorInfo("输入无效。")
            cdid = int(context.args[0])
            if cdid < 0:
                return self.errorInfo("卡片id为正数。")
            if cdid not in pl.cards:
                return self.errorInfo("找不到这个id的卡。")

            pl.controlling = pl.cards[cdid]
            pl.write()

            self.reply(
                f"现在操作的卡：{pl.controlling.getname()}")
            return True

        # 多个选项。创建按钮
        rtbuttons = [[]]
        for card in pl.cards.values():
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])

            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
                card.getname(), callback_data="switch "+str(card.id)))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply("请选择要切换控制的卡：", reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_SWITCH
        # 交给按钮来完成
        return True

    @commandCallbackMethod
    def switchgamecard(self, update: Update, context: CallbackContext):
        """用于KP切换游戏中进行对抗时使用的NPC卡片。

        （仅限私聊时）`/switchgamecard --groupid`：创建按钮，让KP选择要用的卡。
        （私聊群聊皆可）`/switchgamecard --cardid`：切换到id为cardid的卡并控制。"""

        if len(context.args) == 0:
            return self.errorInfo("需要参数")

        if not isint(context.args[0]):
            return self.errorInfo("参数无效")

        pl = self.forcegetplayer(update)
        iid = int(context.args[0])
        if iid >= 0:
            cdid = iid
            if cdid not in pl.gamecards:
                return self.errorInfo("你没有这个id的游戏中的卡")

            card = pl.gamecards[cdid]
            game: GroupGame = card.group.game if card.group.game is not None else card.group.pausedgame
            assert(game is not None)
            if game.kp != pl:
                return self.errorInfo("你不是该卡对应群的kp")
            game.kpctrl = card
            self.reply("切换成功")
            game.write()
            return True

        gpid = iid

        if isgroup(update):
            return self.errorInfo("请直接指定要切换的卡id，或者向bot发送私聊消息切换卡！")

        gp = self.getgp(gpid)
        if gp is None:
            return self.errorInfo("找不到该群")

        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None:
            return self.errorInfo("该群没有在进行游戏")
        if game.kp != pl:
            return self.errorInfo("你不是kp")

        rtbuttons = [[]]
        for card in game.cards.values():
            if card.player != pl:
                continue

            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])

            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
                card.getname(), callback_data="switchgamecard "+str(card.id)))

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        self.reply("请选择要切换控制的卡：", reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_SWITCHGAMECARD
        # 交给按钮来完成
        return True

    def buttonaddmainskill(self, query: CallbackQuery, args: List[str], card1: GameCard) -> bool:

        if card1 is None:
            return self.errorHandlerQ(query, "找不到卡。")

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加主要技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_ADDMAINSKILL
        return True

    def buttoncgmainskill(self, query: CallbackQuery, args: List[str], card1: GameCard) -> bool:
        if card1 is None:
            return self.errorHandlerQ(query, "找不到卡。")

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "更改主要技能点数。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.skill.get(args[1])), reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_CGMAINSKILL
        return True

    def buttonaddsgskill(self, query: CallbackQuery,  args: List[str], card1: Optional[GameCard]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, True)
            card1.skill.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="主要技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.skill.points))
            card1.suggestskill.pop(args[1])
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, True)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加建议技能。剩余技能点："+str(card1.skill.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_ADDSGSKILL
        return True

    def buttonaddintskill(self, query: CallbackQuery,  args: List[str], card1: Optional[GameCard]) -> bool:
        """响应KeyboardButton的addintskill请求。

        因为使用的是能翻页的列表，所以有可能位置1的参数是`page`，
        且位置2的参数是页码。"""
        if args[1] == "page":
            rttext, rtbuttons = self.showskillpages(int(args[2]), card1)
            query.edit_message_text(rttext)
            query.edit_message_reply_markup(InlineKeyboardMarkup(rtbuttons))
            self.workingMethod[self.lastchat] = BUTTON_ADDINTSKILL
            return True

        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, False)
            card1.interest.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
            card1.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            else:
                self.sendto(
                    card1.player, "接下来，如果没有设置过的话，请使用 /setname 设置姓名、 /setsex 设置性别、 /setbkg 设置背景信息。")
                self.reply(
                    card1.player.id, "背景设定中必要的部分有：故事、信仰、重要之人、意义非凡之地、珍视之物、性格特质。如果需要帮助，请点击`/help setbkg`并发送给我。", parse_mode="MarkdownV2")
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, False)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "添加兴趣技能。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1], reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_ADDINTSKILL
        return True

    def buttoncgintskill(self, query: CallbackQuery, args: List[str], card1: Optional[GameCard]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        if len(args) == 3:
            skvalue = int(args[2])
            needpt = self.evalskillcost(args[1], skvalue, card1, False)
            card1.interest.set(args[1], skvalue, needpt)
            query.edit_message_text(
                text="兴趣技能："+args[1]+"的值现在是"+str(skvalue)+"。剩余技能点："+str(card1.interest.points))
            card1.group.write()
            if card1.skill.points or card1.interest.points:
                self.addskill0(card1)
            return True

        m = self.getskilllevelfromdict(card1, args[1])
        mm = self.skillmaxval(args[1], card1, False)
        rtbuttons = self.makeIntButtons(m, mm, args[0], args[1])
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            "更改兴趣技能点数。剩余技能点："+str(card1.interest.points)+" 技能名称："+args[1]+"，当前技能点："+str(card1.interest.get(args[1])), reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_CGINTSKILL
        return True

    def buttonjob(self, query: CallbackQuery, args: List[str], card1: GameCard) -> bool:
        jobname = args[1]
        if len(args) == 2:
            # 切换至显示职业详情
            jobinfo = self.joblist[jobname]
            rttext = "如果确认选择该职业，请点击下面按钮进行确认。职业信息如下\n信用点范围："
            rttext += str(jobinfo[0])+"至"+str(jobinfo[1])+"\n"
            pointsrule = jobinfo[2]
            sep = ""
            for key in pointsrule:
                if len(key) < 4:
                    rttext += sep+key+"*"+str(pointsrule[key])
                elif len(key) == 7:
                    rttext += sep+key[:3]+"或"+key[4:] + \
                        "之一*"+str(pointsrule[key])
                else:
                    rttext += sep+key[:3]+"或"+key[4:7]+"或" + \
                        key[8:]+"之一*"+str(pointsrule[key])
                sep = "+"
            rttext += "\n推荐技能：\n"
            sep = ""
            for i in range(3, len(jobinfo)):
                rttext += sep+jobinfo[i]
                sep = "，"

            rtbuttons = [[
                InlineKeyboardButton(
                    text="确认", callback_data="job "+jobname+" True"),
                InlineKeyboardButton(
                    text="返回", callback_data="job "+jobname+" False")
            ]]
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text(rttext, reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_JOB
            return True
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")
        confirm = args[2]  # 只能是True，或False
        if confirm == "False":
            rtbuttons = self.makejobbutton()
            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_text("请选择职业查看详情：", reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_JOB
            return True
        # 确认完成
        card1.info.job = jobname
        query.edit_message_text(
            "职业设置为："+jobname+"\n现在你可以用指令 /addskill 添加技能，首先需要设置信用点。")
        if not self.generatePoints(card1):
            self.sendtoAdmin("生成技能出错，位置：buttonjob")
            return self.errorHandlerQ(query, "生成技能点出错！")
        for i in range(3, len(self.joblist[jobname])):  # Classical jobs
            card1.suggestskill.set(self.joblist[jobname][i], self.getskilllevelfromdict(
                card1, self.joblist[jobname][i]))   # int
        card1.group.write()
        return True

    def buttonchoosedec(self, query: CallbackQuery, args: List[str], card1: Optional[GameCard]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")

        if card1.data.datadec is None:
            return self.errorHandlerQ(query, "不需要设置降值。")

        dname = args[1]
        decnames = card1.data.datadec[0].split('_')
        if dname not in decnames:
            return self.errorHandlerQ(query, "无法为该属性设置降值。")

        if len(decnames) == 2:
            anotherdecname = decnames[0] if dname == decnames[1] else decnames[1]
            rtbuttons = self.makeIntButtons(max(0, 1-card1.data.__dict__[anotherdecname]-card1.data.datadec[1]), min(
                card1.data.__dict__[dname]-1, -card1.data.datadec[1]), f"{dname}dec", "", 1)
        elif len(decnames) == 3:
            decnames.pop(decnames.index(dname))
            d1 = decnames[0]
            d2 = decnames[1]
            rtbuttons = self.makeIntButtons(max(0, 2-card1.data.__dict__[d1]-card1.data.__dict__[d2]-card1.data.datadec[1]), min(
                card1.data.__dict__[dname]-1, -card1.data.datadec[1]
            ), f"{dname}dec", "", 1)
        else:
            raise ValueError("datadec参数错误")

        rp_markup = InlineKeyboardMarkup(rtbuttons)
        query.edit_message_text(
            f"选择下降值，目前全部数值如下：\n{str(card1.data)}", reply_markup=rp_markup)
        self.workingMethod[self.lastchat] = BUTTON_SETDEC
        return True

    def buttonsetdec(self, query: CallbackQuery, args: List[str], card1: Optional[GameCard]) -> bool:
        if not card1:
            return self.errorHandlerQ(query, "找不到卡。")

        dname = args[0][:args[0].find("dec")]
        if dname not in card1.data.alldatanames:
            self.sendtoAdmin("属性名错误，请检查代码")
            return self.errorHandlerQ(query, "属性名错误，请检查代码")
        if card1.data.datadec is None:
            return self.errorHandlerQ(query, "该卡无需设置属性降值。")

        decnames = card1.data.datadec[0].split('_')
        decval = int(args[2])

        assert(card1.data.__dict__[dname]-decval >= 1)
        assert(card1.data.datadec[1]+decval <= 0)

        if len(decnames) == 2:
            otherdec = decnames[0] if dname == decnames[1] else decnames[1]
            assert(card1.data.__dict__[otherdec] +
                   card1.data.datadec[1]+decval >= 1)

            card1.data.__dict__[dname] -= decval
            card1.data.__dict__[otherdec] += card1.data.datadec[1]+decval
            card1.data.datadec = None

            card1.generateOtherAttributes()

            query.edit_message_text(
                f"属性下降设置完成，现在基础属性：\n{str(card1.data)}\n请点击 /setjob 设置职业。")
            return True

        if len(decnames) == 3:
            decnames.pop(decnames.index(dname))

            card1.data.__dict__[dname] -= decval
            card1.data.datadec = ('_'.join(decnames),
                                  card1.data.datadec[1]+decval)
            card1.write()

            query.edit_message_text(f"请继续设置属性降值，目前全部数值如下：\n{str(card1.data)}")

            rtbuttons = [[]]
            for dname in decnames:
                rtbuttons[0].append(InlineKeyboardButton(
                    text=dname, callback_data="choosedec "+dname))

            rp_markup = InlineKeyboardMarkup(rtbuttons)
            query.edit_message_reply_markup(reply_markup=rp_markup)
            self.workingMethod[self.lastchat] = BUTTON_CHOOSEDEC
            return True

        self.sendtoAdmin("下降属性参数长度有误")
        return self.errorHandlerQ(query, "下降属性参数长度有误")

    def buttonswitch(self, query: CallbackQuery, args: List[str]) -> bool:
        pl = self.forcegetplayer(self.lastchat)
        cdid = int(args[1])

        if cdid not in pl.cards:
            return self.errorHandlerQ(query, "没有找到这个id的卡。")

        pl.controlling = pl.cards[cdid]
        pl.write()

        query.edit_message_text("修改成功，现在操作的卡是："+pl.controlling.getname())
        return True

    def buttonsetsex(self, query: CallbackQuery, args: List[str]) -> bool:
        cardi = self.findcard(self.lastchat)
        if cardi is None:
            return self.errorHandlerQ(query, "找不到卡。")

        sex = args[1]
        if sex == "other":
            self.addOP(self.lastchat, "setsex")
            query.edit_message_text("请输入具体的性别：")
            return True

        cardi.info.sex = sex
        cardi.write()

        rttext = "性别设定为"
        if sex == "male":
            rttext += "男性。"
        else:
            rttext += "女性。"
        query.edit_message_text(rttext)
        return True

    @buttonQueryHandleMethod
    def buttonHandler(self, *args, **kwargs) -> handleStatus:
        # TODO(Antares): try to use @buttonQueryHandleMethod decorate this
        pl = self.forcegetplayer(self.lastuser)
        card1 = pl.controlling
        matchdict = {
            "addmainskill": (BUTTON_ADDMAINSKILL, self.buttonaddmainskill, (card1,)),
            "cgmainskill": (BUTTON_CGMAINSKILL, self.buttoncgmainskill, (card1,)),
            "addsgskill": (BUTTON_ADDSGSKILL, self.buttonaddsgskill, (card1,)),
            "addintskill": (BUTTON_ADDINTSKILL, self.buttonaddintskill, (card1,)),
            "cgintskill": (BUTTON_CGINTSKILL, self.buttoncgintskill, (card1,)),
            "job": (BUTTON_JOB, self.buttonjob, (card1,)),
            "choosedec": (BUTTON_CHOOSEDEC, self.buttonchoosedec, (card1,)),
            "switch": (BUTTON_SWITCH, self.buttonswitch),
            "setsex": (BUTTON_SETSEX, self.buttonsetsex)
        }
        for x in CardData.alldatanames:
            matchdict[x+"dec"] = (
                BUTTON_SETDEC,
                self.buttonsetdec,
                (card1,),
                "该请求已经过期，请点击 /choosedec 重新进行操作。"
            )
        return matchdict
