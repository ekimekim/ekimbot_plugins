
import random

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

class SeagullCommand(ClientPlugin):
	name = 'seagull'

	@CommandHandler('seagull', 0)
	def seagull(self, msg, openchar='{', closechar='}', *args):
		if openchar == closechar:
			self.reply(msg, "Can't make a flock out of only one character")
			return
		out = openchar
		depth = 1
		while depth:
			c = openchar if random.random() * 20 > len(out) else closechar
			if c == openchar:
				depth += 1
			else:
				depth -= 1
			out += c
		self.reply(msg, out)
