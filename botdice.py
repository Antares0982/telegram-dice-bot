import numpy as np
from typing import List


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
    ansint = []
    for i in range(len(dicess)):
        if dicess[i].find('d') < 0:
            return "Invalid input."
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
