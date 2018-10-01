
import time

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

# This isn't a perfect way of getting 'interpreter start time', but is close enough
import_time = time.time()


class Uptime(ClientPlugin):
	name = 'uptime'

	def init(self):
		self.client_start_time = time.time()

	@CommandHandler('uptime', 0)
	def uptime(self, msg, *args):
		now = time.time()
		self.reply(msg, "{} since interpreter start, {} since client start".format(
			*map(self.format_interval, [
				now - import_time,
				now - self.client_start_time,
			])
		))

	def format_interval(self, interval):
		units = [
			('minutes', 60),
			('hours', 60),
			('days', 24),
		]
		result_name = 'seconds'
		for name, factor in units:
			new_interval = interval / factor
			if new_interval < 2:
				break
			interval = new_interval
			result_name = name
		return '{:.1f} {}'.format(interval, result_name)
