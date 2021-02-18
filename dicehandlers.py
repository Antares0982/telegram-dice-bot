# -*- coding:utf-8 -*-

import time
from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

import utils


def start(update: Update, context: CallbackContext) -> None:
    """显示bot的帮助信息，群聊时不显示"""
    if utils.isprivatemsg(update):  # private message
        update.message.reply_text(utils.HELP_TEXT)
    else:
        update.message.reply_text("Dice bot已启用！")


def addkp(update: Update, context: CallbackContext) -> bool:
    """添加KP。在群里发送`/addkp`将自己设置为KP。
    如果这个群已经有一名群成员是KP，则该指令无效。
    若原KP不在群里，该指令可以替换KP。

    如果原KP在群里，需要先发送`/delkp`来撤销自己的KP，或者管理员用`/transferkp`来强制转移KP权限。"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, '发送群消息添加KP')
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    utils.initrules(gpid)
    # 判断是否已经有KP
    if gpid in utils.GROUP_KP_DICT:
        # 已有KP
        if not utils.isingroup(update, utils.getkpid(gpid)):
            if not utils.changeKP(gpid, kpid):  # 更新NPC卡拥有者
                # 不应触发
                return utils.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")
            return True
        if utils.getkpid(gpid) == kpid:
            return utils.errorHandler(update, "你已经是KP了", True)
        return utils.errorHandler(update, '这个群已经有一位KP了，请先让TA发送 /delkp 撤销自己的KP。如果需要强制更换KP，请管理员用\'/transferkp kpid\'添加本群成员为KP，或者 /transferkp 将自己设为KP。')
    # 该群没有KP，可以直接添加KP
    # delkp指令会将KP的卡playerid全部改为0，检查如果有id为0的卡，id设为新kp的id
    utils.changeplids(gpid, 0, kpid)
    game, ok = utils.findgame(gpid)
    if ok:
        game.kpid = kpid
        for cardi in game.kpcards:
            cardi.playerid = kpid
        utils.writegameinfo(utils.ON_GAME)
    update.message.reply_text(
        "绑定群(id): " + str(gpid) + "与KP(id): " + str(kpid))
    utils.GROUP_KP_DICT[gpid] = kpid  # 更新KP表
    utils.writekpinfo(utils.GROUP_KP_DICT)
    return True


def transferkp(update: Update, context: CallbackContext) -> bool:
    """转移KP权限，只有群管理员可以使用这个指令。
    当前群没有KP时或当前群KP为管理员时，无法使用。

    `/transferkp`：将当前群KP权限转移到自身。

    `/transferkp --kpid`：将当前群KP权限转移到某个群成员。
    如果指定的`kpid`不在群内则无法设定。"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "发送群消息强制转移KP权限")
    if not utils.isadmin(update, update.message.from_user.id):
        return utils.errorHandler(update, "没有权限", True)
    gpid = update.effective_chat.id
    if utils.getkpid(gpid) == -1:
        return utils.errorHandler(update, "没有KP", True)
    if utils.isadmin(update, utils.getkpid(gpid)):
        return utils.errorHandler(update, "KP是管理员，无法转移")
    newkpid: int
    if len(context.args) != 0:
        if not utils.isint(context.args[0]):
            return utils.errorHandler(update, "参数需要是整数", True)
        newkpid = int(context.args[0])
    else:
        newkpid = update.message.from_user.id
    if newkpid == utils.getkpid(gpid):
        return utils.errorHandler(update, "原KP和新KP相同", True)
    if not utils.changeKP(gpid, newkpid):
        return utils.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发
    return True


def delkp(update: Update, context: CallbackContext) -> bool:
    """撤销自己的KP权限。只有当前群内KP可以使用该指令。
    在撤销KP之后的新KP会自动获取原KP的所有NPC的卡片"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, '发群消息撤销自己的KP权限')
    gpid = update.effective_chat.id
    if utils.getkpid(gpid) == -1:
        return utils.errorHandler(update, '本群没有KP', True)
    if update.message.from_user.id != utils.getkpid(gpid):
        return utils.errorHandler(update, '你不是KP', True)
    if not utils.changeKP(gpid):
        return utils.errorHandler(update, "程序错误：不符合添加KP要求，请检查代码")  # 不应触发
    update.message.reply_text('KP已撤销')
    return True


def reload(update: Update, context: CallbackContext) -> bool:
    """重新读取所有文件，只有bot管理者可以使用"""
    if update.message.from_user.id != utils.ADMIN_ID:
        return utils.errorHandler(update, "没有权限", True)
    try:
        utils.GROUP_KP_DICT, utils.CARDS_DICT, utils.ON_GAME = utils.readinfo()
        utils.CURRENT_CARD_DICT = utils.readcurrentcarddict()
        utils.GROUP_RULES = utils.readrules()
    except:
        return utils.errorHandler(update, "读取文件出现问题，请检查json文件！")
    update.message.reply_text('成功重新读取文件。')
    return True


def showuserlist(update: Update, context: CallbackContext) -> bool:
    """显示所有信息。非KP无法使用这一指令。
    群聊时不可以使用该指令。

    Bot管理者使用该指令，bot将逐条显示群-KP信息、
    全部的卡信息、游戏信息。KP使用时，只会显示与TA相关的这些消息。"""
    if utils.isgroupmsg(update):  # Group msg: do nothing, even sender is USER or KP
        return utils.errorHandler(update, "没有这一指令", True)
    if update.effective_chat.id == utils.ADMIN_ID:  # 全部显示
        rttext = "GROUP_KP_LIST:\n"
        if not utils.GROUP_KP_DICT:
            rttext += "None"
        else:
            for keys in utils.GROUP_KP_DICT:
                rttext += str(keys) + ": "+str(utils.GROUP_KP_DICT[keys])+"\n"
        update.message.reply_text(rttext)
        if not utils.CARDS_DICT:
            update.message.reply_text("CARDS: None")
        else:
            update.message.reply_text("CARDS:")
            for gpids in utils.CARDS_DICT:
                time.sleep(0.5)
                update.message.reply_text("group:"+str(gpids))
                for cdids in utils.CARDS_DICT[gpids]:
                    update.message.reply_text(
                        str(utils.CARDS_DICT[gpids][cdids]))
                    time.sleep(0.5)
        time.sleep(0.5)
        rttext = "Game Info:\n"
        if not utils.ON_GAME:
            rttext += "None"
        else:
            for i in range(len(utils.ON_GAME)):
                rttext += str(utils.ON_GAME[i].groupid) + \
                    ": " + str(utils.ON_GAME[i].kpid)+"\n"
        update.message.reply_text(rttext)
        return True
    if utils.isfromkp(update):  # private msg
        kpid = update.effective_chat.id
        gpids = utils.findkpgroups(kpid)
        if len(utils.CARDS_DICT) == 0:
            return utils.errorHandler(update, "没有角色卡")
        for gpid in gpids:
            if gpid not in utils.CARDS_DICT:
                update.message.reply_text("群: "+str(gpid)+" 没有角色卡")
            else:
                update.message.reply_text("群: "+str(gpid)+" 角色卡:")
                for cdid in utils.CARDS_DICT[gpid]:
                    update.message.reply_text(
                        str(utils.CARDS_DICT[gpid][cdid]))
        for i in range(len(utils.ON_GAME)):
            if utils.ON_GAME[i].kpid == kpid:
                update.message.reply_text(
                    "群："+str(utils.ON_GAME[i].groupid)+"正在游戏中")
        return True
    return utils.errorHandler(update, "没有这一指令", True)


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
    delnum = 1
    chatid = update.effective_chat.id
    if utils.isgroupmsg(update) and not utils.isadmin(update, utils.BOT_ID):
        return utils.errorHandler(update, "Bot没有管理权限")
    senderid = update.message.from_user.id
    if utils.isgroupmsg(update) and not utils.isfromkp(update) and not utils.isadmin(update, senderid):
        return utils.errorHandler(update, "没有权限", True)
    if len(context.args) >= 1 and utils.isint(context.args[0]):
        delnum = int(context.args[0])
        if delnum <= 0:
            return utils.errorHandler(update, "参数错误", True)
        if delnum > 10:
            return utils.errorHandler(update, "一次最多删除10条消息")
    lastmsgid = update.message.message_id
    while delnum >= 0:
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
    """获取所在聊天环境的id。私聊使用该指令发送用户id，群聊使用该指令则发送群id"""
    chatid = utils.getchatid(update)
    update.message.reply_text("<code>"+str(chatid) +
                              "</code> \n点击即可复制", parse_mode='HTML')


def showrule(update: Update, context: CallbackContext) -> bool:
    """显示当前群内的规则。"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "请在群内查看规则")
    gpid = utils.getchatid(update)
    if gpid not in utils.GROUP_RULES:
        utils.initrules(gpid)
    rule = utils.GROUP_RULES[gpid]
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
    例如：`r=[1,80,2,100]`，则从10点升至90点需要花费`1*70+2*10=90`点数。

    greatsuccess：大成功范围。接收长度为4的数组，记为r。
    `r[0]-r[1]`为检定大于等于50时大成功范围，否则是`r[2]-r[3]`。

    greatfail：大失败范围。同上。"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "请在群内用该指令设置规则")
    gpid = update.effective_chat.id
    utils.initrules(gpid)
    if not utils.isfromkp(update):
        return utils.errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数", True)
    if utils.isint(context.args[0]):
        return utils.errorHandler(update, "参数无效", True)
    gprule = utils.GROUP_RULES[gpid]
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
    utils.writerules(utils.GROUP_RULES)
    if not ok:
        return utils.errorHandler(update, msg)
    update.message.reply_text(msg)
    return True


def createcardhelp(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(utils.CREATE_CARD_HELP, parse_mode="MarkdownV2")


def newcard(update: Update, context: CallbackContext) -> bool:
    """随机生成一张新的角色卡。需要一个群id作为参数。
    只接受私聊消息。

    如果发送者不是KP，那么只能在一个群内拥有最多一张角色卡。

    如果不知道群id，请先发送`/getid`到群里获取id。
    `/newcard`提交创建卡请求，bot会等待你输入`groupid`。
    `/newcard --groupid`新建一张卡片，绑定到`groupid`对应的群。
    `/newcard --groupid --cardid`新建一张卡片，绑定到`groupid`对应的群的同时，
    将卡片id设置为`cardid`，`cardid`必须是非负整数。
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
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息创建角色卡。")
    if len(context.args) == 0:
        update.message.reply_text(
            "准备创建新卡。\n如果你不知道群id，在群里发送 /getid 获取群id。\n请发送群id：")
        utils.addOP(update.effective_chat.id, "newcard")
        return True
    msg = context.args[0]
    if not utils.isint(msg) or int(msg) >= 0:
        return utils.errorHandler(update, "无效群id")
    gpid = int(msg)
    utils.initrules(gpid)
    # 检查(pl)是否已经有卡
    plid = update.effective_chat.id
    if utils.hascard(plid, gpid):
        return utils.errorHandler(update, "你在这个群已经有一张卡了！")
    # 符合建卡条件，生成新卡
    if len(context.args) > 1:
        if not utils.isint(context.args[1]) or int(context.args[1]) < 0:
            return utils.errorHandler(update, "输入的卡片id参数无效，需要是非负整数")
        return utils.getnewcard(update, gpid, plid, int(context.args[1]))
    return utils.getnewcard(update, gpid, plid)


def discard(update: Update, context: CallbackContext):
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
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息删除卡。")
    plid = update.effective_chat.id  # 发送者
    # 先找到所有可删除的卡，返回一个列表
    discardgpcdTupleList = utils.findDiscardCardsGroupIDTuple(plid)
    if len(context.args) > 0:
        # 求args提供的卡id与可删除的卡id的交集
        trueDiscardTupleList: List[Tuple[int, int]] = []
        for gpid, cdid in discardgpcdTupleList:
            if str(gpid) in context.args or str(cdid) in context.args:
                trueDiscardTupleList.append((gpid, cdid))
        if len(trueDiscardTupleList) == 0:  # 交集为空集
            update.message.reply_text("输入的（群/卡片）ID均无效。")
            return False
        if len(trueDiscardTupleList) == 1:
            gpid, cdid = trueDiscardTupleList[0]
            rttext = "删除卡："+str(cdid)
            if "name" in utils.CARDS_DICT[gpid][cdid].info and utils.CARDS_DICT[gpid][cdid].info["name"] != "":
                rttext += "\nname: " + \
                    str(utils.CARDS_DICT[gpid][cdid].info["name"])
            rttext += "\n/details 显示删除的卡片信息。删除操作不可逆。"
            update.message.reply_text(rttext)
        else:
            update.message.reply_text(
                "删除了"+str(len(trueDiscardTupleList))+"张卡片。\n/details 显示删除的卡片信息。删除操作不可逆。")
        detailinfo = ""
        for gpid, cdid in trueDiscardTupleList:
            detailinfo += "删除卡片：\n" + \
                str(utils.CARDS_DICT[gpid][cdid])+"\n"  # 获取删除的卡片的详细信息
            utils.CARDS_DICT[gpid].pop(cdid)
            if len(utils.CARDS_DICT[gpid]) == 0:
                utils.CARDS_DICT.pop(gpid)
            if plid in utils.CURRENT_CARD_DICT and utils.CURRENT_CARD_DICT[plid][0] == gpid and utils.CURRENT_CARD_DICT[plid][1] == cdid:
                utils.CURRENT_CARD_DICT.pop(plid)
                utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
        utils.DETAIL_DICT[plid] = detailinfo
        utils.writecards(utils.CARDS_DICT)
        return True
    if len(discardgpcdTupleList) > 1:  # 创建按钮，接下来交给按钮完成
        rtbuttons: List[List[str]] = [[]]
        for gpid, cdid in discardgpcdTupleList:
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            if "name" in utils.CARDS_DICT[gpid][cdid].info and utils.CARDS_DICT[gpid][cdid].info["name"] != 0:
                cardname: str = utils.CARDS_DICT[gpid][cdid].info["name"]
            else:
                cardname: str = str(cdid)
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(cardname,
                                                                    callback_data=utils.IDENTIFIER+" "+"discard "+str(gpid)+" "+str(cdid)))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("请点击要删除的卡片：", reply_markup=rp_markup)
        return True
    if len(discardgpcdTupleList) == 1:
        gpid, cdid = discardgpcdTupleList[0]
        if plid in utils.CURRENT_CARD_DICT and utils.CURRENT_CARD_DICT[plid][0] == gpid and utils.CURRENT_CARD_DICT[plid][1] == cdid:
            utils.CURRENT_CARD_DICT.pop(plid)
            utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
        rttext = "删除卡："+str(cdid)
        if "name" in utils.CARDS_DICT[gpid][cdid].info and utils.CARDS_DICT[gpid][cdid].info["name"] != "":
            rttext += "\nname: "+str(utils.CARDS_DICT[gpid][cdid].info["name"])
        rttext += "\n/details 显示删除的卡片信息。删除操作不可逆。"
        update.message.reply_text(rttext)
        detailinfo = "删除卡片：\n"+str(utils.CARDS_DICT[gpid][cdid])+"\n"
        utils.DETAIL_DICT[plid] = detailinfo
        utils.CARDS_DICT[gpid].pop(cdid)
        if len(utils.CARDS_DICT[gpid]) == 0:
            utils.CARDS_DICT.pop(gpid)
        utils.writecards(utils.CARDS_DICT)
        return True
    # 没有可删除的卡
    return utils.errorHandler(update, "找不到可删除的卡。")


def details(update: Update, context: CallbackContext):
    """显示详细信息。
    该指令主要是为了与bot交互时产生尽量少的文本消息而设计。

    当一些指令产生了“详细信息”时，这些详细信息会被暂时存储。
    当使用`/details`查看了这些“详细信息”，该“信息”将从存储中删除，即只能读取一次。
    如果没有查看上一个“详细信息”，就又获取到了下一个“详细信息”，
    上一个“详细信息”将会被覆盖。"""
    if update.effective_chat.id not in utils.DETAIL_DICT or utils.DETAIL_DICT[update.effective_chat.id] == "":
        utils.DETAIL_DICT[update.effective_chat.id] = ""
        return utils.errorHandler(update, "没有可显示的信息。")
    update.message.reply_text(utils.DETAIL_DICT[update.effective_chat.id])
    utils.DETAIL_DICT[update.effective_chat.id] = ""
    return True


def setage(update: Update, context: CallbackContext):
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息设置年龄。")
    cardi, ok = utils.findcard(update.effective_chat.id)
    if not ok:
        return utils.errorHandler(update, "找不到卡。")
    if "AGE" in cardi.info:
        return utils.errorHandler(update, "已经设置过年龄了。")
    if len(context.args) == 0:
        update.message.reply_text("请输入年龄：")
        utils.addOP(update.effective_chat.id, "setage")
        return True
    age = context.args[0]
    if not utils.isint(age):
        return utils.errorHandler(update, "输入无效")
    age = int(age)

    return utils.cardsetage(update, cardi, age)


def setstrdec(update: Update, context: CallbackContext):
    """设置力量（STR）的减少值。因为年龄的设定，会导致力量属性减少。
    一般而言，年龄导致的需要减少的属性数目至少是两项，其中一项会是力量。
    它们减少的总值是定值。
    当只有两项需要下降时，用力量的减少值，就能自动计算出另一项减少值。
    但如果有三项下降，那么其中一项会是体质（CON）。
    那么可能需要再使用`/setcondec`指令。

    `/setstrdec`生成按钮来让玩家选择力量下降多少。

    `/setstrdec --STRDEC`可以直接指定力量的下降值。"""
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "Send private message to set STR decrease.")
    plid = update.effective_chat.id
    cardi, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if len(context.args) == 0:
        if "STR_SIZ_M" in cardi.data:
            rtbuttons = utils.makeIntButtons(max(0, 1 - cardi.data["SIZ"] - cardi.data["STR_SIZ_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_SIZ_M"]), "strdec", "", 1)
        elif "STR_CON_M" in cardi.data:
            rtbuttons = utils.makeIntButtons(max(0, 1 - cardi.data["CON"] - cardi.data["STR_CON_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_CON_M"]), "strdec", "", 1)
        elif "STR_CON_DEX_M" in cardi.data:
            rtbuttons = utils.makeIntButtons(max(0, 2 - cardi.data["CON"]-cardi.data["DEX"] - cardi.data["STR_CON_DEX_M"]), min(
                cardi.data["STR"]-1, -cardi.data["STR_CON_DEX_M"]), "strdec", "", 1)
        else:
            return utils.errorHandler(update, "无需设置力量下降值")
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("设置力量下降值：", reply_markup=rp_markup)
        return True
    dec = context.args[0]
    if not utils.isint(dec):
        return utils.errorHandler(update, "输入无效")
    dec = int(dec)
    cardi, hintmsg, needcon = utils.choosedec(cardi, dec)
    if hintmsg == "输入无效":
        return utils.errorHandler(update, hintmsg)
    update.message.reply_text(hintmsg)
    if needcon:
        update.message.reply_text("Use /setcondec to set CON decrease.")
    else:
        utils.generateOtherAttributes(cardi)
        update.message.reply_text("Use /setjob to set job.")
    utils.writecards(utils.CARDS_DICT)
    return True


def setcondec(update: Update, context: CallbackContext):
    """设置体质（CON）的减少值。请先参见帮助`/help setstrdec`。

    `/setcondec`生成按钮来让玩家选择体质下降多少。

    `/setcondec --CONDEC`可以直接指定体质的下降值。"""
    if utils.isgroupmsg(update):
        update.message.reply_text("Send private message to set CON decrease.")
        return False
    plid = update.effective_chat.id
    cardi, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if len(context.args) == 0:
        if "CON_DEX_M" not in cardi.data:
            update.message.reply_text("No need to set STR decrease.")
            return False
        rtbuttons = utils.makeIntButtons(max(0, 1 - cardi.data["DEX"] - cardi.data["CON_DEX_M"]), min(
            cardi.data["CON"]-1, -cardi.data["CON_DEX_M"]), "condec", "", 1)
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("Set CON decrease: ", reply_markup=rp_markup)
        return True
    dec = context.args[0]
    if not utils.isint(dec):
        update.message.reply_text("Invalid input.")
        return False
    dec = int(dec)
    cardi, hintmsg = utils.choosedec2(cardi, dec)
    if hintmsg == "输入无效":
        update.message.reply_text("Invalid input!")
        return False
    utils.generateOtherAttributes(cardi)
    utils.writecards(utils.CARDS_DICT)
    update.message.reply_text(hintmsg)
    return True


# Button. need 0-1 args, if len(args)==0, show button and listen
def setjob(update: Update, context: CallbackContext) -> bool:
    """设置职业。

    `/setjob`生成按钮来设定职业。点击职业将可以查看对应的推荐技能，
    以及对应的信用范围和主要技能点计算方法。再点击确认即可确认选择该职业。
    确认了职业就不能再更改。

    `/setjob --job`将职业直接设置为给定职业。
    如果允许非经典职业，需要参数`utils.IGNORE_JOB_DICT`为`True`，
    否则不能设置。如果设置了非经典职业，技能点计算方法为教育乘4。

    在力量、体质等属性减少值计算完成后才可以设置职业。"""
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发送私聊消息设置职业。")
    plid = update.effective_chat.id
    card1, ok = utils.findcard(plid)
    if not ok:
        return utils.errorHandler(update, "找不到卡。")
    if not card1.cardcheck["check2"]:
        for keys in card1.data:
            if len(keys) > 4:
                if keys[:3] == "STR":
                    return utils.errorHandler(update, "请先使用'/setstrdec --STRDEC'来设置力量下降值。")
                else:
                    return utils.errorHandler(update, "请先使用'/setcondec --CONDEC'来设置体质下降值。")
        utils.sendtoAdmin("卡片检查出错，位置：setjob")
        return utils.errorHandler(update, "错误！卡片检查：2不通过，但没有找到原因。")
    if "job" in card1.info:
        update.message.reply_text("职业已经设定了！如果需要帮助，使用 /createcardhelp 来获取帮助。")
        return False
    if len(context.args) == 0:
        rtbuttons = utils.makejobbutton()
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        # 设置职业的任务交给函数buttonjob
        update.message.reply_text(
            "请选择职业查看详情：", reply_markup=rp_markup)
        return True
    jobname = context.args[0]
    if not utils.IGNORE_JOB_DICT and jobname not in utils.JOB_DICT:
        update.message.reply_text("This job is not allowed!")
        return False
    card1.info["job"] = jobname
    if jobname not in utils.JOB_DICT:
        update.message.reply_text(
            "这个职业不在职业表内，你可以用'/addskill 技能名 点数 (main/interest)'来选择技能！如果有interest参数，该技能将是兴趣技能并消耗兴趣技能点。")
        card1.skill["points"] = int(card1.data["EDU"]*4)
        utils.writecards(utils.CARDS_DICT)
        return True
    for i in range(3, len(utils.JOB_DICT[jobname])):  # Classical jobs
        card1.suggestskill[utils.JOB_DICT[jobname][i]] = utils.getskilllevelfromdict(
            card1, utils.JOB_DICT[jobname][i])  # int
    update.message.reply_text(
        "用 /addskill 来添加技能。")
    # This trap should not be hit
    if not utils.generatePoints(card1, jobname):
        return utils.errorHandler(update, "Some error occured when generating skill points!")
    utils.writecards(utils.CARDS_DICT)
    return True


def showjoblist(update: Update, context: CallbackContext) -> None:
    """显示职业列表"""
    rttext = "职业列表："
    for job in utils.JOB_DICT:
        rttext += job+"\n"


# Button. need 0-3 args, if len(args)==0 or 1, show button and listen; if len(args)==3, the third should be "interest/main" to give interest skills
# Compicated
def addskill(update: Update, context: CallbackContext) -> bool:
    """该函数用于增加/修改技能。

    `/addskill`：生成按钮，玩家按照提示一步步操作。"""
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "发私聊消息来增改技能", True)
    plid = update.effective_chat.id
    card1, ok = utils.findcard(plid)
    if not ok:
        return utils.errorHandler(update, "找不到卡。")
    if card1.skill["points"] == -1:
        return utils.errorHandler(update, "信息不完整，无法添加技能")
    if card1.skill["points"] == 0 and card1.interest["points"] == 0 and len(context.args) == 0:
        if len(context.args) == 0 or (context.args[0] not in card1.skill and context.args[0] not in card1.interest):
            return utils.errorHandler(update, "你已经没有技能点了，请添加参数来修改具体的技能！")
    if "job" not in card1.info:
        return utils.errorHandler(update, "请先设置职业")
    if "信用" not in card1.skill:
        return utils.addcredit(update, context, card1)
    if len(context.args) == 0:  # HIT GOOD TRAP
        return utils.addskill0(update, context, card1)
    skillname = context.args[0]
    # HIT BAD TRAP
    if skillname != "母语" and skillname != "闪避" and (skillname not in utils.SKILL_DICT or skillname == "克苏鲁神话"):
        return utils.errorHandler(update, "无法设置这个技能")
    if len(context.args) == 1:  # HIT GOOD TRAP
        # This function only returns True
        return utils.addskill1(update, context, card1)
    skillvalue = context.args[1]
    if not utils.isint(skillvalue):
        return utils.errorHandler(update, "第二个参数：无效输入")
    skillvalue = int(skillvalue)
    # HIT GOOD TRAP
    if len(context.args) >= 3:
        # No buttons
        return utils.addskill3(update, context, card1)
    return utils.addskill2(update, context, card1)


def showskilllist(update: Update, context: CallbackContext) -> None:
    """显示技能列表"""
    rttext = "技能：基础值\n"
    rttext += "母语：等于EDU\n"
    rttext += "闪避：等于DEX的一半\n"
    for skill in utils.SKILL_DICT:
        rttext += skill+"："+str(utils.SKILL_DICT[skill])+"\n"
    update.message.reply_text(rttext)


def button(update: Update, context: CallbackContext):
    """所有按钮请求经该函数处理。功能十分复杂，拆分成多个子函数来处理。
    接收到按钮的参数后，转到对应的子函数处理。"""
    query = update.callback_query
    query.answer()
    if utils.isgroupmsg(update):
        query.edit_message_text(text="群按钮请求均无效。")
        return False
    args = query.data.split(" ")
    identifier = args[0]
    if identifier != utils.IDENTIFIER:
        query.edit_message_text(text="该请求已经过期。")
        return False
    args = args[1:]
    plid = update.effective_chat.id
    card1, ok = utils.findcard(plid)
    if not ok and args[0] != "switch" and args[0] != "discard":
        query.edit_message_text(text="找不到卡。")
        return False
    # receive types: job, skill, sgskill, intskill, cgskill, addmainskill, addintskill, addsgskill
    if args[0] == "job":  # Job in buttons must be classical
        return utils.buttonjob(query, update, card1, args)
    # Increase skills already added, because sgskill is none. second arg is skillname
    if args[0] == "addmainskill":
        return utils.buttonaddmainskill(query, update, card1, args)
    if args[0] == "cgmainskill":
        return utils.buttoncgmainskill(query, update, card1, args)
    if args[0] == "addsgskill":
        return utils.buttonaddsgskill(query, update, card1, args)
    if args[0] == "addintskill":
        return utils.buttonaddintskill(query, update, card1, args)
    if args[0] == "cgintskill":
        return utils.buttoncgintskill(query, update, card1, args)
    if args[0] == "strdec":
        return utils.buttonstrdec(query, update, card1, args)
    if args[0] == "condec":
        return utils.buttoncondec(query, update, card1, args)
    if args[0] == "discard":
        return utils.buttondiscard(query, update, card1, args)
    if args[0] == "switch":
        return utils.buttonswitch(query, update, card1, args)
    if args[0] == "switchkp":
        return utils.buttonswitchkp(query, update, card1, args)
    if args[0] == "setsex":
        return utils.buttonsetsex(query, update, card1, args)
    # HIT BAD TRAP
    return False


def setname(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) == 0:
        if utils.isprivatemsg(update):
            utils.addOP(update.effective_chat.id, "setname")
        else:
            utils.addOP(update.effective_chat.id, "setname "+str(plid))
        update.message.reply_text("请输入姓名：")
        return True
    card1, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    card1.info["name"] = ' '.join(context.args)
    update.message.reply_text("Name is set to: "+card1.info["name"]+".")
    card1.cardcheck["check5"] = True
    utils.writecards(utils.CARDS_DICT)
    return True


def startgame(update: Update, context: CallbackContext) -> bool:
    """开始一场游戏。

    这一指令将拷贝本群内所有卡，之后将用拷贝的卡片副本进行游戏，修改属性将不会影响到游戏外的原卡属性。
    如果要正常结束游戏，使用`/endgame`可以将游戏的角色卡数据覆写到原本的数据上。
    如果要放弃这些游戏内进行的修改，使用`/abortgame`会直接删除这些副本副本"""
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "游戏需要在群里进行")
    if utils.getkpid(update.effective_chat.id) == -1:
        return utils.errorHandler(update, "这个群没有KP")
    if not utils.isfromkp(update):
        return utils.errorHandler(update, "游戏应由KP发起", True)
    gpid = update.effective_chat.id
    kpid = update.message.from_user.id
    for games in utils.ON_GAME:
        if games.kpid == kpid:
            return utils.errorHandler(update, "一个KP一次只能同时主持一场游戏。")
    if utils.popallempties(utils.CARDS_DICT):
        utils.writecards(utils.CARDS_DICT)
    if gpid not in utils.CARDS_DICT:
        update.message.reply_text("注意！本群没有卡片。游戏开始。")
        utils.ON_GAME.append(
            utils.GroupGame(groupid=update.effective_chat.id, kpid=kpid, cards=[]))
        utils.writegameinfo(utils.ON_GAME)
        return True
    gamecards = []
    for cdid in utils.CARDS_DICT[gpid]:
        cardcheckinfo = utils.showchecks(utils.CARDS_DICT[gpid][cdid])
        if cardcheckinfo != "All pass.":
            return utils.errorHandler(update, "卡片: "+str(cdid)+"还没有准备好。因为：\n"+cardcheckinfo)
        gamecards.append(utils.CARDS_DICT[gpid][cdid].__dict__)
    utils.ON_GAME.append(utils.GroupGame(groupid=update.effective_chat.id,
                                         kpid=kpid, cards=gamecards))
    utils.writegameinfo(utils.ON_GAME)
    update.message.reply_text("游戏开始！")
    return True


def abortgame(update: Update, context: CallbackContext) -> bool:
    if utils.isprivatemsg(update):
        return utils.errorHandler(update, "发送群聊消息来中止游戏")
    gpid = update.effective_chat.id
    if update.message.from_user.id != utils.getkpid(gpid):
        return utils.errorHandler(update, "只有KP可以中止游戏", True)
    if not utils.gamepop(gpid):
        return utils.errorHandler(update, "没有找到游戏", True)
    update.message.reply_text("游戏已终止！")
    return True


def endgame(update: Update, context: CallbackContext) -> bool:
    if update.effective_chat.id > 0:
        return utils.errorHandler(update, "该指令仅用于群聊")
    if utils.getkpid(update.effective_chat.id) == -1:
        return utils.errorHandler(update, "这个群没有KP")
    if update.message.from_user.id != utils.getkpid(update.effective_chat.id):
        update.message.reply_text("Only KP can end a game.")
        return False
    gpid = update.effective_chat.id
    kpid = utils.getkpid(gpid)
    game = utils.gamepop(gpid)
    if not game:
        return utils.errorHandler(update, "没找到进行中的游戏。")
    gamecards = game.cards
    for cardi in gamecards:
        if cardi.playerid in utils.CURRENT_CARD_DICT and utils.CURRENT_CARD_DICT[cardi.playerid][0] == gpid and utils.CURRENT_CARD_DICT[cardi.playerid][1] == cardi.id:
            utils.CURRENT_CARD_DICT.pop(cardi.playerid)
            utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
        cardi.playerid = kpid
        if cardi.id not in utils.CARDS_DICT[gpid]:
            utils.CARDS_DICT[gpid][cardi.id] = cardi
            continue
        utils.CARDS_DICT[gpid].pop(cardi.id)
        utils.CARDS_DICT[gpid][cardi.id] = cardi
    utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
    update.message.reply_text("游戏结束！")
    utils.writecards(utils.CARDS_DICT)
    return True


# /switch (--id): 切换进行修改操作时控制的卡，可以输入gpid，也可以是cdid
def switch(update: Update, context: CallbackContext):
    if utils.isgroupmsg(update):
        update.message.reply_text("对bot私聊来切换卡。")
        return False
    plid = update.effective_chat.id
    if len(context.args) > 0:
        if not utils.isint(context.args[0]):
            update.message.reply_text("输入无效。")
            return False
        numid = int(context.args[0])
        if numid < 0:
            gpid = numid
            cardscount = 0
            temptuple: Tuple[int, int] = (0, 0)
            for cdid in utils.CARDS_DICT[gpid]:
                if utils.CARDS_DICT[gpid][cdid].playerid == plid:
                    cardscount += 1
                    if cardscount > 1:
                        update.message.reply_text(
                            "在这个群你有多于一张卡，请输入具体的卡id。如果不知道自己的卡id，用 /showmycards 来显示ID。")
                        return False
                    temptuple = (gpid, cdid)
            if cardscount == 0:
                update.message.reply_text("你在这个群没有卡。")
                return False
            rttext = "切换成功，现在操作的卡：\n"
            cardi = utils.CARDS_DICT[gpid][temptuple[1]]
            if "name" in cardi.info and cardi.info["name"] != "":
                rttext += cardi.info["name"]+": "+str(cardi.id)
            else:
                rttext += "(No name): "+str(cardi.id)
            utils.CURRENT_CARD_DICT[plid] = temptuple
            utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
            update.message.reply_text(rttext)
            return True
        else:
            cdid = numid
            for gpid in utils.CARDS_DICT:
                if cdid in utils.CARDS_DICT[gpid]:
                    rttext = "切换成功，现在操作的卡：\n"
                    cardi = utils.CARDS_DICT[gpid][cdid]
                    if "name" in cardi.info and cardi.info["name"] != "":
                        rttext += cardi.info["name"]+": "+str(cardi.id)
                    else:
                        rttext += "(No name): "+str(cardi.id)
                    utils.CURRENT_CARD_DICT[plid] = (gpid, cdid)
                    utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
                    update.message.reply_text(rttext)
                    return True
            update.message.reply_text("找不到这张卡。")
            return False
    mycardslist = utils.findallplayercards(plid)
    if len(mycardslist) == 0:
        update.message.reply_text("你没有任何卡。")
        return False
    if len(mycardslist) == 1:
        gpid, cdid = mycardslist[0]
        rttext = "你只有一张卡，自动切换。现在操作的卡：\n"
        cardi = utils.CARDS_DICT[gpid][cdid]
        if "name" in cardi.info and cardi.info["name"] != "":
            rttext += cardi.info["name"]+": "+str(cardi.id)
        else:
            rttext += "(No name): "+str(cardi.id)
        update.message.reply_text(rttext)
        utils.CURRENT_CARD_DICT[plid] = (gpid, cdid)
        utils.writecurrentcarddict(utils.CURRENT_CARD_DICT)
        return True
    # 多个选项。创建按钮
    rtbuttons = [[]]
    for gpid, cdid in mycardslist:
        cardi = utils.CARDS_DICT[gpid][cdid]
        cardiname: str
        if "name" not in cardi.info or cardi.info["name"] == "":
            cardiname = str(cdid)
        else:
            cardiname = cardi.info["name"]
        if len(rtbuttons[len(rtbuttons)-1]) == 4:
            rtbuttons.append([])
        rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
            cardiname, callback_data=utils.IDENTIFIER+" "+"switch "+str(gpid)+" "+str(cdid)))
    rp_markup = InlineKeyboardMarkup(rtbuttons)
    update.message.reply_text("请选择要切换控制的卡：", reply_markup=rp_markup)
    # 交给按钮来完成
    return True


def switchkp(update: Update, context: CallbackContext):
    """用于KP切换游戏中进行对抗时使用的NPC卡片。

    （仅限私聊时）`/swtichkp`：创建按钮，让KP选择要用的卡。
    （私聊群聊皆可）`/switchkp --cardid`：切换到id为cardid的卡并控制。"""
    game, ok = utils.findgamewithkpid(update.message.from_user.id)
    if not ok:
        return utils.errorHandler(update, "没有游戏或没有权限", True)
    if len(context.args) == 0:
        if utils.isgroupmsg(update):
            return utils.errorHandler(update, "请直接指定要切换的卡id，或者向bot发送私聊消息切换卡！")
        rtbuttons = [[]]
        for cardi in game.kpcards:
            cardiname = utils.getname(cardi)
            if cardiname == "None":
                cardiname = str(cardi.id)
            if len(rtbuttons[len(rtbuttons)-1]) == 4:
                rtbuttons.append([])
            rtbuttons[len(rtbuttons)-1].append(InlineKeyboardButton(
                cardiname, callback_data=utils.IDENTIFIER+" "+"switchkp "+str(cardi.id)))
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("请选择要切换控制的卡：", reply_markup=rp_markup)
        # 交给按钮来完成
        return True
    num = context.args[0]
    if not utils.isint(num) or int(num) < 0:
        return utils.errorHandler(update, "无效输入", True)
    cdid = int(num)
    cardi, ok = utils.findcardfromgamewithid(game, cdid)
    if not ok or cardi.playerid != game.kpid:
        return utils.errorHandler(update, "无效id", True)
    game.kpctrl = cdid
    update.message.reply_text(
        "切换到卡" + str(num)+"，角色名称：" + cardi.info["name"])
    utils.writegameinfo(utils.ON_GAME)
    return True


def showmycards(update: Update, context: CallbackContext) -> bool:
    """显示自己所持的卡"""
    plid = update.message.from_user.id
    allcardsTuple = utils.findallplayercards(plid)
    if len(allcardsTuple) == 0:
        return utils.errorHandler(update, "找不到卡。")
    if utils.isgroupmsg(update):
        # 群消息，只发送本群的卡
        rttext = ""
        for gpid, cdid in allcardsTuple:
            if gpid != update.effective_chat.id:
                continue
            cardi = utils.cardget(gpid, cdid)
            name = utils.getname(cardi)
            rttext += str(cdid)+": "+name+"\n"
        if rttext == "":
            update.message.reply_text("找不到本群的卡。")
        else:
            update.message.reply_text(rttext)
        return True
    # 私聊消息，发送全部卡
    rttext = ""
    for gpid, cdid in allcardsTuple:
        cardi = utils.cardget(gpid, cdid)
        name = utils.getname(cardi)
        rttext += "群id "+str(gpid)+" 卡id "+str(cdid)+":\n"+name+"\n"
    update.message.reply_text(rttext)
    return True


# /tempcheck --tpcheck:int: add temp check
# /tempcheck --tpcheck:int (--cardid --dicename): add temp check for one card in a game


def tempcheck(update: Update, context: CallbackContext):
    """增加一个临时的检定修正。该指令只能在游戏中使用。
    `/tempcheck --tpcheck`只能用一次的检定修正。使用完后消失
    `/tempcheck --tpcheck --cardid --dicename`对某张卡，持久生效的检定修正"""
    if len(context.args) == 0:
        return utils.errorHandler(update, "没有参数", True)
    if update.effective_chat.id > 0:
        return utils.errorHandler(update, "在群里设置临时检定")
    if not utils.isint(context.args[0]):
        return utils.errorHandler(update, "临时检定修正应当是整数", True)
    game, ok = utils.findgame(update.effective_chat.id)
    if not ok:
        return utils.errorHandler(update, "没有进行中的游戏", True)
    if utils.getkpid(update.effective_chat.id) != update.message.from_user.id:
        return utils.errorHandler(update, "KP才可以设置临时检定", True)
    if len(context.args) >= 3 and utils.isint(context.args[1]) and 0 <= int(context.args[1]):
        card, ok = utils.findcardfromgamewithid(game, int(context.args[1]))
        if not ok:
            return utils.errorHandler(update, "找不到这张卡", True)
        card.tempstatus[context.args[2]] = int(context.args[0])
        update.message.reply_text(
            "新增了对id为"+context.args[1]+"卡的检定修正\n修正项："+context.args[2]+"修正值："+context.args[0])
    else:
        game.tpcheck = int(context.args[0])
        update.message.reply_text("新增了仅限一次的全局检定修正："+context.args[0])
    utils.writegameinfo(utils.ON_GAME)
    return True


def roll(update: Update, context: CallbackContext):
    """基本的骰子功能。

    只接受第一个空格前的参数`dicename`。
    `dicename`可能是技能名，可能是`3d6`，可能是`1d4+2d10`。
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
        update.message.reply_text(utils.commondice("1d100"))  # 骰1d100
        return True
    dicename = context.args[0]
    gpid = update.effective_chat.id
    if utils.isgroupmsg(update):  # Group msg
        utils.initrules(gpid)
        game, ok = utils.findgame(gpid)
        # 检查输入参数是不是一个基础骰子，如果是则直接计算骰子
        if not ok or dicename.find('d') >= 0:
            rttext = utils.commondice(dicename)
            if rttext == "Invalid input.":
                return utils.errorHandler(update, "无效输入")
            update.message.reply_text(rttext)
            return True
        # 确认不是基础骰子的计算，转到卡检定
        # 获取临时检定
        tpcheck, game.tpcheck = game.tpcheck, 0
        if tpcheck != 0:
            utils.writegameinfo(utils.ON_GAME)
        senderid = update.message.from_user.id
        gpid = update.effective_chat.id
        # 获取卡
        if senderid != utils.getkpid(gpid):
            gamecard = utils.findcardfromgame(game, senderid)
        else:
            gamecard = utils.getkpctrl(game)
        if not gamecard:
            return utils.errorHandler(update, "找不到游戏中的卡。")
        # 找卡完成，开始检定
        test = 0
        if dicename in gamecard.skill:
            test = gamecard.skill[dicename]
        elif dicename in gamecard.interest:
            test = gamecard.interest[dicename]
        elif dicename == "母语":
            test = gamecard.data["EDU"]
        elif dicename == "闪避":
            test = gamecard.data["DEX"]//2
        elif dicename in gamecard.data:
            test = gamecard.data[dicename]
        elif dicename == "力量":
            dicename = "STR"
            test = gamecard.data[dicename]
        elif dicename == "体质":
            dicename = "CON"
            test = gamecard.data[dicename]
        elif dicename == "体型":
            dicename = "SIZ"
            test = gamecard.data[dicename]
        elif dicename == "敏捷":
            dicename = "DEX"
            test = gamecard.data[dicename]
        elif dicename == "外貌":
            dicename = "APP"
            test = gamecard.data[dicename]
        elif dicename == "智力" or dicename == "灵感":
            dicename = "INT"
            test = gamecard.data[dicename]
        elif dicename == "意志":
            dicename = "POW"
            test = gamecard.data[dicename]
        elif dicename == "教育":
            dicename = "EDU"
            test = gamecard.data[dicename]
        elif dicename == "幸运":
            dicename = "LUCK"
            test = gamecard.data[dicename]
        elif dicename in utils.SKILL_DICT:
            test = utils.SKILL_DICT[dicename]
        elif dicename[:2] == "暗骰" and (utils.isint(dicename[2:]) or len(dicename) == 2):
            if len(dicename) != 2:
                test = int(dicename[2:])
            else:
                test = 50
        else:  # HIT BAD TRAP
            return utils.errorHandler(update, "无效输入")
        if "global" in gamecard.tempstatus:
            test += gamecard.tempstatus["global"]
        if dicename in gamecard.tempstatus:
            test += gamecard.tempstatus[dicename]
        test += tpcheck
        testval = utils.dicemdn(1, 100)[0]
        rttext = dicename+" 检定/出目："+str(test)+"/"+str(testval)+" "
        greatsuccessrule = utils.GROUP_RULES[gpid].greatsuccess
        greatfailrule = utils.GROUP_RULES[gpid].greatfail
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
            if utils.getkpid(gpid) == -1:
                return utils.errorHandler(update, "本群没有KP！请先添加一个KP再试！！")
            update.message.reply_text(dicename+" 检定/出目："+str(test)+"/???")
            context.bot.send_message(
                chat_id=utils.getkpid(gpid), text=rttext)
        else:
            update.message.reply_text(rttext)
        return True
    rttext = utils.commondice(dicename)  # private msg
    update.message.reply_text(rttext)
    if rttext == "Invalid input.":
        return False
    return True


def show(update: Update, context: CallbackContext) -> bool:
    """显示目前操作中的卡片的信息。
    如果有多张卡，用`/switch`切换目前操作的卡。
    `/show card`：显示当前操作的整张卡片的信息；
    `/show --attrname`：显示卡片的某项具体属性。
    例如，`/show skill`显示主要技能，
    `/show interest`显示兴趣技能。
    如果当前卡中没有这个属性，则无法显示。
    可以显示的属性例子：
    `STR`,`description`
    """
    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数：card或者attrname其中一个")
    if utils.isprivatemsg(update):
        plid = update.effective_chat.id
        card1, ok = utils.findcard(plid)
        if not ok:
            return utils.errorHandler(update, "找不到卡。")
        if context.args[0] == "card":
            update.message.reply_text(utils.showcardinfo(card1))
            return True
        attrname = context.args[0]
        return utils.showattrinfo(update, card1, attrname)
    # 群消息
    gpid = update.effective_chat.id
    senderid = update.message.from_user.id
    # KP
    if utils.getkpid(gpid) == senderid and context.args[0] == "card":
        return utils.errorHandler(update, "为保护NPC或敌人信息，不可以在群内显示KP整张卡片", True)
    game, ingame = utils.findgame(gpid)
    if not ingame:  # 显示游戏外数据，需要提示
        cardi, ok = utils.findcard(senderid)
        if not ok:
            return utils.errorHandler(update, "找不到卡。")
    else:
        if utils.isfromkp(update):
            cardi = utils.getkpctrl(game)
            if not cardi:
                return utils.errorHandler(update, "注意：kpctrl值为-1")
        else:
            cardi = utils.findcardfromgame(game, senderid)
            if not cardi:
                return utils.errorHandler(update, "找不到卡。")
    # 显示游戏内数据，需要提示是游戏内/外的卡
    if context.args[0] == "card":
        rttext = ""
        if ingame:
            rttext += "显示游戏中的卡片：\n"
        else:
            rttext += "显示游戏外的卡片：\n"
        rttext += utils.showcardinfo(cardi)
        update.message.reply_text(rttext)
        return True
    attrname = context.args[0]
    if ingame:
        update.message.reply_text("显示游戏中的卡片：")
    else:
        update.message.reply_text("显示游戏外的卡片：")
    return utils.showattrinfo(update, cardi, attrname)


def showkp(update: Update, context: CallbackContext) -> bool:
    """这一指令是为KP设计的。

    `/showkp game`: 显示发送者主持的游戏中所有的卡
    `/showkp card`: 显示发送者作为KP控制的所有卡
    `/showkp group --groupid`: 显示发送者是KP的某个群内的所有卡"""
    # Should not return game info, unless args[0] == "game"
    if utils.isgroupmsg(update):
        return utils.errorHandler(update, "使用该指令请发送私聊消息", True)
    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")
    arg = context.args[0]
    if arg == "group":
        kpid = update.effective_chat.id
        # args[1] should be group id
        if len(context.args) < 2:
            return utils.errorHandler(update, "需要群ID")
        gpid = context.args[1]
        if not utils.isint(gpid):
            return utils.errorHandler(update, "无效ID")
        gpid = int(gpid)
        if gpid not in utils.CARDS_DICT:
            return utils.errorHandler(update, "这个群没有卡")
        ans: List[utils.GameCard] = []
        for cdid in utils.CARDS_DICT[gpid]:
            ans.append(utils.CARDS_DICT[gpid][cdid])
        if len(ans) == 0:
            return utils.errorHandler(update, "没有找到卡")
        for i in ans:
            update.message.reply_text(utils.showcardinfo(i))
        return True
    if arg == "game":
        kpid = update.effective_chat.id
        game, ok = utils.findgamewithkpid(kpid)
        if not ok:
            return utils.errorHandler(update, "没有找到游戏")
        for i in game.cards:
            update.message.reply_text(utils.showcardinfo(i))
        return True
    if arg == "card":
        kpid = update.effective_chat.id
        cards = utils.findkpcards(kpid)
        if len(cards) == 0:
            return utils.errorHandler(update, "你没有控制的卡")
        for i in range(len(cards)):
            update.message.reply_text(utils.showcardinfo(cards[i]))
        return True
    return utils.errorHandler(update, "无法识别的参数")


def showcard(update: Update, context: CallbackContext) -> bool:
    """显示某张卡的信息。

    `/showcard --cardid (--attrname)`: 显示卡id为`cardid`的卡片的信息。
    如果第二个参数存在，则显示这一项数据。

    显示前会检查发送者是否有权限显示这张卡。在这些情况下，无法显示卡：

    群聊环境：显示非本群的卡片，或者显示本群PL以外的卡片；

    私聊环境：作为PL，显示非自己控制的卡片；KP想显示非自己管理的群的卡片。"""
    if len(context.args) == 0:
        return utils.errorHandler(update, "需要参数")
    if not utils.isint(context.args[0]):
        return utils.errorHandler(update, "参数不是整数", True)
    cdid = int(context.args[0])
    cardi, ok = utils.findcardwithid(cdid)
    if not ok:
        return utils.errorHandler(update, "没有这张卡", True)
    if utils.isprivatemsg(update):
        # 检查是否合法
        if utils.isfromkp(update):  # KP
            kpid = update.effective_chat.id
            if kpid != utils.ADMIN_ID and utils.getkpid(cardi.groupid) != kpid:
                return utils.errorHandler(update, "没有权限")
        else:
            # 非KP，只能显示自己的卡
            plid = update.effective_chat.id
            if plid != utils.ADMIN_ID and cardi.playerid != plid:
                return utils.errorHandler(update, "没有权限")
        # 有权限，开始处理
        if len(context.args) >= 2:
            if not utils.showattrinfo(update, cardi, context.args[1]):
                return False
            return True
        # 显示整张卡
        update.message.reply_text(utils.showcardinfo(cardi))
        return True
    # 处理群聊消息
    gpid = update.effective_chat.id
    if cardi.groupid != gpid or cardi.playerid == utils.getkpid(gpid) or cardi.type != "PL":
        return utils.errorHandler(update, "不可显示该卡", True)
    # 有权限，开始处理
    if len(context.args) >= 2:
        if not utils.showattrinfo(update, cardi, context.args[1]):
            return False
        return True
    update.message.reply_text(utils.showcardinfo(cardi))
    return True

# (private)
# (private)showids game: return all card ids in a game
# (private)showids kp: return all card ids kp controlling


def showids(update: Update, context: CallbackContext) -> bool:
    """用于显示卡的名字-id对。群聊时使用只能显示游戏中PL的卡片id。

    `showids`: 显示游戏外的卡id。

    `showids game`: 显示游戏中的卡id。

    私聊时，只有KP可以使用该指令。两个指令同上，但结果将更详细，结果会包括KP主持游戏的所有群的卡片。额外有一个功能：

    `showids kp`: 返回KP游戏中控制的所有卡片id"""
    if utils.isgroupmsg(update):
        gpid = update.effective_chat.id
        if len(context.args) == 0:
            if gpid not in utils.CARDS_DICT:
                return utils.errorHandler(update, "本群没有卡")
            rttext = ""
            for cdid in utils.CARDS_DICT[gpid]:
                cardi = utils.CARDS_DICT[gpid][cdid]
                if cardi.playerid == utils.getkpid(gpid) or cardi.type != "PL":
                    continue
                rttext += str(cardi.id)+": "
                if "name" not in cardi.info or cardi.info["name"] == "":
                    rttext += "No name\n"
                else:
                    rttext += cardi.info["name"]+"\n"
            if rttext == "":
                return utils.errorHandler(update, "本群没有卡")
            update.message.reply_text(rttext)
            return True
        if context.args[0] != "game":
            return utils.errorHandler(update, "无法识别的参数", True)
        game, ok = utils.findgame(gpid)
        if not ok:
            return utils.errorHandler(update, "没有进行中的游戏", True)
        rttext = ""
        for cardi in game.cards:
            if cardi in game.kpcards or cardi.type != "PL":
                continue
            rttext += str(cardi.id)+": "
            if "name" not in cardi.info or cardi.info["name"] == "":
                rttext += "No name\n"
            else:
                rttext += cardi.info["name"]+"\n"
        if rttext == "":
            return utils.errorHandler(update, "游戏中没有卡")
        update.message.reply_text(rttext)
        return True
    # 下面处理私聊消息
    if not utils.isfromkp(update):
        return utils.errorHandler(update, "没有权限")
    kpid = update.effective_chat.id
    game, ok = utils.findgamewithkpid(kpid)
    if len(context.args) >= 1:
        if context.args[0] != "kp" and context.args[0] != "game":
            return utils.errorHandler(update, "无法识别的参数")
        if context.args[0] == "kp":
            if not ok:
                return utils.errorHandler(update, "该参数只返回游戏中你的卡片，但你目前没有主持游戏")
            cards = game.kpcards
        else:
            if not ok:
                return utils.errorHandler(update, "你目前没有主持游戏")
            cards = game.cards
        rttext = ""
        if len(cards) == 0:
            return utils.errorHandler(update, "游戏中KP没有卡")
        for cardi in cards:
            if "name" in cardi.info and cardi.info["name"] != "":
                rttext += str(cardi.id)+": "+cardi.info["name"]+"\n"
            else:
                rttext += str(cardi.id) + ": No name\n"
        update.message.reply_text(rttext)
        return True
    # 不带参数，显示全部该KP做主持的群中的卡id
    kpgps = utils.findkpgroups(kpid)
    rttext = ""
    if utils.popallempties(utils.CARDS_DICT):
        utils.writecards(utils.CARDS_DICT)
    for gpid in kpgps:
        if gpid not in utils.CARDS_DICT:
            continue
        for cdid in utils.CARDS_DICT[gpid]:
            if utils.CARDS_DICT[gpid][cdid].playerid == kpid:
                rttext += "(KP) "
            if "name" in utils.CARDS_DICT[gpid][cdid].info and utils.CARDS_DICT[gpid][cdid].info["name"].strip() != "":
                rttext += str(utils.CARDS_DICT[gpid][cdid].id) + \
                    ": "+utils.CARDS_DICT[gpid][cdid].info["name"]+"\n"
            else:
                rttext += str(utils.CARDS_DICT[gpid][cdid].id) + ": No name\n"
    if rttext == "":
        return utils.errorHandler(update, "没有可显示的卡")
    update.message.reply_text(rttext)
    return True


def modify(update: Update, context: CallbackContext) -> bool:
    """强制修改某张卡某个属性的值。
    需要注意可能出现的问题，使用该指令前，请三思。

    `/modify --cardid --arg --value (game)`: 修改id为cardid的卡的value，要修改的参数是arg。
    带game时修改的是游戏内卡片数据，不指明时默认游戏外
    （对于游戏中与游戏外卡片区别，参见 `/help startgame`）。
    修改对应卡片的信息必须要有对应的KP权限，或者是BOT的管理者。
    id和groupid这两个属性不可以修改。
    想要修改id，请使用指令
    `/changeid --cardid --newid`
    （参考`/help changeid`）。
    想要修改所属群，使用指令
    `/changegroup --cardid --newgroupid`
    （参考`/help changegroup`）。"""
    if not utils.isfromkp(update) and update.effective_chat.id != utils.ADMIN_ID:
        return utils.errorHandler(update, "没有权限", True)
    # need 3 args, first: card id, second: attrname, third: value
    if len(context.args) < 3:
        return utils.errorHandler(update, "需要至少3个参数", True)
    if context.args[1] == "id" or context.args[1] == "groupid":
        return utils.errorHandler(update, "该属性无法修改", True)
    card_id = context.args[0]
    if not utils.isint(card_id):
        return utils.errorHandler(update, "无效ID", True)
    card_id = int(card_id)
    if update.message.from_user.id == utils.ADMIN_ID:  # 最高控制权限
        if len(context.args) == 3 or context.args[3] != "game":
            cardi, ok = utils.findcardwithid(card_id)
            if not ok:
                return utils.errorHandler(update, "找不到该ID对应的卡。")
            rtmsg, ok = utils.modifycardinfo(
                cardi, context.args[1], context.args[2])
            if not ok:
                update.message.reply_text(rtmsg)
                return False
            update.message.reply_text("修改了游戏外的卡片！\n"+rtmsg)
            utils.writecards(utils.CARDS_DICT)
            return True
        cardi, ok = utils.findcardwithid(card_id)
        if not ok:
            return utils.errorHandler(update, "找不到游戏外对应卡片，请务必核查ID是否输入有误！")
        game, ok = utils.findgame(cardi.groupid)
        if not ok:
            return utils.errorHandler(update, "找不到游戏", True)
        cardi, ok = utils.findcardfromgamewithid(game, card_id)
        if not ok:
            update.message.reply_text("警告：找不到游戏中的卡，数据出现不一致！")
            utils.sendtoAdmin("警告：游戏内外卡片信息出现不一致，位置：/modify")
            return False
        rtmsg, ok = utils.modifycardinfo(
            cardi, context.args[1], context.args[2])
        if not ok:
            update.message.reply_text(rtmsg)
            return False
        update.message.reply_text("修改了游戏中的卡片！\n"+rtmsg)
        utils.writecards(utils.ON_GAME)
        return True
    # 处理有权限的非BOT控制者，即kp
    kpid = update.message.from_user.id
    if len(context.args) <= 3 or context.args[3] != "game":
        cardi, ok = utils.findcardwithid(card_id)
        if not ok:
            return utils.errorHandler(update, "找不到该ID对应的卡。")
        if utils.getkpid(cardi.groupid) != kpid:
            return utils.errorHandler(update, "没有权限", True)
        rtmsg, ok = utils.modifycardinfo(
            cardi, context.args[1], context.args[2])
        if not ok:
            update.message.reply_text(rtmsg)
            return False
        update.message.reply_text("修改了游戏外的卡片！\n"+rtmsg)
        utils.writecards(utils.CARDS_DICT)
        return True
    game, ok = utils.findgamewithkpid(kpid)
    if not ok:
        return utils.errorHandler(update, "没有进行中的游戏", True)
    cardi, ok = utils.findcardfromgamewithid(card_id)
    if not ok:
        return utils.errorHandler(update, "找不到游戏中的卡")
    rtmsg, ok = utils.modifycardinfo(cardi, context.args[1], context.args[2])
    if not ok:
        update.message.reply_text(rtmsg)
        return False
    update.message.reply_text("修改了游戏中的卡片！\n"+rtmsg)
    utils.writecards(utils.ON_GAME)
    return True


def changeid(update: Update, context: CallbackContext) -> bool:
    """修改卡片id。卡片的所有者或者KP均有使用该指令的权限。

    指令格式：
    `/changeid --cardid --newid`

    如果`newid`已经被占用，则指令无效。
    这一行为将同时改变游戏内以及游戏外的卡id。"""
    if len(context.args) < 2:
        return utils.errorHandler(update, "至少需要两个参数。")
    if not utils.isint(context.args[0]) or not utils.isint(context.args[1]):
        return utils.errorHandler(update, "参数错误", True)
    oldid = int(context.args[0])
    newid = int(context.args[1])
    if newid < 0:
        return utils.errorHandler(update, "负数id无效", True)
    if newid == oldid:
        return utils.errorHandler(update, "前后id相同", True)
    addids = utils.getallid()
    if newid in addids:
        return utils.errorHandler(update, "该ID已经被占用")
    cardi, ok = utils.findcardwithid(oldid)
    if not ok:
        return utils.errorHandler(update, "找不到该ID对应的卡")
    plid = update.message.from_user.id
    gpid = cardi.groupid
    if plid != utils.ADMIN_ID and cardi.playerid != plid and utils.getkpid(gpid) != plid:
        return utils.errorHandler(update, "非控制者且没有权限", True)
    # 有修改权限，开始处理
    utils.CARDS_DICT[gpid][newid] = utils.CARDS_DICT[gpid].pop(oldid)
    utils.CARDS_DICT[gpid][newid].id = newid
    utils.writecards(utils.CARDS_DICT)
    if "name" in cardi.info and cardi.info["name"] != "":
        rtmsg = "修改了卡片："+cardi.info["name"]+"的id至"+str(newid)
    else:
        rtmsg = "修改了卡片：No name 的id至"+str(newid)
    # 判断游戏是否也在进行，进行的话也要修改游戏内的卡
    game, ok = utils.findgame(gpid)
    if ok:
        card2, ok = utils.findcardfromgamewithid(game, oldid)
        if not ok:
            utils.errorHandler(update, "游戏内没有找到对应的卡")
            utils.sendtoAdmin("游戏内外数据不一致，位置：changeid")
        else:
            rtmsg += "\n游戏内id同步修改了。"
        card2.id = newid
        utils.writegameinfo(utils.ON_GAME)
    update.message.reply_text(rtmsg)
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
    if len(context.args) < 2:
        return utils.errorHandler(update, "至少需要2个参数")
    if not utils.isint(context.args[0]) or not utils.isint(context.args[1]):
        return utils.errorHandler(update, "参数错误", True)
    newgpid = int(context.args[1])
    if newgpid >= 0:
        return utils.errorHandler(update, "转移的目标群id应该是负数", True)
    if int(context.args[0]) < 0:  # 转移全部群卡片
        oldgpid = int(context.args[0])
        _, ok = utils.findgame(oldgpid)
        if ok:
            return utils.errorHandler(update, "游戏正在进行，无法转移")
        kpid = update.message.from_user.id
        if utils.getkpid(oldgpid) != kpid and kpid != utils.ADMIN_ID:
            return utils.errorHandler(update, "没有权限", True)
        if len(utils.CARDS_DICT[oldgpid]) == 0:
            return utils.errorHandler(update, "原群没有卡片！")
        # 检查权限通过
        numofcards = len(utils.CARDS_DICT[oldgpid])
        utils.changecardgpid(oldgpid, newgpid)
        update.message.reply_text(
            "操作成功，已经将"+str(numofcards)+"张卡片从群："+str(oldgpid)+"移动到群："+str(newgpid))
        return True
    # 转移一张卡片
    cdid = int(context.args[0])
    cardi, ok = utils.findcardwithid(cdid)
    if not ok:
        return utils.errorHandler(update, "找不到这个id的卡片", True)
    oldgpid = cardi.groupid
    _, ok = utils.findgame(oldgpid)
    if ok:
        return utils.errorHandler(update, "游戏正在进行，无法转移")
    if newgpid not in utils.CARDS_DICT:
        utils.CARDS_DICT[newgpid] = {}
    utils.CARDS_DICT[newgpid][cdid] = utils.CARDS_DICT[oldgpid].pop(cdid)
    utils.CARDS_DICT[newgpid][cdid].groupid = newgpid
    utils.writecards(utils.CARDS_DICT)
    cardname = "No name"
    if "name" in cardi.info and cardi.info["name"] != "":
        cardname = cardi.info["name"]
    update.message.reply_text(
        "操作成功，已经将卡片"+cardname+"从群："+str(oldgpid)+"移动到群："+str(newgpid))
    return True


def randombackground(update: Update, context: CallbackContext) -> bool:
    """生成随机的背景故事。

    获得当前发送者修改中的卡，生成随机的背景故事并写入。"""
    plid = update.message.from_user.id
    card1, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    # 随机信仰
    rdfaithlist = [
        "毗沙门天",
        "伊斯兰教",
        "海尔·塞拉西一世",
        "耶稣",
        "佛教",
        "道教",
        "无神论",
        "进化论",
        "冷冻休眠",
        "太空探索",
        "因果轮回",
        "共济会",
        "女协",
        "社会正义",
        "占星术",
        "保守党",
        "共产党",
        "民主党",
        "金钱",
        "女权运动",
        "平等主义",
        "工会"
    ]
    rdviplist = [
        "父亲",
        "母亲",
        "继父",
        "继母",
        "哥哥",
        "弟弟",
        "姐姐",
        "妹妹",
        "儿子",
        "女儿",
        "配偶",
        "前任",
        "青梅竹马",
        "明星",
        "另一位调查员",
        "NPC"
    ]
    rdsigplacelist = [
        "学校（母校）",
        "故乡",
        "相识初恋之处",
        "静思之地",
        "社交之地",
        "联系到信念的地方",
        "重要之人的坟墓",
        "家族的地方",
        "生命中最高兴时所在地",
        "工作地点"
    ]
    rdpreciouslist = [
        "与得意技能相关的某件物品",
        "职业必需品",
        "童年遗留物",
        "逝者遗物",
        "重要之人给予之物",
        "收藏品",
        "发掘而不知真相的东西",
        "体育用品",
        "武器",
        "宠物"
    ]
    rdspecialitylist = [
        "慷慨大方",
        "善待动物",
        "梦想家",
        "享乐主义者",
        "冒险家",
        "好厨子",
        "万人迷",
        "忠心",
        "好名头",
        "雄心壮志"
    ]
    card1.background["faith"] = rdfaithlist[utils.dicemdn(1, len(rdfaithlist))[
        0]-1]
    card1.background["vip"] = rdviplist[utils.dicemdn(1, len(rdviplist))[
        0]-1]
    card1.background["exsigplace"] = rdsigplacelist[utils.dicemdn(
        1, len(rdsigplacelist))[0]-1]
    card1.background["precious"] = rdpreciouslist[utils.dicemdn(
        1, len(rdpreciouslist))[0]-1]
    card1.background["speciality"] = rdspecialitylist[utils.dicemdn(
        1, len(rdspecialitylist))[0]-1]
    utils.writecards(utils.CARDS_DICT)
    rttext = "faith: "+card1.background["faith"]
    rttext += "\nvip: "+card1.background["vip"]
    rttext += "\nexsigplace: "+card1.background["exsigplace"]
    rttext += "\nprecious: "+card1.background["precious"]
    rttext += "\nspeciality: "+card1.background["speciality"]
    update.message.reply_text(rttext)
    return True


def setsex(update: Update, context: CallbackContext) -> bool:
    plid = update.message.from_user.id
    if len(context.args) == 0:
        if utils.isgroupmsg(update):
            utils.addOP(update.effective_chat.id, "setsex "+str(plid))
            update.message.reply_text("请输入性别：")
            return True
        rtbuttons = [[InlineKeyboardButton("男性", callback_data=utils.IDENTIFIER+" setsex male"), InlineKeyboardButton(
            "女性", callback_data=utils.IDENTIFIER+" setsex female"), InlineKeyboardButton("其他", callback_data=utils.IDENTIFIER+" setsex other")]]
        rp_markup = InlineKeyboardMarkup(rtbuttons)
        update.message.reply_text("请选择性别：", reply_markup=rp_markup)
        return True
    card1, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False

    utils.cardsetsex(update, card1, context.args[0])


# setbkground --bkgroundname --bkgroundinfo...: Need at least 2 args


def setbkground(update: Update, context: CallbackContext) -> bool:
    """设置背景信息。

    指令格式如下：
    `/setbkground bkgroundname bkgroudinfo...`

    其中第一个参数是背景的名称，只能是下面几项之一：

    `description`故事、
    `faith`信仰、
    `vip`重要之人、
    `exsigplace`意义非凡之地、
    `precious`珍视之物、
    `speciality`性格特质、
    `dmg`曾经受过的伤、
    `terror`恐惧之物、
    `myth`神秘学相关物品、
    `thirdencounter`第三类接触。

    第二至最后一个参数将被空格连接成为一段文字，填入背景故事中。"""
    plid = update.message.from_user.id
    if len(context.args) <= 1:
        update.message.reply_text(
            "Please use '/setbkground bkgroundname bkgroudinfo' to set background story.")
        return False
    card1, ok = utils.findcard(plid)
    if not ok:
        update.message.reply_text("Can't find card.")
        return False
    if context.args[0] not in card1.background:
        rttext = "Cannot find this background name. The background name should be one of:\n"
        for keys in card1.background:
            rttext += keys+"\n"
        update.message.reply_text(rttext)
        return False
    card1.background[context.args[0]] = ' '.join(context.args[1:])
    utils.writecards(utils.CARDS_DICT)
    update.message.reply_text("Add background story successfully.")
    return True


def sancheck(update: Update, context: CallbackContext) -> bool:
    if utils.isprivatemsg(update):
        update.message.reply_text("Please do san check in a game.")
        return False
    if len(context.args) == 0:
        update.message.reply_text("Need argument.")
        return False
    checkname = context.args[0]
    if checkname.find("/") == -1:
        update.message.reply_text("Seperate your check with a '/'.")
        return False
    checkpass, checkfail = checkname.split(sep='/', maxsplit=1)
    if not utils.isadicename(checkpass) or not utils.isadicename(checkfail):
        update.message.reply_text("Invalid input.")
        return False
    gpid = update.effective_chat.id
    game, ok = utils.findgame(gpid)
    if not ok:
        update.message.reply_text("Please do san check in a game.")
        return False
    # KP 进行
    if update.message.from_user.id == utils.getkpid(gpid):
        card1 = utils.getkpctrl(game)
        if not card1:
            return utils.errorHandler(update, "请先用 /switchkp 切换到你的卡")
    else:  # 玩家进行
        plid = update.message.from_user.id
        card1 = utils.findcardfromgame(game, plid)
        if not card1:
            return utils.errorHandler(update, "找不到卡。")
    rttext = "检定：理智 "
    sanity = card1.attr["SAN"]
    check = utils.dicemdn(1, 100)[0]
    rttext += str(check)+"/"+str(sanity)+" "
    utils.initrules(gpid)
    greatfailrule = utils.GROUP_RULES[gpid].greatfail
    if (sanity < 50 and check >= greatfailrule[2] and check <= greatfailrule[3]) or (sanity >= 50 and check >= greatfailrule[0] and check <= greatfailrule[1]):  # 大失败
        rttext += "大失败"
        anstype = "大失败"
    elif check > sanity:  # check fail
        rttext += "失败"
        anstype = "失败"
    else:
        rttext += ""
        anstype = ""
    rttext += "\n损失理智："
    sanloss, m, n = 0, 0, 0
    if anstype == "大失败":
        if utils.isint(checkfail):
            sanloss = int(checkfail)
        else:
            sanloss = int(checkfail.split("d", maxsplit=1)[
                          0])*int(checkfail.split("d", maxsplit=1)[1])
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
    card1.attr["SAN"] -= sanloss
    rttext += str(sanloss)+"\n"
    if card1.attr["SAN"] <= 0:
        card1.attr["SAN"] = 0
        card1.status = "mad"
        rttext += "陷入永久疯狂，快乐撕卡~\n"
    elif sanloss > (card1.attr["SAN"]+sanloss)//5:
        rttext += "一次损失五分之一以上理智，进入不定性疯狂状态。\n"
    elif sanloss >= 5:
        rttext += "一次损失5点或以上理智，可能需要进行智力（灵感）检定。\n"
    utils.writegameinfo(utils.ON_GAME)
    update.message.reply_text(rttext)
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
            if argname in utils.SKILL_DICT or argname == "母语" or argname == "闪避":
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
    utils.initrules(t["groupid"])
    # 检查是否输入了以及是否有权限输入playerid
    if not utils.isfromkp(update):
        if t["playerid"] != 0 and t["playerid"] != update.effective_chat.id:
            return utils.errorHandler(update, "没有权限设置playerid")
        t["playerid"] = update.effective_chat.id
    else:
        kpid = update.effective_chat.id
        if utils.getkpid(t["groupid"]) != kpid and t["playerid"] != 0 and t["playerid"] != kpid:
            return utils.errorHandler(update, "没有权限设置playerid")
        if t["playerid"] == 0:
            t["playerid"] = kpid
    # 生成成功
    card1 = utils.GameCard(t)
    # 添加id
    addids = utils.getallid()
    if "id" not in context.args or int(context.args[context.args.index("id")+1]) < 0 or card1.id in addids:
        update.message.reply_text("输入了已被占用的id，或id未设置。自动获取id")
        nid = 0
        while nid in addids:
            nid += 1
        card1.id = nid
    # 卡检查
    rttext = utils.showchecks(card1)
    if rttext != "All pass.":
        update.message.reply_text(
            "卡片添加成功，但没有通过开始游戏的检查。")
        update.message.reply_text(rttext)
    else:
        update.message.reply_text("卡片添加成功")
    utils.CARDS_DICT[card1.groupid][card1.id] = card1
    utils.writecards(utils.CARDS_DICT)
    return True


def helper(update: Update, context: CallbackContext) -> True:
    """查看指令对应函数的说明文档。

    `/help --command`查看指令对应的文档。
    `/help`查看所有的指令。"""
    allfuncs = utils.readhandlers()
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
            update.message.reply_text("Markdown格式parse错误，请检查并改写文档")
            return False
        return True
    return utils.errorHandler(update, "找不到这个指令，或这个指令没有帮助信息。")


def textHandler(update: Update, context: CallbackContext) -> bool:
    """信息处理函数，用于无指令的消息处理。
    具体指令处理正常完成时再删除掉当前操作状态`OPERATION[chatid]`，处理出错时不删除。"""
    if update.message.text == "cancel":
        utils.popOP(update.effective_chat.id)
        return True
    oper = utils.getOP(update.effective_chat.id)
    opers = oper.split(" ")
    if oper == "":
        utils.botchat(update)
        return True
    if oper == "newcard":
        return utils.textnewcard(update, context)
    if oper == "setage":
        return utils.textsetage(update, context)
    if oper == "setname":  # 私聊情形
        return utils.textsetname(update, 0)
    if opers[0] == "setname":  # 群消息情形
        return utils.textsetname(update, int(opers[1]))
    if oper == "setsex":
        return utils.textsetsex(update, 0)
    if opers[0] == "setsex":
        return utils.textsetsex(update, int(opers[1]))


def unknown(update: Update, context: CallbackContext) -> None:
    utils.errorHandler(update, "没有这一指令", True)


ALL_HANDLER = globals()
