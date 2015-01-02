
from ekimbot.botplugin import BotPlugin

import gevent
from collections import Counter


class ModuleMonitor(BotPlugin):
	"""Periodically checks that multiple copies of a module aren't loaded"""
	INTERVAL = 60
	name = 'module_monitor'
	bad = set()
	_monitor = None

	def init(self):
		self._monitor = gevent.spawn(self.monitor)

	def monitor(self):
		while True:
			self.check()
			gevent.sleep(self.INTERVAL)

	def check(self):
		new_bad = self.get_bad()
		for name in new_bad - self.bad:
			self.logger.warning("Module {} has multiple copies loaded".format(name))
		self.bad = new_bad

	def get_bad(self):
		names = [module.__name__ for module in BotPlugin.loaded]
		return set(name for name, count in Counter(names).items() if count > 1)

	def cleanup(self):
		if self._monitor is not None:
			self._monitor.kill()
