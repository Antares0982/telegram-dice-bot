class Card:
    def __init__(self, userid, groupid, data):
        self.userid = userid
        self.groupid = groupid
        self.data = data

class PL:
    def __init__(self, groupid, card):
        self.groupid = groupid
        self.card = card

class GroupGame: # If defined, game is started.
    def __init__(self, groupid, kpid, cards):
        self.groupid = groupid
        self.kpid = kpid
        self.cards = cards # dict
        
