import logging
import json
from flask import Flask, request
from tgapi import IncomingTelegramCommand, CommandDelegator
from tgapi import BaseCommandHandler, TempHandler
from analytics import GameAnalyzer
app = Flask(__name__)

command_delegator = CommandDelegator()
command_delegator.register_handler("HelloHandler", BaseCommandHandler())
command_delegator.register_handler("Temp", TempHandler())
FORMAT = '%(asctime)-15s %(filename)15s:%(lineno)3d %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('TiltBot')
logger.setLevel(logging.DEBUG)

with open("keys/hook.key") as f:
    hook = f.read().strip()

@app.route('/tgbot/')
def main():
    return '<h1>Blip!</h1>'

@app.route('/tgbot/{}/'.format(hook), methods=['POST'])
def botmain():
    raw_data = request.get_json()
    try:
        cmd = IncomingTelegramCommand.from_tg_dict(raw_data)
    except KeyError as exc:
        logger.error('Command parsing failed due to missing key %s. Message %s', exc, raw_data)
        return ""
    command_delegator.delegate_command(cmd)
    return ""

