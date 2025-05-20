behavior_name=goto_list
# Written by gen-goto-list-ma ver 1.0 on GMT:Tue Feb 19 18:56:54 2002
# 07-Aug-02 tc@DinkumSoftware.com Manually edited for spawars 7aug02 op in buzzards bay
# 07-Aug-02 tc@DinkumSoftware.com Changed from decimal degrees to degrees, minutes,
# decimal minutes
# goto_l10.ma
# Flies a hexagon around R4
<start:b_arg>
b_arg: num_legs_to_run(nodim) -1 # loop
b_arg: start_when(enum) 0 # BAW_IMMEDIATELY
b_arg: list_stop_when(enum) 7 # BAW_WHEN_WPT_DIST
b_arg: initial_wpt(enum) -2 # closest
b_arg: num_waypoints(nodim) 6
<end:b_arg>
<start:waypoints>
#-2408.520 2348.000
#-2408.520 2347.995
#-2408.525 2347.990
#-2408.530 2347.995
#-2408.530 2348.000
#-2408.525 2348.005
2713.35 -1525.35
2713.35 -1525.35
2713.35 -1525.35
<end:waypoints>
