# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

# edited j.brian 10-7-16

import sys
import os, time
import gobject
gobject.threads_init()

# optional Launchpad integration
# this shouldn't crash if not found as it is simply used for bug reporting
try:
    import LaunchpadIntegration
    launchpad_available = True
except:
    launchpad_available = False
import pygst
pygst.require('0.10')
import gst

import cgi
import math
import webbrowser
import os
import urllib2
import json

from util import *
from gobject_worker import GObjectWorker
from plugin import load_plugins
from pandora import *
from radio import vlc

from radio.config import preferences
#from beaglebone import Beaglebone


def radioRootPath():
    if sys.platform == "darwin":
            return os.path.expanduser("~/Library/Application Support/radio/img")
    elif sys.platform.startswith("win"):
            return os.path.join(os.environ['APPDATA'], "radio/img")
    else:
            return os.path.expanduser("~/.radio/img")


def openBrowser(url):
    print "Opening %s" % url
    webbrowser.open(url)
    try:
        os.wait()  # workaround for http://bugs.python.org/issue5993
    except:
        pass


def get_album_art(url, song, index):
    if not os.path.isdir(os.path.realpath('../Radio/static/cache')):
                os.mkdir(os.path.realpath('../Radio/static/cache'))

    outfile = open(os.path.join(os.path.realpath('../Radio/static/cache'), str(index) + ".jpg"), "wb")
    outfile.write(urllib2.urlopen(url).read())
    outfile.close()
    art = str(index) + ".jpg"
    return art, song, index


class Pithos(object):

    def __init__(self, radiologger):
        self.radiologger = radiologger
        self.loop = gobject.MainLoop()
        self.prefs = preferences.Prefs()
        self.default_client_id = "android-generic"
        self.default_one_client_id = "pandora-one"
        self.default_album_art = None
        self.song_thumbnail = None
        self.songChanged = False

        #global launchpad_available
        #if False and launchpad_available:  # Disable this
            # see https://wiki.ubuntu.com/UbuntuDevelopment/Internationalisation/Coding for more information
            # about LaunchpadIntegration
        #    helpmenu = self.builder.get_object('menu_options')
        #    if helpmenu:
        #        LaunchpadIntegration.set_sourcepackagename('pithos')
        #        LaunchpadIntegration.add_items(helpmenu, 0, False, True)
        #    else:
        #        launchpad_available = False

        self.init_core()
        self.beaglebone = Beaglebone(self, self.radiologger, self.player)
        self.beaglebone.greenOn()
        self.plugins = {}
        load_plugins()
        self.stations_model = []
        self.songs_model = []

        self.pandora = make_pandora(self.radiologger)
        self.set_proxy()
        self.set_audio_quality()
        self.pandora_connect()

    def init_core(self):
        self.player = gst.element_factory_make("playbin2", "player")

        #self.player.props.flags |= (1 << 7)  # enable progressive download (GST_PLAY_FLAG_DOWNLOAD)

        self.time_format = gst.Format(gst.FORMAT_TIME)
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.on_gst_eos)
        self.bus.connect("message::buffering", self.on_gst_buffering)
        self.bus.connect("message::error", self.on_gst_error)
        self.player.connect("notify::volume", self.on_gst_volume)
        self.player.connect("notify::source", self.on_gst_source)

        self.stations_dlg = None

        self.playing = False
        self.current_song_index = None
        self.current_station = None
        self.current_station_name = None
        self.current_station_id = self.prefs.getLastStationId()

        self.buffer_percent = 100
        self.auto_retrying_auth = False
        self.have_stations = False
        self.playcount = 0
        self.gstreamer_errorcount_1 = 0
        self.gstreamer_errorcount_2 = 0
        self.gstreamer_error = ''
        self.waiting_for_playlist = False
        self.start_new_playlist = False

        self.worker = GObjectWorker(self.radiologger)
        self.songWorker = GObjectWorker(self.radiologger)
        self.art_worker = GObjectWorker(self.radiologger)

    def worker_run(self, fn, args=(), callback=None, message=None, context='net'):
        if context and message:
            self.radiologger.log(message, "INFO")

        if isinstance(fn, str):
            fn = getattr(self.pandora, fn)

        def cb(v=None):
            if callback:
                if v is None:
                    callback()
                else:
                    callback(v)

        def eb(e):

            def retry_cb():
                self.auto_retrying_auth = False
                if fn is not self.pandora.connect:
                    self.worker_run(fn, args, callback, message, context)

            if isinstance(e, PandoraAuthTokenInvalid) and not self.auto_retrying_auth:
                self.auto_retrying_auth = True
                self.radiologger.log("Automatic reconnect after invalid auth token", "INFO")
                self.pandora_connect("Reconnecting to pandora...", retry_cb)
            elif isinstance(e, PandoraAPIVersionError):
                self.api_update_dialog()
            elif isinstance(e, PandoraError):
                self.error_dialog(e.message, retry_cb, submsg=e.submsg)
            else:
                self.radiologger.log(e.traceback, "WARNING")
        self.worker.send(fn, args, cb, eb)

    def song_worker_run(self, fn, args=(), callback=None, message=None, context='net'):
        if context and message:
            self.radiologger.log(message, "INFO")

        if isinstance(fn, str):
            fn = getattr(self.pandora, fn)

        def cb(v=None):
            if callback:
                if v is None:
                    callback()
                else:
                    callback(v)

        def eb(e):

            def retry_cb():
                self.auto_retrying_auth = False
                if fn is not self.pandora.connect:
                    self.worker_run(fn, args, callback, message, context)

            if isinstance(e, PandoraAuthTokenInvalid) and not self.auto_retrying_auth:
                self.auto_retrying_auth = True
                self.radiologger.log("Automatic reconnect after invalid auth token", "INFO")
                self.pandora_connect("Reconnecting to pandora...", retry_cb)
            elif isinstance(e, PandoraAPIVersionError):
                self.api_update_dialog()
            elif isinstance(e, PandoraError):
                self.error_dialog(e.message, retry_cb, submsg=e.submsg)
            else:
                self.radiologger.log(e.traceback, "WARNING")
        self.songWorker.send(fn, args, cb, eb)

    def get_proxy(self):
        """ Get HTTP proxy, first trying preferences then system proxy """
        proxy = self.prefs.getPandoraProxy()

        if proxy != "":
            return proxy

        system_proxies = urllib.getproxies()
        if 'http' in system_proxies:
            return system_proxies['http']

        return None

    def set_proxy(self):
        # proxy preference is used for all Pithos HTTP traffic
        # control proxy preference is used only for Pandora traffic and
        # overrides proxy
        #
        # If neither option is set, urllib2.build_opener uses urllib.getproxies()
        # by default

        handlers = []
        global_proxy = self.prefs.getPandoraProxy()
        if global_proxy != "":
            handlers.append(urllib2.ProxyHandler({'http': global_proxy, 'https': global_proxy}))
        global_opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(global_opener)

        control_opener = global_opener
        control_proxy = self.prefs.getPandoraControlProxy()
        if control_proxy != "":
            control_opener = urllib2.build_opener(urllib2.ProxyHandler({'http': control_proxy, 'https': control_proxy}))
        self.worker_run('set_url_opener', (control_opener,))

    def set_audio_quality(self):
        self.worker_run('set_audio_quality', (self.prefs.getPandoraAudioQuality(),))

    def pandora_connect(self, message="Logging in to pandora...", callback=None):
        pandoraOne = self.prefs.getPandoraOne()
        if pandoraOne != "off" and pandoraOne != "False":
            client = self.prefs.getPandoraClient(self.default_one_client_id)
        else:
            client = self.prefs.getPandoraClient(self.default_client_id)

        # Allow user to override client settings
        #force_client = self.prefs.getPandoraForceClient()
        #if force_client in client_keys:
        #    client = client_keys[force_client]
        #elif force_client and force_client[0] == '{':
        #    try:
        #        client = json.loads(force_client)
        #    except:
        #        logging.error("Could not parse force_client json")

        args = (
            client[0],
            self.prefs.getPandoraUsername(),
            self.prefs.getPandoraPassword(),
        )

        def pandora_ready(*ignore):
            self.radiologger.log("Pandora connected", "INFO")
            self.beaglebone.greenOff()
            self.process_stations(self)
            if callback:
                callback()

        self.worker_run('connect', args, pandora_ready, message, 'login')

    def process_stations(self, *ignore):
        self.stations_model = []
        self.current_station = None
        self.current_station_name = None
        selected = None

        for i in self.pandora.stations:
            self.beaglebone.greenOn()
            if i.isQuickMix and i.isCreator:
                self.stations_model.append((i, "QuickMix"))
            self.beaglebone.greenOff()
        self.stations_model.append((None, 'sep'))
        for i in self.pandora.stations:
            self.beaglebone.greenOn()
            if not (i.isQuickMix and i.isCreator):
                self.stations_model.append((i, i.name))
            if i.id == self.current_station_id:
                self.radiologger.log("Restoring saved station: id = %s" % (i.id), "INFO")
                selected = i
                self.current_station_name = i.name
            self.beaglebone.greenOff()
        if not selected:
            selected = self.stations_model[0][0]
            self.current_station_name = self.stations_model[0][1]
        self.station_changed(selected, reconnecting=self.have_stations)
        self.have_stations = True

    def getStations(self):
        stations = False
        if self.have_stations:
            return self.stations_model
        return stations

    def getVolume(self):
        return self.player.get_property('volume')

    def getCurrentStation(self):
        return self.current_station_name

    def getSongArt(self):
        return self.current_song.artRadio

    def getSong(self):
        song = False
        try:
            self.current_song.title
            song = True
            return song
        except:
            return song

    def getSongs(self):
        return self.songs_model

    def getSongIndex(self):
        return self.current_song.index

    @property
    def current_song(self):
        if self.current_song_index is not None:
            return self.songs_model[self.current_song_index][0]

    def start_song(self, song_index):
        songs_remaining = len(self.songs_model) - song_index

        if songs_remaining <= 0:
            # We don't have this song yet. Get a new playlist.
            return self.get_playlist(start=True)
        elif songs_remaining == 1:
            # Preload next playlist so there's no delay
            self.get_playlist()

        prev = self.current_song

        self.stop()
        self.beaglebone.blueOff()
        self.current_song_index = song_index

        if prev:
            self.update_song_row(prev)

        if not self.current_song.is_still_valid():
            self.current_song.message = "Playlist expired"
            self.update_song_row()
            return self.next_song()

        if self.current_song.tired or self.current_song.rating == RATE_BAN:
            return self.next_song()

        self.buffer_percent = 100

        def playSong():

            self.player.set_property("uri", self.current_song.audioUrl)

            self.play()
            self.songChanged = False
            self.beaglebone.blueOn()
            self.playcount += 1

            self.current_song.start_time = time.time()

            #self.songs_treeview.scroll_to_cell(song_index, use_align=True, row_align=1.0)
            #self.songs_treeview.set_cursor(song_index, None, 0)
            self.radiologger.log("Radio - %s by %s" % (self.current_song.title, self.current_song.artist), "INFO")
            self.loop.run()

        def cb(v=None):
            if self.loop.is_running():
                self.loop.quit()
                #self.loop = gobject.MainLoop()

        self.song_worker_run(playSong, (), cb)
        self.radiologger.log("Starting song: index: %i" % (song_index), "INFO")
        #self.emit('song-changed', self.current_song)

    def getSongTitle(self):
        return self.current_song.title

    def getSongArtist(self):
        return self.current_song.artist

    def getSongAlbum(self):
        return self.current_song.album

    def next_song(self, *ignore):
        self.start_song(self.current_song_index + 1)
        self.songChanged = True

    def songChange(self):
        return self.songChanged

    def isPlaying(self):
        return self.playing

    def user_play(self, *ignore):
        self.play()

    def play(self):
        if not self.playing:
            self.playing = True
            self.player.set_state(gst.STATE_PLAYING)
            self.player.get_state(timeout=1)

        self.update_song_row()

    def user_pause(self, *ignore):
        # todo: make blue light flash
        self.pause()

    def pause(self):
        self.playing = False
        self.player.set_state(gst.STATE_PAUSED)

        self.update_song_row()
        if self.loop.is_running():
                self.loop.quit()

    def stop(self):
        prev = self.current_song
        if prev and prev.start_time:
            prev.finished = True
            try:
                prev.duration = self.player.query_duration(self.time_format, None)[0] / 1000000000
                prev.position = self.player.query_position(self.time_format, None)[0] / 1000000000
            except gst.QueryError:
                prev.duration = prev.position = None

        self.playing = False
        self.player.set_state(gst.STATE_NULL)
        if self.loop.is_running():
                self.loop.quit()

    def playpause(self, *ignore):
        if self.playing:
            self.pause()
        else:
            self.play()

    def playpause_notify(self, *ignore):
        if self.playing:
            self.user_pause()
        else:
            self.user_play()

    def get_playlist(self, start=False):
        self.beaglebone.redOff()
        self.start_new_playlist = self.start_new_playlist or start
        if self.waiting_for_playlist:
            return

        if self.gstreamer_errorcount_1 >= self.playcount and self.gstreamer_errorcount_2 >= 1:
            self.radiologger.log("Too many gstreamer errors. Not retrying", "WARNING")
            self.beaglebone.redOn()
            self.waiting_for_playlist = 1
            self.error_dialog(self.gstreamer_error, self.get_playlist)
            return

        def art_callback(t=None):
            picContent, song, index = t
            if index < len(self.songs_model) and self.songs_model[index][0] is song:  # in case the playlist has been reset
                self.radiologger.log("Downloaded album art for %i" % song.index, "INFO")
                song.artRadio = picContent.encode('ascii', 'ignore')
                self.songs_model[index][3] = picContent
                self.update_song_row(song)

        def callback(l):
            start_index = len(self.songs_model)
            for i in l:
                self.beaglebone.greenOn()
                i.index = len(self.songs_model)
                self.songs_model.append([i, '', '', self.default_album_art])
                self.update_song_row(i)

                i.art_pixbuf = None
                if i.artRadio:
                    self.art_worker.send(get_album_art, (i.artRadio, i, i.index), art_callback)

                self.beaglebone.greenOff()

            if self.start_new_playlist:
                self.start_song(start_index)

            self.gstreamer_errorcount_2 = self.gstreamer_errorcount_1
            self.gstreamer_errorcount_1 = 0
            self.playcount = 0
            self.waiting_for_playlist = False
            self.start_new_playlist = False

        self.waiting_for_playlist = True
        self.worker_run(self.current_station.get_playlist, (), callback, "Getting songs...")

    def error_dialog(self, message, retry_cb, submsg=None):
        self.beaglebone.redOn()
        #dialog = self.builder.get_object("error_dialog")

        #dialog.props.text = message
        #dialog.props.secondary_text = submsg

        #response = dialog.run()
        #dialog.hide()

        #if response == 2:
        #    self.gstreamer_errorcount_2 = 0
        #    logging.info("Manual retry")
        #    return retry_cb()
        #elif response == 3:
        #    self.show_preferences()

    def fatal_error_dialog(self, message, submsg):
        self.beaglebon.redOn()
        dialog = self.builder.get_object("fatal_error_dialog")
        dialog.props.text = message
        dialog.props.secondary_text = submsg

        response = dialog.run()
        dialog.hide()

        self.quit()

    def api_update_dialog(self):
        dialog = self.builder.get_object("api_update_dialog")
        response = dialog.run()
        if response:
            openBrowser("http://kevinmehall.net/p/pithos/itbroke?utm_source=pithos&utm_medium=app&utm_campaign=%s" % VERSION)
        self.quit()

    def station_index(self, station):
        return [i[0] for i in self.stations_model].index(station)

    def station_changed(self, station, reconnecting=False):
        # print station, type(station)
        if station is self.current_station:
            return

        for availableStation in self.stations_model:
            self.beaglebone.greenOn()
            try:
                if availableStation[0].id == station:
                    station = availableStation[0]
                    self.current_station_name = availableStation[1]
                    # print self.current_station_name
                    self.beaglebone.greenOff()
            except:
                self.beaglebone.greenOff()

        self.waiting_for_playlist = False
        if not reconnecting:
            self.stop()
            self.beaglebone.blueOff()
            self.current_song_index = None
            self.songs_model = []

        self.radiologger.log("Selecting station %s; total = %i" % (station.id, len(self.stations_model)), "INFO")
        self.current_station_id = station.id
        self.current_station = station
        if not reconnecting:
            self.get_playlist(start=True)
        #self.stations_combo.set_active(self.station_index(station))

    def on_gst_eos(self, bus, message):
        if self.loop.is_running():
                self.loop.quit()
        self.radiologger.log("EOS", "INFO")
        self.next_song()

    def on_gst_error(self, bus, message):
        err, debug = message.parse_error()
        self.radiologger.log("Gstreamer error: %s, %s, %s" % (err, debug, err.code), "ERROR")
        if self.current_song:
            self.current_song.message = "Error: " + str(err)

        if err.code is int(gst.CORE_ERROR_MISSING_PLUGIN):
            self.radiologger.log("Missing codec: GStreamer is missing a plugin", "ERROR")
            return

        self.gstreamer_error = str(err)
        self.gstreamer_errorcount_1 += 1
        self.next_song()

    def on_gst_buffering(self, bus, message):
        percent = message.parse_buffering()
        self.buffer_percent = percent
        if percent < 100:
            self.player.set_state(gst.STATE_PAUSED)
        elif self.playing:
            self.player.set_state(gst.STATE_PLAYING)
        self.update_song_row()

    def set_volume_cb(self, volume):
        # Convert to the cubic scale that the volume slider uses
        scaled_volume = math.pow(volume, 1.0 / 3.0)
        self.volume.handler_block_by_func(self.on_volume_change_event)
        self.volume.set_property("value", scaled_volume)
        self.volume.handler_unblock_by_func(self.on_volume_change_event)
        self.preferences['volume'] = volume

    def on_gst_volume(self, player, volumespec):
        pass
        #vol = self.player.get_property('volume')
        #gobject.idle_add(self.set_volume_cb, vol)

    def on_gst_source(self, player, params):
        """ Setup httpsoupsrc to match Pithos proxy settings """
        soup = player.props.source.props
        proxy = self.get_proxy()
        if proxy and hasattr(soup, 'proxy'):
            scheme, user, password, hostport = parse_proxy(proxy)
            soup.proxy = hostport
            soup.proxy_id = user
            soup.proxy_pw = password

    def song_text(self, song):
        title = cgi.escape(song.title)
        artist = cgi.escape(song.artist)
        album = cgi.escape(song.album)
        msg = []
        if song is self.current_song:
            try:
                dur_int = self.player.query_duration(self.time_format, None)[0]
                dur_str = self.format_time(dur_int)
                pos_int = self.player.query_position(self.time_format, None)[0]
                pos_str = self.format_time(pos_int)
                msg.append("%s / %s" % (pos_str, dur_str))
                if not self.playing:
                    msg.append("Paused")
            except gst.QueryError:
                pass
            if self.buffer_percent < 100:
                msg.append("Buffering (%i%%)" % self.buffer_percent)
        if song.message:
            msg.append(song.message)
        msg = " - ".join(msg)
        if not msg:
            msg = " "
        return "<b><big>%s</big></b>\nby <b>%s</b>\n<small>from <i>%s</i></small>\n<small>%s</small>" % (title, artist, album, msg)

    def song_icon(self, song):
        pass
        """if song.tired:
            return gtk.STOCK_JUMP_TO
        if song.rating == RATE_LOVE:
            return gtk.STOCK_ABOUT
        if song.rating == RATE_BAN:
            return gtk.STOCK_CANCEL"""

    def update_song_row(self, song=None):
        if song is None:
            song = self.current_song
        if song:
            self.songs_model[song.index][1] = self.song_text(song)
            self.songs_model[song.index][2] = self.song_icon(song)
        return self.playing

    def format_time(self, time_int):
        time_int = time_int / 1000000000
        s = time_int % 60
        time_int /= 60
        m = time_int % 60
        time_int /= 60
        h = time_int

        if h:
            return "%i:%02i:%02i" % (h, m, s)
        else:
            return "%i:%02i" % (m, s)

    def selected_song(self):
        sel = self.songs_treeview.get_selection().get_selected()
        if sel:
            return self.songs_treeview.get_model().get_value(sel[1], 0)

    def love_song(self, song=None):
        song = song or self.current_song

        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_LOVE,), callback, "Loving song...")

    def ban_song(self, song=None):
        song = song or self.current_song

        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_BAN,), callback, "Banning song...")
        if song is self.current_song:
            self.next_song()

    def unrate_song(self, song=None):
        song = song or self.current_song

        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.rate, (RATE_NONE,), callback, "Removing song rating...")

    def tired_song(self, song=None):
        song = song or self.current_song

        def callback(l):
            self.update_song_row(song)
            self.emit('song-rating-changed', song)
        self.worker_run(song.set_tired, (), callback, "Putting song on shelf...")
        if song is self.current_song:
            self.next_song()

    def bookmark_song(self, song=None):
        song = song or self.current_song
        self.worker_run(song.bookmark, (), None, "Bookmarking...")

    def bookmark_song_artist(self, song=None):
        song = song or self.current_song
        self.worker_run(song.bookmark_artist, (), None, "Bookmarking...")

    def on_menuitem_love(self, widget):
        self.love_song(self.selected_song())

    def on_menuitem_ban(self, widget):
        self.ban_song(self.selected_song())

    def on_menuitem_unrate(self, widget):
        self.unrate_song(self.selected_song())

    def on_menuitem_tired(self, widget):
        self.tired_song(self.selected_song())

    def on_menuitem_info(self, widget):
        song = self.selected_song()
        openBrowser(song.songDetailURL)

    def on_menuitem_bookmark_song(self, widget):
        self.bookmark_song(self.selected_song())

    def on_menuitem_bookmark_artist(self, widget):
        self.bookmark_song_artist(self.selected_song())

    def on_treeview_button_press_event(self, treeview, event):
        x = int(event.x)
        y = int(event.y)
        thisTime = event.time
        pthinfo = treeview.get_path_at_pos(x, y)
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor(path, col, 0)

            if event.button == 3:
                rating = self.selected_song().rating
                self.song_menu_love.set_property("visible", rating != RATE_LOVE)
                self.song_menu_unlove.set_property("visible", rating == RATE_LOVE)
                self.song_menu_ban.set_property("visible", rating != RATE_BAN)
                self.song_menu_unban.set_property("visible", rating == RATE_BAN)

                self.song_menu.popup(None, None, None, event.button, thisTime)
                return True

            if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
                self.radiologger.log("Double clicked on song %s", self.selected_song().index, "INFO")
                if self.selected_song().index <= self.current_song_index:
                    return False
                self.start_song(self.selected_song().index)

    def on_volume_change_event(self, volumebutton, value):
        # Use a cubic scale for volume. This matches what PulseAudio uses.
        volume = math.pow(value, 3)
        self.player.set_property("volume", volume)
        self.preferences['volume'] = volume

    def station_properties(self, *ignore):
        openBrowser(self.current_station.info_url)

    #def report_bug(self, *ignore):
    #    openBrowser("https://bugs.launchpad.net/pithos")

    def stations_dialog(self, *ignore):
        if self.stations_dlg:
            self.stations_dlg.present()
        else:
            self.stations_dlg = StationsDialog.NewStationsDialog(self)
            self.stations_dlg.show_all()

    def refresh_stations(self, *ignore):
        self.worker_run(self.pandora.get_stations, (), self.process_stations, "Refreshing stations...")

    def on_destroy(self, widget, data=None):
        """on_destroy - called when the PithosWindow is close. """
        self.stop()
        self.beaglebone.blueOff()
        self.preferences['last_station_id'] = self.current_station_id
        self.prefs_dlg.save()
        gtk.main_quit()


try:
    import Adafruit_BBIO.ADC as adc
    import Adafruit_BBIO.GPIO as gpio
    beaglebone = True
except:
    beaglebone = False

import threading
from random import choice


class Beaglebone(Pithos):

    def __init__(self, pithos, radiologger, player):
        self.volumePot = "AIN5"
        self.stationPot = "AIN3"
        self.radiologger = radiologger
        self.player = player
        self.common = "P8_10"
        self.red = "P8_12"
        self.green = "P8_14"
        self.blue = "P8_16"
        self.pithos = pithos

        if beaglebone:
            adc.setup()
            self.radioPowerAndVolume()
            gpio.setup(self.common, gpio.OUT)
            gpio.setup(self.red, gpio.OUT)
            gpio.setup(self.green, gpio.OUT)
            gpio.setup(self.blue, gpio.OUT)
            gpio.output(self.common, gpio.LOW)
            gpio.output(self.red, gpio.LOW)
            gpio.output(self.green, gpio.LOW)
            gpio.output(self.blue, gpio.LOW)

    def radioPowerAndVolume(self):
        def getVolumeAndStationValue():
            prevStation = 0
            while True:
                sample = 0
                volReading = 0
                statReading = 0
                while sample < 10:
                    volReading += adc.read(self.volumePot)
                    time.sleep(0.01)
                    statReading += adc.read(self.stationPot)
                    sample += 1
                    time.sleep(0.05)

                volReading = volReading / 10.0
                statReading = statReading * 100

                currStation = statReading
                #print statReading, currStation

                if currStation > prevStation + 2 or currStation < prevStation - 2:
                    #print prevStation, currStation
                    if self.pithos.have_stations:
                            stationIds = []
                            stations = self.pithos.getStations()
                            for myStation in stations:
                                try:
                                    stationIds.append(myStation[0].id)
                                except:
                                    #probably just the seperator
                                    pass
                            newStation = choice(stationIds)
                            print newStation, type(newStation)
                            self.pithos.station_changed(newStation)

                    prevStation = currStation

                volume = volReading
                volString = "%.2f" % round(volume, 2)

                previousVolume = self.player.get_property('volume')
                prevVolString = "%.2f" % round(previousVolume, 2)

                if volString != prevVolString:
                    # print previousVolume, volume
                    self.player.set_property('volume', volume)

        thread = threading.Thread(target=getVolumeAndStationValue, args=())
        thread.start()

    def redOn(self):
        if beaglebone:
            gpio.output(self.red, gpio.HIGH)

    def redOff(self):
        if beaglebone:
            gpio.output(self.red, gpio.LOW)

    def greenOn(self):
        if beaglebone:
            gpio.output(self.green, gpio.HIGH)

    def greenOff(self):
        if beaglebone:
            gpio.output(self.green, gpio.LOW)

    def blueOn(self):
        if beaglebone:
            gpio.output(self.blue, gpio.HIGH)

    def blueOff(self):
        if beaglebone:
            gpio.output(self.blue, gpio.LOW)
