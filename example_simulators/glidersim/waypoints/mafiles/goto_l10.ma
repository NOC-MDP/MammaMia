behavior_name=Goto_list
<start:b_arg>
	b_arg: start_when(enum) 0
	b_arg: list_stop_when(enum) 12
	b_arg: list_when_wpt_dist(m) 500
	b_arg: initial_wpt(enum)     -1 # -1 ==> one after last one achieved
                                                        # -2 ==> closest
	b_arg: num_waypoints(nodim) 1
	b_arg: num_legs_to_run(nodim) -1
<end:b_arg>
<start:waypoints>
-1525.35 2725.5
-1525.35 2749.5
<end:waypoints>
