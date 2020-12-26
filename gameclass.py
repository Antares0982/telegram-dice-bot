class Group:
    def __init__(self, groupid: int, kpid: int, plid: list):
        self.groupid = groupid
        self.kpid = kpid


class GroupGame: # If defined, game is started.
    def __init__(self, groupid, cards, kpid = None):
        if isinstance(groupid, Group):
            self.groupid=groupid.groupid
            self.kpid = groupid.kpid
            self.cards = cards
        else:
            if kpid == None:
                raise Exception("Class: Groupgame initialize failed.")
            self.groupid = groupid
            self.kpid = kpid
            self.cards = cards # list of dict
        
