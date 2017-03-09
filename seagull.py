
import random

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

class SeagullCommand(ClientPlugin):
	name = 'seagull'

	@CommandHandler('seagull', 0)
	def seagull(self, msg, openchar='{', closechar='}', targetlen=20, *args):
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
			if random.random() * targetlen > len(out):
				out += openchar
				depth += 1
			else:
				out += closechar
				depth -= 1
		if isinstance(out, unicode):
			out = out.encode('utf-8')
		self.reply(msg, out)
