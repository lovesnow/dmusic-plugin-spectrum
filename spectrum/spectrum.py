#! /usr/bin/env python
# -*- coding: utf-8 -*-

import gtk
import gst
import cairo

from player import Player

from collections import namedtuple
Rect = namedtuple('Rectangle', 'x y width height')

LINEAR_COLORS = [ 
                 (1.0, 0.9176470588235294, 0.5764705882352941), 
                 (1.0, 0.8392156862745098, 0.19215686274509805)]

# LINEAR_COLORS = [
#                  (0.4666666666666667, 0.8196078431372549, 1.0), 
#                  (0.2549019607843137, 0.6, 0.8352941176470589)]


LINEAR_POS = [0.3, 0.8]


class SpectrumPlayer(gtk.Window):
    
    def __init__(self):
        super(SpectrumPlayer, self).__init__()
        
        # init 
        self.spect_height = 100
        self.spect_bands = 64
        self.spect_atom = 64.0
        self.height_scale = 1.0
        self.band_width = 6
        self.band_interval = 3
        self.spect_data = None
        
        try:
            self.spectrum = gst.element_factory_make("spectrum", "spectrum")
            self.spectrum.set_property("bands", self.spect_bands)
            self.spectrum.set_property("threshold", -80)
            self.spectrum.set_property("message", True)
            # self.spectrum.set_property("multi-channel", True)
            
        except gst.PluginNotFoundError:    
            self.spectrum = None
        else:    
            pass
            
            
        Player.bin.connect("spectrum-data-found", self.on_event_load_spect)
        Player.bin.connect("tee-removed", self.on_player_tee_removed)
        
        self.set_colormap(gtk.gdk.Screen().get_rgba_colormap())
        self.set_default_size(self.adjust_width, self.spect_height)
        self.connect("expose-event", self.on_expose_event)
        self.connect("configure-event", self.on_configure_event)
        
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK |
                                   gtk.gdk.BUTTON_RELEASE_MASK |
                                   gtk.gdk.POINTER_MOTION_MASK)
        
        self.drag_flag = False
        self.mouse_x = self.mouse_y = 0
        self.old_x = self.old_y = 0
        self.set_decorated(False)
        self.set_keep_above(True)
        
        self.connect("expose-event", self.on_expose_event)
        self.connect("button-press-event", self.on_button_press)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-release-event", self.on_button_release)
        
    def enable(self):    
        Player.bin.xfade_add_filter(self.spectrum)
        self.show_all()        
        
    def disable(self):    
        Player.bin.xfade_remove_filter(self.spectrum)
        self.hide_all()
        
    def on_player_tee_removed(self, pbin, tee, element):    
        if element != self.spectrum:
            return
        self.spectrum.set_state(gst.STATE_NULL)
        
    @property 
    def adjust_width(self):    
        return (self.band_width + self.band_interval) * self.spect_bands
        
    def on_expose_event(self, widget, event):    
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
        cr.rectangle(0, 0, rect.width, rect.height)
        cr.fill()
        
        cr.set_operator(cairo.OPERATOR_OVER)
        self.draw_spectrum(cr)
        
        return True
        
        
    def delayed_idle_spectrum_update(self, spect):    
        self.spect_data = spect
        self.queue_draw()
        
        return False
    
    def on_event_load_spect(self, obj, magnitude_list):
        spect = map(lambda i: i * self.height_scale, magnitude_list)
        gtk.idle_add(self.delayed_idle_spectrum_update, spect)        
    
    def on_configure_event(self, widget, event):
        self.spect_height = event.height
        self.height_scale = event.height / self.spect_atom
        self.spect_bands = event.width / (self.band_width + self.band_interval)
        
        self.spectrum.set_property("bands", self.spect_bands)
        return False
    
    def draw_spectrum(self, cr):
        start = 5
        data = self.spect_data
        if data:
            for i in range(self.spect_bands):
                cr.push_group()
                cr.set_source_rgb(1, 1, 1)
                rect = Rect(start, -data[i], self.band_width, self.spect_height + data[i])

                
                pattern = cairo.LinearGradient(rect.x, rect.y, rect.x, rect.y + rect.height)
                for i, each_linear in enumerate(LINEAR_COLORS):
                    pattern.add_color_stop_rgb(LINEAR_POS[i],
                                               each_linear[0],
                                               each_linear[1],
                                               each_linear[2])
            
                    cr.set_source(pattern)    
                
                cr.rectangle(*rect)                                
                cr.fill()
                cr.pop_group_to_source()
                cr.paint_with_alpha(0.5)
                start += self.band_width + self.band_interval
                
                
    def on_button_press(self, widget, event):
        if event.button == 1:
            self.drag_flag = True
            self.old_x, self.old_y = widget.get_position()
            self.mouse_x, self.mouse_y = event.x_root, event.y_root
            
    def on_motion_notify(self, widget, event):        
        x = max(self.old_x + (event.x_root - self.mouse_x), 0)
        y = max(self.old_y + (event.y_root - self.mouse_y), 0)
        widget.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
        if self.drag_flag:
            new_x, new_y = self.adjust_move_coordinate(widget, x, y)
            widget.move(new_x, new_y)
            
    def on_button_release(self, widget, event):        
        self.drag_flag = False
        
        
    def adjust_move_coordinate(self, widget, x, y):
        screen = widget.get_screen()
        w, h = widget.get_size()
        screen_w, screen_h = screen.get_width(), screen.get_height()
        
        if x + w > screen_w:
            x = screen_w - w
           
        if y + h > screen_h:    
            y = screen_h - h
            
        return (int(x), int(y))
