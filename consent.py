
import gevent

from ekimbot.botplugin import ChannelPlugin
from ekimbot.commands import CommandHandler

class ConsentPlugin(ChannelPlugin):
	name = 'consent'

	@CommandHandler('skullfuck', 0)
	def consent(self, msg):
		with self.client._nick_lock:
			self.client.nick = 'Boneathan'
			for text, sleep in [
				('CONTINUOUS', 1),
				('ENTHUSIASTIC', 1),
				('CONSENT!!!', 10),
			]:
				self.reply(msg, text)
				gevent.sleep(sleep)
			self.client.nick = self.client.config['nick']
