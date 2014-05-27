
from flask import render_template, session, request, redirect, url_for, jsonify

from radio import app, pandoraplayer
from radio.config import preferences
#from pithos import pithos

title = None


@app.route('/')
def index():
    pandora = pandoraplayer
    stations = False
    song = False

    while not stations:
        stations = pandora.getStations()

    currentStation = pandora.getCurrentStation()

    while not song:
        song = pandora.getSong()
    global title
    title = pandora.getSongTitle()
    artist = pandora.getSongArtist()
    album = pandora.getSongAlbum()
    index = pandora.getSongIndex()

    thumbnail = pandora.getSongArt()
    volume = int(pandora.getVolume() * 100)
    upcomingSongs = pandora.getSongs()

    return render_template('index.html',
                            stations=stations,
                            currentStation=currentStation,
                            title=title,
                            artist=artist,
                            album=album,
                            thumbnail=thumbnail,
                            volume=volume,
                            upcomingSongs=upcomingSongs,
                            index=index)


@app.route('/pandoraPreferences')
def pandoraPreferences():
    pandora = pandoraplayer
    stations = False

    while not stations:
        stations = pandora.getStations()

    currentStation = pandora.getCurrentStation()

    prefs = preferences.Prefs()
    user = prefs.getPandoraUsername()
    password = prefs.getPandoraPassword()
    pandoraOne = prefs.getPandoraOne()
    if pandoraOne == "True":
        pandoraOne = "checked"
    else:
        pandoraOne = ""

    proxy = prefs.getPandoraProxy()
    control_proxy = prefs.getPandoraControlProxy()
    audio_quality = prefs.getPandoraAudioQuality()

    audio_quality_combo = prefs. getPandoraAudioQualitySettings()

    notify = prefs.getNotify()
    if notify == "True" or notify == "on":
        notify = "checked"
    else:
        notify = ""

    screensaverpause = prefs.getScreensaverPause()
    if screensaverpause == "True" or screensaverpause == "on":
        screensaverpause = "checked"
    else:
        screensaverpause = ""

    icon = prefs.getIcon()
    if icon == "True" or icon == "on":
        icon = "checked"
    else:
        icon = ""

    #self.lastfm_auth = LastFmAuth(self.__preferences, "lastfm_key", self.builder.get_object('lastfm_btn'))

    title = pandora.getSongTitle()
    artist = pandora.getSongArtist()
    album = pandora.getSongAlbum()
    index = pandora.getSongIndex()

    thumbnail = pandora.getSongArt()
    volume = int(pandora.getVolume() * 100)
    upcomingSongs = pandora.getSongs()

    return render_template('preferences.html',
                            username=user,
                            password=password,
                            pandoraOne=pandoraOne,
                            songsNotify=notify,
                            screensaverpause=screensaverpause,
                            icon=icon,
                            proxy=proxy,
                            controlProxy=control_proxy,
                            audioQuality=audio_quality,
                            audioQualitySettings=audio_quality_combo,
                            stations=stations,
                            currentStation=currentStation,
                            title=title,
                            artist=artist,
                            album=album,
                            thumbnail=thumbnail,
                            volume=volume,
                            upcomingSongs=upcomingSongs,
                            index=index)


@app.route('/save_settings', methods=['GET', 'POST'])
def save_settings():
    if request.method == 'POST':
        values = request.values
        prefs = preferences.Prefs()
        # TODO: fix this for first run
        try:
            audioQuality = values["audioQuality"]
            password = values["password"]
            username = values["user"]
            proxyURL = values["proxyURL"]
            controlProxyURL = values["controlProxyURL"]
            try:
                screensaver = values["screensaver"]
            except:
                screensaver = "off"

            try:
                icon = values["icon"]
            except:
                icon = "off"

            try:
                songsUpdate = values["songsUpdate"]
            except:
                songsUpdate = "off"

            try:
                pandoraOne = values["pandoraOne"]
            except:
                pandoraOne = "off"

            prefs.setPandoraUsername(username)
            prefs.setPandoraPassword(password)
            prefs.setPandoraAudioQuality(audioQuality)
            prefs.setPandoraProxy(proxyURL)
            prefs.setPandoraControlProxy(controlProxyURL)
            prefs.setScreensaverPause(screensaver)
            prefs.setIcon(icon)
            prefs.setNotify(songsUpdate)
            prefs.setPandoraOne(pandoraOne)

        except:
            print "request error: save_settings"

    return redirect(url_for('pandoraPreferences'))


@app.route('/changeStation', methods=['GET', 'POST'])
def changeStation():
    if request.method == 'POST':
        pandora = pandoraplayer
        values = request.values
        for value in values:
            station = value

        pandora.station_changed(station)


@app.route('/check_still_playing', methods=['GET', 'POST'])
def check_still_playing():
    if request.method == 'POST':
        pandora = pandoraplayer
        global title
        thisTitle = pandora.getSongTitle()
        if title != thisTitle:
            success = True
            return jsonify(success=success)


@app.route('/next_song', methods=['GET', 'POST'])
def next_song():
    if request.method == 'POST':
        pandora = pandoraplayer
        pandora.next_song()


@app.route('/stop_song', methods=['GET', 'POST'])
def stop_song():
    if request.method == 'POST':
        pandora = pandoraplayer
        pandora.stop()


@app.route('/play_pause', methods=['GET', 'POST'])
def play_pause():
    if request.method == 'POST':
        pandora = pandoraplayer
        state = pandora.isPlaying()
        if state:
            pandora.user_pause()
        else:
            pandora.user_play()