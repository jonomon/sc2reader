# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
from collections import defaultdict

from sc2reader import log_utils
from sc2reader.utils import Length
from sc2reader.plugins.utils import PlayerSelection, GameState, JSONDateEncoder, plugin


@plugin
def toJSON(replay, **user_options):
    options = dict(cls=JSONDateEncoder)
    options.update(user_options)
    return json.dumps(toDict()(replay), **options)


@plugin
def toDict(replay):
    # Build observers into dictionary
    observers = list()
    for observer in replay.observers:
        messages = list()
        for message in getattr(observer,'messages',list()):
            messages.append({
                'time': message.time.seconds,
                'text': message.text,
                'is_public': message.to_all
            })
        observers.append({
            'name': getattr(observer, 'name', None),
            'pid': getattr(observer, 'pid', None),
            'messages': messages,
        })

    # Build players into dictionary
    players = list()
    for player in replay.players:
        messages = list()
        for message in player.messages:
            messages.append({
                'time': message.time.seconds,
                'text': message.text,
                'is_public': message.to_all
            })
        players.append({
            'avg_apm': getattr(player, 'avg_apm', None),
            'color': player.color.__dict__ if hasattr(player, 'color') else None,
            'handicap': getattr(player, 'handicap', None),
            'name': getattr(player, 'name', None),
            'pick_race': getattr(player, 'pick_race', None),
            'pid': getattr(player, 'pid', None),
            'play_race': getattr(player, 'play_race', None),
            'result': getattr(player, 'result', None),
            'type': getattr(player, 'type', None),
            'uid': getattr(player, 'uid', None),
            'url': getattr(player, 'url', None),
            'messages': messages,
        })

    # Consolidate replay metadata into dictionary
    return {
        'gateway': getattr(replay, 'gateway', None),
        'map_name': getattr(replay, 'map_name', None),
        'file_time': getattr(replay, 'file_time', None),
        'filehash': getattr(replay, 'filehash', None),
        'unix_timestamp': getattr(replay, 'unix_timestamp', None),
        'date': getattr(replay, 'date', None),
        'utc_date': getattr(replay, 'utc_date', None),
        'speed': getattr(replay, 'speed', None),
        'category': getattr(replay, 'category', None),
        'type': getattr(replay, 'type', None),
        'is_ladder': getattr(replay, 'is_ladder', False),
        'is_private': getattr(replay, 'is_private', False),
        'filename': getattr(replay, 'filename', None),
        'file_time': getattr(replay, 'file_time', None),
        'frames': getattr(replay, 'frames', None),
        'build': getattr(replay, 'build', None),
        'release': getattr(replay, 'release_string', None),
        'game_fps': getattr(replay, 'game_fps', None),
        'game_length': getattr(getattr(replay, 'game_length', None), 'seconds', None),
        'players': players,
        'observers': observers,
        'real_length': getattr(getattr(replay, 'real_length', None), 'seconds', None),
        'real_type': getattr(replay, 'real_type', None),
        'time_zone': getattr(replay, 'time_zone', None),
        'versions': getattr(replay, 'versions', None)
    }

@plugin
def APMTracker(replay):
    """
    Builds ``player.aps`` and ``player.apm`` dictionaries where an action is
    any Selection, Hotkey, or Ability event.

    Also provides ``player.avg_apm`` which is defined as the sum of all the
    above actions divided by the number of seconds played by the player (not
    necessarily the whole game) multiplied by 60.
    """
    for player in replay.players:
        player.aps = defaultdict(int)
        player.apm = defaultdict(int)
        seconds_played = replay.length.seconds

        for event in player.events:
            if event.name == 'SelectionEvent' or 'AbilityEvent' in event.name or 'Hotkey' in event.name:
                player.aps[event.second] += 1
                player.apm[event.second/60] += 1

            elif event.name == 'PlayerLeaveEvent':
                seconds_played = event.second

        if len(player.apm) > 0:
            player.avg_apm = sum(player.aps.values())/float(seconds_played)*60
        else:
            player.avg_apm = 0

    return replay

@plugin
def CreepTracker(replay):
    '''
    The Creep tracker populates player.max_creep_spread and
    player.creep_spread by minute

    All the Creep Generating units (CGU) are contained in the
    creep_generating_units_list.  creep_generating_units_list is
    a list organised by time which contains a list of CGUs that are
    alive

    '''
    from itertools import dropwhile
    from sets import Set
    
    def add_to_list(player_id,unit_id,unit_location,\
                unit_type, creep_generating_units_list):
    # This functions adds a new time frame to creep_generating_units_list
    # Each time frame contains a list of all CGUs that are alive
        length_cgu_list = len(creep_generating_units_list[player_id])
        if length_cgu_list==0:
            creep_generating_units_list[player_id].append([(unit_id, unit_location,unit_type)])
        else:
            #if the list is not empty, take the previous time frame,
            # add the new CGU to it and append it as a new time frame
            previous_list = creep_generating_units_list[player_id][length_cgu_list-1][:]
            previous_list.append((unit_id, unit_location,unit_type))
            creep_generating_units_list[player_id].append(previous_list)

    def radius_to_map_positions(radius):
        ## this function converts all radius into map coordinates
        ## centred around  the origin that the creep can exist
        ## the cgu_radius_to_map_position function will simply
        ## substract every coordinate with the centre point of the tumour
        output_coordinates = list()
        # Sample a square area using the radius
        for x in range (-radius,radius):
            for y in range (-radius, radius):
                if (x**2 + y**2) <= (radius * radius):
                    output_coordinates.append((x,y))
        return output_coordinates
        
    def cgu_radius_to_map_positions(cgu_radius,radius_to_coordinates):
    ## This function uses the output of radius_to_map_positions
        total_points_on_map = Set()
        if len(cgu_radius)==0:
            return 0
        for cgu in cgu_radius:
            point = cgu[0]
            radius = cgu[1]
            ## subtract all radius_to_coordinates with centre of
            ## cgu radius to change centre of circle 
            cgu_map_position = map( lambda x: (x[0]- point[0], x[1] -  point[1])\
                            ,radius_to_coordinates[radius])
            total_points_on_map= total_points_on_map | Set(cgu_map_position)
        return len(total_points_on_map)   
            
    #Get Map Size
    mapinfo = replay.map.archive.read_file('MapInfo')
    mapSizeX = ord(mapinfo[16])
    mapSizeY = ord(mapinfo[20])
    mapSize = mapSizeX * mapSizeY

    ## This list contains all the active cgus in every time frame
    creep_generating_units_list = dict()
    ## Thist list corresponds to creep_generating_units_lists storing
    ## the time
    creep_generating_units_times= dict()
    
    for player in replay.players:
        player.creep_spread_by_minute = defaultdict(int)
        player.max_creep_spread = int()
        creep_generating_units_list[player.pid] = list()
        creep_generating_units_times[player.pid] = list()
    try:
        replay.tracker_events
    except AttributeError:
        print "Replay does not have tracker events"
        return replay

    for event in replay.events:
        if event.name == "UnitBornEvent":
            if event.unit_type_name== "Hatchery":
                add_to_list(event.control_pid, event.unit_id,\
                            (event.x,event.y),\
                            event.unit_type_name,\
                            creep_generating_units_list)
                creep_generating_units_times[event.control_pid].append(event.second)
        # Search things that generate creep
        # Tumor, hatcheries, nydus and overlords generating creep
        if event.name == "UnitInitEvent":
            units = ["CreepTumor", "Hatchery","Nydus"] # check nydus name
            if event.unit_type_name in units:
                add_to_list(event.control_pid,event.unit_id,\
                            (event.x, event.y), \
                            event.unit_type_name,\
                            creep_generating_units_list)
                creep_generating_units_times[event.control_pid].append(event.second)
        if event.name == "AbilityEvent":
            if event.ability_name == "GenerateCreep":
                add_to_list(event.control_pid,event.unit_id,\
                            (event.x, event.y), \
                            event.unit_type_name,\
                            creep_generating_units_list)
                creep_generating_units_times[event.control_pid].append(event.second)
     # Removes creep generating units that were destroyed
        if event.name == "UnitDiedEvent":
            for player_id in creep_generating_units_list:
                length_cgu_list = len(creep_generating_units_list[player_id])
                if length_cgu_list ==0:
                    break
                cgu_per_player = creep_generating_units_list[player_id][length_cgu_list-1]
                creep_generating_died = dropwhile(lambda x: x[0] != event.unit_id, \
                                            cgu_per_player)
                for creep_generating_died_unit in creep_generating_died:
                    cgu_per_player.remove(creep_generating_died_unit)
                    creep_generating_units_list[player_id].append(cgu_per_player)
                    creep_generating_units_times[player_id].append(event.second)

    #the creep_generating_units_lists contains every single time frame
    #where a CGU is added,
    #To reduce the calculations required, the time frame containing
    #the last CGUs per minute will be used
    for player_id in replay.player:
        last_minute_found = 0
        cgu_per_player_new = list()
        cgu_time_per_player_new = list()
        for index,cgu_time in enumerate(creep_generating_units_times[player_id]):
            if (cgu_time/60)>last_minute_found:
                last_minute_found = cgu_time/60
                cgu_per_player_new.append(creep_generating_units_list[player_id][index-1])
                cgu_time_per_player_new.append(cgu_time)
        creep_generating_units_list[player_id] = cgu_per_player_new
        creep_generating_units_times[player_id] = cgu_time_per_player_new

    ## convert all radii into a sets centred around the origin,
    ## in order to use this with the CGUs, the centre point will be
    ## subtracted with all values in the set
    unit_name_to_radius = {'CreepTumor': 22, "Hatchery":24,
        "GenerateCreep": 12, "Nydus": 8 }

    radius_to_coordinates= dict()
    for x in unit_name_to_radius:
         radius_to_coordinates[unit_name_to_radius[x]] =\
         radius_to_map_positions(unit_name_to_radius[x])

    max_creep_spread=defaultdict()
    for player_id in replay.player:
        max_creep_spread[player_id] = 0
        for index,cgu_per_player in enumerate(creep_generating_units_list[player_id]):
            # convert cgu list into centre of circles and radius
            cgu_radius = map(lambda x: (x[1],   unit_name_to_radius[x[2]]),\
                                  cgu_per_player)
            creep_area = cgu_radius_to_map_positions(cgu_radius,radius_to_coordinates)
            cgu_last_event_time = creep_generating_units_times[player_id][index]/60
            replay.player[player_id].creep_spread_by_minute[cgu_last_event_time]= \
                float(creep_area)/mapSize*100
            if creep_area>max_creep_spread[player_id]:
                  max_creep_spread[player_id] =float(creep_area)/mapSize
    for player_id in replay.player:
        replay.player[player_id].max_creep_spread = max_creep_spread[player_id]
    return replay 


@plugin
def SelectionTracker(replay):
    debug = replay.opt.debug
    logger = log_utils.get_logger(SelectionTracker)

    for person in replay.people:
        # TODO: A more robust person interface might be nice
        person.selection_errors = 0
        player_selections = GameState(PlayerSelection())
        for event in person.events:
            error = False
            if event.name == 'SelectionEvent':
                selections = player_selections[event.frame]
                control_group = selections[event.control_group].copy()
                error = not control_group.deselect(event.mask_type, event.mask_data)
                control_group.select(event.new_units)
                selections[event.control_group] = control_group
                if debug: logger.info("[{0}] {1} selected {2} units: {3}".format(Length(seconds=event.second),person.name,len(selections[0x0A].objects),selections[0x0A]))

            elif event.name == 'SetToHotkeyEvent':
                selections = player_selections[event.frame]
                selections[event.control_group] = selections[0x0A].copy()
                if debug: logger.info("[{0}] {1} set hotkey {2} to current selection".format(Length(seconds=event.second),person.name,event.hotkey))

            elif event.name == 'AddToHotkeyEvent':
                selections = player_selections[event.frame]
                control_group = selections[event.control_group].copy()
                error = not control_group.deselect(event.mask_type, event.mask_data)
                control_group.select(selections[0x0A].objects)
                selections[event.control_group] = control_group
                if debug: logger.info("[{0}] {1} added current selection to hotkey {2}".format(Length(seconds=event.second),person.name,event.hotkey))

            elif event.name == 'GetFromHotkeyEvent':
                selections = player_selections[event.frame]
                control_group = selections[event.control_group].copy()
                error = not control_group.deselect(event.mask_type, event.mask_data)
                selections[0xA] = control_group
                if debug: logger.info("[{0}] {1} retrieved hotkey {2}, {3} units: {4}".format(Length(seconds=event.second),person.name,event.control_group,len(selections[0x0A].objects),selections[0x0A]))

            else:
                continue

            # TODO: The event level interface here should be improved
            #       Possibly use 'added' and 'removed' unit lists as well
            event.selected = selections[0x0A].objects
            if error:
                person.selection_errors += 1
                if debug:
                    logger.warn("Error detected in deselection mode {0}.".format(event.mask_type))

        person.selection = player_selections
        # Not a real lock, so don't change it!
        person.selection.locked = True

    return replay
