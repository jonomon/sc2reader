from __future__ import absolute_import

from itertools import dropwhile
from sets import Set
from Image import open as PIL_open
from Image import ANTIALIAS 
from StringIO import StringIO
from collections import defaultdict
    
class creep_tracker():
    def __init__(self,replay):
        #if the debug option is selected, minimaps will be printed to a file
        ##and a stringIO containing the minimap image will be saved for 
        ##every minite in the game
        self.debug = replay.opt.debug
        self.creep_spread_by_minute = dict()
        self.creep_spread_image_by_minute = dict()
        ## This list contains all the active cgus in every time frame
        self.creep_gen_units = dict()
        ## Thist list corresponds to creep_generating_units_lists storing
        ## the time
        self.creep_gen_units_times= dict()
        ## convert all radii into a sets centred around the origin,
        ## in order to use this with the CGUs, the centre point will be
        ## subtracted with all values in the 
        self.unit_name_to_radius = {'CreepTumor': 10, "Hatchery":10, 
                               "GenerateCreep": 6, "Nydus": 4 }
        self.radius_to_coordinates= dict()
        for x in self.unit_name_to_radius:
            self.radius_to_coordinates[self.unit_name_to_radius[x]] =\
                  self.radius_to_map_positions(self.unit_name_to_radius[x])
        
        #Get map information
        replayMap = replay.map
        # extract image from replay package
        mapsio = StringIO(replayMap.minimap)
        im = PIL_open(mapsio)
        mapinfo = replay.map.archive.read_file('MapInfo')
        mapSizeX = ord(mapinfo[16])
        mapSizeY = ord(mapinfo[20])
        ## get map size for calculating % area
                ##remove black box around minimap
        cropped = im.crop(im.getbbox())
        cropsize = cropped.size
        self.map_height = 100.0
        # resize height to MAPHEIGHT, and compute new width that
        # would preserve aspect ratio
        self.map_width = int(cropsize[0] * (float(self.map_height) / cropsize[1]))
        self.mapSize =self.map_height * self.map_width 
        minimapSize = ( self.map_width,int(self.map_height) )
        self.minimap_image = cropped.resize(minimapSize, ANTIALIAS)
        mapOffsetX, mapOffsetY = self.cameraOffset(mapinfo)
        mapCenter = [mapOffsetX + cropsize[0]/2.0, mapOffsetY + cropsize[1]/2.0]
        # this is the center of the minimap image, in pixel coordinates
        imageCenter = [(self.map_width/2), self.map_height/2]
        # this is the scaling factor to go from the SC2 coordinate
        # system to pixel coordinates
        self.image_scale = float(self.map_height) / cropsize[0] 
        self.transX =imageCenter[0] + self.image_scale * (mapCenter[0])
        self.transY = imageCenter[1] + self.image_scale * (mapCenter[1])
        
    def radius_to_map_positions(self,radius):
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

    def init_cgu_lists(self, player_id):
        self.creep_spread_by_minute[player_id] = defaultdict(int)
        self.creep_spread_image_by_minute[player_id] = defaultdict(StringIO)
        self.creep_gen_units[player_id] = list()
        self.creep_gen_units_times[player_id] = list()

    def add_to_list(self,player_id,unit_id,unit_location,unit_type,event_time):
    # This functions adds a new time frame to creep_generating_units_list
    # Each time frame contains a list of all CGUs that are alive
        length_cgu_list = len(self.creep_gen_units[player_id])
        if length_cgu_list==0:
            self.creep_gen_units[player_id].append([(unit_id, unit_location,unit_type)])
            self.creep_gen_units_times[player_id].append(event_time)
        else:
            #if the list is not empty, take the previous time frame,
            # add the new CGU to it and append it as a new time frame
            previous_list = self.creep_gen_units[player_id][length_cgu_list-1][:]
            previous_list.append((unit_id, unit_location,unit_type))
            self.creep_gen_units[player_id].append(previous_list)
            self.creep_gen_units_times[player_id].append(event_time)

    def remove_from_list(self,unit_id,time_frame):
        for player_id in self.creep_gen_units:
            length_cgu_list = len(self.creep_gen_units[player_id])
            if length_cgu_list ==0:
                    break
            cgu_per_player = self.creep_gen_units[player_id]\
                                                   [length_cgu_list-1]
            creep_generating_died = dropwhile(lambda x: x[0] != \
                                                  unit_id, cgu_per_player)
            for creep_generating_died_unit in creep_generating_died:
                cgu_per_player.remove(creep_generating_died_unit)
                self.creep_gen_units[player_id].append(cgu_per_player)
                self.creep_gen_units_times[player_id].append(time_frame)

    def add_event(self,event):
        if event.name == "UnitBornEvent":
           if event.unit_type_name== "Hatchery":
               self.add_to_list(event.control_pid, event.unit_id,\
                                (event.x,event.y),event.unit_type_name,event.second)
        # Search things that generate creep
        # Tumor, hatcheries, nydus and overlords generating creep
        if event.name == "UnitInitEvent":
            units = ["CreepTumor", "Hatchery","Nydus"] # check nydus name
            if event.unit_type_name in units:
                self.add_to_list(event.control_pid,event.unit_id,\
                            (event.x, event.y), event.unit_type_name,event.second)
        if event.name == "AbilityEvent":
            if event.ability_name == "GenerateCreep":
                self.add_to_list(control_pid,event.unit_id,\
                            (event.x, event.y), event.unit_type_name,event.second)
            if event.ability_name == "StopGenerateCreep":
                self.remove_from_list(event.unit_id,event.second)
     # Removes creep generating units that were destroyed
        if event.name == "UnitDiedEvent":
            self.remove_from_list(event.unit_id,event.second)

    def reduce_cgu_per_minute(self,player_id):
    #the creep_gen_units_lists contains every single time frame
    #where a CGU is added,
    #To reduce the calculations required, the time frame containing
    #the last CGUs per minute will be used
        last_minute_found = 0
        cgu_per_player_new = list()
        cgu_time_per_player_new = list()
        for index,cgu_time in \
                       enumerate(self.creep_gen_units_times[player_id]):
            if (cgu_time/60)>last_minute_found:
                last_minute_found = cgu_time/60
                cgu_per_player_new.append(self.creep_gen_units[player_id][index-1])
                cgu_time_per_player_new.append(cgu_time)
        self.creep_gen_units[player_id] = cgu_per_player_new
        self.creep_gen_units_times[player_id] = cgu_time_per_player_new

    def get_creep_spread_area(self,player_id):
        for index,cgu_per_player in enumerate(self.creep_gen_units[player_id]):
            # convert cgu list into centre of circles and radius
            cgu_radius = map(lambda x: (x[1], self.unit_name_to_radius[x[2]]),\
                                  cgu_per_player)
            # convert event coords to minimap coords
            cgu_radius = self.convert_cgu_radius_event_to_map_coord(cgu_radius)
            creep_area_positions = self.cgu_radius_to_map_positions(cgu_radius,self.radius_to_coordinates)
            cgu_last_event_time = self.creep_gen_units_times[player_id][index]/60
            if self.debug: 
                self.print_image(creep_area_positions,player_id,cgu_last_event_time)
            creep_area = len(creep_area_positions)
            self.creep_spread_by_minute[player_id][cgu_last_event_time]=\
                                                    float(creep_area)/self.mapSize*100
        return self.creep_spread_by_minute[player_id]

    def cgu_radius_to_map_positions(self,cgu_radius,radius_to_coordinates):
    ## This function uses the output of radius_to_map_positions
        total_points_on_map = Set()
        if len(cgu_radius)==0:
            return []
        for cgu in cgu_radius:
            point = cgu[0]
            radius = cgu[1]
            ## subtract all radius_to_coordinates with centre of
            ## cgu radius to change centre of circle 
            cgu_map_position = map( lambda x:(x[0]+point[0],x[1]+point[1])\
                            ,self.radius_to_coordinates[radius])
            total_points_on_map= total_points_on_map | Set(cgu_map_position)
        return total_points_on_map

    def print_image(self,total_points_on_map,player_id,time_stamp):
        minimap_copy = self.minimap_image.copy()
        # Convert all creeped points to white
        for points in total_points_on_map:
            x = points[0]
            y = points[1]
            x,y = self.check_image_pixel_within_boundary(x,y)
            minimap_copy.putpixel((x,y) , (255, 255, 255))
        creeped_image = minimap_copy
        # write creeped minimap image to a string as a png
        creeped_imageIO = StringIO()
        creeped_image.save(creeped_imageIO, "png")
        self.creep_spread_image_by_minute[player_id][time_stamp]=creeped_imageIO
        ##debug for print out the images
        f = open(str(player_id)+'image'+str(time_stamp)+'.png','w')
        f.write(creeped_imageIO.getvalue())
        creeped_imageIO.close()
        f.close()

    def check_image_pixel_within_boundary(self,pointX, pointY):
        if pointX <0:
            pointX=0
        if pointY <0:
            pointY=0
        pointX = int(pointX % self.map_width)
        pointY = int(pointY % self.map_height)
        return pointX,pointY

    def convert_cgu_radius_event_to_map_coord(self,cgu_radius):
        cgu_radius_new = list()
        for cgu in cgu_radius:
            x = cgu[0][0]
            y = cgu[0][1]
            (x,y) = self.convert_event_coord_to_map_coord(x,y)
            cgu = ((x,y),cgu[1])
            cgu_radius_new.append(cgu)
        return cgu_radius_new

    def convert_event_coord_to_map_coord(self,x,y):
        imageX = int(self.map_height - self.transX + self.image_scale * x)
        imageY = int(self.transY - self.image_scale * y)
        return imageX, imageY

    def cameraOffset(self,mapinfo):
        fogOfWarStart = mapinfo.find('Dark')
        textureEnd = mapinfo[fogOfWarStart + 5:-1].find('\0')
        rest = mapinfo[fogOfWarStart + 5 + textureEnd + 1: -1]
        return ord(rest[0]), ord(rest[4])


