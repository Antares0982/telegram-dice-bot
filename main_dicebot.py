# -*- coding:utf-8 -*-
# version: 1.0.1

import logging
import asyncio
import signal
import sys
import os
from telegram import Update, error
from telegram.ext import CallbackQueryHandler, MessageHandler, Filters, CommandHandler, CallbackContext

import dicehandlers


dispatcher = dicehandlers.updater.dispatcher

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


async def timer():
    istime = False
    clockhour = 3
    clockmin = 0
    while True:
        nowtime = dicehandlers.time.localtime(dicehandlers.time.time())
        if not istime and nowtime.tm_hour == clockhour and nowtime.tm_min == clockmin:
            dicehandlers.sendtoAdmin("bot自检中！")
            botcheckdata("bot自检中……")
            istime = True
            continue
        if istime:
            if nowtime.tm_min != clockmin:
                istime = False
            await asyncio.sleep(10)
            continue
        await asyncio.sleep(30)


def botcheckdata(msg: str, recall: bool = True):
    """进行一次数据自检，检查是否有群因为升级而id变化了"""
    gpids: dicehandlers.List[int] = []
    for key in dicehandlers.CARDS_DICT:
        gpids.append(key)
    for key in dicehandlers.GROUP_KP_DICT:
        if key not in gpids:
            gpids.append(key)
    for gpid in gpids:
        try:
            sendmsg = dicehandlers.updater.bot.send_message(
                chat_id=gpid, text=msg)
        except error.ChatMigrated as err:
            if gpid in dicehandlers.CARDS_DICT:
                dicehandlers.sendtoAdmin(
                    "群id发生变化，原群id："+str(gpid)+"变化为"+str(err.new_chat_id))
                for game in dicehandlers.ON_GAME:
                    if game.groupid == gpid:
                        game.groupid = err.new_chat_id
                        dicehandlers.writegameinfo(dicehandlers.ON_GAME)
                        break
                dicehandlers.sendtoAdmin("出现问题，强制转移群数据！！！")
                dicehandlers.changecardgpid(gpid, err.new_chat_id)
                dicehandlers.sendtoAdmin("转移群数据完成")
            if gpid in dicehandlers.GROUP_KP_DICT:
                dicehandlers.GROUP_KP_DICT[err.new_chat_id] = dicehandlers.GROUP_KP_DICT.pop(
                    gpid)
                dicehandlers.writekpinfo(dicehandlers.GROUP_KP_DICT)
        except:
            return False
        else:
            if recall:
                sendmsg.delete()
    dicehandlers.sendtoAdmin("自检完成！")
    return True


def bot(update: Update, context: CallbackContext) -> bool:
    """直接控制控制程序的行为。可以直接调用updater。使用方法：

    `/bot stop`将结束程序。

    `/bot restart`将调用`reload`方法重新加载所有数据。"""
    if update.message.from_user.id != dicehandlers.ADMIN_ID:
        return dicehandlers.errorHandler(update, "没有权限", True)
    if len(context.args) == 0:
        return dicehandlers.errorHandler(update, "参数无效", True)
    inst = context.args[0]
    if inst == "check":
        update.message.reply_text("开始数据自检")
        if not botcheckdata("bot自检中……"):
            dicehandlers.sendtoAdmin("出现了未知的错误，请检查报错信息")
            return False
        return True
    if inst == "stop":
        if not botcheckdata("Bot程序终止！", False):
            dicehandlers.sendtoAdmin("出现了未知的错误，请检查报错信息")
        dicehandlers.sendtoAdmin("进程被指令终止。")
        # 结束进程，先写入所有数据
        dicehandlers.writecards(dicehandlers.CARDS_DICT)
        dicehandlers.writecurrentcarddict(dicehandlers.CURRENT_CARD_DICT)
        dicehandlers.writekpinfo(dicehandlers.GROUP_KP_DICT)
        dicehandlers.writegameinfo(dicehandlers.ON_GAME)
        pid = os.getpid()
        if sys.platform == "win32":  # windows
            os.kill(pid, signal.SIGBREAK)
        else:  # Other
            os.kill(pid, signal.SIGKILL)
        return dicehandlers.errorHandler(update, "关闭失败！")
    if inst == "restart":
        return dicehandlers.reload(update, context)
    return dicehandlers.errorHandler(update, "没有这一指令", True)


def main() -> None:
    dispatcher.add_handler(CommandHandler('bot', bot))

    dispatcher.add_handler(CommandHandler('start', dicehandlers.start))
    dispatcher.add_handler(CommandHandler('addkp', dicehandlers.addkp))
    dispatcher.add_handler(CommandHandler(
        'transferkp', dicehandlers.transferkp))
    dispatcher.add_handler(CommandHandler('delkp', dicehandlers.delkp))
    dispatcher.add_handler(CommandHandler('reload', dicehandlers.reload))
    dispatcher.add_handler(CommandHandler(
        'showuserlist', dicehandlers.showuserlist))
    dispatcher.add_handler(CommandHandler('getid', dicehandlers.getid))
    dispatcher.add_handler(CommandHandler('showrule', dicehandlers.showrule))
    dispatcher.add_handler(CommandHandler('setrule', dicehandlers.setrule))
    dispatcher.add_handler(CommandHandler(
        'createcardhelp', dicehandlers.createcardhelp))
    dispatcher.add_handler(CommandHandler('newcard', dicehandlers.newcard))
    dispatcher.add_handler(CommandHandler('discard', dicehandlers.discard))
    dispatcher.add_handler(CommandHandler('details', dicehandlers.details))
    dispatcher.add_handler(CommandHandler('setage', dicehandlers.setage))
    dispatcher.add_handler(CommandHandler('setstrdec', dicehandlers.setstrdec))
    dispatcher.add_handler(CommandHandler('setcondec', dicehandlers.setcondec))
    dispatcher.add_handler(CommandHandler('setjob', dicehandlers.setjob))
    dispatcher.add_handler(CommandHandler(
        'showjoblist', dicehandlers.showjoblist))
    dispatcher.add_handler(CommandHandler('addskill', dicehandlers.addskill))
    dispatcher.add_handler(CommandHandler(
        'showskilllist', dicehandlers.showskilllist))
    dispatcher.add_handler(CommandHandler('setname', dicehandlers.setname))
    dispatcher.add_handler(CommandHandler('startgame', dicehandlers.startgame))
    dispatcher.add_handler(CommandHandler('abortgame', dicehandlers.abortgame))
    dispatcher.add_handler(CommandHandler('endgame', dicehandlers.endgame))
    dispatcher.add_handler(CommandHandler('switch', dicehandlers.switch))
    dispatcher.add_handler(CommandHandler('switchkp', dicehandlers.switchkp))
    dispatcher.add_handler(CommandHandler('tempcheck', dicehandlers.tempcheck))
    dispatcher.add_handler(CommandHandler('roll', dicehandlers.roll))
    dispatcher.add_handler(CommandHandler('show', dicehandlers.show))
    dispatcher.add_handler(CommandHandler('showkp', dicehandlers.showkp))
    dispatcher.add_handler(CommandHandler('showcard', dicehandlers.showcard))
    dispatcher.add_handler(CommandHandler('showids', dicehandlers.showids))
    dispatcher.add_handler(CommandHandler('modify', dicehandlers.modify))
    dispatcher.add_handler(CommandHandler('changeid', dicehandlers.changeid))
    dispatcher.add_handler(CommandHandler(
        'changegroup', dicehandlers.changegroup))
    dispatcher.add_handler(CommandHandler(
        'randombackground', dicehandlers.randombackground))
    dispatcher.add_handler(CommandHandler(
        'setbkground', dicehandlers.setbkground))
    dispatcher.add_handler(CommandHandler('setsex', dicehandlers.setsex))
    dispatcher.add_handler(CommandHandler('sancheck', dicehandlers.sancheck))
    dispatcher.add_handler(CommandHandler('addcard', dicehandlers.addcard))
    dispatcher.add_handler(CommandHandler('help', dicehandlers.helper))
    dispatcher.add_handler(CallbackQueryHandler(dicehandlers.button))
    dispatcher.add_handler(MessageHandler(
        Filters.command, dicehandlers.unknown))
    dicehandlers.updater.start_polling(clean=True)


if __name__ == "__main__":
    main()
    asyncio.run(timer())
