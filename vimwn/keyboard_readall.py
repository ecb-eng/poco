from Xlib import X
from Xlib.ext import record
from Xlib.display import Display
from Xlib.protocol import rq


def handler(reply):
    data = reply.data
    while len(data):
        event, data = rq.EventField(None).parse_binary_value(data, display.display, None, None)
        print event.detail

        if event.type == X.KeyPress:
            print 'pressed'
        elif event.type == X.KeyRelease:
            print 'released'

display = Display()
context = display.record_create_context(0, [record.AllClients], [{
    'core_requests': (0, 0),
    'core_replies': (0, 0),
    'ext_requests': (0, 0, 0, 0),
    'ext_replies': (0, 0, 0, 0),
    'delivered_events': (0, 0),
    'device_events': (X.KeyReleaseMask, X.ButtonReleaseMask),
    'errors': (0, 0),
    'client_started': False,
    'client_died': False,
}])
display.record_enable_context(context, handler)
display.record_free_context(context)

while True:
    display.screen().root.display.next_event()
