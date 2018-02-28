import re
import time

import gevent

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import EkimbotHandler


class Gerhard(ClientPlugin):
	name = 'gerhard'

	FINE_REGEX = ".*([^a-zA-Z]|^)everything('?s| is) fine([^a-zA-Z]|$)"
	last_fire = None

	defaults = {
		'cooldown': 5 * 60,
		'return_wait': 10,
	}

	@EkimbotHandler(command='PRIVMSG', payload=re.compile(FINE_REGEX))
	def everything_is_fine(self, client, msg):
		if self.last_fire is not None and time.time() - self.last_fire < self.config.cooldown:
			return

		# No PMs
		if client.matches_nick(msg.target):
			return
		channel = client.channel(msg.target)

		self.last_fire = time.time()

		# nick lock keeps slave module from noticing until we release
		try:
			with client._nick_lock:
				client.nick = 'Lars_Gerhard'
				self.reply(msg, "I WAS NEVER HERE, AND EVERYTHING IS FINE.")
				channel.part(block=True)
				gevent.sleep(self.config.return_wait)
				client.nick = self.client.config['nick']
		finally:
			channel.join()
