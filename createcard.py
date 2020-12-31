# coding=utf-8
from telegram.games.game import Game
from gameclass import GameCard
from cfg import *
import numpy as np
from typing import Tuple
from botdicts import readjobdict

JOB_DICT = readjobdict()


def generateNewCard(userid, groupid) -> Tuple[GameCard, str]:
    newcard = {
        "id": -1,
        "playerid": userid,
        "groupid": groupid,
        "data": {

        },
        "info": {
            "classicaljob": True
        },
        "skill": {
            "points": -1
        },
        "interest": {
            
        },
        "suggestskill": {

        },
        "cardcheck": {
            "check1": False,  # 年龄是否设定
            "check2": False,  # str, con, dex等设定是否完成
            "check3": False,  # job是否设定完成
            "check4": False  # skill是否设定完成
        },
        "attr": {

        },
        "background": {
            "description": "",
            "faith": "",
            "vip": "",
            "exsigplace": "",
            "precious": "",
            "speciality": "",
            "dmg": "",
            "terror": "",
            "myth": "",
            "thirdencounter": ""
        },
        "tempstatus": {
            "global": 0
        },
        "item": "",
        "assets": "",
        "type": "PL",
        "discard": False,
        "status": "alive"
    }
    card = GameCard(newcard)
    text = ""
    a, b, c = np.random.randint(1, 7, size=3)
    STR = int(5*(a+b+c))
    text += "STR = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(STR) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    CON = int(5*(a+b+c))
    text += "CON = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(CON) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    SIZ = int(5*(a+b+6))
    text += "SIZ = 5*(2d6+6) = 5*(" + str(a) + "+" + \
        str(b) + "+6) = " + str(SIZ) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    DEX = int(5*(a+b+c))
    text += "DEX = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(DEX) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    APP = int(5*(a+b+c))
    text += "APP = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(APP) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    INT = int(5*(a+b+6))
    text += "INT = 5*(2d6+6) = 5*(" + str(a) + "+" + \
        str(b) + "+6) = " + str(INT) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    POW = int(5*(a+b+c))
    text += "POW = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(POW) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    EDU = int(5*(a+b+6))
    text += "EDU = 5*(2d6+6) = 5*(" + str(a) + "+" + str(b) + "+6) = " + str(EDU)
    card.data["STR"] = STR
    card.data["CON"] = CON
    card.data["SIZ"] = SIZ
    card.data["DEX"] = DEX
    card.data["APP"] = APP
    card.data["INT"] = INT
    card.data["POW"] = POW
    card.data["EDU"] = EDU
    card.interest["points"] = INT*2
    return card, text


def generateAgeAttributes(card: GameCard) -> Tuple[GameCard, str]:
    if "AGE" not in card.info:  # This trap should not be hit
        return card, "Attribute: AGE is NONE, please set AGE first"
    AGE = card.info["AGE"]
    luck = int(5*sum(np.random.randint(1, 7, size=3)))
    rttext = ""
    if AGE < 20:
        luck2 = int(5*sum(np.random.randint(1, 7, size=3)))
        if luck < luck2:
            card.data["LUCK"] = luck2
        else:
            card.data["LUCK"] = luck
        rttext += "年龄低于20，幸运得到奖励骰。结果分别为"+str(luck)+", "+str(luck2)+"。教育减5，力量体型合计减5。"
        card.data["STR_SIZ_M"] = -5
        card.data["EDU"] -= 5
    elif AGE < 40:
        card.cardcheck["check2"] = True  # No STR decrease, check2 passes
        rttext += "年龄20-39，得到一次教育增强。"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升，现在教育："
            card.data["EDU"] += a
            rttext += str(card.data["EDU"])+"。"
        else:
            rttext += "检定增强："+str(int(5*(a+b+6)))+"失败，现在教育：" + \
                str(card.data["EDU"])+"。"
    elif AGE < 50:
        rttext += "年龄40-49，得到两次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_M"] = -5
        card.data["APP"] -= 5
        rttext += "力量体质合计减5，外貌减5。\n"
    elif AGE < 60:
        rttext += "年龄50-59，得到三次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -10
        card.data["APP"] -= 10
        rttext += "力量体质敏捷合计减10，外貌减10。\n"
    elif AGE < 70:
        rttext += "年龄60-69，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -20
        card.data["APP"] -= 15
        rttext += "力量体质敏捷合计减20，外貌减15。\n"
    elif AGE < 80:
        rttext += "年龄70-79，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -40
        card.data["APP"] -= 20
        rttext += "力量体质敏捷合计减40，外貌减20。\n"
    else:
        rttext += "年龄80以上，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card.data["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card.data["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card.data["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card.data["EDU"])+"。\n"
        card.data["STR_CON_DEX_M"] = -80
        card.data["APP"] -= 25
        rttext += "力量体质敏捷合计减80，外貌减25。\n"
    if AGE >= 20:
        card.data["LUCK"] = luck
        rttext += "幸运："+str(luck)+"\n"
    rttext += "使用 /setjob 进行职业设定。完成职业设定之后，用'/addskill 技能名 技能点数' 来分配技能点，用空格分隔。"
    return card, rttext


def choosedec(card: GameCard, strength: int) -> Tuple[GameCard, str, bool]: # If returns "输入无效", card should not be edited
    if card.data["STR"] <= strength:
        return card, "输入无效", False
    card.data["STR"] -= strength # Add it back if "HIT BAD TRAP"
    needCON = False
    rttext = "力量减"+str(strength)+"点，"
    if "STR_SIZ_M" in card.data:  # AGE less than 20
        if strength > -card.data["STR_SIZ_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        card.data["SIZ"] += card.data["STR_SIZ_M"]+strength
        rttext += "体型减"+str(-card.data["STR_SIZ_M"]-strength)+"点。"
        card.data.pop("STR_SIZ_M")
        card.cardcheck["check2"] = True  # No other decrease, check2 passes
    elif "STR_CON_M" in card.data:
        if strength > -card.data["STR_CON_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        card.data["CON"] += card.data["STR_CON_M"]+strength
        rttext += "体质减"+str(-card.data["STR_CON_M"]-strength)+"点。"
        card.data.pop("STR_SIZ_M")
        card.cardcheck["check2"] = True  # No other decrease, check2 passes
    elif "STR_CON_DEX_M" in card.data:
        if strength > -card.data["STR_CON_DEX_M"]:
            card.data["STR"] += strength
            return card, "输入无效", False
        if not strength == -card.data["STR_CON_DEX_M"]:
            needCON = True
            card.data["CON_DEX_M"] = card.data["STR_CON_DEX_M"]+strength
        rttext += "体质敏捷合计减"+str(-card.data["CON_DEX_M"])+"点。"
        card.data.pop("STR_CON_DEX_M")
    else:
        return card, "输入无效", False
    return card, rttext, needCON


def choosedec2(card: dict, con: int) -> Tuple[dict, str]:
    if card.data["CON"] <= con or "CON_DEX_M" not in card.data:
        return card, "输入无效", False
    card.data["CON"] -= con
    rttext = "体质减"+str(con)+"点，"
    if con > -card.data["CON_DEX_M"]:
        card.data["CON"] += con
        return card, "输入无效"
    card.data["DEX"] += card.data["CON_DEX_M"]+con
    rttext += "敏捷减"+str(-card.data["CON_DEX_M"]-con)+"点。"
    card.data.pop("CON_DEX_M")
    card.cardcheck["check2"] = True
    return card, rttext


def generateOtherAttributes(card: GameCard) -> Tuple[GameCard, str]:
    if not card.cardcheck["check2"]:  # This trap should not be hit
        return card, "Please set DATA decrease first"
    card.attr["SAN"] = card.data["POW"]
    card.attr["MAXSAN"] = card.data["POW"]
    card.attr["MAGIC"] = card.data["POW"]//5
    card.attr["MAXLP"] = (card.data["SIZ"]+card.data["CON"])//10
    card.attr["LP"] = card.attr["MAXLP"]
    rttext = "SAN: " + str(card.attr["SAN"])+"\n"
    rttext += "MAGIC: " + str(card.attr["MAGIC"])+"\n"
    rttext += "LP: " + str(card.attr["LP"])+"\n"
    if card.data["STR"]+card.data["SIZ"] < 65:
        card.attr["physique"] = -2
    elif card.data["STR"]+card.data["SIZ"] < 85:
        card.attr["physique"] = -1
    elif card.data["STR"]+card.data["SIZ"] < 125:
        card.attr["physique"] = 0
    elif card.data["STR"]+card.data["SIZ"] < 165:
        card.attr["physique"] = 1
    elif card.data["STR"]+card.data["SIZ"] < 205:
        card.attr["physique"] = 2
    else:
        card.attr["physique"] = 2+(card.data["STR"]+card.data["SIZ"]-125)//80
    if card.attr["physique"] <= 0:
        card.attr["DB"] = str(card.attr["physique"])
    elif card.attr["physique"] == 1:
        card.attr["DB"] = "1d4"
    else:
        card.attr["DB"] = str(card.attr["physique"]-1)+"d6"
    rttext += "physique: " + str(card.attr["physique"])+"\n"
    return card, rttext


def generatePoints(card: GameCard, job: str):
    if job not in JOB_DICT:
        return False
    ptrule = JOB_DICT[job][2]
    pt = 0
    for keys in ptrule:
        if keys in card.data:
            pt += card.data[keys]*ptrule[keys]
        elif keys[:3] in card.data and keys[4:] in card.data:
            pt += max(card.data[keys[:3]], card.data[keys[4:]])*ptrule[keys]
        else:
            return False
    card.skill["points"] = int(pt)
    return True


def checkcard(card: GameCard) -> bool:
    if "AGE" in card.info:
        card.cardcheck["check1"] = True
    if not card.cardcheck["check1"]:
        return False
    if "STR_SIZ_M" in card.data or "STR_CON_DEX_M" in card.data or "STR_CON_M" in card.data or "CON_DEX_M" in card.data:
        return False
    card.cardcheck["check2"] = True
    if "job" not in card.info:
        return False
    card.cardcheck["check3"] = True
    if card.skill["points"] != 0:
        return False
    if card.interest["points"] != 0:
        return False
    card.cardcheck["check4"] = True
    return True


def showchecks(card: GameCard) -> str:
    if checkcard(card):
        return "All pass."
    rttext = ""
    for keys in card.cardcheck:
        if not card.cardcheck[keys]:
            rttext += keys+": False\n"
    return rttext
