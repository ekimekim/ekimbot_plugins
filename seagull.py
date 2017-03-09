
import random

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

class SeagullCommand(ClientPlugin):
	name = 'seagull'

	@CommandHandler('seagull', 0)
	def seagull(self, msg, openchar='{', closechar='}', targetlen=20, *args):
		if openchar == closechar:
			self.reply(msg, "Can't make a flock out of only one character")
			return
		try:
			targetlen = int(targetlen)
		except ValueError:
			self.reply(msg, "Invalid length: {!r}".format(targetlen))
			return
		# opportunistically measure length in unicode chars if both strings valid unicode
		try:
			_openchar = openchar.decode('utf-8')
			_closechar = closechar.decode('utf-8')
		except UnicodeDecodeError:
			self.logger.info("Got invalid unicode in one of {!r}, {!r}".format(openchar, closechar))
		else:
			openchar = _openchar
			closechar = _closechar
			self.logger.info("Using opportunistic unicode handling: {!r}, {!r}".format(openchar, closechar))
		out = openchar
		depth = 1
		while depth:
			c = openchar if random.random() * targetlen > len(out) else closechar
			if c == openchar:
				depth += 1
			else:
				depth -= 1
			out += c
		if isinstance(out, unicode):
			out = out.encode('utf-8')
		self.reply(msg, out)
