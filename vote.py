
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class VotingPlugin(ClientPlugin):
	name = 'vote'
	options = None

	@CommandHandler('vote help')
	def help(self, msg, *args):
		self.reply("A simple preference vote system. Votes run until 'vote end' is called."
		           " Only the latest vote from each nick is counted. When you vote, you list all options in order"
		           " from most preferred to least.")

	@CommandHandler('vote start', nargs=1)
	def start(self, msg, *args):
		if self.options:
			self.reply("Cannot start vote - another vote is already in progress")
			return
		self.options = [x.strip() for x in ' '.join(args).split(',')]
