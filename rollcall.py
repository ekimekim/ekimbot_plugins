
import re
import socket

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import EkimbotHandler

from girc.message import Privmsg


class Rollcall(ClientPlugin):
	"""All bots (even non-master) respond to the rollcall phrase with their hostname"""
	name = 'rollcall'

	defaults = {
		# regex that must match message to trigger roll call
		"trigger": "roll call"
	}

	@EkimbotHandler(master=None, command=Privmsg)
	def rollcall(self, client, msg):
		if re.match('^(?:{})$'.format(self.config['trigger']), msg.payload):
			nick = client.nick
			self.reply(msg, "{}{} @ {} reporting for duty!".format(
				nick,
				'(master)' if client.is_master(nick) else '',
				socket.gethostname(),
			))

