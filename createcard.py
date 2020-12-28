# coding=utf-8
from cfg import *
import numpy as np
from typing import Tuple


def generateNewCard(userid, groupid) -> Tuple[dict, str]:
    card = {
        "player": {
            "playerid": userid
        },
        "group": {
            "groupid": groupid
        },
        "data": {

        },
        "info": {

        },
        "skill": {

        },
        "cardcheck": {
            "check1": False,
            "check2": False,
            "check3": False
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

        },
        "item": {

        },
        "assets": {

        },
        "type": {

        },
        "discard": False,
        "status": "alive"
    }
    text = ""
    a, b, c = np.random.randint(1, 7, size=3)
    STR = int(5*(a+b+c))
    text += "STR = 5*(3d6) = " + str(a) + "+" + str(b) + \
        "+" + str(c) + " = " + str(STR) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    CON = int(5*(a+b+c))
    text += "CON = 5*(3d6) = " + str(a) + "+" + str(b) + \
        "+" + str(c) + " = " + str(CON) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    SIZ = int(5*(a+b+6))
    text += "SIZ = 5*(2d6+6) = " + str(a) + "+" + str(b) + "+6 = " + str(SIZ) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    DEX = int(5*(a+b+c))
    text += "DEX = 5*(3d6) = " + str(a) + "+" + str(b) + \
        "+" + str(c) + " = " + str(DEX) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    APP = int(5*(a+b+c))
    text += "APP = 5*(3d6) = " + str(a) + "+" + str(b) + \
        "+" + str(c) + " = " + str(APP) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    INT = int(5*(a+b+6))
    text += "INT = 5*(2d6+6) = " + str(a) + "+" + str(b) + "+6 = " + str(INT) + "\n"
    a, b, c = np.random.randint(1, 7, size=3)
    POW = int(5*(a+b+c))
    text += "POW = 5*(3d6) = " + str(a) + "+" + str(b) + \
        "+" + str(c) + " = " + str(POW) + "\n"
    a, b = np.random.randint(1, 7, size=2)
    EDU = int(5*(a+b+6))
    text += "EDU = 5*(2d6+6) = " + str(a) + "+" + str(b) + "+6 = " + str(EDU)
    card["data"]["STR"] = STR
    card["data"]["CON"] = CON
    card["data"]["SIZ"] = SIZ
    card["data"]["DEX"] = DEX
    card["data"]["APP"] = APP
    card["data"]["INT"] = INT
    card["data"]["POW"] = POW
    card["data"]["EDU"] = EDU
    card["info"] = {}
    card["derived"] = {}
    return card, text


def generateOtherAttributes(card: dict) -> Tuple[dict, str]:
    if "AGE" not in card["info"]:
        return card, "Attribute: AGE is NONE, please set AGE first"
    AGE = card["info"]["AGE"]
    luck = int(5*sum(np.random.randint(1, 7, size=3)))
    rttext = ""
    if AGE < 20:
        card["cardcheck"]["check2"] = True
        luck2 = int(5*sum(np.random.randint(1, 7, size=3)))
        if luck < luck2:
            card["data"]["LUCK"] = luck2
        else:
            card["data"]["LUCK"] = luck
        rttext += "年龄低于20，幸运两次骰子结果分别为"+luck+", "+luck2+"。教育减5，力量体型合计减5。"
        card["data"]["STR_SIZ_M"] = -5
        card["data"]["EDU"] -= 5
    elif AGE < 40:
        card["cardcheck"]["check2"] = True
        rttext += "年龄20-39，得到一次教育增强。"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升，现在教育："
            card["data"]["EDU"] += a
            rttext += str(card["data"]["EDU"])+"。"
        else:
            rttext += "检定增强："+str(int(5*(a+b+6)))+"失败，现在教育：" + \
                str(card["data"]["EDU"])+"。"
    elif AGE < 50:
        rttext += "年龄40-49，得到两次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card["data"]["EDU"])+"。\n"
        card["data"]["STR_CON_M"] = -5
        card["data"]["APP"] -= 5
        rttext += "力量体质合计减5，外貌减5。\n"
    elif AGE < 60:
        rttext += "年龄50-59，得到三次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card["data"]["EDU"])+"。\n"
        card["data"]["STR_CON_DEX_M"] = -10
        card["data"]["APP"] -= 10
        rttext += "力量体质敏捷合计减10，外貌减10。\n"
    elif AGE < 70:
        rttext += "年龄60-69，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card["data"]["EDU"])+"。\n"
        card["data"]["STR_CON_DEX_M"] = -20
        card["data"]["APP"] -= 15
        rttext += "力量体质敏捷合计减20，外貌减15。\n"
    elif AGE < 80:
        rttext += "年龄70-79，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card["data"]["EDU"])+"。\n"
        card["data"]["STR_CON_DEX_M"] = -40
        card["data"]["APP"] -= 20
        rttext += "力量体质敏捷合计减40，外貌减20。\n"
    else:
        rttext += "年龄80以上，得到四次教育增强。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第一次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第二次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第三次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        a, b = np.random.randint(1, 7, size=2)
        if int(5*(a+b+6)) > card["data"]["EDU"]:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"成功，获得"
            a = min(99-card["data"]["EDU"], np.random.randint(1, 11))
            rttext += str(a)+"点提升。\n"
            card["data"]["EDU"] += a
        else:
            rttext += "第四次检定增强："+str(int(5*(a+b+6)))+"失败。\n"
        rttext += "现在教育："+str(card["data"]["EDU"])+"。\n"
        card["data"]["STR_CON_DEX_M"] = -80
        card["data"]["APP"] -= 25
        rttext += "力量体质敏捷合计减80，外貌减25。\n"
    if AGE >= 20:
        card["data"]["LUCK"] = luck
        rttext += "幸运："+str(luck)+"\n"
    rttext += "使用 /setjob 进行职业设定。完成职业设定之后，用'/addskill 技能名 技能点数' 来分配技能点，用空格分隔。"
    return card, rttext


def choosedec(card: dict, strength: int) -> Tuple[dict, str, bool]:
    card["data"]["STR"] -= strength
    needCON = False
    rttext = "力量减"+str(strength)+"点，"
    if "STR_SIZ_M" in card["data"]:
        if strength > -card["data"]["STR_SIZ_M"]:
            card["data"]["STR"] += strength
            return card, "输入无效", False
        card["data"]["SIZ"] += card["data"]["STR_SIZ_M"]+strength
        rttext += "体型减"+str(-card["data"]["STR_SIZ_M"]-strength)+"点。"
        card["data"]["STR_SIZ_M"] = 0
        card["cardcheck"]["check2"] = True
    elif "STR_CON_M" in card["data"]:
        if strength > -card["data"]["STR_CON_M"]:
            card["data"]["STR"] += strength
            return card, "输入无效", False
        card["data"]["CON"] += card["data"]["STR_CON_M"]+strength
        rttext += "体质减"+str(-card["data"]["STR_CON_M"]-strength)+"点。"
        card["data"]["STR_CON_M"] = 0
        card["cardcheck"]["check2"] = True
    elif "STR_CON_DEX_M" in card["data"]:
        if strength > -card["data"]["STR_CON_DEX_M"]:
            card["data"]["STR"] += strength
            return card, "输入无效", False
        card["data"]["CON_DEX_M"] = card["data"]["STR_CON_DEX_M"]+strength
        rttext += "体质敏捷合计减"+str(-card["data"]["CON_DEX_M"])+"点。"
        card["data"]["STR_CON_DEX_M"] = 0
        needCON = True
    return card, rttext, needCON


def choosedec2(card: dict, con: int) -> Tuple[dict, str]:
    card["data"]["CON"] -= con
    rttext = "体质减"+str(con)+"点，"
    if con > -card["data"]["CON_DEX_M"]:
        card["data"]["CON"] += con
        return card, "输入无效"
    card["data"]["DEX"] += card["data"]["CON_DEX_M"]+con
    rttext += "敏捷减"+str(-card["data"]["CON_DEX_M"]-con)+"点。"
    card["data"]["CON_DEX_M"] = 0
    card["cardcheck"]["check2"] = True
    return card, rttext


def generatePoints():
    pass


def checkcard(card: dict) -> bool:
    if "skill" not in card:
        return False
    if "points" not in card["skill"]:
        return False
    if card["skill"]["points"] != 0:
        return False
    return True
