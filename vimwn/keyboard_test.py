import threading
from Xlib.display import Display
import Xlib
from Xlib import X
import Xlib.XK
import sys
import signal
import time
display = None
root = None
import gi, os
gi.require_version('Wnck', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from gi.repository import Wnck, GdkX11
a = Gtk.accelerator_parse('<ctrl>e')
mapped_the_same, non_virtual_counterpart = Gdk.Keymap.map_virtual_modifiers(Gdk.Keymap.get_default(), a.accelerator_mods)
keymap = Gdk.Keymap.get_default()
rootwin = Gdk.get_default_root_window()
