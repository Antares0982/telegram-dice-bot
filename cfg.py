# coding=utf-8
from configparser import ConfigParser
cfgparser = ConfigParser()
cfgparser.read('config.ini')


PROXY = cfgparser.getboolean("PROXY", "PROXY")  # 大陆登录telegram需要设置代理，否则关闭

PROXY_URL = cfgparser.get("PROXY", "PROXY_URL")  # 代理

TOKEN = cfgparser.get("TOKEN", "TOKEN")  # BOT TOKEN

# DATA_PATH = r'/home/tgbot/'  # 数据文件存在哪个目录

DATA_PATH = cfgparser.get("PATH", "DATA_PATH")

PATH_USER = DATA_PATH+r'userlist.json'
PATH_GROUP = DATA_PATH+r'grouplist.json'
PATH_USER_GROUP = DATA_PATH+r'usergrouplist.json'
PATH_GROUP_KP = DATA_PATH+r'groupkplist.json'
PATH_GROUP_PL_CARD = DATA_PATH+r'grouppllist.json'
PATH_CARDSLIST = DATA_PATH+r'cards.json'
PATH_ONGAME=DATA_PATH+r'ongame.json'
PATH_SKILLDICT=DATA_PATH+r'skilldict.json'

USERID = cfgparser.getint("ID", "USERID")  # BOT控制者的userid

CREATE_CARD_HELP = "This is help message when creating card, which will be added later."

HELP_TEXT = "This is help message, which will be added later."

del cfgparser