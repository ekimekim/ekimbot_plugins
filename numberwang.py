
import re
from random import random

from girc import Handler
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class NumberWang(ClientPlugin):
	name = 'numberwang'
	CHANCE = 0.1

	def __init__(self, *args, **kwargs):
		self.active = set()
		super(NumberWang, self).__init__(*args, **kwargs)

	@CommandHandler('numberwang', 0)
	def start_cmd(self, msg, *args):
		targets = set(msg.sender if self.client.matches_nick(target) else target for target in msg.targets)
		for target in targets:
			self.start(target)

	def start(self, target):
		if target in self.active:
			self.client.msg(target, "Cannot start numberwang - already running")
		else:
			self.active.add(target)

	@Handler(command='PRIVMSG')
	def find_nums(self, client, msg):
		targets = set(msg.sender if self.client.matches_nick(target) else target for target in msg.targets)
		for target in targets:
			self.find_nums_for_target(msg, target)

	def find_nums_for_target(self, msg, target):
		if target not in self.active:
			return
		matches = re.findall('[+-]?[0-9]+(?:\.[0-9]+)?', msg.payload)
		if len(matches) > 1:
			self.client.msg(target, "Nice try {}, but there can be only one numberwang.".format(msg.sender))
		elif matches:
			numberwang = random() < self.CHANCE
			self.client.msg(target, "{}, {}? That's {}".format(msg.sender, matches[0], 'NUMBERWANG!' if numberwang else 'not numberwang.'))
			if numberwang:
				self.active.discard(target)
