"""
Copyright 2017 Pedro Santos <pedrosans@gmail.com>

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

import ctypes

x11 = ctypes.cdll.LoadLibrary('libX11.so')
x11.XInitThreads()
# add python lock to Xlib internals
from Xlib import threaded

import os, gi, signal, setproctitle, logging
import poco.commands
import poco.configurations as configurations

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from poco.reading import Reading
from gi.repository import GObject, Gtk, GLib, Gdk
from poco.status import StatusIcon
from poco.keyboard import KeyboardListener
from poco.layout import LayoutManager
from poco.windows import Windows
from poco.commands import CommandInput
from poco.remote import NavigatorBusService

SIGINT = getattr(signal, "SIGINT", None)
SIGTERM = getattr(signal, "SIGTERM", None)
SIGHUP = getattr(signal, "SIGHUP", None)

listener = bus_object = status_icon = None
windows = Windows(configurations.is_list_workspaces())
GObject.threads_init()
reading = Reading(configurations=configurations, windows=windows)
layout_manager = LayoutManager(
	reading.windows, remove_decorations=configurations.is_remove_decorations())


def start():
	global listener, bus_object, status_icon
	imported = False
	try:
		import importlib.util
		spec = importlib.util.spec_from_file_location("module.name", configurations.get_custom_mappings_module_path())
		mappings = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mappings)
		imported = True
	except FileNotFoundError as e:
		print(
			'info: it is possible to customize poco bindings by in {}'.format(
				configurations.get_custom_mappings_module_path()))
	if not imported:
		import poco.mappings as mappings

	# as soon as possible so new instances as notified
	bus_object = NavigatorBusService(stop)
	configure_process()
	map_commands()

	listener = KeyboardListener(callback=keyboard_listener, on_error=stop)

	for key in mappings.keys:
		listener.bind(key)

	listener.start()

	status_icon = StatusIcon(configurations, layout_manager, stop_function=stop)
	status_icon.activate()

	Gtk.main()

	print("Ending poco service, pid: {}".format(os.getpid()))


def map_commands():
	import poco.mappings as mappings
	for command in mappings.commands:
		poco.commands.add(command)


def keyboard_listener(key, x_key_event, multiplier=1):
	GLib.idle_add(
		_inside_main_loop, key, x_key_event, multiplier,
		priority=GLib.PRIORITY_HIGH)


def _inside_main_loop(key, x_key_event, multiplier):
	command_input = CommandInput(
		time=x_key_event.time, keyval=x_key_event.keyval, parameters=key.parameters)

	for i in range(multiplier):
		key.function(command_input)

	windows.commit_navigation(x_key_event.time)

	if len(key.accelerators) > 1:
		reading.set_normal_mode()

	return False


# TODO: remove
def reload():
	configurations.reload()
	status_icon.reload()


def configure_process():
	# https://lazka.github.io/pgi-docs/GLib-2.0/functions.html#GLib.log_set_handler
	GLib.log_set_handler(None, GLib.LogLevelFlags.LEVEL_WARNING, log_function)
	GLib.log_set_handler(None, GLib.LogLevelFlags.LEVEL_ERROR, log_function)
	GLib.log_set_handler(None, GLib.LogLevelFlags.LEVEL_CRITICAL, log_function)

	setproctitle.setproctitle("poco")

	for sig in (SIGINT, SIGTERM, SIGHUP):
		install_glib_handler(sig)


def install_glib_handler(sig):
	unix_signal_add = None

	if hasattr(GLib, "unix_signal_add"):
		unix_signal_add = GLib.unix_signal_add
	elif hasattr(GLib, "unix_signal_add_full"):
		unix_signal_add = GLib.unix_signal_add_full

	if unix_signal_add:
		unix_signal_add(GLib.PRIORITY_HIGH, sig, unix_signal_handler, sig)
	else:
		print("Can't install GLib signal handler, too old gi.")


def unix_signal_handler(*args):
	signal_val = args[0]
	if signal_val in (1, SIGHUP, 2, SIGINT, 15, SIGTERM):
		stop()


def release_bus_object():
	global bus_object
	if bus_object:
		bus_object.release()
		bus_object = None


def stop():
	GLib.idle_add(Gtk.main_quit, priority=GLib.PRIORITY_HIGH)
	listener.stop()
	release_bus_object()


def show_warning(error):
	error_dialog = Gtk.MessageDialog(
		None, Gtk.DialogFlags.MODAL, Gtk.MessageType.WARNING,
		Gtk.ButtonsType.CLOSE, error, title="poco - warning")
	error_dialog.run()
	error_dialog.destroy()


def show_error(error):
	error_dialog = Gtk.MessageDialog(
		None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
		Gtk.ButtonsType.CLOSE, error, title="poco error")
	error_dialog.run()
	error_dialog.destroy()


def log_function(log_domain, log_level, message):
	if log_level in (GLib.LogLevelFlags.LEVEL_ERROR, GLib.LogLevelFlags.LEVEL_CRITICAL):
		logging.error('GLib log[%s]:%s', log_domain, message)
		show_error(message)
		Exception(message)
	else:
		logging.warning('GLib log[%s]:%s', log_domain, message)
		show_warning(message)
