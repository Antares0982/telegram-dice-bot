# -*- coding:utf-8 -*-
from typing import List

import numpy as np


def dicemdn(m: int, n: int) -> List[int]:
    if m == 0:
        return []
    if m > 20:
        return []
    ans = np.random.randint(1, n+1, size=m)
    ans = list(map(int, ans))
    return ans


def isint(a: str) -> bool:
    try:
        int(a)
    except:
        return False
    return True


def get3d6str(dtname: str, a: int, b: int, c: int) -> str:
    """返回`dtname = 5*(3d6) = 5*(a+b+c) = ans`"""
    return dtname+" = 5*(3d6) = 5*(" + str(a) + "+" + str(b) + \
        "+" + str(c) + ") = " + str(5*(a+b+c)) + "\n"


def get2d6_6str(dtname: str, a: int, b: int) -> str:
    """返回`dtname = 5*(2d6+6) = 5*(a+b+6) = ans`"""
    return dtname+" = 5*(2d6+6) = 5*(" + str(a) + "+" + \
        str(b) + "+6) = " + str(5*(a+b+6)) + "\n"


def commondice(dicename) -> str:
    """只能计算含d的表达式，返回完整的表达式以及结果"""
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


def realdiv(a: int, b: int) -> int:
    """解决python负数与正数的整除结果是实际除法结果向下取整的问题"""
    if b == 0:
        raise ValueError
    if b < 0:
        return realdiv(-a, -b)
    if a < 0:
        return -((-a)//b)
    return a//b


def __multdiv(s: str) -> int:
    mu = s.rfind("*")
    di = s.rfind("/")
    if mu == -1 and di == -1:
        return int(s)
    if mu == -1:
        return realdiv(__multdiv(s[:di]), int(s[di+1:]))
    if di == -1:
        return __multdiv(s[:mu])*int(s[mu+1:])
    if mu > di:
        return __multdiv(s[:mu])*int(s[mu+1:])
    return realdiv(__multdiv(s[:di]), int(s[di+1:]))


def __pre(s: str) -> str:
    i = len(s)-1
    while i > 0:
        if s[i] == '-':
            if s[i-1] == '-':
                s = s[:i-1]+'+'+s[i+1:]
                i -= 1
            elif s[i-1] != '+':
                s = s[:i]+"+"+s[i:]
        i -= 1
    return s


def __calstr(s: str) -> str:
    if s.find("(") == -1:
        return str(calculator(s, False))
    i = s.rfind("(")
    j = s[i:].find(")")+i
    return s[:i]+__calstr(s[i+1:j])+s[j+1:]


def calculator(s: str, haveSpace: bool = True) -> int:
    """计算器。除法视为整除"""
    if haveSpace:
        s = "".join(s.split())
    while s.find("(") != -1:
        s = __calstr(s)
    s = __pre(s)
    return sum(map(__multdiv, s.split('+')))
