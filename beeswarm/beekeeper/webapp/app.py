# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import json
import logging
import uuid
from flask import Flask, render_template, request, abort
from flask.ext.bootstrap import Bootstrap
from forms import NewHiveConfigForm, NewFeederConfigForm
from pony.orm import commit, select
from beeswarm.beekeeper.db.database import Feeder, Honeybee, Session, Hive, Classification

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = 'beeswarm-is-awesome'
Bootstrap(app)

logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/sessions')
def sessions_all():
    sessions = select(s for s in Session)
    return render_template('logs.html', sessions=sessions)


@app.route('/sessions/honeybees')
def sessions_honeybees():
    honeybees = select(h for h in Honeybee)
    return render_template('logs.html', sessions=honeybees)

@app.route('/sessions/attacks')
def sessions_attacks():
    attacks = select(a for a in Session if a.classification != Classification.get(type='honeybee') and
                                            a.classification != None)
    return render_template('logs.html', sessions=attacks)

@app.route('/ws/feeder_data', methods=['POST'])
def feeder_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)

    _feeder = Feeder.get(id=data['feeder_id'])
    _hive = Hive.get(id=data['hive_id'])

    _honeybee = Honeybee(id=data['id'],
                         timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
                         received=datetime.utcnow(),
                         protocol=data['protocol'],
                         username=data['login'],
                         password=data['password'],
                         destination_ip=data['server_host'],
                         destination_port=data['server_port'],
                         source_ip=data['source_ip'],
                         source_port=data['source_port'],
                         did_connect=data['did_connect'],
                         did_login=data['did_login'],
                         did_complete=data['did_complete'],
                         feeder=_feeder,
                         hive=_hive)

    commit()

    return ''

@app.route('/ws/hive_data', methods=['POST'])
def hive_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)
    logger.debug('Received: {0}'.format(data))

    _hive = Hive.get(id=data['hive_id'])
    #create if not found in the database

    for login_attempt in data['login_attempts']:
        _session = Session(id=login_attempt['id'],
                           timestamp=datetime.strptime(login_attempt['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
                           received=datetime.utcnow(),
                           protocol=data['protocol'],
                           #TODO: not all capabilities delivers login/passwords. This needs to be subclasses...
                           username=login_attempt['username'],
                           password=login_attempt['password'],
                           destination_ip='aaa',
                           destination_port=data['honey_port'],
                           source_ip=data['attacker_ip'],
                           source_port=data['attacker_source_port'],
                           hive=_hive)

    commit()
    return ''

@app.route('/ws/hive/config/<hive_id>', methods=['GET'])
def get_hive_config(hive_id):
    current_hive = Hive[hive_id]
    return current_hive.configuration

@app.route('/ws/feeder/config/<feeder_id>', methods=['GET'])
def get_feeder_config(feeder_id):
    current_feeder = Feeder[feeder_id]
    return current_feeder.configuration


@app.route('/ws/hive', methods=['GET', 'POST'])
def create_hive():
    form = NewHiveConfigForm()
    new_hive_id = str(uuid.uuid4())
    if form.validate_on_submit():
        config = {
            'general': {
                'hive_id': new_hive_id,
                'hive_ip': '192.168.1.1',
                'fetch_ip': False
            },
            'log_hpfeedslogger': {
                'enabled': False,
                'host': 'hpfriends.honeycloud.net',
                'port': 20000,
                'ident': '2wtadBoH',
                'secret': 'mJPyhNhJmLYGbDCt',
                'chan': 'beeswarm.hive',
                'port_mapping': '{}'
            },
            'log_beekeeper': {
                'enabled': False,
                'beekeeper_url': 'http://127.0.0.1:5000/ws/hive_data'
            },
            'log_syslog': {
                'enabled': False,
                'socket': '/dev/log'
            },
            "cap_ftp": {
                "enabled": form.ftp_enabled.data,
                "port": form.ftp_port.data,
                "max_attempts": form.ftp_max_attempts.data,
                "banner": form.ftp_banner.data
            },
            "cap_telnet": {
                "enabled": form.telnet_enabled.data,
                "port": form.telnet_port.data,
                "max_attempts": form.telnet_max_attempts.data
            },
            "cap_pop3": {
                "enabled": form.pop3_enabled.data,
                "port": form.pop3_port.data,
                "max_attempts": form.pop3_max_attempts.data
            },
            "cap_pop3s": {
                "enabled": form.pop3s_enabled.data,
                "port": form.pop3s_port.data,
                "max_attempts": form.pop3s_max_attempts.data
            },
            "cap_ssh": {
                "enabled": form.ssh_enabled.data,
                "port": form.ssh_port.data,
                "key": form.ssh_key.data
            },
            "cap_http": {
                "enabled": form.http_enabled.data,
                "port": form.http_port.data,
                "banner": form.http_banner.data
            },
            "cap_https": {
                "enabled": form.https_enabled.data,
                "port": form.https_port.data,
                "banner": form.https_banner.data
            },
            "cap_smtp": {
                "enabled": form.smtp_enabled.data,
                "port": form.smtp_port.data,
                "banner": form.smtp_banner.data
            },
            "cap_vnc": {
                "enabled": form.vnc_enabled.data,
                "port": form.vnc_port.data
            },
            "timecheck": {
                "enabled": True,
                "poll": 5,
                "ntp_pool": "pool.ntp.org"
            }
        }
        config_json = json.dumps(config)
        new_hive = Hive(id=new_hive_id, configuration=config_json)
        commit()
        return 'http://localhost:5000/ws/hive/config/'+new_hive_id

    return render_template('create-config.html', form=form, mode_name='Hive')

@app.route('/ws/feeder', methods=['GET', 'POST'])
def create_feeder():
    form = NewFeederConfigForm()
    new_feeder_id = str(uuid.uuid4())
    if form.validate_on_submit():
        config = {
            'general': {
                'feeder_id': new_feeder_id,
                'hive_id': None
            },
            'public_ip': {
                'fetch_ip': True
            },
            'bee_http': {
                'enabled': form.http_enabled.data,
                'server': form.http_server.data,
                'port': form.http_port.data,
                'timing': form.http_timing.data,
                'login': form.http_login.data,
                'password': form.http_password.data
            },
            'bee_pop3': {
                'enabled': form.pop3_enabled.data,
                'server': form.pop3_server.data,
                'port': form.pop3_port.data,
                'timing': form.pop3_timing.data,
                'login': form.pop3_login.data,
                'password': form.pop3_password.data
            },
            'bee_smtp': {
                'enabled': form.smtp_enabled.data,
                'server': form.smtp_server.data,
                'port': form.smtp_port.data,
                'timing': form.smtp_timing.data,
                'login': form.smtp_login.data,
                'password': form.smtp_password.data
            },
            'bee_vnc': {
                'enabled': form.vnc_enabled.data,
                'server': form.vnc_server.data,
                'port': form.vnc_port.data,
                'timing': form.vnc_timing.data,
                'login': form.vnc_login.data,
                'password': form.vnc_password.data
            },
            'bee_telnet': {
                'enabled': form.telnet_enabled.data,
                'server': form.telnet_server.data,
                'port': form.telnet_port.data,
                'timing': form.telnet_timing.data,
                'login': form.telnet_login.data,
                'password': form.telnet_password.data
            },
        }
        config_json = json.dumps(config)
        new_feeder = Feeder(id=new_feeder_id, configuration=config_json)
        commit()
        return 'http://localhost:5000/ws/feeder/config/'+new_feeder_id

    return render_template('create-config.html', form=form, mode_name='Feeder')

if __name__ == '__main__':
    app.run()
