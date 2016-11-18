
from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class TurnersCommand(ClientPlugin):
	name = 'turners'

	@CommandHandler('turners', 1)
	def turners(self, msg, *args):
		thing = ' '.join(args)
		if any(thing.lower() in channel.users.users for channel in self.client.joined_channels):
			self.reply(msg, "Hey, we don't do lickability of people!")
			return
		scale = hash(thing) % 11
		self.reply(msg, "{}? That's a lickability of about...{} turners.".format(thing, scale))
