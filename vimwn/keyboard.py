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

def handle_event(event):
    if (event.type == X.KeyRelease):
        print("handle!")

def thread_function(name):
    global display,root
    print("Thread %s: starting", name)
    while 1:
        event = display.next_event()
        print("event")
        handle_event(event)
        display.allow_events(X.AsyncKeyboard, X.CurrentTime)
    print("Thread %s: finishing", name)

def main():
    # current display
    global display,root
    display = Display()
    root = display.screen().root

    # we tell the X server we want to catch keyPress event
    root.change_attributes(event_mask = X.KeyPressMask|X.KeyReleaseMask)
    # just grab the "1"-key for now
    root.grab_key(10, 0, True,X.GrabModeSync, X.GrabModeSync)

    x = threading.Thread(target=thread_function, args=(1,))
    x.setDaemon(True)
    x.start()
    input("asdf")

if __name__ == '__main__':
    main()
