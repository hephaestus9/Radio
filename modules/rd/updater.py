from flask import jsonify, render_template
from ironworks import app, logger, COMMITS_BEHIND, COMMITS_COMPARE_URL
from ironworks.updater import checkGithub, Update
from ironworks.tools import requires_auth
import ironworks

@app.route('/xhr/update_bar')
@requires_auth
def xhr_update_bar():
    if ironworks.COMMITS_BEHIND != 0:
        return render_template('includes/update_bar.html',
            commits = ironworks.COMMITS_BEHIND,
            compare_url = ironworks.COMMITS_COMPARE_URL,
        )
    else:
        return jsonify(up_to_date=True)

@app.route('/xhr/updater/check')
@requires_auth
def xhr_update_check():
    check = checkGithub()
    return jsonify(update=check)

@app.route('/xhr/updater/update')
@requires_auth
def xhr_update():
    updated = Update()
    if updated:
        logger.log('UPDATER :: Update complete', 'INFO')
    else:
        logger.log('UPDATER :: Update failed', 'ERROR')

    return jsonify(updated=updated)
