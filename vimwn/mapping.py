import gi, re
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk



def install(normal_prefix, windows, reading, layout_manager):
	keys = [
		[[Gdk.KEY_q]							,controller.quit					],
		[[Gdk.KEY_o]							,windows.only		    			],
		[[Gdk.KEY_Right, Gdk.KEY_l]				,windows.navigate_right				],
		[[Gdk.KEY_L]							,windows.move_right					],
		[[Gdk.KEY_Down, Gdk.KEY_j]				,windows.navigate_down				],
		[[Gdk.KEY_J]							,windows.move_down					],
		[[Gdk.KEY_Left, Gdk.KEY_h]				,windows.navigate_left				],
		[[Gdk.KEY_H]							,windows.move_left					],
		[[Gdk.KEY_Up, Gdk.KEY_k]				,windows.navigate_up				],
		[[Gdk.KEY_K]							,windows.move_up					],
		[[Gdk.KEY_less]							,windows.decrease_width				],
		[[Gdk.KEY_greater]						,windows.increase_width				],
		[[Gdk.KEY_equal]						,windows.equalize					],
		[[Gdk.KEY_w, Gdk.KEY_W]					,windows.cycle						],
		[[Gdk.KEY_p]							,windows.navigate_to_previous		],
		[[Gdk.KEY_colon]						,controller.colon					],
		[[Gdk.KEY_Return]						,controller.enter					],
		[[Gdk.KEY_Escape, Gdk.KEY_bracketleft ]	,controller.escape					]
	]

	print(keys)
