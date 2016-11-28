
import time

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

from dfaregex import parse, to_text, ParseError, match

class RegexToy(ClientPlugin):
	name = 'regextoy'

	@CommandHandler('regexformat', 1)
	def regexformat(self, msg, *args):
		args = ' '.join(args)
		if not args:
			return
		try:
			tree = parse(args)
		except ParseError as e:
			self.reply(msg, "bad regex: {}".format(e))
		else:
			text = repr(to_text(tree))
			if len(text) > 100:
				self.reply(msg, "sorry, regex too long. avoid '.' or large character ranges.")
			else:
				self.reply(msg, "an equivalent regex: {}".format(text))

	@CommandHandler('regextest', 2)
	def regextest(self, msg, pattern, *args):
		if not args:
			return
		text = ' '.join(args)
		start = time.time()
		try:
			result = match(pattern, text)
		except ParseError as e:
			self.reply(msg, "bad regex: {}".format(e))
		else:
			result = 'matches' if result else 'does not match'
			latency = time.time() - start
			self.reply(msg, "{} (took {:.2f}ms)".format(result, latency * 1000.))
