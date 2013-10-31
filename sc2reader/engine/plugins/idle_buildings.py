# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from __future__ import unicode_literals, division


class idle_buildingTrackerPlugin(object):
    '''
    idle_buildingTrackerPlugin wraps around idle_buildingTracker
    which calculates the total time buildings are not producing.
    '''
    def handleInitGame(self, event, replay):
        pass

    def handleUnitInitEvent(self, event, replay):
        pass

    def handleEndGame(self, event, replay):
        pass


class idle_buildingTracker(object):
    def __init__(self):
        pass
