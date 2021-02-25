# -*- coding:utf-8 -*-
from configparser import ConfigParser

cfgparser = ConfigParser()
cfgparser.read('config.ini')

VERSION = "1.0.9"

PROXY = cfgparser.getboolean("PROXY", "PROXY")  # 大陆登录telegram需要设置代理，否则关闭

PROXY_URL = cfgparser.get("PROXY", "PROXY_URL")  # 代理

TOKEN = cfgparser.get("BOT", "TOKEN")  # BOT TOKEN
BOTUSERNAME = cfgparser.get("BOT", "USERNAME")
BOT_ID = int(TOKEN.split(":")[0])

# DATA_PATH = r'/home/tgbot/'  # 数据文件存在哪个目录

DATA_PATH = cfgparser.get("PATH", "DATA_PATH")

PATH_GROUP_KP = DATA_PATH+r'groupkpdict.json'
PATH_CARDSLIST = DATA_PATH+r'cards.json'
PATH_ONGAME = DATA_PATH+r'ongame.json'
PATH_SKILLDICT = DATA_PATH+r'skilldict.json'
PATH_JOBDICT = DATA_PATH+r'jobdict.json'
PATH_CURRENTCARDDICT = DATA_PATH+r'currentcarddict.json'
PATH_RULES = DATA_PATH+r'grouprules.json'
PATH_HANDLERS = DATA_PATH+r'handlers.json'
PATH_HOLDGAME = DATA_PATH+r'holdgame.json'

ADMIN_ID = cfgparser.getint("ID", "ADMIN_ID")  # BOT控制者的userid

IGNORE_JOB_DICT = cfgparser.getboolean("SETTINGS", "IGNORE_JOB_DICT")

CREATE_CARD_HELP = """建卡流程如下：
1 创建新卡，生成除幸运外的基本属性
2 设置年龄。此时骰幸运，当年龄设置低于20时幸运得到奖励骰。
年龄大于等于40或严格低于20，都会有一些属性需要下降，年龄大于等于20时，教育得到增强。
3 设置力量等属性的下降值。如果上一步设置的年龄在`20-39`，则此步骤忽略。
4 设置职业。不同职业有不同的主要技能和信用范围、技能点计算方法。
5 添加技能。使用 /addskill 添加主要技能、兴趣技能。
6 用 /setname 设置姓名， /setsex 设置性别。
7 用 /setbkground 设置背景信息，或 /randombackground 设置随机的背景信息。"""

HELP_TEXT = "欢迎使用COC dice bot，目前版本：v"+VERSION+"""
作者：@AntaresChr
使用 /help 查看指令的帮助。
（私聊时偶尔触发嘴臭模式）"""

del cfgparser
