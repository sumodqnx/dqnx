import os, sys, copy

import numpy as np

from collections import deque

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    from sumolib import checkBinary
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

from src.trafficmetrics import TrafficMetrics

class TrafficSignalController:
    """Abstract base class for all traffic signal controller.

    Build your own traffic signal controller by implementing the follow methods.
    """
    def __init__(self, conn, tsc_id, mode, netdata, red_t, yellow_t):
        self.conn = conn
        self.id = tsc_id
        self.netdata = netdata
        self.red_t = red_t
        self.yellow_t = yellow_t
        self.green_phases = self.get_tl_green_phases()
        self.phase_time = 0
        self.all_red = len((self.green_phases[0]))*'r'
        self.phase = self.all_red
        self.phase_lanes = self.phase_lanes(self.green_phases)
        #create subscription for this traffic signal junction to gather
        #vehicle information efficiently
        self.conn.junction.subscribeContext(tsc_id, traci.constants.CMD_GET_VEHICLE_VARIABLE, 150, #tianxin: 150? anything else?
                                        [traci.constants.VAR_LANEPOSITION, 
                                        traci.constants.VAR_SPEED, 
                                        traci.constants.VAR_LANE_ID])
        #get all incoming lanes to intersection
        self.incoming_lanes = set()
        for p in self.phase_lanes:
            for l in self.phase_lanes[p]:
                self.incoming_lanes.add(l)

        self.incoming_lanes = sorted(list(self.incoming_lanes))
        #lane capacity is the lane length divided by the average vehicle length+stopped headway
        self.lane_capacity = np.array([float(self.netdata['lane'][lane]['length'])/7.5 for lane in self.incoming_lanes])

        
        #tianxin: added for outgoing_lanes
        self.outgoing_lanes = set()
        for l in self.incoming_lanes:
            for ll in self.netdata['lane'][l]['outgoing']:
                self.outgoing_lanes.add(ll)
        self.outgoing_lanes = sorted(list(self.outgoing_lanes))
        
        #tianxin added
        
        self.outgoing_lane_capacity = np.array([float(self.netdata['lane'][lane]['length'])/7.5 for lane in self.outgoing_lanes])
        # print("outgoing_lanes: ", self.outgoing_lanes)
        # print("outgoing_lane_cap: ", self.outgoing_lane_capacity)
        #for collecting various traffic metrics at the intersection
        #can be extended in trafficmetric.py class to collect new metrics
        # tianxin: change the reward function for training
        if mode == 'train':
            self.metric_args = ['queue', 'delay']
        if mode == 'test':
            self.metric_args = ['queue', 'delay']
        self.trafficmetrics = TrafficMetrics(tsc_id, self.incoming_lanes, netdata, self.metric_args, mode)
        self.prev_queue_square = 0
        self.ep_rewards = []
        
    def run(self):
        data = self.get_subscription_data()
        self.trafficmetrics.update(data)
        self.update(data)
        self.increment_controller()

    def get_metrics(self):
        for m in self.metric_args:
            metric = self.trafficmetrics.get_metric(m)

    def get_traffic_metrics_history(self):
        return {m:self.trafficmetrics.get_history(m) for m in self.metric_args} 
    
    #tianxin 
    def increment_controller(self):
        if self.phase_time == 0:
            ###get new phase and duration
            next_phase = self.next_phase()
            self.conn.trafficlight.setRedYellowGreenState( self.id, next_phase )
            self.phase = next_phase
            self.phase_time = self.next_phase_duration()
        self.phase_time -= 1

    def get_intermediate_phases(self, phase, next_phase):
        if phase == next_phase or phase == self.all_red:
            return []
        else:
            yellow_phase = ''.join([ p if p == 'r' else 'y' for p in phase ])
            return [yellow_phase, self.all_red]

    def next_phase(self):
        raise NotImplementedError("Subclasses should implement this!")
        
    def next_phase_duration(self):
        raise NotImplementedError("Subclasses should implement this!")

    def update(self, data):
        """Implement this function to perform any
           traffic signal class specific control/updates 
        """
        raise NotImplementedError("Subclasses should implement this!")

    def get_subscription_data(self):
        #use SUMO subscription to retrieve vehicle info in batches
        #around the traffic signal controller
        tl_data = self.conn.junction.getContextSubscriptionResults(self.id)                          
        #create empty incoming lanes for use else where
        lane_vehicles = {l:{} for l in self.incoming_lanes}
        #tianxin: add outgoing lane data
        for l in self.outgoing_lanes:
            lane_vehicles[l] = {}

        if tl_data is not None:
            for v in tl_data:
                lane = tl_data[v][traci.constants.VAR_LANE_ID]
                if lane not in lane_vehicles:
                    lane_vehicles[lane] = {}
                lane_vehicles[lane][v] = tl_data[v] 
        return lane_vehicles

    def get_tl_green_phases(self):
        logic = self.conn.trafficlight.getCompleteRedYellowGreenDefinition(self.id)[0]
        #get only the green phases
        green_phases = [ p.state for p in logic.getPhases() 
                         if 'y' not in p.state 
                         and ('G' in p.state or 'g' in p.state) ]

        #sort to ensure parity between sims (for RL actions)
        return sorted(green_phases)
    
    def phase_lanes(self, actions):
        phase_lanes = {a:[] for a in actions}
        for a in actions:
            green_lanes = set()
            red_lanes = set()
            for s in range(len(a)):
                if a[s] == 'g' or a[s] == 'G':
                    green_lanes.add(self.netdata['inter'][self.id]['tlsindex'][s])
                elif a[s] == 'r':
                    red_lanes.add(self.netdata['inter'][self.id]['tlsindex'][s])

            ###some movements are on the same lane, removes duplicate lanes
            pure_green = [l for l in green_lanes if l not in red_lanes]
            if len(pure_green) == 0:
                phase_lanes[a] = list(set(green_lanes))
            else:
                phase_lanes[a] = list(set(pure_green))
        return phase_lanes

    #helper functions for rl controllers
    def input_to_one_hot(self, phases):
        identity = np.identity(len(phases))                                 
        one_hots = { phases[i]:identity[i,:]  for i in range(len(phases)) }
        return one_hots

    def int_to_input(self, phases):
        return { p:phases[p] for p in range(len(phases)) }

    #tianxin 
    def get_state(self):
        #the state is the normalized density of all incoming and outgoing lanes 
        ret = np.concatenate([self.get_normalized_density(), self.get_normalized_queue()])
        # print(self.id)
        # print("ret: ")
        # print(np.shape(ret))
        # print(ret)
        # print("==============================")
        return ret

    #tianxin: add optional arg for self.outgoing_lanes
    def get_normalized_density(self):

        #number of vehicles in each incoming lane divided by the lane's capacity
        # incoming
        # print("get_normalized_density: ")
        # print(len(self.incoming_lanes))
        # print(len(self.lane_capacity))
        ret1 = np.array([len(self.data[lane]) for lane in self.incoming_lanes])/self.lane_capacity
        #outgoing
        # print(len(self.outgoing_lanes))
        # print(len(self.outgoing_lane_capacity))
        # print("keys: ")
        # print(self.data.keys())
        ret2 = np.array([len(self.data[lane]) for lane in self.outgoing_lanes])/self.outgoing_lane_capacity
        return np.concatenate((ret1, ret2))
        # return np.array([len(self.data[lane]) for lane in self.incoming_lanes])/self.lane_capacity
    #tianxin
    def get_normalized_queue(self):
        # incoming
        lane_queues = []
        for lane in self.incoming_lanes:
            q = 0
            for v in self.data[lane]:
                if self.data[lane][v][traci.constants.VAR_SPEED] < 0.3:
                    q += 1
            lane_queues.append(q)
        ret1 = np.array(lane_queues)/self.lane_capacity
        
        #outgoing
        lane_queues = []
        for lane in self.outgoing_lanes:
            q = 0
            for v in self.data[lane]:
                if self.data[lane][v][traci.constants.VAR_SPEED] < 0.3:
                    q += 1
            lane_queues.append(q)
        ret2 = np.array(lane_queues)/self.outgoing_lane_capacity
        return np.concatenate((ret1, ret2))
        # return np.array(lane_queues)/self.lane_capacity

    def empty_intersection(self):
        for lane in self.incoming_lanes:
            if len(self.data[lane]) > 0:
                return False
        return True
# tianxin: original one for the delay
    # def get_reward(self):
    #     #return negative delay as reward
    #     cur_delay = int(self.trafficmetrics.get_metric('delay'))
    #     r = self.prev_delay - cur_delay
    #     self.prev_delay = cur_delay
    #     self.ep_rewards.append(r)
    #     return r

#tianxin: new one for the max queue length
    def get_reward(self):
        #return negative delay as reward
        qs = int(self.trafficmetrics.get_special_reward())
        
        r = self.prev_queue_square - qs
        self.ep_rewards.append(r)
        self.prev_queue_square = qs
        return r

    def empty_dtse(n_lanes, dist, cell_size):
        return np.zeros((n_lanes, int(dist/cell_size)+3 ))
    
    def phase_dtse(phase_lanes, lane_to_int, dtse):
        phase_dtse = {}
        for phase in phase_lanes:
            copy_dtse = np.copy(dtse)
            for lane in phase_lanes[phase]:
                copy_dtse[lane_to_int[lane],:] = 1.0
            phase_dtse[phase] = copy_dtse
        return phase_dtse


    def get_dtse():
        dtse = np.copy(self._dtse)
        for lane,i in zip(incoming_lanes, range(len(incoming_lanes))):
            for v in self.data[lane]:
                pos = self.data[lane][v][traci.constants.VAR_LANEPOSITION]
                dtse[i, pos:pos+1] = 1.0

        return dtse

'''
right_on_red_phases = []
for phase in green_phases:
    new_phase = []
    for idx in range(len(phase)):
        if self.netdata['inter'][self.id]['tlsindexdir'][idx] == 'r' and phase[idx] == 'r':
            new_phase.append('s')
        else:
            new_phase.append(phase[idx])
    right_on_red_phases.append(''.join(new_phase))
'''

'''
n_g = len(green_phases)
                                                                                            
right_on_red_phases = []
for phase in green_phases:
    new_phase = []
    for idx in range(len(phase)):
        if self.netdata['inter'][self.id]['tlsindexdir'][idx] == 'r' and phase[idx] == 'r':
            new_phase.append('s')
        else:
            new_phase.append(phase[idx])
    right_on_red_phases.append(''.join(new_phase))
                                                                                            
green_phases = [ p for p in right_on_red_phases 
                 if 'y' not in p
                 and ('G' in p or 'g' in p) ]
'''
'''
n_ror = len(ror_phases)
if n_ror != n_g:
    print('==========')
    print(self.id)
    print(green_phases)
    print(ror_phases)
'''
