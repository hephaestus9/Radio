from flask import render_template
from radio import app, LOG_FILE
from radio import radiologger
from radioLib.pastebin.pastebin import PastebinAPI
import radio


@app.route('/xhr/log')
def xhr_log():
    return render_template('dialogs/log_dialog.html',
        log=radio.LOG_LIST,
    )


@app.route('/xhr/log/pastebin')
def xhr_log_pastebin():
    file = open(LOG_FILE)
    log = []
    log_str = ''

    for line in reversed(file.readlines()):
        log.append(line.rstrip())
        log_str += line.rstrip()
        log_str += '\n'

    file.close()
    x = PastebinAPI()
    try:
        url = x.paste('', log_str)
        radiologger.log('LOG :: Log successfully uploaded to %s' % url, 'INFO')
    except Exception as e:
        radiologger.log('LOG :: Log failed to upload - %s' % e, 'INFO')

    return render_template('dialogs/log_dialog.html',
        log=log,
        url=url,
    )
