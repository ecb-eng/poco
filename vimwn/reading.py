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
import gi, re, time, traceback, vimwn.commands
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from vimwn.view import NavigatorWindow
from vimwn.windows import Windows
from vimwn.applications import Applications
from vimwn.terminal import Terminal
from vimwn.hint import HintStatus
from vimwn.commands import Command
from vimwn.commands import CommandHistory
from vimwn.message import Messages
from vimwn.commands import CommandInput

HINT_LAUNCH_KEYS = [Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab]
HINT_LEFT = [Gdk.KEY_Left]
HINT_RIGHT = [Gdk.KEY_Right]
HINT_NAVIGATION_KEYS = HINT_LAUNCH_KEYS + HINT_LEFT + HINT_RIGHT
HINT_OPERATION_KEYS = [Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Return] + HINT_NAVIGATION_KEYS

HISTORY_NAVIGATION_KEYS = [Gdk.KEY_Up, Gdk.KEY_Down]


class Mode:

	NORMAL = 0
	KEY = 1
	COMMAND = 2


# TODO chain commands
class Reading:

	def __init__(self, configurations=None, windows=None):
		self.configurations = configurations
		self.cmd_handler_ids = []
		self.mode = Mode.NORMAL
		self.view = None
		self.windows = windows
		self.applications = Applications()
		self.terminal = Terminal()
		self.hint_status = HintStatus(self)
		self.messages = Messages(self, self.windows)
		self.command_history = CommandHistory()
		self.create_and_install_view()
		self._clean_command_state()
		self.messages.clean()

	def _clean_command_state(self):
		for handler_id in self.cmd_handler_ids:
			self.view.entry.disconnect(handler_id)
		self.cmd_handler_ids.clear()
		self.hint_status.clear_state()

	def _internal_reload(self, time):
		self._clean_command_state()
		if self.view:
			self.view.close()
		self.create_and_install_view()
		self.start(time)

	def create_and_install_view(self):
		self.view = NavigatorWindow(self, self.windows, self.messages)
		self.view.connect("focus-out-event", self._focus_out_callback)
		self.view.connect("key-press-event", self._window_key_press_callback)

	def set_normal_mode(self):
		self.mode = Mode.NORMAL
		self.view.hide()
		self.messages.clean()
		self._clean_command_state()

	def set_key_mode(self, event_time, error_message=None):
		self.mode = Mode.KEY
		self.windows.read_screen()
		if error_message:
			self.messages.add(error_message, 'error')
		self._clean_command_state()
		self.view.show(event_time)

	def set_command_mode(self, time):
		self.mode = Mode.COMMAND

		self.view.show(time)

		r_id = self.view.entry.connect("key-release-event", self.on_entry_key_release)
		p_id = self.view.entry.connect("key-press-event", self.on_entry_key_press)
		a_id = self.view.entry.connect("activate", self.on_command, None)

		self.cmd_handler_ids.extend([r_id, p_id, a_id])

	def in_command_mode(self):
		return self.mode == Mode.COMMAND

	#
	# CALLBACKS
	#
	def _focus_out_callback(self, widget, event):
		self.set_normal_mode()

	def _window_key_press_callback(self, widget, event):
		ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)

		if event.keyval == Gdk.KEY_Escape or (ctrl and event.keyval == Gdk.KEY_bracketleft):
			self.escape(CommandInput(time=event.time, keyval=event.keyval))
			return

		if self.in_command_mode():
			return

		if event.keyval == Gdk.KEY_colon and not ctrl:
			self.colon(CommandInput(time=event.time, keyval=event.keyval))
			return True

		if event.keyval == Gdk.KEY_Return:
			self.enter(CommandInput(time=event.time, keyval=event.keyval))
			return True

	def on_entry_key_release(self, widget, event):
		if event.keyval in HINT_OPERATION_KEYS:
			return False

		if not self.view.entry.get_text().strip():
			self.set_key_mode(event.time)
			return True

		if self.configurations.is_auto_hint():
			self.hint_status.hint(CommandInput(text=self.view.get_command()).parse())
		else:
			self.hint_status.clear_state()

		if self.hint_status.hinting:
			self.view.hint(self.hint_status.hints, self.hint_status.highlight_index, self.hint_status.should_auto_hint())
		else:
			self.view.clean_hints()

	def on_entry_key_press(self, widget, event):
		if event.keyval in HISTORY_NAVIGATION_KEYS:
			self.command_history.navigate_history(-1 if event.keyval == Gdk.KEY_Up else 1, self.view.get_command())
			self.view.set_command(self.command_history.current_command())
			self.view.clean_hints()
			self.hint_status.clear_state()
			return True
		else:
			self.command_history.reset_history_pointer()

		if event.keyval not in HINT_NAVIGATION_KEYS:
			return False

		if not self.hint_status.hinting and event.keyval in HINT_LAUNCH_KEYS:
			self.hint_status.hint(CommandInput(text=self.view.get_command()).parse())

		if self.hint_status.hinting:
			shift_mask = event.state & Gdk.ModifierType.SHIFT_MASK
			right = event.keyval in HINT_RIGHT or (event.keyval in HINT_LAUNCH_KEYS and not shift_mask )
			self.hint_status.cycle(1 if right else -1)
			if len(self.hint_status.hints) == 1:
				self.view.clean_hints()
			else:
				self.view.hint(self.hint_status.hints, self.hint_status.highlight_index, self.hint_status.should_auto_hint())
			self.view.set_command(self.hint_status.mount_input())

		return True

	def on_command(self, pane_owner, current):
		if self.mode != Mode.COMMAND:
			return

		gtk_time = Gtk.get_current_event_time()
		cmd = self.view.get_command()

		if self.hint_status.should_auto_hint():
			self.hint_status.cycle(1)
			cmd = self.hint_status.mount_input()

		self.command_history.append(cmd)

		if Command.has_multiple_commands(cmd):
			raise Exception('TODO: iterate multiple commands')

		command_input = CommandInput(time=gtk_time, text=cmd).parse()
		command = Command.get_matching_command(command_input)

		if command:
			try:
				command.function(command_input)
				self.windows.commit_navigation(gtk_time)
			except Exception as inst:
				msg = 'ERROR ({}) executing: {}'.format(str(inst), command_input.text)
				print(traceback.format_exc())
				self.set_key_mode(gtk_time, error_message=msg)
		else:
			self.set_key_mode(gtk_time, error_message='Not an editor command: ' + cmd)

	def execute(self, cmd):
		self.windows.read_screen()
		command_input = CommandInput(time=None, text=cmd).parse()
		command = Command.get_matching_command(command_input)
		command.function(command_input)

	#
	# COMMANDS
	#
	def start(self, c_in):
		event_time = c_in.time
		self.set_key_mode(event_time)

		self.view.present_with_time(event_time)
		self.view.get_window().focus(event_time)

	def reload(self, c_in):
		# TODO: add service reload
		# self.service.reload()
		self.applications.reload()
		self.terminal.reload()
		self.messages.clean()
		self._internal_reload(c_in.time)

	def edit(self, c_in):
		name = c_in.vim_command_parameter
		if not name or not name.strip():
			self.set_normal_mode()
			return

		app_name = None
		if self.applications.has_perfect_match(name.strip()):
			app_name = name.strip()

		possible_apps = self.applications.find_by_name(name)
		if possible_apps:
			app_name = possible_apps

		if app_name:
			try:
				self.applications.launch_by_name(app_name)
				self.set_normal_mode()
			except GLib.GError as exc:
				self.set_key_mode(time, error_message='Error launching ' + name)
		elif len(possible_apps) == 0:
			self.set_key_mode(time, error_message='No matching application for ' + name)
		else:
			self.set_key_mode(time, error_message='More than one application matches: ' + name)

	def bang(self, c_in):
		cmd = c_in.vim_command_parameter
		if not cmd:
			self.set_key_mode(time, error_message='ERROR: empty command')
			return
		stdout, stderr = self.terminal.execute(cmd)
		if stdout:
			for line in stdout.splitlines():
				self.messages.add(line, None)
		if stderr:
			for line in stderr.splitlines():
				self.messages.add(line, 'error')
		self.set_key_mode(c_in.time)

	def colon(self, c_in):
		if self.mode == Mode.KEY:
			self.set_command_mode(c_in.time)

	def enter(self, c_in):
		self.messages.clean()
		self.set_key_mode(c_in.time)

	def escape(self, c_in):
		self.set_normal_mode()

	def buffers(self, c_in):
		self.messages.list_buffers()
		self.set_key_mode(c_in.time)

	def debug(self, c_in):
		self.messages.add(self.windows.get_metadata_resume(), None)
		self.set_key_mode(c_in.time)

	def buffer(self, c_in):
		buffer_number_match = re.match(vimwn.commands.GROUPED_INDEXED_BUFFER_REGEX, c_in.text)
		if buffer_number_match:
			buffer_number = buffer_number_match.group(2)
			index = int(buffer_number) - 1
			if index < len(self.windows.buffers):
				self.windows.show(self.windows.buffers[index])
			else:
				self.set_key_mode(time, error_message='Buffer {} does not exist'.format(buffer_number))
		elif c_in.vim_command_parameter:
			window_title = c_in.vim_command_parameter
			w = self.windows.find_by_name(window_title)
			if w:
				self.windows.show(w)
			else:
				self.set_key_mode(c_in.time, error_message='No matching buffer for ' + window_title)
		else:
			self.set_key_mode(c_in.time)

	def delete_buffer(self, c_in):
		if re.match('^\s*(bdelete|bd)\s*([0-9]+\s*)+$', c_in.text):
			to_delete = []
			for number in re.findall(r'\d+', c_in.text):
				index = int(number) - 1
				if index < len(self.windows.buffers):
					to_delete.append(self.windows.buffers[index])
				else:
					self.set_key_mode(c_in.time, error_message='No buffers were deleted')
					return
			for window in to_delete:
				self.windows.remove(window, c_in.time)
			self.set_normal_mode()
		elif re.match('^\s*(bdelete|bd)\s+\w+\s*$', c_in.text):
			window_title = c_in.vim_command_parameter
			w = self.windows.find_by_name(window_title)
			if w:
				self.windows.remove(w, c_in.time)
				self.set_normal_mode()
			else:
				self.set_key_mode(c_in.time, error_message='No matching buffer for ' + window_title)
		else:
			if self.windows.active:
				self.windows.remove(self.windows.active, c_in.time)
				self.set_normal_mode()
			else:
				self.set_key_mode(c_in.time, error_message='There is no active window')

