#!/usr/bin/env python3

import os
import sys
import signal
import logging
import argparse
import requests

from flask import Flask, request, abort, jsonify
from flask import send_file
from flask_restful import Resource, Api
from waitress import serve
from unifi_poe.unifi import UnifiApi, UnifiControllerType, UnifiPoEMode


def poe_mode_set(mode):
    switch_mac, switch_port, api = ctx
    switch_info = api.get_switch_info(switch_mac)
    existing_overrides = switch_info["port_overrides"]

    for port in existing_overrides:
        if port["port_idx"] == switch_port:
            port["poe_mode"] = mode.name
            break
    else:
        raise Exception("No existing override")

    api.request(
        "/rest/device/{}".format(switch_info["_id"]),
        method="PUT",
        data={"port_overrides": existing_overrides},
    )

class port_on(Resource):
    def get(self, port):
        poe_mode_set(UnifiPoEMode.auto)
        return({"port": "switched on"})

class port_off(Resource):
    def get(self, port):
        poe_mode_set(UnifiPoEMode.off)
        return({"port": "switched off"})

class port_cycle(Resource):
    def get(self, port):
            switch_mac, switch_port, api = ctx
            api.request(
                "/cmd/devmgr",
                method="POST",
                data={
                    "cmd": "power-cycle",
                    "mac": switch_mac,
                    "port_idx": switch_port,
                },
            )
            return({"port": "power cycled"})

def sigterm_handler(signal, frame):
    logging.debug(f"cought sigterm: {signal}")
    os._exit(0)

# main function
def main():
    # command line options and argument handling
    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--verbose',
                            required=False,
                            action='store_true',
                            help='enable verbose logging level')

    parser.add_argument('--host',
                            required=True,
                            action='store',
                            default="0.0.0.0",
                            help='the url of the unifi controller')
    parser.add_argument('--username',
                            required=True,
                            action='store',
                            default="default",
                            help='username to access the Unifi api')   
    parser.add_argument('--password',
                            required=True,
                            action='store',
                            default="default",
                            help='password to access the Unifi api')   
    parser.add_argument('--site',
                            required=False,
                            action='store',
                            default="default",
                            help='unifi site name')   
    parser.add_argument('--controller_type',
                            required=False,
                            action='store',
                            default="udm",
                            help='unifi controller type: udm or unifi_controller')   
    parser.add_argument('--switch-mac',
                            required=True,
                            action='store',
                            default="00:00:00:00:00:00",
                            help='mac address of the switch who\'s port you wish to control')      
    parser.add_argument('--switch-port',
                            required=True,
                            action='store',
                            default="0",
                            help='the port on the switch you wish to control')     
    parser.add_argument('--server-ip',
                            required=False,
                            action='store',
                            default="0.0.0.0",
                            help='server ip to listen on')      
    parser.add_argument('--server-port',
                            required=False,
                            action='store',
                            default="5050",
                            help='server port to listen on')                     

    global args, verbose, host, username, password, site, controller_type,switch_mac, switch_port, ctx
    args = parser.parse_args()

    # overwrite arguments with environment settings
    verbose         = bool(int(os.getenv("UNIFI_SERVER_VERBOSE", args.verbose)))
    host            = os.getenv("UNIFI_HOST", args.host)
    username        = os.getenv("UNIFI_USERNAME", args.username)
    password        = os.getenv("UNIFI_PASSWORD", args.password)
    site            = os.getenv("UNIFI_SITE", args.site)
    controller_type = os.getenv("UNIFI_CONTROLLER_TYPE", args.controller_type)
    switch_mac      = os.getenv("UNIFI_SWITCH_MAC", args.switch_mac)
    switch_port     = int(os.getenv("UNIFI_SWITCH_PORT", args.switch_port))
    
    # set logging format and level
    if verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.NOTSET, format='%(asctime)-15s %(message)s')
        flask_debug=True
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)-15s %(message)s')   
        flask_debug=False

    # setup environment and directories
    cwd      = os.getcwd()
    cmd      = os.path.abspath(__file__)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    etc_dir  = base_dir + "/etc"
    global data_dir
    data_dir = base_dir + "/data"

    # create context for flask handler
    ctx = (
        switch_mac,
        switch_port,
        UnifiApi(
            host,
            username,
            password,
            site=site,
            controller_type=UnifiControllerType[controller_type],
        ),
    )

    # initialize flask rest server
    app = Flask(__name__)
    api = Api(app)

    # add resource handlers
    api.add_resource(port_off, '/port/<string:port>/off')
    api.add_resource(port_on, '/port/<string:port>/on')
    api.add_resource(port_cycle, '/port/<string:port>/cycle') 

    # setup SIGINT (Keyboard Interrupt) handling
    signal.signal(signal.SIGINT, sigterm_handler)

    # run the api server
    try:
        if verbose:
            app.run(host=args.server_ip, port=args.server_port, debug=flask_debug)
        else:
            serve(app, host=args.server_ip, port=args.server_port)    
    except Exception as e:
        logging.error(f"flask-restful failed with exception: {e}")
        os._exit(-1)

# Mainline coding
if __name__== "__main__":
    main()
