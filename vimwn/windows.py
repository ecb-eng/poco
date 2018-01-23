"""
Copyright 2017 Pedro Santos

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import gi, time, logging
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck

def get_x(window):
	return window.get_geometry().xp

def get_y(window):
	return window.get_geometry().yp

class Axis():
	def __init__(self, coordinate_function, position_mask, size_mask):
		self.coordinate_function = coordinate_function
		self.position_mask = position_mask
		self.size_mask = size_mask

VERTICAL = Axis(get_y, Wnck.WindowMoveResizeMask.Y, Wnck.WindowMoveResizeMask.HEIGHT)
HORIZONTAL = Axis(get_x, Wnck.WindowMoveResizeMask.X, Wnck.WindowMoveResizeMask.WIDTH)
HORIZONTAL.perpendicular_axis = VERTICAL
VERTICAL.perpendicular_axis = HORIZONTAL

class Windows():

	def __init__(self, controller):
		self.controller = controller
		Wnck.set_client_type(Wnck.ClientType.PAGER)
		self.active = None
		self.staging = False
		self.visibles =[]
		self.buffers =[]

	def remove(self, window):
		self.visibles.remove(window)
		self.buffers.remove(window)
		self._update_internal_state()

	def read_screen(self):
		del self.visibles[:]
		del self.buffers[:]
		self.screen = Wnck.Screen.get_default()
		self.screen.force_update()  #make sure we query X server

		active_workspace = self.screen.get_active_workspace()
		for wnck_window in self.screen.get_windows():
			if wnck_window.is_skip_tasklist():
				continue
			in_active_workspace = wnck_window.is_in_viewport(active_workspace)
			if in_active_workspace or self.controller.configurations.is_list_workspaces():
				self.buffers.append(wnck_window)
			if in_active_workspace and not wnck_window.is_minimized():
				self.visibles.append(wnck_window)
		self._update_internal_state()

	def _update_internal_state(self):
		self.active = None
		for w in reversed(self.screen.get_windows_stacked()):
			if w in self.visibles:
				self.active = w
				break
		self.x_line = list(self.visibles)
		self.x_line.sort(key=lambda w: w.get_geometry().xp * 1000 + w.get_geometry().yp)
		self.y_line = list(self.visibles)
		self.y_line.sort(key=lambda w: w.get_geometry().yp)

	def clear_state(self):
		self.screen = None
		self.active = None
		self.visibles =[]
		self.buffers =[]
		self.x_line = None
		self.y_line = None

	#Commits any staged change in the active window
	def commit_navigation(self, time):
		if self.staging:
			self.controller.open_window(self.active, time)
			self.staging = False

	def cycle(self, keyval, time):
		next_window = self.x_line[(self.x_line.index(self.active) + 1) % len(self.x_line)]
		self.active = next_window
		self.staging = True

	def move_right(self, keyval, time):
		self.move_active_window(HORIZONTAL, 0.5)

	def move_left(self, keyval, time):
		self.move_active_window(HORIZONTAL, 0)

	def move_up(self, keyval, time):
		self.move_active_window(VERTICAL, 0)

	def move_down(self, keyval, time):
		self.move_active_window(VERTICAL, 0.5)

	def equalize(self, keyval, time):
		left = None
		right = None
		for w in reversed(self.screen.get_windows_stacked()):
			if w in self.visibles:
				if not right:
					right = w
					continue
				if not left:
					left = w
					break
		if left and right:
			self.move_window(left, HORIZONTAL, 0)
			self.move_window(right, HORIZONTAL, 0.5)

	def move_active_window(self, axis, position):
		self.move_window(self.active, axis, position)

	def move_window(self, window, axis, position):
		if window.is_maximized():
			window.unmaximize()
		if window.is_maximized_horizontally():
			window.unmaximize_horizontally()
		if window.is_maximized_vertically():
			window.unmaximize_vertically()
		monitor_geo = self.controller.view.get_monitor_geometry()
		xp, yp, widthp, heightp = window.get_geometry()
		if axis == HORIZONTAL:
			xp = monitor_geo.x + monitor_geo.width * position
			widthp = monitor_geo.width / 2
			window.maximize_vertically()
		else:
			yp = monitor_geo.y + monitor_geo.height * position
			heightp = monitor_geo.height / 2
			window.maximize_horizontally()

		logging.debug("monitor: x=%d  w=%d y=%d  h=%d",  monitor_geo.x, monitor_geo.width, monitor_geo.y, monitor_geo.height)
		logging.debug("window: x=%d y=%d width=%d heigh=%d", xp, yp, widthp, heightp)

		window.set_geometry(Wnck.WindowGravity.STATIC, axis.position_mask, xp, yp, widthp, heightp)
		window.set_geometry(Wnck.WindowGravity.STATIC, axis.size_mask, xp, yp, widthp, heightp)

		self.staging = True

	def navigate_right(self, keyval, time):
		self.navigate(self.x_line, 1, HORIZONTAL, time)

	def navigate_left(self, keyval, time):
		self.navigate(self.x_line, -1, HORIZONTAL, time)

	def navigate_up(self, keyval, time):
		self.navigate(self.y_line, -1, VERTICAL, time)

	def navigate_down(self, keyval, time):
		self.navigate(self.y_line, 1, VERTICAL, time)

	def navigate(self, oriented_list, increment, axis, time):
		at_the_side = self.look_at(oriented_list, self.active, increment, axis)
		if at_the_side:
			self.active = at_the_side
			self.staging = True

	def look_at(self, oriented_list, reference, increment, axis):
		destination = self.get_candidates(oriented_list, reference, increment, axis.coordinate_function)
		coordinate_function = axis.perpendicular_axis.coordinate_function
		pos = coordinate_function(reference)
		if destination:
			return min(destination, key=lambda w: abs( pos - coordinate_function(w)))
		return None

	def get_candidates(self, oriented_list, reference, increment, position_function):
		line = []
		coordinate = position_function(reference)
		index = oriented_list.index(reference) + increment
		while index >= 0 and index < len(oriented_list):
			if position_function(oriented_list[index]) != coordinate:
				line.append(oriented_list[index])
			index = index + increment
		return line

