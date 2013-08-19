from __future__ import absolute_import, print_function, unicode_literals, division

import sc2reader
from sc2reader.engine.plugins.creeptracker import CreepTracker, creep_tracker

def test_creepTracker():
    factory = sc2reader.factories.SC2Factory()
    pluginEngine=sc2reader.engine.GameEngine(plugins=[
                CreepTracker()
            ])
    replay =factory.load_replay("test_replays/2.0.8.25605/ggtracker_3621402.SC2Replay",load_map= True,engine=pluginEngine,load_level=4)
    creepTracker = creep_tracker(replay)
    ## check the map size calculated
    scaled_map_height = creepTracker.map_height

    minimap_map_height = replay.map.map_info.camera_top - replay.map.map_info.camera_bottom
    minimap_map_width = replay.map.map_info.camera_right - replay.map.map_info.camera_left
    imageScale = scaled_map_height  / minimap_map_height
    assert(creepTracker.image_scale==imageScale)
    
    ## check transX and transY
    height_width_ratio = minimap_map_height / minimap_map_width
    scaled_map_width =  height_width_ratio * scaled_map_height
    transX = scaled_map_width/2 + imageScale*(replay.map.map_info.camera_left + minimap_map_width/2)
    transY = scaled_map_height/2 + imageScale*(replay.map.map_info.camera_bottom + minimap_map_height/2)
    assert(creepTracker.transX ==transX)
    assert(creepTracker.transY ==transY)

    ## test event coord to map coord
    converted = (int(scaled_map_width - transX + imageScale*1),int( transY - imageScale*2))
    converted_by_class = creepTracker.convert_event_coord_to_map_coord(1,2)
    assert(converted==converted_by_class)







