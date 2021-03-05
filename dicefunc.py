# -*- coding:utf-8 -*-
from typing import List
import numpy as np


def isint(a: str) -> bool:
    try:
        int(a)
    except:
        return False
    return True


def dicemdn(m: int, n: int) -> List[int]:
    if m == 0:
        return []
    if m > 20:
        return []
    ans = np.random.randint(1, n+1, size=m)
    ans = list(map(int, ans))
    return ans


def get3d6str(dtname: str, a: int, b: int, c: int) -> str:
    return dtname+" = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(5*(a+b+c)) + "\n"


def get2d6_6str(dtname: str, a: int, b: int) -> str:
    return dtname+" = 5*(2d6+6) = 5*(" + str(a) + "+" + \
        str(b) + "+6) = " + str(5*(a+b+6)) + "\n"


def commondice(dicename) -> str:
    if dicename.find('+') < 0:
        if dicename.find('d') < 0:
            return "Invalid input."
        dices = dicename.split('d')
        if len(dices) != 2 or not isint(dices[0]) or not isint(dices[1]) or int(dices[0]) > 20:
            return "Invalid input."
        ansint = dicemdn(int(dices[0]), int(dices[1]))
        if len(ansint) == 0:
            return "Invalid input."
        if len(ansint) == 1:
            return dicename+" = "+str(ansint[0])
        ans = dicename + " = "
        for i in range(len(ansint)):
            if i < len(ansint)-1:
                ans += str(ansint[i])+'+'
            else:
                ans += str(ansint[i])
        ans += " = "+str(int(sum(ansint)))
        return ans
    dicess = dicename.split('+')
    ansint: List[int] = []
    for i in range(len(dicess)):
        if dicess[i].find('d') < 0 and not isint(dicess[i]):
            return "Invalid input."
        if isint(dicess[i]):
            ansint.append(int(dicess[i]))
        else:
            dices = dicess[i].split('d')
            if len(dices) != 2 or not isint(dices[0]) or not isint(dices[1]) or int(dices[0]) > 20:
                return "Invalid input."
            ansint += dicemdn(int(dices[0]), int(dices[1]))
    ans = dicename + " = "
    for i in range(len(ansint)):
        if i < len(ansint)-1:
            ans += str(ansint[i])+'+'
        else:
            ans += str(ansint[i])
    ans += " = "+str(int(sum(ansint)))
    return ans


def isadicename(dicename: str) -> bool:
    """判断`dicename`是否是一个可以计算的骰子字符串。

    一个可以计算的骰子字符串应当是类似于这样的字符串：`3`或`3d6`或`2d6+6+1d10`，即单项骰子或数字，也可以是骰子与数字相加"""
    if not isint(dicename):  # 不是数字，先判断是否有'+'
        if dicename.find("+") == -1:  # 没有'+'，判断是否是单项骰子
            if dicename.find("d") == -1:
                return False
            a, b = dicename.split("d", maxsplit=1)
            if not isint(a) or not isint(b):
                return False
            return True
        else:  # 有'+'，split后递归判断是否每一项都是单项骰子
            dices = dicename.split("+")
            for dice in dices:
                if not isadicename(dice):
                    return False
            return True
    # 是数字
    if int(dicename) >= 0:
        return True
    return False