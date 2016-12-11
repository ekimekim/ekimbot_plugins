
import random

import gevent

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import EkimbotHandler


class RustleBackPlugin(ClientPlugin):
	name = 'rustleback'
	defaults = {
		'min': 30,
		'max': 90,
	}

	@EkimbotHandler(command='PRIVMSG', payload=lambda value: value.startswith('!rustle '))
	def rustle_back(self, client, msg):
		if client.matches_nick(msg.payload[len('!rustle '):]):
			interval = self.config.min + random.random() * (self.config.max - self.config.min)
			gevent.sleep(interval)
			self.reply(msg, '!rustle {}'.format(msg.sender))
