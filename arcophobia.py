import gevent

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class Arcophobia(ClientPlugin):
	name = 'arcophobia'

	def init(self):
		self.games = {} # maps {channel: greenlet playing}

	@CommandHandler('arcophobia start', 0)
	def start(self, msg):
		"""Begin a game of arcophobia in the channel"""
		channel = msg.target
		if self.client.matches_nick(channel):
			self.reply(msg, "You can't start arcophobia via PM, I need a channel.")
			return
		if channel in self.games and not self.games[channel].ready():
			self.reply(msg, "A game of arcophobia is already running in this channel.")
			return
		self.games[channel] = self.client._group.spawn(self.play, channel)
		self.games[channel].link(lambda g: self.games[channel] is g and self.games.pop(channel))

	@CommandHandler('arcophobia cancel', 0)
	def cancel(self, msg):
		"""Abort an in-progress arcophobia game"""
		channel = msg.target
		if channel not in self.games or self.games[channel].ready():
			self.reply(msg, "There is no arcophobia game currently running in this channel.")
			return
		self.games[channel].kill(block=True)
		self.reply(msg, "The arcophobia game has been cancelled.")

	def play(self, channel):
		self.client.msg(channel, "This is a placeholder. The game will end in 10 seconds.")
		gevent.sleep(10)
		self.client.msg(channel, "The game has ended.")
