import logging
from flask import Flask, request
from tgapi import IncomingTelegramCommand, CommandDelegator
from tgapi import BaseCommandHandler, TempHandler
app = Flask(__name__)

command_delegator = CommandDelegator()
command_delegator.register_handler("HelloHandler", BaseCommandHandler())
command_delegator.register_handler("Temp", TempHandler())
FORMAT = '%(asctime)-15s %(filename)15s:%(lineno)3d %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('TiltBot')
logger.setLevel(logging.DEBUG)


@app.route('/tgbot/')
def main():
    return '<h1>Blip!</h1>'

@app.route('/tgbot/xWunSf50L2sRTjAIMd8I/', methods=['POST'])
def botmain():
    raw_data = request.get_json()
    try:
        cmd = IncomingTelegramCommand.from_tg_dict(raw_data)
    except KeyError as exc:
        logger.error('Command parsing failed due to missing key %s. Message %s', exc, raw_data)
        return ""
    command_delegator.delegate_command(cmd)
    return ""