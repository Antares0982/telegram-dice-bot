# coding=utf-8
import json
from typing import Tuple
from cfg import *


def writeuserinfo(dict1: dict) -> None:
    with open(PATH_USER, "w") as f:
        json.dump(dict1, f)


def writegroupinfo(dict1: dict) -> None:
    with open(PATH_GROUP, "w") as f:
        json.dump(dict1, f)


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


def readinfo() -> Tuple(dict, dict, dict, dict, dict, list):
    with open(PATH_USER, "r") as f:
        usdict = json.load(f)
    with open(PATH_GROUP, "r") as f:
        gpdict = json.load(f)
    with open(PATH_USER_GROUP, "r") as f:
        usgpdict = json.load(f)
    with open(PATH_GROUP_KP, "r") as f:
        gpkpdict = json.load(f)
    with open(PATH_GROUP_PL_CARD, "r") as f:
        gppldict = json.load(f)
    with open(PATH_CARDSLIST, "r") as f:
        cardslist = json.load(f)
    return usdict, gpdict, usgpdict, gpkpdict, gppldict, cardslist
