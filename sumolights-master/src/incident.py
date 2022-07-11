import os, sys

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    from sumolib import checkBinary
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

# import numpy as np
import random
class Incident:
    def __init__(self, netdata, sim_len, conn):
        random.seed()
        self.netdata = netdata
        self.conn = conn
        self.sim_len = sim_len
        self.origins = self.netdata['origin']
        self.destinations = self.netdata['destination']

        self.incident_time = random.randint(sim_len*1//3, sim_len*2//3)
        self.incident_route = self.generate_route()
        self.incident_origin = self.incident_route[0]
        # for testing
        # self.incident_duration = 60

        self.incident_duration = random.choice([15*60, 30*60])
        self.incident_edge = self.get_incident_edge()
        self.incident_stop_lane = 1
        self.incident_veh_total_length = random.choice([1, 3])*7.5
        self.incident_vid = "99999901"
        self.incident_stop_pos = 50 # manually set to avoid too close to the stop line
        # set color for the incident car for gui
        
        # generate emergency vehicle
        self.emergency_route = self.incident_route.copy()
        self.emergency_time = self.incident_time + 300 # dispatched 5 mins after incident
        self.vehicle_length = random.randint(3, 6)*7.5
        self.emergency_vehicle_stop_lane = None
        self.emergency_vid = "99999902"
        self.emergency_duration = self.incident_duration
        self.emergency_stop_lane = 1 + random.choice([1, -1])
        # set color for the emergency car for gui


        
    def generate_route(self):
        cur_edge = random.choice(self.origins)
        route = [cur_edge]
        while cur_edge not in self.destinations:
            next_edge = random.choice(self.netdata['edge'][cur_edge]['outgoing'])
            route.append(next_edge)
            cur_edge = next_edge
        if len(route) <= 4:
            return self.generate_route()
        # print(route)
        return route
    
    def get_incident_edge(self):
        # make sure the incident_edge in the middle of the network
        cand = self.incident_route[2:-2] 
        incident_edge = random.choice(cand)
        # print("incident_edge: ", incident_edge)
        return incident_edge

    def set_incident(self):
        vid = self.incident_vid
        origin = self.incident_origin
        self.conn.vehicle.addFull(vid, origin, departLane="best")
        route = self.incident_route
        color = (0, 0, 255) # blue
        
        self.conn.vehicle.setRoute(vid, route)
        self.conn.vehicle.setColor(vid, color)
        self.conn.vehicle.setLength(vid, self.incident_veh_total_length)
        self.conn.vehicle.setStop(vid, 
                            self.incident_edge, 
                            self.incident_stop_pos,
                            self.incident_stop_lane,
                            self.incident_duration)
        # print("incident_time: ", self.incident_time)
        # print("incident_duration: ", self.incident_duration)


    def set_emergency(self):
        vid = self.emergency_vid
        origin = self.incident_origin
        self.conn.vehicle.addFull(vid, origin, departLane="best")
        route = self.incident_route
        color = (0, 255, 0) 
        
        self.conn.vehicle.setRoute(vid, route)
        self.conn.vehicle.setColor(vid, color)
        self.conn.vehicle.setLength(vid, self.vehicle_length)
        self.conn.vehicle.setStop(vid, 
                            self.incident_edge, 
                            self.incident_stop_pos,
                            self.emergency_stop_lane,
                            self.incident_duration)

