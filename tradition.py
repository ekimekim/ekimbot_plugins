
import re

from girc import Handler
from ekimbot.botplugin import ClientPlugin

# we specifically want to match PyMoronBot's pattern for best consistency
PATTERN = re.compile(r'([^a-zA-Z]|^)as is tradition([^a-zA-Z]|$)', flags=re.I)

class TraditionPlugin(ClientPlugin):
	"""Replies 'as is tradition' in respond to 'as is tradition', as is tradition."""
	name = 'tradition'

	@Handler(command='PRIVMSG', payload=PATTERN)
	def as_is_tradition(self, client, msg):
		self.reply(msg, "As is tradition.")
