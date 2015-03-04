
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

class ReverseCommand(ClientPlugin):
	name = 'reverse'

	@CommandHandler('reverse', 1)
	def reverse(self, msg, *args):
		args = ' '.join(args)
		self.reply(msg, args[::-1])
