# coding=utf-8
import json
from cfg import *



def writeuserinfo(dict1):
    with open(PATH_USER, "w") as f:
        json.dump(dict1, f)


def writegroupinfo(dict1):
    with open(PATH_GROUP, "w") as f:
        json.dump(dict1, f)


def writeusergroupinfo(dict1):
    with open(PATH_USER_GROUP, "w") as f:
        json.dump(dict1, f)


def writekpinfo(dict1):
    with open(PATH_GROUP_KP, "w") as f:
        json.dump(dict1, f)


def writeplinfo(dict1):
    with open(PATH_GROUP_PL_CARD, "w") as f:
        json.dump(dict1, f)


def readinfo():
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
    return usdict, gpdict, usgpdict, gpkpdict, gppldict
