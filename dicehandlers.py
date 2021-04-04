# -*- coding:utf-8 -*-
# only define handlers

import copy
import time
from typing import Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.callbackquery import CallbackQuery
from telegram.error import ChatMigrated
from telegram.ext import CallbackContext

import utils
from cfg import *
from gameclass import (PLTYPE, CardBackground, GameCard, Group, GroupGame,
                       Player)
from utils import dicebot

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


def start(update: Update, context: CallbackContext) -> None:
    """显示bot的帮助信息"""
    update.message.reply_text(utils.HELP_TEXT)

###########################################################


def addkp(update: Update, context: CallbackContext) -> bool:
    """添加KP。在群里发送`/addkp`将自己设置为KP。
    如果这个群已经有一名群成员是KP，则该指令无效。
    若原KP不在群里，该指令可以替换KP。

    如果原KP在群里，需要先发送`/delkp`来撤销自己的KP，或者管理员用`/transferkp`来强制转移KP权限。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, '发送群消息添加KP')

    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)

    # 判断是否已经有KP
    if gp.kp is not None:
        # 已有KP
        if not utils.isingroup(gp, kp):
            if not utils.changeKP(gp, kp):  # 更新NPC卡拥有者
                # 不应触发
                return utils.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")
            return True

        return utils.errorHandler(update, "你已经是KP了", True) if gp.kp == kp else utils.errorHandler(update, '这个群已经有一位KP了，请先让TA发送 /delkp 撤销自己的KP。如果需要强制更换KP，请管理员用\'/transferkp kpid\'添加本群成员为KP，或者 /transferkp 将自己设为KP。')

    # 该群没有KP，可以直接添加KP
    dicebot.addkp(gp, kp)

    # delkp指令会将KP的卡playerid全部改为0，检查如果有id为0的卡，id设为新kp的id
    utils.changecardsplid(gp, dicebot.forcegetplayer(0), kp)

    update.message.reply_text(
        "绑定群(id): " + gp.getname() + "与KP(id): " + kp.getname())

    return True


def transferkp(update: Update, context: CallbackContext) -> bool:
    """转移KP权限，只有群管理员可以使用这个指令。
    当前群没有KP时或当前群KP为管理员时，无法使用。

    `/transferkp --kpid`：将当前群KP权限转移到某个群成员。
    如果指定的`kpid`不在群内则无法设定。

    `/transferkp`：将当前群KP权限转移到自身。

    `/trasferkp`(reply to someone)：将kp权限转移给被回复者。"""

    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "发送群消息强制转移KP权限")

    gp = dicebot.getgp(update)
    pl = dicebot.getplayer(update)
    f = utils.checkaccess(pl, gp)

    if not f & GROUPADMIN:
        return utils.errorHandler(update, "没有权限", True)

    if gp.kp is None:
        return utils.errorHandler(update, "没有KP", True)

    if utils.checkaccess(gp.kp, gp) & GROUPADMIN:
        return utils.errorHandler(update, "KP是管理员，无法转移")

    # 获取newkp
    newkpid: int
    if len(context.args) != 0:
        if not utils.isint(context.args[0]):
            return utils.errorHandler(update, "参数需要是整数", True)
        newkp = dicebot.forcegetplayer(int(context.args[0]))
    else:
        t = utils.getreplyplayer(update)
        newkp = t if t is not None else dicebot.forcegetplayer(update)

    if newkp == gp.kp:
        return utils.errorHandler(update, "原KP和新KP相同", True)

    if not utils.changeKP(gp, newkp):
        return utils.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发

    return True


def delkp(update: Update, context: CallbackContext) -> bool:
    """撤销自己的KP权限。只有当前群内KP可以使用该指令。
    在撤销KP之后的新KP会自动获取原KP的所有NPC的卡片"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, '发群消息撤销自己的KP权限')

    gp = dicebot.forcegetgroup(update)
    if gp.kp is None:
        return utils.errorHandler(update, '本群没有KP', True)

    if not utils.checkaccess(dicebot.forcegetplayer(update), gp) & GROUPKP:
        return utils.errorHandler(update, '你不是KP', True)

    utils.changecardsplid(gp, gp.kp, dicebot.forcegetplayer(0))
    dicebot.delkp(gp)

    update.message.reply_text('KP已撤销')

    if utils.getOP(gp.id).find("delcard") != -1:
        utils.popOP(gp.id)

    return True


def reload(update: Update, context: CallbackContext) -> bool:
    """重新读取所有文件，只有bot管理者可以使用"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.getmsgfromid(update) != utils.ADMIN_ID:
        return utils.errorHandler(update, "没有权限", True)

    try:
        dicebot.readall()
        dicebot.construct()
    except:
        return utils.errorHandler(update, "读取文件出现问题，请检查json文件！")

    update.message.reply_text('重新读取文件成功。')
    return True


def showuserlist(update: Update, context: CallbackContext) -> bool:
    """显示所有信息。非KP无法使用这一指令。
    群聊时不可以使用该指令。
    Bot管理者使用该指令，bot将逐条显示群-KP信息、
    全部的卡信息、游戏信息。KP使用时，只会显示与TA相关的这些消息。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):  # Group msg: do nothing, even sender is USER or KP
        return utils.errorHandler(update, "没有这一指令", True)

    user = dicebot.forcegetplayer(update)

    if not utils.searchifkp(user) and user.id != ADMIN_ID:
        return utils.errorHandler(update, "没有这一指令")

    # 群
    for gp in dicebot.groups.values():
        if utils.checkaccess(user, gp) & (GROUPKP | BOTADMIN) != 0:
            update.message.reply_text(str(gp))
            time.sleep(0.2)

    # 玩家
    for pl in dicebot.players.values():
        if pl == user or user.id == ADMIN_ID:
            update.message.reply_text(str(pl))
            time.sleep(0.2)

    # 卡片
    for card in dicebot.cards.values():
        if utils.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
            update.message.reply_text(str(card))
            time.sleep(0.2)

    # 游戏中卡片
    for card in dicebot.gamecards.values():
        if utils.checkaccess(pl, card) != 0 or user.id == ADMIN_ID:
            update.message.reply_text(str(card))
            time.sleep(0.2)

    return True


def delmsg(update: Update, context: CallbackContext) -> bool:
    """用于删除消息，清空当前对话框中没有用的消息。
    bot可以删除任意私聊消息，无论是来自用户还是bot。
    如果是群内使用该指令，需要管理员或KP权限，
    以及bot是管理员，此时可以删除群内的任意消息。

    当因为各种操作产生了过多冗杂消息的时候，使用
    `/delmsg --msgnumber`将会删除：delmsg指令的消息
    以及该指令上面的msgnumber条消息。例如：
    `/delmsg 2`将删除包含delmsg指令在内的3条消息。
    没有参数的时候，`/delmsg`默认删除指令和指令的上一条消息。

    因为要进行连续的删除请求，删除的时间会稍微有些滞后，
    请不要重复发送该指令，否则可能造成有用的消息丢失。
    如果感觉删除没有完成，请先随意发送一条消息来拉取删除情况，
    而不是继续用`/delmsg`删除。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    delnum = 1
    chatid = utils.getchatid(update)

    if utils.isgroupmsg(update) and not utils.isadmin(update, utils.BOT_ID):
        return utils.errorHandler(update, "Bot没有管理权限")

    if utils.isgroupmsg(update) and utils.checkaccess(dicebot.forcegetplayer(update), dicebot.forcegetgroup(update)) & (GROUPKP | GROUPADMIN) != 0:
        return utils.errorHandler(update, "没有权限", True)

    if len(context.args) >= 1:
        if not utils.isint(context.args[0]) or int(context.args[0]) <= 0:
            return utils.errorHandler(update, "参数错误", True)
        delnum = int(context.args[0])
        if delnum > 10:
            return utils.errorHandler(update, "一次最多删除10条消息")

    lastmsgid = update.message.message_id
    while delnum >= 0:  # 这是因为要连同delmsg指令的消息也要删掉
        if lastmsgid < -100:
            break
        try:
            context.bot.delete_message(chat_id=chatid, message_id=lastmsgid)
        except:
            lastmsgid -= 1
        else:
            delnum -= 1
            lastmsgid -= 1

    update.effective_chat.send_message("删除完成").delete()
    return True


def getid(update: Update, context: CallbackContext) -> None:
    """获取所在聊天环境的id。
    私聊使用该指令发送用户id，群聊使用该指令则发送群id。
    在创建卡片等待群id时使用该指令，会自动创建卡。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    chatid = utils.getchatid(update)
    pl = dicebot.forcegetplayer(update)
    fromuser = pl.id
    # 检测是否处于newcard状态
    opers = utils.getOP(fromuser)

    if opers != "" and utils.isgroupmsg(update):
        opers = opers.split(" ")
        if utils.isgroupmsg(update) and opers[0] == "newcard":
            utils.popOP(fromuser)

            if utils.hascard(fromuser, chatid) and dicebot.getgp(update).kp is not None and dicebot.getgp(update).kp != pl:
                context.bot.send_message(
                    chat_id=fromuser, text="你在这个群已经有一张卡了！")
                return
            if len(opers) >= 3:
                utils.getnewcard(
                    int(opers[1]), chatid, fromuser, int(opers[2]))
            else:
                utils.getnewcard(int(opers[1]), chatid, fromuser)

            rtbutton = [[InlineKeyboardButton(
                text="跳转到私聊", callback_data="None", url="t.me/"+utils.BOTUSERNAME)]]
            rp_markup = InlineKeyboardMarkup(rtbutton)

            update.message.reply_text("<code>"+str(chatid) +
                                      "</code> \n点击即可复制", parse_mode='HTML', reply_markup=rp_markup)
            return True

    update.message.reply_text("<code>"+str(chatid) +
                              "</code> \n点击即可复制", parse_mode='HTML')


def showrule(update: Update, context: CallbackContext) -> bool:
    """显示当前群内的规则。
    如果想了解群规则的详情，请查阅setrule指令的帮助：
    `/help setrule`"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "请在群内查看规则")

    gp = dicebot.forcegetgroup(update)
    rule = gp.rule

    update.message.reply_text(str(rule))
    return True


def setrule(update: Update, context: CallbackContext) -> bool:
    """设置游戏的规则。
    一个群里游戏有自动生成的默认规则，使用本指令可以修改这些规则。

    `/setrule --args`修改规则。`--args`格式如下：

    `rulename1:str --rules1:List[int] rulename2:str --rule2:List[int] ...`

    一次可以修改多项规则。
    有可能会出现部分规则设置成功，但部分规则设置失败的情况，
    查看返回的信息可以知道哪些部分已经成功修改。

    规则的详细说明：

    skillmax：接收长度为3的数组，记为r。`r[0]`是一般技能上限，
    `r[1]`是个别技能的上限，`r[2]`表示个别技能的个数。

    skillmaxAged：年龄得到的技能上限增加设定。
    接收长度为4的数组，记为r。`r[0]`至`r[2]`同上，
    但仅仅在年龄大于`r[3]`时开启该设定。`r[3]`等于100代表不开启该设定。

    skillcost：技能点数分配时的消耗。接收长度为偶数的数组，记为r。
    若i为偶数（或0），`r[i]`表示技能点小于`r[i+1]`时，
    需要分配`r[i]`点点数来获得1点技能点。r的最后一项必须是100。
    例如：`r=[1, 80, 2, 100]`，则从10点升至90点需要花费`1*70+2*10=90`点数。

    greatsuccess：大成功范围。接收长度为4的数组，记为r。
    `r[0]-r[1]`为检定大于等于50时大成功范围，否则是`r[2]-r[3]`。

    greatfail：大失败范围。同上。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "请在群内用该指令设置规则")

    gp = dicebot.forcegetgroup(update)

    if not utils.isfromkp(update):
        return utils.errorHandler(update, "没有权限", True)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)

    gprule = gp.rule

    ruledict: Dict[str, List[int]] = {}

    i = 0
    while i < len(context.args):
        j = i+1
        tplist: List[int] = []
        while j < len(context.args):
            if utils.isint(context.args[j]):
                tplist.append(int(context.args[j]))
                j += 1
            else:
                break
        ruledict[context.args[i]] = tplist
        i = j
    del i, j

    msg, ok = gprule.changeRules(ruledict)
    if not ok:
        return utils.errorHandler(update, msg)

    update.message.reply_text(msg)
    return True


def createcardhelp(update: Update, context: CallbackContext) -> None:
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    update.message.reply_text(utils.CREATE_CARD_HELP, parse_mode="MarkdownV2")


def trynewcard(update: Update, context: CallbackContext) -> bool:
    """测试建卡，用于熟悉建卡流程。
    测试创建的卡一定可以删除。
    创建新卡指令的帮助见`/help newcard`，
    对建卡过程有疑问，见 `/createcardhelp`。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息创建角色卡。")

    gp = dicebot.getgp(-1)
    if gp is None:
        gp = dicebot.creategp(-1)
        gp.kp = dicebot.forcegetplayer(ADMIN_ID)

    return utils.getnewcard(update.message.message_id, -1, utils.getchatid(update))


def newcard(update: Update, context: CallbackContext) -> bool:
    """随机生成一张新的角色卡。需要一个群id作为参数。
    只接受私聊消息。

    如果发送者不是KP，那么只能在一个群内拥有最多一张角色卡。

    如果不知道群id，请先发送`/getid`到群里获取id。

    `/newcard`提交创建卡请求，bot会等待你输入`groupid`。
    `/newcard --groupid`新建一张卡片，绑定到`groupid`对应的群。
    `/newcard --cardid`新建一张卡片，将卡片id设置为`cardid`，`cardid`必须是非负整数。
    `/newcard --groupid --cardid`新建一张卡片，绑定到`groupid`对应的群的同时，将卡片id设置为`cardid`。

    当指定的卡id已经被别的卡占用的时候，将自动获取未被占用的id。

    当生成时有至少三项基础属性低于50时，可以使用`/discard`来放弃并删除这张角色卡。
    创建新卡之后，当前控制卡片会自动切换到新卡，详情参见
    `/help switch`。

    角色卡说明
    一张角色卡具有：
    `groupid`，`id`，`playerid`基本信息。
    STR，CON，SIZ，DEX，APP，INT，EDU，LUCK基本属性；
    职业、姓名、性别、年龄；
    技能信息；
    背景故事（描述，重要之人，重要之地，珍视之物，特质，受过的伤，恐惧之物，神秘学物品，第三类接触）；
    检定修正值；
    物品，财产；
    角色类型（PL，NPC）；
    是否可以被删除；
    状态（存活，死亡，疯狂等）。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息创建角色卡。")

    gpid: int = None
    gp: Optional[Group] = None
    newcdid: Optional[int] = None

    if len(context.args) > 0:
        msg = context.args[0]

        if not utils.isint(msg):
            return utils.errorHandler(update, "输入无效")

        if int(msg) >= 0:
            newcdid = int(msg)
        else:
            gpid = int(msg)
            gp = dicebot.forcegetgroup(gpid)
            if len(context.args) > 1:
                if not utils.isint(context.args[1]) or int(context.args[1]) < 0:
                    return utils.errorHandler(update, "输入无效")
                newcdid = int(context.args[1])

    if gp is None:
        update.message.reply_text(
            "准备创建新卡。\n如果你不知道群id，在群里发送 /getid 即可创建角色卡。\n你也可以选择手动输入群id，请发送群id：")
        if newcdid is None:
            utils.addOP(utils.getchatid(update), "newcard " +
                        str(update.message.message_id))
        else:
            utils.addOP(utils.getchatid(update), "newcard " +
                        str(update.message.message_id)+" "+str(newcdid))
        return True

    # 检查(pl)是否已经有卡
    pl = dicebot.forcegetplayer(update)
    plid = pl.id
    if utils.hascard(plid, gpid) and pl != gp.kp:
        return utils.errorHandler(update, "你在这个群已经有一张卡了！")

    # 符合建卡条件，生成新卡
    # gp is not None
    assert(gpid is not None)

    return utils.getnewcard(update.message.message_id, gpid, plid, newcdid) if newcdid is not None else utils.getnewcard(update.message.message_id, gpid, plid)


def renewcard(update: Update, context: CallbackContext) -> bool:
    """如果卡片是可以discard的状态，使用该指令可以将卡片重置。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if pl.controlling is None:
        return utils.errorHandler(update, "没有操作中的卡")
    f = utils.checkaccess(pl, pl.controlling)
    if f & CANDISCARD == 0:
        return utils.errorHandler(update, "选中的卡不可重置。如果您使用了 /switch 切换操作中的卡，请使用 /switch 切换回要重置的卡")

    pl.controlling.backtonewcard()
    update.message.reply_text(pl.controlling.data.datainfo)
    if pl.controlling.data.countless50discard():
        pl.controlling.discard = True
        update.message.reply_text(
            "因为有三项属性小于50，如果你愿意的话可以再次点击 /renewcard 来重置这张角色卡。如果停止创建卡，点击 /discard 来放弃建卡。\n设定年龄后则不能再删除这张卡。")
    else:
        pl.controlling.discard = False
    return True


def discard(update: Update, context: CallbackContext) -> bool:
    """该指令用于删除角色卡。
    通过识别卡中`discard`是否为`True`来判断是否可以删除这张卡。
    如果`discard`为`False`，需要玩家向KP申请，让KP修改`discard`属性为`True`。

    指令格式如下：
    `/discard (--groupid_1/--cardid_1 --groupid_2/--cardid_2 ...)`。
    可以一次输入多个群或卡id来批量删除。

    无参数时，如果只有一张卡可以删除，自动删除那张卡。
    否则，会创建一组按钮来让玩家选择要删除哪张卡。

    有参数时，
    若其中一个参数为群id（负数），则删除该群内所有可删除的卡。
    若其中一个参数为卡id，删除对应的那张卡。
    找不到参数对应的卡时，该参数会被忽略。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息删除卡。")

    pl = dicebot.getplayer(update)  # 发送者
    if pl is None:
        return utils.errorHandler(update, "找不到可删除的卡。")

    if len(context.args) > 0:
        # 先处理context.args
        if any(not utils.isint(x) for x in context.args):
            return utils.errorHandler(update, "参数需要是整数")
        nargs = list(map(int, context.args))

        discards = utils.findDiscardCardsWithGpidCdid(pl, nargs)

        # 求args提供的卡id与可删除的卡id的交集

        if len(discards) == 0:  # 交集为空集
            return utils.errorHandler(update, "输入的（群/卡片）ID均无效。")

        if len(discards) == 1:
            card = discards[0]
            rttext = "删除卡："+str(card.getname())
            rttext += "\n/details 显示删除的卡片信息。删除操作不可逆。"
            update.message.reply_text(rttext)
        else:
            update.message.reply_text(
                "删除了"+str(len(discards))+"张卡片。\n删除操作不可逆。")

        for card in discards:
            utils.cardpop(card)
        return True

    # 计算可以discard的卡有多少
    discardgpcdTupleList = utils.findAllDiscardCards(pl)
    if len(discardgpcdTupleList) > 1:  # 创建按钮，接下来交给按钮完成
        rtbuttons: List[List[str]] = [[]]

        for card in discardgpcdTupleList:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            cardname = card.getname()
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(cardname,
                                                                    callback_data=dicebot.IDENTIFIER+" "+"discard "+str(card.id)))

        rp_markup = InlineKeyboardMarkup(rtbuttons)

        update.message.reply_text("请点击要删除的卡片：", reply_markup=rp_markup)
        return True

    if len(discardgpcdTupleList) == 1:
        card = discardgpcdTupleList[0]

        rttext = "删除卡："+card.getname()
        rttext += "\n删除操作不可逆。"
        update.message.reply_text(rttext)

        utils.cardpop(card)
        return True

    # 没有可删除的卡
    return utils.errorHandler(update, "找不到可删除的卡。")


def delcard(update: Update, context: CallbackContext) -> bool:
    """KP才能使用该指令，删除一张卡片。一次只能删除一张卡。
    `/delcard --cardid`：删除id为cardid的卡。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要卡id作为参数", True)
    if not utils.isint(context.args[0]) or int(context.args[0]) < 0:
        return utils.errorHandler(update, "参数无效", True)

    cdid = int(context.args[0])
    card = dicebot.getcard(cdid)

    if card is None:
        return utils.errorHandler(update, "找不到对应id的卡")

    kp = dicebot.forcegetplayer(update)
    if not utils.checkaccess(kp, card) & CANMODIFY:
        return utils.errorHandler(update, "没有权限", True)

    # 开始处理
    update.message.reply_text(
        f"请确认是否删除卡片\n姓名：{card.getname()}\n如果确认删除，请回复：确认。否则，请回复其他任何文字。")
    utils.addOP(utils.getchatid(update), "delcard "+context.args[0])
    return True


def link(update: Update, context: CallbackContext) -> bool:
    """获取群邀请链接，并私聊发送给用户。

    使用该指令必须要满足两个条件：指令发送者和bot都是该群管理员。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "在群聊使用该指令。")
    if not utils.isadmin(update, utils.BOT_ID):
        return utils.errorHandler(update, "Bot没有权限")
    if not utils.isadmin(update, update.message.from_user.id):
        return utils.errorHandler(update, "没有权限", True)

    adminid = update.message.from_user.id
    gpid = update.effective_chat.id
    chat = context.bot.get_chat(chat_id=gpid)
    ivlink = chat.invite_link
    if not ivlink:
        ivlink = context.bot.export_chat_invite_link(chat_id=gpid)

    try:
        context.bot.send_message(
            chat_id=adminid, text="群："+chat.title+"的邀请链接：\n"+ivlink)
    except:
        update.message.reply_text("消息发送失败！请检查是否开启了和我的私聊！")
        return False

    rtbutton = [[InlineKeyboardButton(
        text="跳转到私聊", callback_data="None", url="t.me/"+BOTUSERNAME)]]
    rp_markup = InlineKeyboardMarkup(rtbutton)

    update.message.reply_text("群邀请链接已经私聊发送。", reply_markup=rp_markup)
    return True


def setage(update: Update, context: CallbackContext):
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息设置年龄。", True)

    pl = dicebot.forcegetplayer(update)
    card = pl.controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。")

    if card.info.age >= 17 and card.info.age <= 99:
        return utils.errorHandler(update, "已经设置过年龄了。")

    if len(context.args) == 0:
        update.message.reply_text("请输入年龄：")
        utils.addOP(utils.getchatid(update), "setage")
        return True

    age = context.args[0]
    if not utils.isint(age):
        return utils.errorHandler(update, "输入无效")

    age = int(age)
    return utils.cardsetage(update, card, age)


def choosedec(update: Update, context: CallbackContext) -> bool:
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "私聊使用该指令")

    pl = dicebot.forcegetplayer(update)

    if pl.controlling is None:
        return utils.errorHandler(update, "请先使用 /switch 切换回要设定降值的卡。")

    if pl.controlling.data.datadec is None:
        return utils.errorHandler(update, "该卡不需要进行降值设定。请先使用 /switch 切换回要设定降值的卡。")

    utils.choosedec(update, pl.controlling)
    return True


def addnewjob(update: Update, context: CallbackContext) -> bool:
    """向bot数据库中申请添加一个新的职业。
    仅限kp使用这个指令。添加后，请等待bot控制者审核该职业的信息。格式如下：
    `/addnewjob --jobname --creditMin --creditMax --dataname1:ratio --dataname2:ratio/--dataname3_dataname4:ratio...  --skillname1 --skillname2...`
    例如：
    `/addnewjob 刺客 30 60 EDU:2 DEX_STR:2 乔装 电器维修 斗殴 火器 锁匠 机械维修 潜行 心理学`。
    EDU等属性名请使用大写字母。
    审核完成后结果会私聊回复给kp，请开启与bot的私聊。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if pl.id in dicebot.addjobrequest:
        return utils.errorHandler(update, "已经提交过一个申请了")

    if not utils.searchifkp(pl):
        return utils.errorHandler(update, "kp才能使用该指令", True)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)

    if len(context.args) <= 3:
        return utils.errorHandler(update, "参数长度不足")

    if not utils.isint(context.args[1]) or not utils.isint(context.args[2]) or int(context.args[1]) < 0 or int(context.args[1]) > int(context.args[2]):
        return utils.errorHandler(update, "信用范围参数无效")

    jobname: str = context.args[0]
    mincre = int(context.args[1])
    maxcre = int(context.args[2])

    i = 3
    ptevalpairs: List[Tuple[str, int]] = []
    while i < len(context.args) and context.args[i].find(':') != -1:
        p = context.args[i].split(':')
        if not utils.isint(p[1]):
            return utils.errorHandler(update, "参数无效")

        ptevalpairs.append((p[0], int(p[1])))
        i += 1

    if sum(j for _, j in ptevalpairs) != 4:
        return utils.errorHandler(update, "技能点数的乘数总值应该为4")

    skilllist: List[str] = context.args[i:]
    if any(j not in dicebot.skilllist for j in skilllist):
        return utils.errorHandler(update, "存在技能表中没有的技能，请先发起技能添加申请或者核阅是否有错别字、使用了同义词")

    ptevald: Dict[str, int] = {}
    for n, j in ptevalpairs:
        ptevald[n] = j

    jobl = [mincre, maxcre, ptevald]
    jobl += skilllist

    ans = (jobname, jobl)
    dicebot.addjobrequest[pl.id, ans]

    pl.renew(dicebot.updater)
    plname = pl.username if pl.username != "" else pl.name
    if plname == "":
        plname = str(pl.id)
    dicebot.sendtoAdmin("有新的职业添加申请："+str(ans) +
                        f"\n来自：@{plname}，id为：{str(pl.id)}")
    utils.addOP(ADMIN_ID, "passjob")

    update.message.reply_text("申请已经提交，请开启与我的私聊接收审核消息")
    return True


def addnewskill(update: Update, context: CallbackContext) -> bool:
    """向bot数据库中申请添加一个新的技能。
    仅限kp使用这个指令。添加后，请等待bot控制者审核该技能的信息。格式如下：
    `/addnewskill --skillname --basicpoints`
    例如：`/addnewskill 识破 25`。
    审核完成后结果会私聊回复给kp，请开启与bot的私聊。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if pl.id in dicebot.addskillrequest:
        return utils.errorHandler(update, "已经提交过一个申请了")

    if not utils.searchifkp(pl):
        return utils.errorHandler(update, "kp才能使用该指令", True)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)

    if len(context.args) < 2:
        return utils.errorHandler(update, "参数长度不足")

    if not utils.isint(context.args[1]) or int(context.args[1]) < 0 or int(context.args[1]) > 99:
        return utils.errorHandler(update, "技能基础点数参数无效")

    skillname: str = context.args[0]
    bspt = int(context.args[1])

    if skillname in dicebot.skilllist:
        return utils.errorHandler(update, "该技能已经存在于列表中")

    ans = (skillname, bspt)
    dicebot.addskillrequest[pl.id, ans]

    pl.renew(dicebot.updater)
    plname = pl.username if pl.username != "" else ""
    if plname == "":
        plname = str(pl.id)
    dicebot.sendtoAdmin("有新的技能添加申请："+str(ans) +
                        f"\n来自：@{plname}，id为：{str(pl.id)}")
    utils.addOP(ADMIN_ID, "passskill")

    update.message.reply_text("申请已经提交，请开启与我的私聊接收审核消息")
    return True


def setjob(update: Update, context: CallbackContext) -> bool:
    """设置职业。

    `/setjob`生成按钮来设定职业。点击职业将可以查看对应的推荐技能，
    以及对应的信用范围和主要技能点计算方法。再点击确认即可确认选择该职业。
    确认了职业就不能再更改。

    `/setjob --job`将职业直接设置为给定职业。
    如果允许非经典职业，需要参数`utils.IGNORE_JOB_DICT`为`True`，
    否则不能设置。如果设置了非经典职业，技能点计算方法为教育乘4。

    在力量、体质等属性减少值计算完成后才可以设置职业。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息设置职业。")

    pl = dicebot.forcegetplayer(update)
    card = pl.controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。")
    if card.info.age == -1:
        return utils.errorHandler(update, "年龄未设置")
    if card.data.datadec is not None:
        return utils.errorHandler(update, "属性下降未设置完成")

    if len(context.args) == 0:
        rtbuttons = utils.makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        # 设置职业的任务交给函数buttonjob
        update.message.reply_text(
            "请选择职业查看详情：", reply_markup=rp_markup)
        return True

    jobname = context.args[0]
    if not IGNORE_JOB_DICT and jobname not in utils.dicebot.joblist:
        return utils.errorHandler("该职业无法设置")

    card.info.job = jobname
    if jobname not in utils.dicebot.joblist:
        update.message.reply_text(
            "这个职业不在职业表内，你可以用'/addskill 技能名 点数 (main/interest)'来选择技能！如果有interest参数，该技能将是兴趣技能并消耗兴趣技能点。")
        card.skill.points = int(card.data.EDU*4)
        card.write()
        return True

    for skillname in dicebot.joblist[jobname][3:]:
        card.suggestskill.set(skillname, utils.getskilllevelfromdict(
            card, skillname))
    update.message.reply_text("用 /addskill 来添加技能。")
    # This trap should not be hit
    if not utils.generatePoints(card):
        return utils.errorHandler(update, "生成主要技能点出现错误")
    return True


def showjoblist(update: Update, context: CallbackContext) -> None:
    """显示职业列表"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isprivatemsg(update):
        return utils.errorHandler(update, "请在私聊中使用该指令")

    rttext = "职业列表："
    counts = 0

    for job in dicebot.joblist:
        jobinfo = dicebot.joblist[job]

        rttext += job+f"：\n信用范围 [{str(jobinfo[0])},{str(jobinfo[1])}]\n"

        rttext += "技能点计算方法："
        calcd: Dict[str, int] = jobinfo[2]
        calcmeth = " 加 ".join("或".join(x.split('_')) +
                              "乘"+str(calcd[x]) for x in calcd)
        rttext += calcmeth+"\n"

        rttext += "主要技能："+"、".join(x for x in jobinfo[3:])+"\n"

        counts += 1

        if counts == 3:
            update.message.reply_text(rttext)
            rttext = ""
            counts = 0
            time.sleep(0.2)


def addskill(update: Update, context: CallbackContext) -> bool:
    """该函数用于增加/修改技能。

    `/addskill`：生成按钮，玩家按照提示一步步操作。
    `/addskill 技能名`：修改某项技能的点数。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发私聊消息来增改技能", True)

    pl = dicebot.forcegetplayer(update)
    card1 = pl.controlling
    if card1 is None:
        return utils.errorHandler(update, "找不到卡。")

    if card1.skill.points == -1:
        return utils.errorHandler(update, "信息不完整，无法添加技能")

    if card1.skill.points == 0 and card1.interest.points == 0:
        if len(context.args) == 0 or (context.args[0] not in card1.skill.allskills() and context.args[0] not in card1.interest.allskills()):
            return utils.errorHandler(update, "你已经没有技能点了，请添加参数来修改具体的技能！")

    if card1.info.job == "":
        return utils.errorHandler(update, "请先设置职业")

    # 开始处理
    if "信用" not in card1.skill.allskills():
        return utils.addcredit(update, card1)

    if len(context.args) == 0:
        return utils.addskill0(card1)

    if context.args[0] == "信用" or context.args[0] == "credit":
        return utils.addcredit(update, card1) if "信用" not in card1.skill.allskills() else utils.cgcredit(update, card1)

    skillname = context.args[0]

    if skillname != "母语" and skillname != "闪避" and (skillname not in dicebot.skilllist or skillname == "克苏鲁神话"):
        return utils.errorHandler(update, "无法设置这个技能")

    # This function only returns True
    return utils.addskill1(update, context, card1)


def showskilllist(update: Update, context: CallbackContext) -> None:
    """显示技能列表"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    rttext = "技能：基础值\n"
    rttext += "母语：等于EDU\n"
    rttext += "闪避：等于DEX的一半\n"

    for skill in dicebot.skilllist:
        rttext += skill+"："+str(dicebot.skilllist[skill])+"\n"

    update.message.reply_text(rttext)


def button(update: Update, context: CallbackContext):
    """所有按钮请求经该函数处理。功能十分复杂，拆分成多个子函数来处理。
    接收到按钮的参数后，转到对应的子函数处理。"""
    query: CallbackQuery = update.callback_query
    query.answer()

    if query.data == "None":
        return False
    if utils.isgroupmsg(update):
        return False

    args = query.data.split(" ")
    identifier = args[0]
    if identifier != dicebot.IDENTIFIER:
        if args[1].find("dec") != -1:
            return utils.errorHandlerQ(query, "该请求已经过期，请点击 /choosedec 重新进行操作。")
        return utils.errorHandlerQ(query, "该请求已经过期。")

    chatid = utils.getchatid(update)
    pl = dicebot.forcegetplayer(query.from_user.id)
    card1 = pl.controlling
    args = args[1:]

    # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
    if args[0] == "job":  # Job in buttons must be classical
        return utils.buttonjob(query, card1, args)
    # Increase skills already added, because sgskill is none. second arg is skillname
    if args[0] == "addmainskill":
        return utils.buttonaddmainskill(query, card1, args)
    if args[0] == "cgmainskill":
        return utils.buttoncgmainskill(query, card1, args)
    if args[0] == "addsgskill":
        return utils.buttonaddsgskill(query, card1, args)
    if args[0] == "addintskill":
        return utils.buttonaddintskill(query, card1, args)
    if args[0] == "cgintskill":
        return utils.buttoncgintskill(query, card1, args)
    if args[0] == "choosedec":
        return utils.buttonchoosedec(query, card1, args)
    if args[0].find("dec") != -1:
        return utils.buttonsetdec(query, card1, args)
    if args[0] == "discard":
        return utils.buttondiscard(query, chatid, args)
    if args[0] == "switch":
        return utils.buttonswitch(query, chatid, args)
    if args[0] == "switchgamecard":
        return utils.buttonswitchgamecard(query, chatid, args)
    if args[0] == "setsex":
        return utils.buttonsetsex(query, chatid, args)
    # HIT BAD TRAP
    return False


def setname(update: Update, context: CallbackContext) -> bool:
    """设置角色卡姓名。

    `/setname --name`：直接设定姓名。
    `/setname`：bot将等待输入姓名。
    设置的姓名可以带有空格等字符。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    card1 = dicebot.forcegetplayer(update).controlling
    if card1 is None:
        return utils.errorHandler(update, "找不到卡。")

    if len(context.args) == 0:
        if utils.isprivatemsg(update):
            utils.addOP(utils.getchatid(update), "setname")
        else:
            utils.addOP(utils.getchatid(update),
                        "setname "+str(card1.playerid))
        update.message.reply_text("请输入姓名：")
        return True

    utils.nameset(card1, ' '.join(context.args))
    update.message.reply_text("角色的名字已经设置为"+card1.info.name+"。")
    return True


def additem(update: Update, context: CallbackContext) -> bool:
    """为你的人物卡添加一些物品。用空格，制表符或回车来分隔不同物品。
    `/additem --item1 --item2...`"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    card = dicebot.forcegetplayer(update).controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。")

    card.additems(context.args)
    update.message.reply_text(f"添加了{str(len(context.args))}件物品。")
    return True


def setasset(update: Update, context: CallbackContext) -> bool:
    """设置你的角色卡的资金或财产，一段文字描述即可。`/setasset`"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    card = dicebot.forcegetplayer(update).controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。")

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")

    card.setassets(' '.join(context.args))
    update.message.reply_text("设置资金成功")
    return True


def startgame(update: Update, context: CallbackContext) -> bool:
    """开始一场游戏。

    这一指令将拷贝本群内所有卡，之后将用拷贝的卡片副本进行游戏，修改属性将不会影响到游戏外的原卡属性。
    如果要正常结束游戏，使用`/endgame`可以将游戏的角色卡数据覆写到原本的数据上。
    如果要放弃这些游戏内进行的修改，使用`/abortgame`会直接删除这些副本副本"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "游戏需要在群里进行")

    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)
    if gp.kp != kp:
        return utils.errorHandler(update, "游戏只能由KP发起", True)
    if gp.game is not None:
        return utils.errorHandler(update, "游戏已经在进行中")

    # 开始执行
    if gp.pausedgame is not None:
        return continuegame(update, context)  # 检测到游戏暂停中，直接继续

    if len(gp.cards) == 0:
        return utils.errorHandler(update, "本群没有任何卡片，无法开始游戏")

    canstart = True
    for card in gp.cards.values():
        card.generateOtherAttributes()
        if card.type != PLTYPE:
            continue
        ck = card.check()
        if ck != "":
            canstart = False
            update.message.reply_text(ck)

    if not canstart:
        return False

    gp.game = GroupGame(gp.id, gp.cards)
    # 构建数据关联
    gp.game.group = gp
    gp.game.kp = gp.kp
    kp.kpgames[gp.id] = gp.game
    for card in gp.game.cards.values():
        dicebot.gamecards[card.id] = card
        card.write()
        card.group = gp
        card.player = dicebot.getcard(card.id).player
        card.player.gamecards[card.id] = card

    update.message.reply_text("游戏开始！")
    return True


def pausegame(update: Update, context: CallbackContext) -> bool:
    """暂停游戏。
    游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
    当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
    可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
    继续游戏后会覆盖游戏中的这些属性。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送群消息暂停游戏")

    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)

    if gp.kp != kp:
        return utils.errorHandler(update, "只有KP可以暂停游戏", True)
    if gp.game is None:
        return utils.errorHandler(update, "没有进行中的游戏", True)

    gp.pausedgame = gp.game
    gp.game = None
    gp.write()

    update.message.reply_text("游戏暂停，用 /continuegame 恢复游戏")
    return True


def continuegame(update: Update, context: CallbackContext) -> bool:
    """继续游戏。必须在`/pausegame`之后使用。
    游戏被暂停时，可以视为游戏不存在，游戏中卡片被暂时保护起来。
    当有中途加入的玩家时，使用该指令先暂停游戏，再继续游戏即可将新的角色卡加入进来。
    可以在暂停时（或暂停前）修改：姓名、性别、随身物品、财产、背景故事，
    继续游戏后会覆盖游戏中的这些属性。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送群消息暂停游戏")

    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)

    if gp.kp != kp:
        return utils.errorHandler(update, "只有KP可以暂停游戏", True)
    if gp.pausedgame is None:
        return utils.errorHandler(update, "没有进行中的游戏", True)

    for card in gp.pausedgame.cards.values():
        outcard = gp.getcard(card.id)
        assert(outcard is not None)
        card.info.name = outcard.info.name
        card.info.sex = outcard.info.sex
        card.item = copy.copy(outcard.item)
        card.assets = outcard.assets
        card.background = CardBackground(d=outcard.background.to_json())

    for card in gp.cards.values():
        if card.id not in gp.pausedgame.cards:
            ngcard = GameCard(card.to_json())
            ngcard.isgamecard = True
            gp.pausedgame.cards[card.id] = ngcard
            dicebot.gamecards[card.id] = gp.pausedgame.cards[card.id]

    gp.write()
    update.message.reply_text("游戏继续！")
    return True


def abortgame(update: Update, context: CallbackContext) -> bool:
    """放弃游戏。只有KP能使用该指令。这还将导致放弃在游戏中做出的所有修改，包括hp，SAN等。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送群聊消息来中止游戏")
    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)

    if gp.kp != kp:
        return utils.errorHandler(update, "只有KP可以中止游戏", True)

    if utils.gamepop(gp) is None:
        return utils.errorHandler(update, "没有找到游戏", True)

    update.message.reply_text("游戏已终止！")
    return True


def endgame(update: Update, context: CallbackContext) -> bool:
    """结束游戏。

    这一指令会导致所有角色卡的所有权转移给KP，之后玩家无法再操作这张卡片。
    同时，游戏外的卡片会被游戏内的卡片覆写。
    如果还没有准备好进行覆写，就不要使用这一指令。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "群聊才能使用该指令")

    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)
    if gp.kp != kp:
        return utils.errorHandler("只有KP可以结束游戏。")

    game = gp.game if gp.game is not None else gp.pausedgame
    if game is None:
        return utils.errorHandler(update, "没找到进行中的游戏。")

    idl = list(game.cards.keys())  # 在迭代过程中改变键会抛出错误，复制键
    for x in idl:
        dicebot.popcard(x)
        nocard = dicebot.popgamecard(x)
        nocard.isgamecard = False
        nocard.playerid = kp.id
        dicebot.addcard(nocard)

    gp.game = None
    gp.pausedgame = None
    gp.kp.kpgames.pop(gp.id)

    update.message.reply_text("游戏结束！")
    return True


def switch(update: Update, context: CallbackContext):
    """切换目前操作的卡。
    注意，这不是指kp在游戏中的多张卡之间切换，如果kp要切换游戏中骰骰子的卡，请参见指令`/switchgamecard`。
    玩家只能修改目前操作的卡的基本信息，例如：年龄、性别、背景、技能点数等。
    `/switch`：生成按钮来切换卡。
    `/switch --cdid`切换至id为`cdid`的卡。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "对bot私聊来切换卡。")

    pl = dicebot.forcegetplayer(update)

    if len(pl.cards) == 0:
        return utils.errorHandler(update, "你没有任何卡。")

    if len(pl.cards) == 1:
        if pl.controlling is not None:
            return utils.errorHandler(update, "你只有一张卡，无需切换。")

        for card in pl.cards.values():
            pl.controlling = card
            break
        pl.write()

        update.message.reply_text(
            f"你只有一张卡，自动控制这张卡。现在操作的卡：{pl.controlling.getname()}")
        return True

    if len(context.args) > 0:
        if not utils.isint(context.args[0]):
            return utils.errorHandler(update, "输入无效。")
        cdid = int(context.args[0])
        if cdid < 0:
            return utils.errorHandler(update, "卡片id为正数。")
        if cdid not in pl.cards:
            return utils.errorHandler(update, "找不到这个id的卡。")

        pl.controlling = pl.cards[cdid]
        pl.write()

        update.message.reply_text(
            f"现在操作的卡：{pl.controlling.getname()}")
        return True

    # 多个选项。创建按钮
    rtbuttons = [[]]
    for card in pl.cards.values():
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])

        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
            card.getname(), callback_data=dicebot.IDENTIFIER+" switch "+str(card.id)))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("请选择要切换控制的卡：", reply_markup=rp_markup)
    # 交给按钮来完成
    return True


def switchgamecard(update: Update, context: CallbackContext):
    """用于KP切换游戏中进行对抗时使用的NPC卡片。

    （仅限私聊时）`/swtichkp --groupid`：创建按钮，让KP选择要用的卡。
    （私聊群聊皆可）`/switchgamecard --cardid`：切换到id为cardid的卡并控制。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")

    if not utils.isint(context.args[0]):
        return utils.errorHandler(update, "参数无效")

    pl = dicebot.forcegetplayer(update)
    iid = int(context.args[0])
    if iid >= 0:
        cdid = iid
        if cdid not in pl.gamecards:
            return utils.errorHandler(update, "你没有这个id的游戏中的卡")

        card = pl.gamecards[cdid]
        game: GroupGame = card.group.game if card.group.game is not None else card.group.pausedgame
        assert(game is not None)
        if game.kp != pl:
            return utils.errorHandler(update, "你不是该卡对应群的kp")
        game.kpctrl = card
        game.write()
        return True

    gpid = iid

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "请直接指定要切换的卡id，或者向bot发送私聊消息切换卡！")

    gp = dicebot.getgp(gpid)
    if gp is None:
        return utils.errorHandler(update, "找不到该群")

    game = gp.game if gp.game is not None else gp.pausedgame
    if game is None:
        return utils.errorHandler(update, "该群没有在进行游戏")
    if game.kp != pl:
        return utils.errorHandler(update, "你不是kp")

    rtbuttons = [[]]
    for card in game.cards.values():
        if card.player != pl:
            continue

        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])

        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
            card.getname(), callback_data=dicebot.IDENTIFIER+" switchgamecard "+str(card.id)))

    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("请选择要切换控制的卡：", reply_markup=rp_markup)
    # 交给按钮来完成
    return True


def showmycards(update: Update, context: CallbackContext) -> bool:
    """显示自己所持的卡。群聊时发送所有在本群可显示的卡片。私聊时发送所有卡片。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if len(pl.cards) == 0:
        return utils.errorHandler(update, "你没有任何卡。")

    if utils.isgroupmsg(update):
        # 群消息，只发送本群的卡
        gp = dicebot.forcegetgroup(update)
        rttexts: List[str] = []

        for card in pl.cards.values():
            if card.group != gp or card.type != PLTYPE:
                continue
            rttexts.append(str(card))

        if len(rttexts) == 0:
            return utils.errorHandler(update, "找不到本群的卡。")

        for x in rttexts:
            update.message.reply_text(x)
            time.sleep(0.2)
        return True

    # 私聊消息，发送全部卡
    for card in pl.cards.values():
        update.message.reply_text(str(card))
        time.sleep(0.2)
    return True


def tempcheck(update: Update, context: CallbackContext):
    """增加一个临时的检定修正。该指令只能在游戏中使用。
    `/tempcheck --tpcheck`只能用一次的检定修正。使用完后消失
    `/tempcheck --tpcheck --cardid --dicename`对某张卡，持久生效的检定修正。
    如果需要对这张卡全部检定都有修正，dicename参数请填大写单词`GLOBAL`。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        return utils.errorHandler(update, "没有参数", True)
    if not utils.isgroupmsg(update):
        return utils.errorHandler(update, "在群里设置临时检定")
    if not utils.isint(context.args[0]):
        return utils.errorHandler(update, "临时检定修正应当是整数", True)

    gp = dicebot.forcegetgroup(update)
    game = gp.game if gp.game is not None else gp.pausedgame
    if game is None:
        return utils.errorHandler(update, "没有进行中的游戏", True)
    if game.kp != dicebot.forcegetplayer(update):
        return utils.errorHandler(update, "KP才可以设置临时检定", True)

    if len(context.args) >= 3 and utils.isint(context.args[1]) and 0 <= int(context.args[1]):
        card = dicebot.getgamecard(int(context.args[1]))
        if card is None or card.group != gp:
            return utils.errorHandler(update, "找不到这张卡")

        card.tempstatus.setstatus(context.args[2], int(context.args[0]))
        card.write()
        update.message.reply_text(
            "新增了对id为"+context.args[1]+"卡的检定修正\n修正项："+context.args[2]+"，修正值："+context.args[0])
    else:
        game.tpcheck = int(context.args[0])
        update.message.reply_text("新增了仅限一次的全局检定修正："+context.args[0])
        game.write()
    return True


def roll(update: Update, context: CallbackContext):
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
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        update.message.reply_text(utils.commondice("1d100"))  # 骰1d100
        return True

    dicename = context.args[0]

    if utils.isprivatemsg(update):
        update.message.reply_text(utils.commondice(dicename))
        return True

    gp = dicebot.forcegetgroup(update)

    # 检查输入参数是不是一个基础骰子，如果是则直接计算骰子
    if gp.game is None or dicename.find('d') >= 0 or utils.isint(dicename):
        if utils.isint(dicename) and dicename > 0:
            dicename = "1d"+dicename
        rttext = utils.commondice(dicename)
        if rttext == "Invalid input.":
            return utils.errorHandler(update, "输入无效")
        update.message.reply_text(rttext)
        return True

    if gp.game is None:
        return utils.errorHandler(update, "输入无效")
    # 确认不是基础骰子的计算，转到卡检定
    # 获取临时检定
    tpcheck, gp.game.tpcheck = gp.game.tpcheck, 0
    if tpcheck != 0:
        gp.write()

    pl = dicebot.forcegetplayer(update)

    # 获取卡
    if pl != gp.kp:
        gamecard = utils.findcardfromgame(gp.game, pl)
    else:
        gamecard = gp.game.kpctrl
        if gamecard is None:
            return utils.errorHandler(update, "请用 /switchgamecard 切换kp要用的卡")
    if not gamecard:
        return utils.errorHandler(update, "找不到游戏中的卡。")
    # 找卡完成，开始检定
    test = 0

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

    elif dicename in dicebot.skilllist:
        test = dicebot.skilllist[dicename]

    elif dicename[:2] == "暗骰" and (utils.isint(dicename[2:]) or len(dicename) == 2):
        if len(dicename) != 2:
            test = int(dicename[2:])
        else:
            test = 50

    else:  # HIT BAD TRAP
        return utils.errorHandler(update, "输入无效")

    # 将所有检定修正相加
    test += gamecard.tempstatus.GLOBAL
    if gamecard.hasstatus(dicename):
        test += gamecard.getstatus(dicename)
    test += tpcheck

    testval = utils.dicemdn(1, 100)[0]
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
            return utils.errorHandler(update, "本群没有KP，请先添加一个KP再试！")

        update.message.reply_text(dicename+" 检定/出目："+str(test)+"/???")
        dicebot.sendto(gp.kp, rttext)
    else:
        update.message.reply_text(rttext)

    return True


def show(update: Update, context: CallbackContext) -> bool:
    """显示目前操作中的卡片的信息。私聊时默认显示游戏外的卡，群聊时优先显示游戏内的卡。
    （如果有多张卡，用`/switch`切换目前操作的卡。）
    `/show`：显示最基础的卡片信息；
    `/show card`：显示当前操作的整张卡片的信息；
    `/show --attrname`：显示卡片的某项具体属性。
    （回复某人消息）`/show card或--attrname`：同上，但显示的是被回复者的卡片的信息。

    例如，`/show skill`显示主要技能，
    `/show interest`显示兴趣技能。
    如果当前卡中没有这个属性，则无法显示。
    可以显示的属性例子：
    `STR`,`description`,`SAN`,`MAGIC`,`name`,`item`,`job`"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    rppl = utils.getreplyplayer(update)
    rpcard: Optional[GameCard] = None
    if rppl is not None:
        gp = dicebot.forcegetgroup(update)
        rpcard = utils.findcardfromgroup(rppl, gp)
        if rpcard is None:
            return utils.errorHandler(update, "该玩家在本群没有卡")

    card = rpcard if rpcard is not None else None
    if card is None:
        if utils.isgroupmsg(update):
            gp = dicebot.forcegetgroup(update)
            card = utils.findcardfromgroup(pl, gp)
            if card is None:
                return utils.errorHandler(update, "请先在本群创建卡")
        else:
            card = pl.controlling
            if card is None:
                return utils.errorHandler(update, "请先创建卡，或者使用 /switch 选中一张卡")

    game = card.group.game if card.group.game is not None else card.group.pausedgame

    rttext = ""

    if game is not None and utils.isgroupmsg(update):
        if card.id in game.cards:
            rttext = "显示游戏中的卡：\n"
            card = game.cards[card.id]

    if rttext == "":
        rttext = "显示游戏外的卡：\n"

    if not utils.checkaccess(pl, card) & CANREAD:
        return utils.errorHandler(update, "没有权限")

    if card.type != PLTYPE and utils.isgroupmsg(update):
        return utils.errorHandler(update, "非玩家卡片不可以在群内显示")

    if len(context.args) == 0:
        update.message.reply_text(card.basicinfo())
        return True

    if context.args[0] == "card":
        update.message.reply_text(str(card))
        return True

    ans = card.show(context.args[0])
    if ans == "找不到该属性":
        return utils.errorHandler(update, "找不到该属性")

    if ans == "":
        update.message.reply_text(rttext+"无")
    else:
        update.message.reply_text(rttext+ans)
    return True


def showkp(update: Update, context: CallbackContext) -> bool:
    """这一指令是为KP设计的。不能在群聊中使用。

    `/showkp game --groupid`: 显示发送者在某个群主持的游戏中所有的卡
    `/showkp card`: 显示发送者作为KP控制的所有卡
    `/showkp group --groupid`: 显示发送者是KP的某个群内的所有卡"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "使用该指令请发送私聊消息", True)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")

    arg = context.args[0]
    if arg == "group":
        kp = dicebot.forcegetplayer(update)
        # args[1] should be group id
        if len(context.args) < 2:
            return utils.errorHandler(update, "需要群ID")
        gpid = context.args[1]
        if not utils.isint(gpid) or int(gpid) >= 0:
            return utils.errorHandler(update, "无效ID")

        gpid = int(gpid)
        if gpid < 0 or dicebot.getgp(gpid) is None or dicebot.getgp(gpid).kp != kp:
            return utils.errorHandler(update, "这个群没有卡或没有权限")

        gp: Group = dicebot.getgp(gpid)
        ans: List[GameCard] = []
        for card in kp.cards.values():
            if card.group != gp:
                continue
            ans.append(card)

        if len(ans) == 0:
            return utils.errorHandler(update, "该群没有你的卡")

        for i in ans:
            update.message.reply_text(str(i))
            time.sleep(0.2)
        return True

    if arg == "game":
        kp = dicebot.forcegetplayer(update)

        if len(context.args) < 2:
            return utils.errorHandler(update, "需要群ID")
        gpid = context.args[1]
        if not utils.isint(gpid) or int(gpid) >= 0:
            return utils.errorHandler(update, "无效群ID")

        gp = dicebot.getgp(gpid)
        if gp is None or (gp.game is None and gp.pausedgame is None):
            return utils.errorHandler(update, "没有找到游戏")

        if gp.kp != kp:
            return utils.errorHandler(update, "你不是这个群的kp")

        game = gp.game if gp.game is not None else gp.pausedgame

        hascard = False
        for i in game.cards.values():
            if i.player != kp:
                continue
            hascard = True
            update.message.reply_text(str(i))
            time.sleep(0.2)

        return True if hascard else utils.errorHandler(update, "你没有控制的游戏中的卡")

    if arg == "card":
        kp = dicebot.forcegetplayer(update)

        hascard = False
        for card in kp.cards.values():
            if card.group.kp != kp:
                continue
            hascard = True
            update.message.reply_text(str(card))
            time.sleep(0.2)

        return True if hascard else utils.errorHandler(update, "你没有控制NPC卡片")

    return utils.errorHandler(update, "无法识别的参数")


def showcard(update: Update, context: CallbackContext) -> bool:
    """显示某张卡的信息。

    `/showcard --cardid (card/--attrname)`: 显示卡id为`cardid`的卡片的信息。
    如果第二个参数是`card`，显示整张卡；否则，显示这一项数据。
    如果第二个参数不存在，显示卡片基本信息。
    群聊时使用该指令，优先查看游戏内的卡片。

    显示前会检查发送者是否有权限显示这张卡。在这些情况下，无法显示卡：

    群聊环境：显示非本群的卡片，或者显示本群的type不为PL的卡片；

    私聊环境：显示没有查看权限的卡片。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")
    if not utils.isint(context.args[0]) or int(context.args[0]) < 0:
        return utils.errorHandler(update, "卡id参数无效", True)
    cdid = int(context.args[0])

    rttext: str = ""
    cardi: Optional[GameCard] = None

    if utils.isgroupmsg(update):
        cardi = dicebot.getgamecard(cdid)
        if cardi is not None:
            rttext = "显示游戏内的卡片\n"

    if cardi is None:
        cardi = dicebot.getcard(cdid)

        if cardi is None:
            return utils.errorHandler(update, "找不到这张卡")

    if rttext == "":
        rttext = "显示游戏内的卡片\n"

    # 检查是否有权限
    if utils.isprivatemsg(update):

        pl = dicebot.forcegetplayer(update)

        if utils.checkaccess(pl, cardi) & CANREAD == 0:
            return utils.errorHandler(update, "没有权限")
    else:
        if cardi.group != dicebot.forcegetgroup(update) or cardi.type != PLTYPE:
            return utils.errorHandler(update, "没有权限", True)

    # 开始处理
    if len(context.args) >= 2:
        if context.args[1] == "card":
            update.message.reply_text(rttext+str(cardi))
        else:
            ans = cardi.show(context.args[1])
            if ans == "找不到该属性":
                return utils.errorHandler(update, ans)

            update.message.reply_text(rttext+ans)
        return True

    # 显示基本属性
    update.message.reply_text(rttext+cardi.basicinfo())
    return True


# (private)
# (private)showids game: return all card ids in a game
# (private)showids kp: return all card ids kp controlling


def showids(update: Update, context: CallbackContext) -> bool:
    """用于显示卡的名字-id对。群聊时使用只能显示游戏中PL的卡片id。

    `showids`: 显示游戏外的卡id。

    `showids game`: 显示游戏中的卡id。

    私聊时，只有KP可以使用该指令，显示的是该玩家作为KP的所有群的id对，按群分开。
    两个指令同上，但结果将更详细，结果会包括KP主持游戏的所有群的卡片。
    KP使用时有额外的一个功能：

    `showids kp`: 返回KP游戏中控制的所有卡片id"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        gp = dicebot.forcegetgroup(update)

        out = bool(len(context.args) == 0) or bool(context.args[0] != "game")

        if not out and gp.game is None and gp.pausedgame is None:
            return utils.errorHandler(update, "没有进行中的游戏")

        hascard = False
        if out:
            cdd = gp.cards
        else:
            game = gp.game if gp.game is not None else gp.pausedgame
            cdd = game.cards

        rttext = "卡id：卡名\n"
        for card in cdd.values():
            if card.type != PLTYPE:
                continue
            hascard = True
            rttext += str(card.id)+"："+card.getname()+"\n"

        if not hascard:
            return utils.errorHandler(update, "本群没有卡")

        update.message.reply_text(rttext)
        return True

    # 下面处理私聊消息
    kp = dicebot.forcegetplayer(update)
    if not utils.searchifkp(kp):
        return utils.errorHandler(update, "没有权限")

    searchtype = 0
    if len(context.args) > 0:
        if context.args[0] == "game":
            searchtype = 1
        elif context.args[0] == "kp":
            searchtype = 2
    allempty = True
    for gp in kp.kpgroups.values():
        game = gp.game if gp.game is not None else gp.pausedgame
        if game is None and searchtype > 0:
            continue

        if searchtype > 0:
            cdd = game.cards
        else:
            cdd = gp.cards

        hascard = False
        rttext = "群id："+str(gp.id)+"，群名："+gp.getname()+"，id信息如下\n"
        rttext += "卡id：卡名\n"
        for card in cdd.values():
            if searchtype == 2 and card.player != kp:
                continue
            allempty = False
            hascard = True
            rttext += str(card.id)+"："+card.getname()+"\n"

        if not hascard:
            continue

        update.message.reply_text(rttext)
        time.sleep(0.2)

    if allempty:
        return utils.errorHandler(update, "没有可显示的卡。")

    return True


def modify(update: Update, context: CallbackContext) -> bool:
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
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if not utils.searchifkp(pl) and pl.id != ADMIN_ID:
        return utils.errorHandler(update, "没有权限", True)

    # need 3 args, first: card id, second: attrname, third: value
    if len(context.args) < 3:
        return utils.errorHandler(update, "需要至少3个参数", True)

    card_id = context.args[0]
    if not utils.isint(card_id) or int(card_id) < 0:
        return utils.errorHandler(update, "无效ID", True)

    card_id = int(card_id)
    if len(context.args) > 3 and context.args[3] == "game":
        card = dicebot.getgamecard(card_id)
        rttext = "修改了游戏内的卡片：\n"
    else:
        card = dicebot.getcard(card_id)
        rttext = "修改了游戏外的卡片：\n"

    if card is None:
        return utils.errorHandler(update, "找不到这张卡")

    if not utils.checkaccess(pl, card) & CANMODIFY:
        return utils.errorHandler(update, "没有权限", True)
    try:
        ans, ok = card.modify(context.args[1], context.args[2])
    except TypeError as e:
        return utils.errorHandler(update, str(e))

    if not ok:
        return utils.errorHandler(update, "修改失败。"+ans)

    rttext += context.args[1]+"从"+ans+"变为"+context.args[2]
    update.message.reply_text(rttext)
    return True


def changeid(update: Update, context: CallbackContext) -> bool:
    """修改卡片id。卡片的所有者或者KP均有使用该指令的权限。

    指令格式：
    `/changeid --cardid --newid`

    如果`newid`已经被占用，则指令无效。
    这一行为将同时改变游戏内以及游戏外的卡id。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) < 2:
        return utils.errorHandler(update, "至少需要两个参数。")

    if not utils.isint(context.args[0]) or not utils.isint(context.args[1]):
        return utils.errorHandler(update, "参数无效", True)

    oldid = int(context.args[0])
    newid = int(context.args[1])

    if newid < 0:
        return utils.errorHandler(update, "卡id不能为负数", True)
    if newid == oldid:
        return utils.errorHandler(update, "前后id相同", True)
    if newid in dicebot.allids:
        return utils.errorHandler(update, "该ID已经被占用")

    card = dicebot.getcard(oldid)
    if card is None:
        return utils.errorHandler(update, "找不到该ID对应的卡")

    pl = dicebot.forcegetplayer(update)
    if not utils.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
        return utils.errorHandler(update, "没有权限")

    gamecard = dicebot.getgamecard(oldid)
    if gamecard is not None:
        gamecard = dicebot.popgamecard(oldid)
        gamecard.id = newid
        dicebot.addgamecard(gamecard)

    card = dicebot.popcard(oldid)
    card.id = newid
    dicebot.addcard(card)
    rttext = "修改卡片的id：从"+str(oldid)+"修改为"+str(newid)
    if gamecard is not None:
        rttext += "\n游戏内卡片id同步修改完成。"

    update.message.reply_text(rttext)
    return True


def cardtransfer(update: Update, context: CallbackContext) -> bool:
    """转移卡片所有者。格式为
    `/cardtransfer --cardid --playerid`：将卡转移给playerid。
    回复某人`/cardtransfer --cardid`：将卡转移给被回复的人。
    只有卡片拥有者或者KP有权使用该指令。
    如果对方不是KP且对方已经在本群有卡，则无法转移。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)
    if len(context.args) == 1 and utils.getreplyplayer(update) is None:
        return utils.errorHandler(update, "参数不足", True)
    if not utils.isint(context.args[0]) or (len(context.args) > 1 and not utils.isint(context.args[1])):
        return utils.errorHandler(update, "参数无效", True)
    if int(context.args[0]) < 0 or (len(context.args) > 1 and int(context.args[1]) < 0):
        return utils.errorHandler(update, "负数参数无效", True)

    cdid = int(context.args[0])
    card = dicebot.getcard(cdid)
    if card is None:
        return utils.errorHandler(update, "找不到这张卡")

    opl = dicebot.forcegetplayer(update)
    if len(context.args) == 1:
        tpl: Player = utils.getreplyplayer(update)
    else:
        tpl = dicebot.forcegetplayer(int(context.args[1]))

    if not utils.checkaccess(opl, card) & (OWNCARD | CANMODIFY):
        return utils.errorHandler(update, "没有权限", True)

    if tpl != card.group.kp:
        for c in tpl.cards.values():
            if c.group == card.group:
                return utils.errorHandler(update, "目标玩家已经在对应群有一张卡了")

    # 开始处理
    gamecard = dicebot.getgamecard(cdid)
    if gamecard is not None:
        gamecard = dicebot.popgamecard(cdid)
        gamecard.playerid = tpl.id
        dicebot.addgamecard(gamecard)

    card = dicebot.popcard(cdid)
    card.playerid = tpl.id
    dicebot.addcard(card)

    rttext = "卡id"+str(cdid)+"拥有者从"+str(opl.id)+"修改为"+str(tpl.id)+"。"
    if gamecard is not None:
        rttext += "游戏内数据也被同步修改了。"

    update.message.reply_text(rttext)
    return True


def changegroup(update: Update, context: CallbackContext) -> bool:
    """修改卡片的所属群。
    一般只用于卡片创建时输入了错误的群id。
    比较特殊的情形：
    如果需要将某个群的所有卡片全部转移到另一个群，
    第一个参数写为负数的`groupid`即可。这一操作需要原群的kp权限。
    在原群进行游戏时，这个指令无效。

    指令格式：
    `/changegroup --groupid/--cardid --newgroupid`
    """
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if len(context.args) < 2:
        return utils.errorHandler(update, "至少需要2个参数", True)
    if not utils.isint(context.args[0]) or not utils.isint(context.args[1]):
        return utils.errorHandler(update, "参数无效", True)

    newgpid = int(context.args[1])
    if newgpid >= 0:
        return utils.errorHandler(update, "转移的目标群id应该是负数", True)

    if int(context.args[0]) < 0:  # 转移全部群卡片
        ogpid = int(context.args[0])

        oldgp = dicebot.getgp(ogpid)
        if oldgp is None or len(oldgp.cards) == 0:
            return utils.errorHandler(update, "该群没有卡")

        newgp = dicebot.forcegetgroup(newgpid)
        kp = dicebot.forcegetgroup(update)
        if (kp != oldgp.kp or kp != newgp.kp) and kp.id != ADMIN_ID:
            return utils.errorHandler(update, "没有权限", True)

        if oldgp.getexistgame() is not None:
            return utils.errorHandler(update, "游戏进行中，无法转移")

        # 检查权限通过
        numofcards = len(oldgp.cards)
        utils.changecardgpid(ogpid, newgpid)
        update.message.reply_text(
            "操作成功，已经将"+str(numofcards)+"张卡片从群："+str(ogpid)+"移动到群："+str(newgpid))
        return True

    # 转移一张卡片
    cdid = int(context.args[0])
    card = dicebot.getcard(cdid)
    if card is None:
        return utils.errorHandler(update, "找不到这个id的卡片", True)

    oldgp = card.group
    if oldgp.getexistgame():
        return utils.errorHandler(update, "游戏正在进行，无法转移")

    pl = dicebot.forcegetplayer(update)
    if not utils.checkaccess(pl, card) & (OWNCARD | CANMODIFY):
        return utils.errorHandler(update, "没有权限")

    # 开始执行
    card = dicebot.popcard(cdid)
    utils.cardadd(card, newgpid)
    cardname = card.getname()
    update.message.reply_text(
        "操作成功，已经将卡片"+cardname+"从群："+str(oldgp.id)+"移动到群："+str(newgpid))
    return True


def copygroup(update: Update, context: CallbackContext) -> bool:
    """复制一个群的所有数据到另一个群。
    新的卡片id将自动从小到大生成。

    格式：
    `/copygroup --oldgroupid --newgroupid (kp)`
    将`oldgroupid`群中数据复制到`newgroupid`群中。
    如果有第三个参数kp，则仅复制kp的卡片。

    使用者需要同时是两个群的kp。
    任何一个群在进行游戏的时候，该指令都无法使用。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    try:
        oldgpid, newgpid = int(context.args[0]), int(context.args[1])
    except (IndexError, ValueError):
        return utils.errorHandler(update, "输入无效", True)

    ogp = dicebot.getgp(oldgpid)
    if ogp is None or len(ogp.cards) == 0:
        return utils.errorHandler(update, "该群没有卡", True)

    kp = dicebot.forcegetplayer(update)
    ngp = dicebot.getgp(newgpid)
    if ngp is None or kp != ogp.kp or ngp.kp != kp:
        return utils.errorHandler(update, "没有权限", True)

    copyall = True
    if len(context.args) >= 3 and context.args[2] == "kp":
        copyall = False

    if not utils.groupcopy(oldgpid, newgpid, copyall):
        return utils.errorHandler(update, "无法复制")

    update.message.reply_text("复制成功")
    return True


def randombkg(update: Update, context: CallbackContext) -> bool:
    """生成随机的背景故事。

    获得当前发送者选中的卡，生成随机的背景故事并写入。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    card = pl.controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。")

    update.message.reply_text(card.background.randbackground())
    return True


def setsex(update: Update, context: CallbackContext) -> bool:
    """设置性别。比较明显的性别词汇会被自动分类为男性或女性，其他的性别也可以设置。
    `/setsex 性别`：直接设置。
    `/setsex`：使用交互式的方法设置性别。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if pl.controlling is None:
        return utils.errorHandler(update, "找不到卡。", True)
    if len(context.args) == 0:
        if utils.isgroupmsg(update):
            gpid = utils.getchatid(update)
            utils.addOP(gpid, "setsex "+str(pl.id))
            update.message.reply_text("请输入性别：")
            return True

        rtbuttons = [[InlineKeyboardButton("男性", callback_data=dicebot.IDENTIFIER+" setsex male"), InlineKeyboardButton(
            "女性", callback_data=dicebot.IDENTIFIER+" setsex female"), InlineKeyboardButton("其他", callback_data=dicebot.IDENTIFIER+" setsex other")]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("请选择性别：", reply_markup=rp_markup)
        return True

    card = pl.controlling
    utils.cardsetsex(update, card, context.args[0])
    return True

# setbkg --bkgroundname --bkgroundinfo...: Need at least 2 args


def setbkg(update: Update, context: CallbackContext) -> bool:
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
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    pl = dicebot.forcegetplayer(update)
    if len(context.args) <= 1:
        return utils.errorHandler(update, "参数不足", True)

    card = pl.controlling
    if card is None:
        return utils.errorHandler(update, "找不到卡。", True)

    if context.args[0] not in card.background.__dict__ or not isinstance(card.background.__dict__[context.args[0]], str):
        rttext = "找不到这项背景属性，背景属性只支持以下参数：\n"
        for keys in card.background.__dict__:
            if not isinstance(card.background.__dict__[keys], str):
                continue
            rttext += keys+"\n"
        return utils.errorHandler(update, rttext)

    card.background.__dict__[context.args[0]] = ' '.join(context.args[1:])
    card.write()
    update.message.reply_text("背景故事添加成功")
    return True


def sancheck(update: Update, context: CallbackContext) -> bool:
    """进行一次sancheck，格式如下：
    `/sancheck checkpass/checkfail`"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "在游戏中才能进行sancheck。")

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)

    checkname = context.args[0]
    if checkname.find("/") == -1:
        return utils.errorHandler(update, "将成功和失败的扣除点数用/分开。")

    checkpass, checkfail = checkname.split(sep='/', maxsplit=1)
    if not utils.isadicename(checkpass) or not utils.isadicename(checkfail):
        return utils.errorHandler(update, "无效输入")

    gp = dicebot.forcegetgroup(update)

    if gp.game is None:
        return utils.errorHandler(update, "找不到游戏", True)

    pl = dicebot.forcegetplayer(update)
    # KP 进行
    if pl == gp.kp:
        card1 = gp.game.kpctrl
        if card1 is None:
            return utils.errorHandler(update, "请先用 /switchgamecard 切换到你的卡")
    else:  # 玩家进行
        card1 = utils.findcardfromgame(gp.game, pl)
        if card1 is None:
            return utils.errorHandler(update, "找不到卡。")

    rttext = "检定：理智 "
    sanity = card1.attr.SAN
    check = utils.dicemdn(1, 100)[0]
    rttext += str(check)+"/"+str(sanity)+" "
    greatfailrule = gp.rule.greatfail
    if (sanity < 50 and check >= greatfailrule[2] and check <= greatfailrule[3]) or (sanity >= 50 and check >= greatfailrule[0] and check <= greatfailrule[1]):  # 大失败
        rttext += "大失败"
        anstype = "大失败"
    elif check > sanity:  # check fail
        rttext += "失败"
        anstype = "失败"
    else:
        anstype = ""

    rttext += "\n损失理智："
    sanloss, m, n = 0, 0, 0

    if anstype == "大失败":
        if utils.isint(checkfail):
            sanloss = int(checkfail)
        else:
            t = checkfail.split("+")
            for tt in t:
                if utils.isint(tt):
                    sanloss += int(tt)
                else:
                    ttt = tt.split('d')
                    sanloss += int(ttt[0])*int(ttt[1])

    elif anstype == "失败":
        if utils.isint(checkfail):
            sanloss = int(checkfail)
        else:
            m, n = checkfail.split("d", maxsplit=1)
            m, n = int(m), int(n)
            sanloss = int(sum(utils.dicemdn(m, n)))

    else:
        if utils.isint(checkpass):
            sanloss = int(checkpass)
        else:
            m, n = checkpass.split("d", maxsplit=1)
            m, n = int(m), int(n)
            sanloss = int(sum(utils.dicemdn(m, n)))

    card1.attr.SAN -= sanloss
    rttext += str(sanloss)+"\n"
    if card1.attr.SAN <= 0:
        card1.attr.SAN = 0
        card1.status = "mad"
        rttext += "陷入永久疯狂，快乐撕卡~\n"

    elif sanloss > (card1.attr.SAN+sanloss)//5:
        rttext += "一次损失五分之一以上理智，进入不定性疯狂状态。\n"
    elif sanloss >= 5:
        rttext += "一次损失5点或以上理智，可能需要进行智力（灵感）检定。\n"

    card1.write()
    return True


def lp(update: Update, context: CallbackContext) -> bool:
    """修改LP。KP通过回复某位PL消息并在回复消息中使用本指令即可修改对方卡片的LP。
    回复自己的消息，则修改选中的游戏卡。
    使用范例：
    `/lp +3`恢复3点LP。
    `/lp -2`扣除2点LP。
    `/lp 10`将LP设置为10。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "游戏中才可以修改lp。")
    gp = dicebot.forcegetgroup(update)
    kp = dicebot.forcegetplayer(update)
    if gp.kp != kp:
        return utils.errorHandler(update, "没有权限", True)

    if len(context.args) == 0:
        return utils.errorHandler(update, "需要指定扣除的生命值", True)

    clp: str = context.args[0]
    game = gp.game
    if game is None:
        return utils.errorHandler(update, "找不到进行中的游戏", True)

    rppl = utils.getreplyplayer(update)
    if rppl is None:
        return utils.errorHandler(update, "请用回复的方式来选择玩家改变lp")

    if rppl != kp:
        cardi = utils.findcardfromgame(game, rppl)
    else:
        cardi = game.kpctrl

    if cardi is None:
        return utils.errorHandler(update, "找不到这名玩家的卡。")

    if clp[0] == "+" or clp[0] == "-":
        if not utils.isint(clp[1:]):
            return utils.errorHandler(update, "参数无效", True)
    elif not utils.isint(clp):
        return utils.errorHandler(update, "参数无效", True)

    originlp = cardi.attr.LP
    if clp[0] == "+":
        cardi.attr.LP += int(clp[1:])
    elif clp[0] == "-":
        cardi.attr.LP -= int(clp[1:])
    else:
        cardi.attr.LP = int(clp)

    if cardi.attr.LP <= 0:
        cardi.attr.LP = 0
        update.message.reply_to_message.reply_text("生命值归0，进入濒死状态")

    update.message.reply_text("生命值从"+str(originlp)+"修改为"+str(cardi.attr.LP))
    return True


def addcard(update: Update, context: CallbackContext) -> bool:
    """使用已有信息添加一张卡片，模板使用的是NPC/怪物模板。指令格式如下：

    `/addcard --attr_1 --val_1 --attr_2 --val_2 …… --attr_n -- val_n`，
    其中`attr`是卡的直接属性，或卡的某个属性（字典）中的键。不可以直接添加tempstatus这个属性。
    `name`和背景信息不支持空格，如果要设置这一项信息，需要之后用别的指令来修改。

    卡的属性只有三种类型的值：`int`, `str`, `bool`，函数会自动判断对应的属性是什么类型，
    其中`bool`类型`attr`对应的`val`只能是`true`, `True`, `false`, `False`之一。

    如果遇到无法识别的属性，将无法创建卡片。
    参数中，必须的`attr`之一为`groupid`，如果找不到`groupid`将无法添加卡片。
    `playerid`会自动识别为发送者，无需填写`playerid`。
    指令使用者是KP的情况下，才可以指定`playerid`这个属性，否则卡片无效。
    给定`id`属性的话，在指定的卡id已经被占用的时候，会重新自动选取。"""
    if utils.ischannel(update):
        return False
    utils.chatinit(update)

    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "向我发送私聊消息来添加卡", True)
    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")
    if (len(context.args)//2)*2 != len(context.args):
        update.message.reply_text("参数长度应该是偶数")

    t = utils.templateNewCard()
    # 遍历args获取attr和val
    for i in range(0, len(context.args), 2):
        argname: str = context.args[i]
        argval = context.args[i+1]
        dt = utils.findattrindict(t, argname)
        if not dt:  # 可能是技能，否则返回
            if argname in dicebot.skilllist or argname == "母语" or argname == "闪避":
                dt = t["skill"]
                dt[argname] = 0  # 这一行是为了防止之后判断类型报错
            else:
                return utils.errorHandler(update, "属性 "+argname+" 在角色卡模板中没有找到")

        if isinstance(dt[argname], dict):
            return utils.errorHandler(update, argname+"是dict类型，不可直接赋值")

        if isinstance(dt[argname], bool):
            if argval == "false" or argval == "False":
                argval = False
            elif argval == "true" or argval == "True":
                argval = True
            if not isinstance(argval, bool):
                return utils.errorHandler(update, argname+"应该为bool类型")
            dt[argname] = argval

        elif isinstance(dt[argname], int):
            if not utils.isint(argval):
                return utils.errorHandler(update, argname+"应该为int类型")
            dt[argname] = int(argval)

        else:
            dt[argname] = argval
    # 参数写入完成
    # 检查groupid是否输入了
    if t["groupid"] == 0:
        return utils.errorHandler(update, "需要groupid！")

    # 检查是否输入了以及是否有权限输入playerid
    pl = dicebot.forcegetplayer(update)
    if not utils.searchifkp(pl):
        if t["playerid"] != 0 and t["playerid"] != pl.id:
            return utils.errorHandler(update, "没有权限设置非自己的playerid")
        t["playerid"] = utils.getchatid(update)
    else:
        if t["groupid"] not in pl.kpgroups and t["playerid"] != 0 and t["playerid"] != pl.id:
            return utils.errorHandler(update, "没有权限设置非自己的playerid")
        if t["playerid"] == 0:
            t["playerid"] = pl.id

    # 生成成功
    card1 = utils.GameCard(t)
    # 添加id

    if "id" not in context.args or card1.id < 0 or card1.id in dicebot.allids:
        update.message.reply_text("输入了已被占用的id，或id未设置，或id无效。自动获取id")
        card1.id = utils.getoneid()
    # 生成衍生数值
    card1.generateOtherAttributes()
    # 卡检查
    rttext = card1.check()
    if rttext != "":
        update.message.reply_text(
            "卡片添加成功，但没有通过开始游戏的检查。")
        update.message.reply_text(rttext)
    else:
        update.message.reply_text("卡片添加成功")

    return True if dicebot.addcard(card1) else utils.errorHandler(update, "卡id重复")


def textHandler(update: Update, context: CallbackContext) -> bool:
    """信息处理函数，用于无指令的消息处理。
    具体指令处理正常完成时再删除掉当前操作状态`OPERATION[chatid]`，处理出错时不删除。"""
    if update.message is None:
        return True

    if update.message.migrate_from_chat_id is not None:
        # 触发migrate
        oldid = update.message.migrate_from_chat_id
        if dicebot.migrateto is not None:
            newid = dicebot.migrateto
            dicebot.migrateto = None
            dicebot.groupmigrate(oldid, newid)
            dicebot.sendtoAdmin(f"群{str(oldid)}迁移了，新的id：{str(newid)}")
            dicebot.sendto(newid, "本群迁移了，原id"+str(oldid)+"新的id"+str(newid))
            return True

        # 等待获取migrateto
        dicebot.migratefrom = oldid
        return True

    if update.message.migrate_to_chat_id is not None:
        # 触发migrate
        newid = update.message.migrate_to_chat_id
        if dicebot.migratefrom is not None:
            oldid = dicebot.migratefrom
            dicebot.migratefrom = None
            dicebot.groupmigrate(oldid, newid)
            dicebot.sendtoAdmin(f"群{str(oldid)}迁移了，新的id：{str(newid)}")
            dicebot.sendto(newid, "本群迁移了，原id"+str(oldid)+"新的id"+str(newid))
            return True

        # 等待获取migratefrom
        dicebot.migrateto = newid
        return True

    if update.message.text == "cancel":
        utils.popOP(utils.getchatid(update))
        return True

    oper = utils.getOP(utils.getchatid(update))
    opers = oper.split(" ")
    if oper == "":
        utils.botchat(update)
        return True
    if opers[0] == "newcard":
        return utils.textnewcard(update, int(opers[2])) if len(opers) > 2 else utils.textnewcard(update)
    if oper == "setage":
        return utils.textsetage(update)
    if oper == "setname":  # 私聊情形
        return utils.textsetname(update, 0)
    if opers[0] == "setname":  # 群消息情形
        return utils.textsetname(update, int(opers[1]))
    if oper == "setsex":  # 私聊情形
        return utils.textsetsex(update, 0)
    if opers[0] == "setsex":  # 群消息情形
        return utils.textsetsex(update, int(opers[1]))
    if opers[0] == "delcard":
        return utils.textdelcard(update, int(opers[1]))
    if opers[0] == "passjob":
        return utils.textpassjob(update)
    if opers[0] == "passskill":
        return utils.textpassskill(update)

    return False


def unknown(update: Update, context: CallbackContext) -> None:
    utils.errorHandler(update, "没有这一指令", True)


def helper(update: Update, context: CallbackContext) -> True:
    """查看指令对应函数的说明文档。

    `/help --command`查看指令对应的文档。
    `/help`查看所有的指令。"""
    allfuncs = dicebot.readhandlers()

    if len(context.args) == 0:
        rttext = "单击下面的命令来复制想要查询的指令：\n"
        for funcname in allfuncs:
            if funcname == "helper":
                funcname = "help"
            rttext += "`/help "+funcname+"`\n"
        update.message.reply_text(rttext, parse_mode="MarkdownV2")
        return True

    glb = globals()

    funcname = context.args[0]
    if funcname == "help":
        funcname = "helper"

    if funcname in allfuncs and glb[funcname].__doc__:
        rttext: str = glb[funcname].__doc__
        ind = rttext.find("    ")
        while ind != -1:
            rttext = rttext[:ind]+rttext[ind+4:]
            ind = rttext.find("    ")
        try:
            update.message.reply_text(rttext, parse_mode="MarkdownV2")
        except:
            update.message.reply_text("Markdown格式parse错误，请联系作者检查并改写文档")
            return False
        return True

    return utils.errorHandler(update, "找不到这个指令，或这个指令没有帮助信息。")


ALL_HANDLER = globals()
