
import os
import subprocess
import time

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler

# This isn't a perfect way of getting 'interpreter start time', but is close enough
import_time = time.time()


class Uptime(ClientPlugin):
	name = 'uptime'

	_process_start_time = None

	def init(self):
		self.client_start_time = time.time()

	@classmethod
	def get_process_start_time(cls):
		if cls._process_start_time is None:
			# I don't want to do a ps every time, this introduces some uncertainty but close enough
			cls._process_start_time = time.time() - float(subprocess.check_output(['ps', '-o', 'etimes=', str(os.getpid())]))
		return cls._process_start_time

	@CommandHandler('uptime', 0)
	def uptime(self, msg, *args):
		now = time.time()
		self.reply(msg, "{} since process start, {} since interpreter start, {} since client start".format(
			*map(self.format_interval, [
				now - self.get_process_start_time(),
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
