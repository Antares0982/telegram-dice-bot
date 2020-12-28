class GroupGame: # If defined, game is started.
    def __init__(self, groupid, cards, kpid = None):
        self.groupid = groupid
        self.kpid = kpid
        self.cards = cards # list of dict
        self.kpcards = []
        for i in range(len(cards)):
            if cards[i]["player"]["playerid"] == kpid:
                self.kpcards.append(cards[i])
        self.kpctrl = -1
