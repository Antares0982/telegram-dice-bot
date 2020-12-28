import numpy as np
import re
from typing import List


def isint(a: str) -> bool:
    try:
        int(a)
    except Exception():
        return False
    return True


def dicemdn(m: int, n: int) -> List[int]:
    ans = np.random.randint(1, n+1, size=m)
    ans = list(map(int, ans))
    return ans


def commondice(dicename) -> str:
    if dicename.find('+')<0:
        if dicename.find('d')<0:
            return "Invalid input."
        dices = dicename.split('d')
        if len(dices)!=2 or not isint(dices[0]) or not isint(dices[1]):
            return "Invalid input."
        ansint = dicemdn(int(dices[0]), int(dices[1]))
        if len(ansint)==0:
            return "Invalid input."
        if len(ansint)==1:
            return dicename+"="+str(ansint[0])
        ans = dicename + "="
        for i in range(len(ansint)):
            if i<len(ansint)-1:
                ans += str(ansint[i])+'+'
            else:
                ans += str(ansint[i])
        return ans
    dicess = dicename.split('+')
    ansint = []
    for i in range(len(dicess)):
        if dicess[i].find('d')<0:
            return "Invalid input."
        dices = dicess.split('d')
        if len(dices)!=2 or not isint(dices[0]) or not isint(dices[1]):
            return "Invalid input."
        ansint+=dicemdn(int(dices[0]), int(dices[1]))
    ans = dicename + "="
    for i in range(len(ansint)):
        if i<len(ansint)-1:
            ans += str(ansint[i])+'+'
        else:
            ans += str(ansint[i])
    return ans

