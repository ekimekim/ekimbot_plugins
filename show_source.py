
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class ShowSourceCommand(ClientPlugin):
	name = 'show_source'

	SOURCES = [
		("Core", "https://github.com/ekimekim/ekimbot"),
		("Extra plugins", "https://github.com/ekimekim/ekimbot_plugins"),
		("IRC client", "https://github.com/ekimekim/geventirc/tree/girc"),
		("Assorted other libs (inc. config and plugin systems)", "https://github.com/ekimekim/pylibs/tree/master/libs"),
	]

	@CommandHandler('source', 0)
	def source(self, msg, *args):
		for part, url in self.SOURCES:
			self.reply(msg, "{}: {}".format(part, url))
