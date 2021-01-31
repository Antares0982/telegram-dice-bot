# coding=utf-8
from configparser import ConfigParser
cfgparser = ConfigParser()
cfgparser.read('config.ini')


PROXY = cfgparser.getboolean("PROXY", "PROXY")  # 大陆登录telegram需要设置代理，否则关闭

PROXY_URL = cfgparser.get("PROXY", "PROXY_URL")  # 代理

TOKEN = cfgparser.get("TOKEN", "TOKEN")  # BOT TOKEN

# DATA_PATH = r'/home/tgbot/'  # 数据文件存在哪个目录

DATA_PATH = cfgparser.get("PATH", "DATA_PATH")

PATH_GROUP_KP = DATA_PATH+r'groupkpdict.json'
PATH_CARDSLIST = DATA_PATH+r'cards.json'
PATH_ONGAME = DATA_PATH+r'ongame.json'
PATH_SKILLDICT = DATA_PATH+r'skilldict.json'
PATH_JOBDICT = DATA_PATH+r'jobdict.json'
PATH_CURRENTCARDDICT = DATA_PATH+r'currentcarddict.json'

USERID = cfgparser.getint("ID", "USERID")  # BOT控制者的userid

IGNORE_JOB_DICT = cfgparser.getboolean("SETTINGS", "IGNORE_JOB_DICT")

CREATE_CARD_HELP = "This is help message when creating card, which will be added later."

HELP_TEXT = "This is help message, which will be added later."

del cfgparser
