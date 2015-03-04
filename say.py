
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class SayCommand(ClientPlugin):
	name = 'say'

	@CommandHandler('say', 1)
	def say(self, msg, *args):
		self.reply(msg, ' '.join(args))

	@CommandHandler('say_at', 2)
	def say_at(self, msg, target, *args):
		self.client.msg(target, ' '.join(args))

	@CommandHandler('do', 1)
	def do(self, msg, *args):
		self.reply(msg, ('ACTION', ' '.join(args)))

	@CommandHandler('do_at', 2)
	def do_at(self, msg, target, *args):
		self.client.msg(target, ('ACTION', ' '.join(args)))

