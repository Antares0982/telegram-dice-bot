# coding=utf-8
from cfg import *
import numpy as np

def generateNewCard(userid, groupid) -> tuple(dict, str):
    card = {
        "player":{
            "playerid":userid
            #"playername" : USER_DICT[userid]
        },
        "group" : {
            "groupid" : groupid
            #"groupname" : GROUP_DICT[groupid]
        },
        "data" : {

        }
    }
    text = ""
    a, b, c = np.random.randint(1, 6), np.random.randint(1, 6), np.random.randint(1, 6)
    STR = 5*(a+b+c)
    text += "STR = 3d6 = " + str(a) + "+" + str(b) + "+" + str(c) + "=" +str(STR) + "\n"
    a, b, c = np.random.randint(1, 6), np.random.randint(1, 6), np.random.randint(1, 6)
    CON = 5*(a+b+c)
    text += "CON = 3d6 = " + str(a) + "+" + str(b) + "+" + str(c) + "=" +str(CON) + "\n"
    a, b = np.random.randint(1, 6), np.random.randint(1, 6)
    SIZ = 5*(a+b+6)
    text += "SIZ = 2d6+6 = " + str(a) + "+" + str(b) + "+6=" +str(SIZ) +"\n"
    a, b, c = np.random.randint(1, 6), np.random.randint(1, 6), np.random.randint(1, 6)
    DEX = 5*(a+b+c)
    text += "DEX = 3d6 = " + str(a) + "+" + str(b) + "+" + str(c) + "=" +str(DEX) + "\n"
    a, b, c = np.random.randint(1, 6), np.random.randint(1, 6), np.random.randint(1, 6)
    APP = 5*(a+b+c)
    text += "APP = 3d6 = " + str(a) + "+" + str(b) + "+" + str(c) + "=" +str(APP) + "\n"
    a, b = np.random.randint(1, 6), np.random.randint(1, 6)
    INT = 5*(a+b+6)
    text += "INT = 2d6+6 = " + str(a) + "+" + str(b) + "+6=" +str(INT) +"\n"
    a, b, c = np.random.randint(1, 6), np.random.randint(1, 6), np.random.randint(1, 6)
    POW = 5*(a+b+c)
    text += "POW = 3d6 = " + str(a) + "+" + str(b) + "+" + str(c) + "=" +str(POW) + "\n"
    a, b = np.random.randint(1, 6), np.random.randint(1, 6)
    EDU = 5*(a+b+6)
    text += "EDU = 2d6+6 = " + str(a) + "+" + str(b) + "+6=" +str(EDU) +"\n"
    card["data"]["STR"]=STR
    card["data"]["CON"]=CON
    card["data"]["SIZ"]=SIZ
    card["data"]["DEX"]=DEX
    card["data"]["APP"]=APP
    card["data"]["INT"]=INT
    card["data"]["POW"]=POW
    card["data"]["EDU"]=EDU
    card["derived"]={}
    return card, text
    
def generateOtherAttributes(card : dict) -> str:
    if "age" not in card["data"]:
        return "Attribute: AGE is NONE, please set AGE first"
    AGE = card["data"]["age"]
    rttext = ""
    if AGE<20:
        newluck = 5*(np.random.randint(1, 6)+np.random.randint(1, 6)+np.random.randint(1, 6))
        if card["data"]["LUCK"]<newluck:
            card["data"]["LUCK"]=newluck
            rttext+="年龄低于20，幸运已经重骰，现在幸运值："+str(newluck)+"。教育减5，力量体型合计减5"
        else:
            card["data"]["LUCK"]
            rttext+="年龄低于20，幸运重骰低于原始值。教育减5，力量体型合计减5"
        card["data"]["STR_SIZ_M"]=-5
        card["data"]["EDU"]-=5
    elif AGE<40:
        pass