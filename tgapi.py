import re
import requests

class IncomingTelegramCommand:
    def __init__(self, msg_id : int, sender_id : int, chat_id: int, command : str):
        self.msg_id = msg_id
        self.sender_id = sender_id
        self.chat_id = chat_id
        self.command = command

    @classmethod
    def from_tg_dict(cls, item : dict):
        msg = item['message']
        data = {
            'msg_id': msg['message_id'],
            'sender_id': msg['from']['id'],
            'chat_id': msg['chat']['id'],
            'command': msg['text'],
        }
        return cls(**data)

    def __str__(self):
        return f'Chat: {self.chat_id}, Command: {self.command}'

class BaseCommandHandler:
    command = '/hello'

    def __init__(self):
        with open('tgapi.key') as f:
            token = f.read().strip()
        self.send_message_url = f'https://api.telegram.org/bot{token}/sendMessage'

    def match(self, message : IncomingTelegramCommand) -> bool:
        '''
        Return true if this handler should handle command. 
        False otherwise
        '''
        return message.command.startswith(self.command)

    def handle(self, message : IncomingTelegramCommand):
        self._send_message(message.chat_id, 'Hello!')

    def _send_message(self, chat_id : int, message : str):
        data = {
            'chat_id': chat_id,
            'text': message, 
        }
        requests.post(self.send_message_url, json=data)


class TempHandler(BaseCommandHandler):
    command = '/temp'
    pattern = re.compile(r'/temp(@\S+)?\s(?P<summoner_name>.*)$')

    def handle(self, message : IncomingTelegramCommand):
        match = self.pattern.match(message.command)
        if not match:
            err = 'Sorry. could not parse summoner name. usage: /temp <summoner_name>'
            return self._send_message(message.chat_id, err)
        name = match.group('summoner_name')
        msg = f'Requested temperature data with summoner name {name}. temp data is not functional yet :/'
        return self._send_message(message.chat_id, msg)



class CommandDelegator:
    def __init__(self):
        self.handlers = {}
    
    def register_handler(self, handler_id : str, handler : BaseCommandHandler) -> None:
        self.handlers[handler_id] = handler
    
    def delete_handler(self, handler_id :str) -> None:
        if handler_id in self.handlers:
            del self.handlers[handler_id]

    def delegate_command(self, message: IncomingTelegramCommand):
        for _, handler in self.handlers.items():
            if handler.match(message):
                handler.handle(message)