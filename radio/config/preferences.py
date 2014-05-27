# -*- coding: utf-8 -*-
import os
import sys

from radio.database import db


def prefsRootPath():
    if sys.platform == "darwin":
            return os.path.expanduser("~/Library/Application Support/radio")
    elif sys.platform.startswith("win"):
            return os.path.join(os.environ['APPDATA'], "radio")
    else:
            return os.path.expanduser("~/.radio")


class Prefs():

    def __init__(self):
        # Check for ~/.ironworks
        if not os.path.isdir(prefsRootPath()):
                os.mkdir(prefsRootPath())

        self.db = db.Db(os.path.join(prefsRootPath(), "prefs.db"))
        #self.configDb = db.Db(os.path.join(prefsRootPath(), "config.db"))
        #query = self.configDb.query("SELECT name FROM sqlite_master")
        #query = query.fetchall()
        #print query

        self.db.beginTransaction()

        self.db.checkTable("radio_server_settings", [
            {"name": "name", "type": "text"},
            {"name": "value", "type": "text"}])

        self.db.checkTable("radio_misc_settings", [
            {"name": "key", "type": "int"},
            {"name": "value", "type": "text"},
            {"name": "description", "type": "text"},
            {"name": "type", "type": "text"},
            {"name": "options", "type": "text"}])

        self.db.checkTable("pandora", [
            {"name": "name", "type": "text"},
            {"name": "value", "type": "text"}])

        self.db.checkTable("radioStreams", [
            {"name": "name", "type": "text"},
            {"name": "value", "type": "text"}])

        self.db.checkTable("audioQuality", [
            {"name": "name", "type": "text"},
            {"name": "value", "type": "text"}])

        self.db.checkTable("client_keys", [
            {"name": "client", "type": "text"},
            {"name": "deviceModel", "type": "text"},
            {"name": "username", "type": "text"},
            {"name": "password", "type": "text"},
            {"name": "rpcUrl", "type": "text"},
            {"name": "encryptKey", "type": "text"},
            {"name": "decryptKey", "type": "text"},
            {"name": "version", "type": "text"}])

        default_audio_quality = 'mediumQuality'

        self.db.commitTransaction()

        # Check radio server defaults
        self.checkDefaults("radio_server_settings", {"name": "timesRun", "value": "0"})
        self.checkDefaults("radio_server_settings", {"name": "daemon", "value": "False"})
        self.checkDefaults("radio_server_settings", {"name": "pidfile", "value": "False"})
        self.checkDefaults("radio_server_settings", {"name": "pidFileName", "value": ""})
        self.checkDefaults("radio_server_settings", {"name": "port", "value": 7000})
        self.checkDefaults("radio_server_settings", {"name": "verbose", "value": "True"})
        self.checkDefaults("radio_server_settings", {"name": "development", "value": "True"})
        self.checkDefaults("radio_server_settings", {"name": "kiosk", "value": "False"})
        self.checkDefaults("radio_server_settings", {"name": "noupdate", "value": "True"})
        self.checkDefaults("radio_server_settings", {"name": "webroot", "value": ""})

        # Check radio misc defaults
        self.checkDefaults("radio_misc_settings", data={'key': 'show_currently_playing',
                                                     'value': '1',
                                                     'description': 'Show currently playing bar',
                                                     'type': 'select',
                                                     'options': "{'1': 'Yes', '2': 'Minimized', '0': 'No'}"})

        #Check Pandora defaults
        self.checkDefaults("pandora", {"name": "user", "value": ""})
        self.checkDefaults("pandora", {"name": "password", "value": ""})
        self.checkDefaults("pandora", {"name": "notify", "value": "True"})
        self.checkDefaults("pandora", {"name": "last_station_id", "value": ""})
        self.checkDefaults("pandora", {"name": "proxy", "value": ""})
        self.checkDefaults("pandora", {"name": "control_proxy", "value": ""})
        self.checkDefaults("pandora", {"name": "show_icon", "value": "False"})
        self.checkDefaults("pandora", {"name": "lastfm_key", "value": "False"})
        self.checkDefaults("pandora", {"name": "mediakeys", "value": "True"})
        self.checkDefaults("pandora", {"name": "screensaverpause", "value": "False"})
        self.checkDefaults("pandora", {"name": "volume", "value": 1.0})
        # If set, allow insecure permissions. Implements CVE-2011-1500
        self.checkDefaults("pandora", {"name": "unsafe_permissions", "value": "False"})
        self.checkDefaults("pandora", {"name": "audio_quality", "value": default_audio_quality})
        self.checkDefaults("pandora", {"name": "pandora_one", "value": "False"})
        self.checkDefaults("pandora", {"name": "force_client", "value": ""})

        self.checkDefaults("radioStreams", {"name": "NPR", "value": "http://nprdmp.ic.llnwd.net/stream/nprdmp_live01_mp3"})
        self.checkDefaults("radioStreams", {"name": "BBC News", "value": "http://bbcwssc.ic.llnwd.net/stream/bbcwssc_mp1_ws-eieuk"})

        self.checkDefaults("audioQuality", {"name": "highQuality", "value": "High"})
        self.checkDefaults("audioQuality", {"name": "mediumQuality", "value": "Medium"})
        self.checkDefaults("audioQuality", {"name": "lowQuality", "value": "Low"})

        self.checkDefaults("client_keys", {"client": "android-generic",
                                            "deviceModel": "android-generic",
                                            "username": "android",
                                            "password": "AC7IBG09A3DTSYM4R41UJWL07VLN8JI7",
                                            "rpcUrl": "//tuner.pandora.com/services/json/?",
                                            "encryptKey": "6#26FRL$ZWD",
                                            "decryptKey": "R=U!LH$O2B#",
                                            "version": "5"})

        self.checkDefaults("client_keys", {"client": "pandora-one",
                                            "deviceModel": "D01",
                                            "username": "pandora one",
                                            "password": "TVCKIBGS9AO9TSYLNNFUML0743LH82D",
                                            "rpcUrl": "//internal-tuner.pandora.com/services/json/?",
                                            "encryptKey": "2%3WCL*JU$MP]4",
                                            "decryptKey": "U#IO$RZPAB%VX2",
                                            "version": "5"})

    def getDb(self):
        return self.db

    def checkDefaults(self, table, data):
        cursor = self.db.select(table, where=data)
        if not cursor.fetchone():
            self.db.beginTransaction()
            self.db.insert(table, data)
            self.db.commitTransaction()

    def getPreference(self, table, name):
        cursor = self.db.select(table, where={"name": name})
        row = cursor.fetchone()
        if not row:
            raise Exception("No preference " + name)
        return row["value"]

    def getRadioSettingValue(self, key, default=None):
        try:
            data = self.db.select("radio_server_settings", where={"key": key}, what="value")
            value = data.fetchone()

            if value == '':
                return None

            return value

        except:
            return default

    def getPandora(self, name):
        cursor = self.db.select("pandora", where={"name": name})
        row = cursor.fetchone()
        if not row:
            raise Exception("No Pandora property named: " + name)
        return row["value"]

    def getPandoraUsername(self):
        username = self.getPandora("user")
        return username

    def getPandoraPassword(self):
        password = self.getPandora("password")
        return password

    def getPandoraOne(self):
        pandoraOne = self.getPandora("pandora_one")
        return pandoraOne

    def getPandoraProxy(self):
        proxy = self.getPandora("proxy")
        return proxy

    def getPandoraControlProxy(self):
        controlProxy = self.getPandora("control_proxy")
        return controlProxy

    def getPandoraAudioQuality(self):
        audioQuality = self.getPandora("audio_quality")
        return audioQuality

    def getPandoraAudioQualitySettings(self):
        cursor = self.db.select("audioQuality")
        row = cursor.fetchall()
        return row

    def getNotify(self):
        notify = self.getPandora("notify")
        return notify

    def getScreensaverPause(self):
        screensaverPause = self.getPandora("screensaverpause")
        return screensaverPause

    def getIcon(self):
        showIcon = self.getPandora("show_icon")
        return showIcon

    def getPandoraForceClient(self):
        forceClient = self.getPandora("force_client")
        return forceClient

    def getPandoraClient(self, client):
        cursor = self.db.select("client_keys", where={"client": client})
        row = cursor.fetchall()
        if not row:
            raise Exception("No Pandora client named: " + client)
        return row

    def getRadioStreams(self):
        cursor = self.db.select("radioStreams")
        row = cursor.fetchall()
        return row

    def getLastStationId(self):
        stationId = self.getPandora("last_station_id")
        return stationId

    def getTimesRun(self):
        return int(self.getPreference("radio_server_settings", "timesRun"))

    def getDaemon(self):
        return self.getPreference("radio_server_settings", "daemon")

    def getPidFile(self):
        return self.getPreference("radio_server_settings", "pidfile")

    def getPidFileName(self):
        return self.getPreference("radio_server_settings", "pidFileName")

    def getPort(self):
        return int(self.getPreference("radio_server_settings", "port"))

    def getVerbose(self):
        return self.getPreference("radio_server_settings", "verbose")

    def getDevelopment(self):
        return self.getPreference("radio_server_settings", "development")

    def getKiosk(self):
        return self.getPreference("radio_server_settings", "kiosk")

    def getNoUpdate(self):
        return self.getPreference("radio_server_settings", "noupdate")

    def incTimesRun(self):
        r = int(self.getPreference("timesRun"))
        self.db.beginTransaction()
        self.db.update("prefs", {"value": r + 1}, {"name": "timesRun"})
        self.db.commitTransaction()

    def setDaemon(self, value):
        self.db.beginTransaction()
        self.db.update("radio_server_settings", {"value": value}, {"name": "daemon"})
        self.db.commitTransaction()

    def setPidFile(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "pidfile"})
        self.db.commitTransaction()

    def setPidFileName(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "pidFileName"})
        self.db.commitTransaction()

    def setPort(self, port):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": port}, {"name": "port"})
        self.db.commitTransaction()

    def setVerbose(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "verbose"})
        self.db.commitTransaction()

    def setDevelopment(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "development"})
        self.db.commitTransaction()

    def setKiosk(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "kiosk"})
        self.db.commitTransaction()

    def setNoUpdate(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("radio_server_settings", {"value": value}, {"name": "noupdate"})
        self.db.commitTransaction()

    def setPandoraUsername(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "user"})
        self.db.commitTransaction()

    def setPandoraPassword(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "password"})
        self.db.commitTransaction()

    def setPandoraOne(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "pandora_one"})
        self.db.commitTransaction()

    def setPandoraProxy(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "proxy"})
        self.db.commitTransaction()

    def setPandoraControlProxy(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "control_proxy"})
        self.db.commitTransaction()

    def setPandoraAudioQuality(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "audio_quality"})
        self.db.commitTransaction()

    def setNotify(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "notify"})
        self.db.commitTransaction()

    def setScreensaverPause(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "screensaverpause"})
        self.db.commitTransaction()

    def setIcon(self, value):
        self.db.beginTransaction()
        self.db.insertOrUpdate("pandora", {"value": value}, {"name": "show_icon"})
        self.db.commitTransaction()

    def getRadioSettings(self):
        daemon = self.getDaemon()
        pidFile = self.getPidFile()
        pidFilename = self.getPidFileName()
        port = self.getPort()
        verbose = self.getVerbose()
        dev = self.getDevelopment()
        kiosk = self.getKiosk()
        update = self.getNoUpdate()

        data = ({'daemon': daemon,
                'pidFile': pidFile,
                'pidFilename': pidFilename,
                'port': port,
                'verbose': verbose,
                'dev': dev,
                'kiosk': kiosk,
                'update': update})
        return {'success': True, 'data': data}