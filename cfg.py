# -*- coding:utf-8 -*-
from configparser import ConfigParser, NoOptionError, NoSectionError
from sys import platform
from os import getcwd, path, makedirs

__all__ = [
    "PROXY", "PROXY_URL", "TOKEN", "DATA_PATH", "ADMIN_ID", "IGNORE_JOB_DICT", "VERSION", "BOT_ID",
    "PATH_PLAYERS", "PATH_GROUPS", "GLOBAL_DATA_PATH", "PATH_SKILLDICT", "PATH_JOBDICT", "PATH_HANDLERS",
    "CREATE_CARD_HELP", "HELP_TEXT", "PATH_CARDS", "PATH_GAME_CARDS"
]

PROXY: bool = False
PROXY_URL: str = ""
TOKEN: str = ""
DATA_PATH: str = ""
ADMIN_ID: int = 0
IGNORE_JOB_DICT: bool = False


def __cfgparse():
    global PROXY, PROXY_URL, TOKEN, DATA_PATH, ADMIN_ID, IGNORE_JOB_DICT
    cfgparser = ConfigParser()
    cfgparser.read('config.ini')

    PROXY = cfgparser.getboolean("PROXY", "proxy")  # 大陆登录telegram需要设置代理，否则关闭
    PROXY_URL = cfgparser.get("PROXY", "proxy_url")  # 代理

    TOKEN = cfgparser.get("BOT", "token")  # BOT TOKEN

    DATA_PATH = cfgparser.get("PATH", "data_path")

    ADMIN_ID = cfgparser.getint("ID", "admin_id")  # BOT控制者的userid

    IGNORE_JOB_DICT = cfgparser.getboolean("SETTINGS", "ignore_job_dict")


def __defaultcfg():
    cfgparser = ConfigParser()

    cfgparser["PROXY"] = {}
    cfgparser["PROXY"]["proxy"] = 'true'
    cfgparser["PROXY"]["proxy_url"] = "http://127.0.0.1:1080/"

    cfgparser["BOT"] = {}
    cfgparser["BOT"]["token"] = "123456789:AABBCC-eeffgghh"

    cfgparser["PATH"] = {}
    if platform == 'win32':
        cfgparser["PATH"]["data_path"] = getcwd()+"\\data\\"
    else:
        cfgparser["PATH"]["data_path"] = getcwd()+"/data/"

    cfgparser["ID"] = {}
    cfgparser["ID"]["admin_id"] = '12345'

    cfgparser["SETTINGS"] = {}
    cfgparser["SETTINGS"]["ignore_job_dict"] = 'true'

    with open("sample_config.ini", 'w') as f:
        cfgparser.write(f)


try:
    __cfgparse()
except (NoSectionError, NoOptionError):
    __defaultcfg()
    raise Exception("配置文件不完整，请检查配置文件")

VERSION = "1.2.0"

BOT_ID = int(TOKEN.split(":")[0])


if platform == "win32":
    if DATA_PATH[-1] != '\\':
        DATA_PATH += '\\'
    PATH_PLAYERS = DATA_PATH+"players\\"
    PATH_GROUPS = DATA_PATH+"groups\\"
    PATH_CARDS = DATA_PATH+"cards\\"
    PATH_GAME_CARDS = DATA_PATH+"cards\\game\\"
    GLOBAL_DATA_PATH = DATA_PATH+"global\\"
else:
    if DATA_PATH[-1] != '/':
        DATA_PATH += '/'
    PATH_PLAYERS = DATA_PATH+"players/"
    PATH_GROUPS = DATA_PATH+"groups/"
    PATH_CARDS = DATA_PATH+"cards/"
    PATH_GAME_CARDS = DATA_PATH+"cards/game/"
    GLOBAL_DATA_PATH = DATA_PATH+"global/"

if not path.exists(PATH_CARDS):
    makedirs(PATH_CARDS)
if not path.exists(PATH_GAME_CARDS):
    makedirs(PATH_GAME_CARDS)
if not path.exists(PATH_GROUPS):
    makedirs(PATH_GROUPS)
if not path.exists(PATH_PLAYERS):
    makedirs(PATH_PLAYERS)


PATH_SKILLDICT = GLOBAL_DATA_PATH+r'skilldict.json'
PATH_JOBDICT = GLOBAL_DATA_PATH+r'jobdict.json'
PATH_HANDLERS = GLOBAL_DATA_PATH+r'handlers.json'


CREATE_CARD_HELP = """建卡流程如下：
1 创建新卡，生成除幸运外的基本属性
2 设置年龄。此时骰幸运，当年龄设置低于20时幸运得到奖励骰。
年龄大于等于40或严格低于20，都会有一些属性需要下降，年龄大于等于20时，教育得到增强。
3 设置力量等属性的下降值。如果上一步设置的年龄在`20-39`，则此步骤忽略。
4 设置职业。不同职业有不同的主要技能和信用范围、技能点计算方法。
5 添加技能。使用 /addskill 添加主要技能、兴趣技能。
6 用 /setname 设置姓名， /setsex 设置性别。
7 用 /setbkg 设置背景信息，或 /randombkg 设置随机的背景信息。"""

HELP_TEXT = "欢迎使用COC dice bot，目前版本：v"+VERSION+"""
作者：@AntaresChr
使用 /manual 查看手册，或者查看telegraph手册 https://telegra.ph/Dicebot-manual-05-08 ，使用 /help 查看指令的帮助。
（私聊时偶尔触发嘴臭模式）"""
