# -*- coding:utf-8 -*-

from typing import Any, Dict
from typing import overload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.callbackquery import CallbackQuery

from cfg import *
from gameclass import Group, Player

# Update相关


def isint(a: str) -> bool:
    try:
        int(a)
    except:
        return False
    return True


def getchatid(update: Update) -> int:
    """返回effective_chat.id"""
    return update.effective_chat.id


def getmsgfromid(update: Update) -> int:
    """返回message.from_user.id"""
    return update.message.from_user.id


def isprivatemsg(update: Update) -> bool:
    return update.effective_chat.type == "private"


def isgroupmsg(update: Update) -> bool:
    return update.effective_chat.type.find("group") != -1


def ischannel(update: Update) -> bool:
    return update.effective_chat.type == "channel"


def popallempties(d: Dict[Any, dict]) -> bool:
    """将二层字典中一层的空值对应的键删除。如果有空值，返回True，否则返回False"""
    ans: bool = False
    for key in d:
        if not d[key]:
            ans = True
            d.pop(key)
    return ans


def isingroup(gp: Group, pl: Player) -> bool:
    """查询某个pl是否在群里"""
    if gp.chat is None:
        return False
    try:
        gp.chat.get_member(user_id=pl.id)
    except:
        return False
    return True


def isadmin(update: Update, userid: int) -> bool:
    """检测发消息的人是不是群管理员"""
    if isprivatemsg(update):
        return False
    admins = update.effective_chat.get_administrators()
    for admin in admins:
        if admin.user.id == userid:
            return True
    return False


def ispladmin(gp: Group, pl: Player) -> bool:
    """检测pl是不是gp的管理员"""
    admins = gp.chat.get_administrators()
    for admin in admins:
        if admin.user.id == pl.id:
            return True
    return False


def recallmsg(update: Update) -> bool:
    """撤回群消息。如果自己不是管理员，不做任何事"""
    if isprivatemsg(update) or not isadmin(update, BOT_ID):
        return False
    update.message.delete()
    return True


def errorHandler(update: Update,  message: str, needrecall: bool = False) -> False:
    """指令无法执行时，调用的函数。
    固定返回`False`，并回复错误信息。
    如果`needrecall`为`True`，在Bot是对应群管理的情况下将删除那条消息。"""
    if ischannel(update):
        return False

    if needrecall and isgroupmsg(update) and isadmin(update, BOT_ID):
        recallmsg(update)
    else:
        if message == "找不到卡。":
            message += "请使用 /switch 切换当前操控的卡再试。"
        elif message.find("参数") != -1:
            message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"

        try:
            msg = update.message.reply_text(message, parse_mode="MarkdownV2")
        except:
            msg = update.message.reply_text(message)

        if message.find("私聊") != -1:
            rtbutton = [[InlineKeyboardButton(
                "跳转到私聊", callback_data="None", url="t.me/"+BOTUSERNAME)]]
            rp_markup = InlineKeyboardMarkup(rtbutton)
            msg.edit_reply_markup(reply_markup=rp_markup)

    return False


def errorHandlerQ(query: CallbackQuery,  message: str) -> False:
    if message == "找不到卡。":
        message += "请使用 /switch 切换当前操控的卡再试。"
    elif message.find("参数") != -1:
        message += "\n如果不会使用这个指令，请使用帮助： `/help --command`"

    try:
        query.edit_message_text(message, parse_mode="MarkdownV2")
    except:
        query.edit_message_text(message)

    return False


def istrueconsttype(val) -> bool:
    """如果val是int, str, bool才返回True"""
    return isinstance(val, int) or isinstance(val, str) or isinstance(val, bool)


def isconsttype(val) -> bool:
    if istrueconsttype(val):
        return True
    if isinstance(val, list):
        for e in val:
            if not isconsttype(e):
                return False
        return True
    if isinstance(val, dict):
        for k in val:
            v = val[k]
            if not isconsttype(v) or not isconsttype(k):
                return False
        return True
    return False


def isallkeyint(d: dict) -> bool:
    for key in d:
        if not isint(key):
            return False
    return True


def turnkeyint(d: dict) -> Dict[int, Any]:
    dd: Dict[int, Any] = {}
    for key in d:
        dd[int(key)] = d[key]
    return dd


def tobool(x: str) -> bool:
    if x in ["F", "false", "False", "假"]:
        return False
    elif x in ["T", "true", "True", "真"]:
        return True
    raise TypeError("不是可识别的bool")


def plainNewCard() -> dict:
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
        },
        "info": {
        },
        "skill": {
            "points": -1
        },
        "interest": {

        },
        "suggestskill": {

        },
        "attr": {
            "build": -10,
            "DB": "",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "0/0",
            "Armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "viplace": "",
            "preciousthing": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": [],
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    return t


def templateNewCard() -> dict:
    """NPC/怪物的卡模板"""
    t = {
        "id": -1,
        "playerid": 0,
        "groupid": 0,
        "data": {
            "STR": 0,
            "CON": 0,
            "SIZ": 0,
            "DEX": 0,
            "APP": 0,
            "INT": 0,
            "POW": 0,
            "EDU": 0,
            "LUCK": 0
        },
        "info": {
            "AGE": 0,
            "job": "",
            "name": "",
            "sex": ""
        },
        "skill": {
            "points": 0
        },
        "interest": {
            "points": 0
        },
        "suggestskill": {

        },
        "attr": {
            "SAN": 0,
            "MAXSAN": 99,
            "MAGIC": 0,
            "MAXLP": 0,
            "LP": 0,
            "build": -10,
            "DB": "",
            "MOV": 0,
            "atktimes": 1,
            "sandown": "1/1d6",
            "armor": ""
        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "viplace": "",
            "preciousthing": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "GLOBAL": 0
        },
        "item": [],
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive",
        "isgamecard": False
    }
    return t
