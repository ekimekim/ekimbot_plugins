
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class TurnersCommand(ClientPlugin):
	name = 'turners'

	@CommandHandler('turners', 1)
	def turners(self, msg, *args):
		scale = hash(' '.join(args)) % 11
		self.reply(msg, "{}? That's a lickability of about...{} turners.".format(' '.join(args), scale))
