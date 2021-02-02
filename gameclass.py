# -*- coding:utf-8 -*-
from typing import List, Dict, Tuple
import copy


class GameCard:
    def __init__(self, cardinfo: dict):
        self.id: int = 0
        self.playerid: int = 0
        self.groupid: int = 0
        self.data: dict = {}
        self.info: dict = {}
        self.skill: dict = {}
        self.interest: dict = {}
        self.suggestskill: dict = {}
        self.cardcheck: dict = {}
        self.attr: dict = {}
        self.background: dict = {}
        self.tempstatus: dict = {}
        self.item: str = ""
        self.assets: str = ""
        self.type: str = ""
        self.discard: bool = False
        self.status: str = ""
        self.__dict__ = copy.deepcopy(cardinfo)

    def __str__(self):
        rttext: str = ""
        rttext += "id: "+str(self.id)+"\n"
        rttext += "playerid: "+str(self.playerid)+"\n"
        rttext += "groupid: "+str(self.groupid)+"\n"
        rttext += "基础数值: "+"\n"
        for keys in self.data:
            rttext += keys+": "+str(self.data[keys])+"\n"
        rttext += "信息: "+"\n"
        for keys in self.info:
            rttext += keys+": "+str(self.info[keys])+"\n"
        rttext += "技能: "+"\n"
        for keys in self.skill:
            rttext += keys+": "+str(self.skill[keys])+"\n"
        rttext += "兴趣技能: "+"\n"
        for keys in self.interest:
            rttext += keys+": "+str(self.interest[keys])+"\n"
        rttext += "建议技能: "+"\n"
        for keys in self.suggestskill:
            rttext += keys+": "+str(self.suggestskill[keys])+"\n"
        rttext += "角色卡检查: "+"\n"
        for keys in self.cardcheck:
            rttext += keys+": "+str(self.cardcheck[keys])+"\n"
        rttext += "其他属性: "+"\n"
        for keys in self.attr:
            rttext += keys+": "+str(self.attr[keys])+"\n"
        rttext += "背景故事: "+"\n"
        for keys in self.background:
            rttext += keys+": "+str(self.background[keys])+"\n"
        rttext += "临时检定加成: "+"\n"
        for keys in self.tempstatus:
            rttext += keys+": "+str(self.tempstatus[keys])+"\n"
        rttext += "物品: "+self.item+"\n"
        rttext += "资产: "+self.assets+"\n"
        rttext += "角色类型: "+self.type+"\n"
        rttext += "可删除: "
        if self.discard:
            rttext += "是\n"
        else:
            rttext += "否\n"
        rttext += "状态: "+self.status+"\n"
        return rttext


class GroupGame:  # If defined, game is started.
    def __init__(self, groupid, cards: List[dict] = None, kpid: int = None):
        if isinstance(groupid, dict):
            self.groupid: int = groupid["groupid"]
            self.kpid: int = groupid["kpid"]
            self.kpctrl: int = groupid["kpctrl"]
            self.tpcheck: int = groupid["tpcheck"]
            self.gamerule: GroupRule = GroupRule(groupid["gamerule"])
            tpcardslist = groupid["cards"]
            self.cards = []
            for i in tpcardslist:
                self.cards.append(GameCard(i))
            del tpcardslist
        else:
            self.groupid: int = groupid  # Unique, should not be edited after initializing
            self.kpid: int = kpid  # Can be edited
            self.cards: List[GameCard] = []  # list of GameCard
            for i in cards:
                self.cards.append(GameCard(i))
            self.kpctrl: int = -1
            self.tpcheck: int = 0
            self.gamerule: GroupRule = GroupRule()
        self.kpcards: List[GameCard] = []
        for i in self.cards:
            if i.playerid == self.kpid:
                self.kpcards.append(i)

    def __str__(self):
        rttext = ""
        for keys in self.__dict__:
            if keys == "cards" or keys == "kpcards":
                continue
            rttext += keys+": "+str(self.__dict__[keys])+"\n"
        rttext += "游戏中卡共有"+str(len(self.cards)) + \
            "张，其中kp所持卡共有"+str(len(self.kpcards))+"张"
        return rttext


class GroupRule:
    def __init__(self, rules: Dict[str, List[int]] = {}):  # 不允许用户调用
        # 0位参数描述一般技能上限，1位参数描述专精技能上限，2位参数描述专精技能个数。上限<=99
        self.skillmax: List[int] = [80, 90, 1]
        # 0位描述一般技能上限，1位描述专精技能上限，2位描述专精技能个数，3位描述至少到什么年龄才能使用此设置，如果没有设置的话默认100
        self.skillmaxAged: List[int] = [80, 90, 1, 100]
        # 1,3,5……位描述技能分段位置，单调递增，最后一个数必须是100。在大于skillCost[2*i-1]但小于等于skillCost[2*i+1]时，每一技能点花费skillCost[2*i]
        self.skillCost: List[int] = [1, 100]
        # 在检定需要骰出大于等于50时，greatsuccess[0]~greatsuccess[1]算大成功，否则greatsuccess[3]~greatsuccess[4]算大成功
        self.greatsuccess: List[int] = [1, 1, 1, 1]
        # 在检定需要骰出大于等于50时，greatfail[0]~greatfail[1]算大失败，否则greatfail[3]~greatfail[4]算大失败
        self.greatfail: List[int] = [100, 100, 96, 100]
        for key in rules:
            self.__dict__[key] = rules[key]

    def changeRules(self, cgrules: Dict[str, List[int]]) -> Tuple[str, bool]:
        rttext: str = ""
        for key in cgrules:
            if key == "skillmax":
                if len(cgrules[key]) != 3:
                    return "skillmax 参数长度有误", False
                if cgrules[key][2] > 20:
                    return "skillmax 专精技能个数太多", False
                if cgrules[key][0] < 0 or cgrules[key][1] <= cgrules[key][0] or cgrules[key][1] >= 100 or cgrules[key][2] < 0:
                    return "skillmax 参数有误", False
                rttext += "skillmax设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "skillmaxAged":
                if len(cgrules[key]) != 4:
                    return "skillmaxAged 参数长度有误", False
                if cgrules[key][2] > 20:
                    return "skillmaxAged 专精技能个数太多", False
                if cgrules[key][0] < 0 or cgrules[key][1] <= cgrules[key][0] or cgrules[key][1] >= 100 or cgrules[key][2] < 0 or cgrules[key][3] < 17 or cgrules[key][3] > 100:
                    return "skillmaxAged 参数有误", False
                rttext += "skillmaxAged设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "skillCost":
                if len(cgrules[key]) & 1 != 0 or len(cgrules[key]) == 0:
                    return "skillCost 参数长度有误", False
                i = 0
                while i+2 < len(cgrules[key]):
                    if cgrules[key][i+2] <= cgrules[key][i]:
                        return "skillCost 参数有误", False
                    i += 2
                i = 1
                while i+2 < len(cgrules[key]):
                    if cgrules[key][i+2] <= cgrules[key][i]:
                        return "skillCost 参数有误", False
                    i += 2
                del i
                if cgrules[key][0] <= 0 or cgrules[key][1] <= 0 or cgrules[key][len(cgrules[key])-1] != 100:
                    return "skillCost 参数有误", False
                rttext += "skillCost设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "greatsuccess":
                if len(cgrules[key]) != 4:
                    return "greatsuccess 参数长度有误", False
                if cgrules[key][0] > cgrules[key][1] or cgrules[key][2] > cgrules[key][3]:
                    return "greatsuccess 参数有误", False
                if cgrules[key][0] <= 0 or cgrules[key][1] > 100 or cgrules[key][2] <= 0 or cgrules[key][1] > 100:
                    return "greatsuccess 参数有误", False
                rttext += "greatsuccess设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            elif key == "greatfail":
                if len(cgrules[key]) != 4:
                    return "greatfail 参数长度有误", False
                if cgrules[key][0] > cgrules[key][1] or cgrules[key][2] > cgrules[key][3]:
                    return "greatfail 参数有误", False
                if cgrules[key][0] <= 0 or cgrules[key][1] > 100 or cgrules[key][2] <= 0 or cgrules[key][1] > 100:
                    return "greatfail 参数有误", False
                rttext += "greatfail设置成功，值："+str(cgrules[key])+"\n"
                self.__dict__[key] = cgrules[key]
            else:
                rttext += "无法识别的key："+key
                continue
        return rttext, True

    def __str__(self):
        rttext = ""
        for key in self.__dict__:
            rttext += key+": "+str(self.__dict__[key])+"\n"
        return rttext
