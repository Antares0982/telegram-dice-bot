# coding=utf-8
import json
from typing import Tuple
from cfg import *
from gameclass import *

def writeusergroupinfo(dict1: dict) -> None:
    with open(PATH_USER_GROUP, "w") as f:
        json.dump(dict1, f)


def writekpinfo(dict1: dict) -> None:
    with open(PATH_GROUP_KP, "w") as f:
        json.dump(dict1, f)


def writeplinfo(dict1: dict) -> None:
    with open(PATH_GROUP_PL_CARD, "w") as f:
        json.dump(dict1, f)


def writecards(listofdict) -> None:
    with open(PATH_CARDSLIST, "w") as f:
        json.dump(listofdict, f)


def writegameinfo(listofobj: list[GroupGame]) -> None:
    savelist = []
    for i in range(listofobj):
        newdict = {}
        newdict["groupid"] = listofobj[i].groupid
        newdict["kpid"] = listofobj[i].kpid
        newdict["cards"] = listofobj[i].cards
        savelist.append(newdict)
    with open(PATH_ONGAME, "w") as f:
        json.dump(savelist, f)

def readinfo() -> Tuple(dict, dict, dict, list, list):
    with open(PATH_USER_GROUP, "r") as f:
        usgpdict = json.load(f)
    with open(PATH_GROUP_KP, "r") as f:
        gpkpdict = json.load(f)
    with open(PATH_GROUP_PL_CARD, "r") as f:
        gppldict = json.load(f)
    with open(PATH_CARDSLIST, "r") as f:
        cardslist = json.load(f)
    with open(PATH_ONGAME, "r") as f:
        ongamelistdict = json.load(f)
    ongamelist = []
    for i in range(ongamelistdict):
        ongamelistdict.append(GroupGame(groupid=ongamelistdict[i]["groupid"], kpid=ongamelist[i]["kpid"], cards=ongamelist[i]["cards"]))
    return usgpdict, gpkpdict, gppldict, cardslist, ongamelist

def readskilldict() -> dict:
    with open(PATH_SKILLDICT, 'r') as f:
        d = json.load(f)
    return d