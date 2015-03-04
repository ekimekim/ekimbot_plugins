
import random

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

class SeagullCommand(ClientPlugin):
	name = 'seagull'

	@CommandHandler('seagull', 0)
	def seagull(self, msg, *args):
		out = "{"
		depth = 1
		while depth:
			c = '{' if random.random() * 20 > len(out) else '}'
			if c == '{':
				depth += 1
			else:
				depth -= 1
			out += c
		if 'verbose' in args:
			import simplejson as j
			out = j.dumps(j.loads(out), indent=4)
		self.reply(msg, out)
