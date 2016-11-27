
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

from dfaregex import parse, to_text, ParseError

class RegexToy(ClientPlugin):
	name = 'regextoy'

	@CommandHandler('regextoy', 1)
	def regextoy(self, msg, *args):
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
