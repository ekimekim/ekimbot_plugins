
# ideas
# parse https://spaceflightnow.com/launch-schedule/ with beautiful soup
# on a poll interval
# on command, give next or search
# 30min before, tell chat (find link?)

from calendar import timegm
from time import gmtime, strptime, time

import gevent
from bs4 import BeautifulSoup
import requests

from ekimbot import ClientPlugin, CommandHandler
from girc.message import Notice


def humanize(delta):
	if delta < 0:
		return '{} ago'.format(humanize(-delta))
	units = [
		('weeks', 60 * 60 * 24 * 7),
		('days', 60 * 60 * 24),
		('hours', 60 * 60),
		('minutes', 60),
	]
	for name, unit in units:
		if delta > unit * 2:
			return '{} {}'.format(int(delta/unit), name)
	return '{} seconds'.format(int(delta))


class LaunchSchedule(ClientPlugin):
	name = 'launch_schedule'

	defaults = {
		'poll_interval': 3600,
		'url': 'https://spaceflightnow.com/launch-schedule/',
		'limit': 3, # limit on launch list
		'channels': [], # channels to announce alerts
	}

	def init(self):
		self.entries = []
		self.client._group.spawn(self.update_loop)

	def update_loop(self):
		while True:
			try:
				self.entries = self.update()
			except Exception:
				self.logger.warning("Failed to update", exc_info=True)
			else:
				self.logger.info("Updated with {} entries".format(len(self.entries)))
				self.logger.debug("Full info: {}".format(self.entries))
				# XXX This is a racey and error-prone way to do this, with bad accuracy,
				# but it's good enough for now.
				now = time()
				for entry in self.entries:
					if entry['time'] is not None and 0 <= (entry['time'] - now) <= self.config.poll_interval:
						self.alert(entry)
			gevent.sleep(self.config.poll_interval)

	def format_list_entry(self, entry):
		return "{datestr}/{timestr}{until}: {mission} - {vehicle} from {site}".format(
			until=(' ({})'.format(humanize(entry['time'] - time())) if entry['time'] is not None else ''),
			**entry
		)

	def alert(self, entry):
		if not self.client.is_master():
			return
		text = 'Upcoming launch: {}'.format(self.format_list_entry(entry))
		for channel in self.config.channels:
			self.client.channel(channel).msg(text)

	@CommandHandler("launch list", 0)
	def reply_list(self, msg, *args):
		"""List upcoming rocket launches"""
		for entry in self.entries[:self.config.limit]:
			self.reply(msg, self.format_list_entry(entry))

	@CommandHandler("launch notice", 1)
	def notice_list(self, msg, *args):
		"""List a number of upcoming rocket launches privately
		Allows you to see more upcoming launches than 'launch list', but isn't public.
		"""
		notice = lambda s: Notice(self.client, msg.sender, s).send()
		arg = ' '.join(args)
		try:
			limit = int(arg)
		except ValueError:
			notice('Not a valid integer: {!r}'.format(arg))
			return
		for entry in self.entries[:limit]:
			notice(self.format_list_entry(entry))

	@CommandHandler("launch show", 1)
	def show_entry(self, msg, *args):
		"""Get details on an upcoming launch
		Give the launch's mission name to see details. Case insensitive.
		"""
		mission = ' '.join(args).strip()
		for entry in self.entries:
			if mission.lower() == entry['mission'].lower():
				self.reply(msg, self.format_list_entry(entry))
				self.reply(msg, entry['description'])
				return
		self.reply(msg, "No upcoming missions called {!r} found".format(mission))

	def update(self):
		resp = requests.get(self.config.url)
		resp.raise_for_status()
		page = BeautifulSoup(resp.text, 'html.parser')
		content = page.find('div', class_='entry-content')
		if content is None:
			raise ValueError("Could not find div with class entry-content")
		classes = [u'datename', u'missiondata', u'missdescrip']
		divs = content.find_all('div', class_=classes, recursive=False)

		results = []
		# Group into entries
		# We expect each entry to be the three div classes in order
		for datename, missiondata, missdescrip in zip(divs[::3], divs[1::3], divs[2::3]):
			for div, cls in zip((datename, missiondata, missdescrip), classes):
				if cls not in div['class']:
					raise ValueError("Divs not in correct order:\n{}\n{}\n{}".format(datename, missiondata, missdescrip))

			entry = {}

			entry['datestr'] = datename.find('span', class_='launchdate').string.strip()
			mission = datename.find('span', class_='mission').string.strip()

			parts = mission.split(u' \u2022 ', 1)
			if len(parts) == 2:
				entry['vehicle'], entry['mission'] = parts
			else:
				entry['vehicle'] = u'unknown'
				entry['mission'] = mission

			# missiondata contains span, launch time (with maybe trailing markup), span, launch site.
			# we scan for only the bare strings and assume the first and last are right.
			# time is broadly "<UTC time> (<ET time>)", so we strip from first '(' onwards
			parts = missiondata.find_all(string=True, recursive=False)
			if len(parts) < 2:
				raise ValueError("Bad missiondata:\n{}".format(missiondata))
			entry['timestr'] = parts[0].split('(', 1)[0].strip()
			entry['site'] = parts[-1].strip()

			# missdescrip contains a body of text, generally with a final "[" + span + "]"
			# denoting update date. We take the first text block and strip any "[".
			entry['description'] = missdescrip.find(string=True).rstrip('[').strip()

			entry['time'] = self.parse_time(entry['datestr'], entry['timestr'])
			results.append(entry)

		return results


	def parse_time(self, date, time):
		# The hard part - let's try to make sense of these times
		# Thankfully, we only care if we can resolve to an exact date,
		# and those at least stay pretty consistent.

		if date.startswith('NET '):
			date = date[len('NET '):]

		# date format has been observed like the following:
		#	Feb. 22
		#	March 1
		#	March 6/7 (in which case time str may have "on %dth" suffix)
		#		In this case we assume the latter day, since they're generally reporting UTC/ET
		#		Further to simplify, we cut off at the first / and assume latter is former + 1
		if '/' in date:
			date = date.split('/', 1)[0]
			fix_up = 60 * 60 * 24
		else:
			fix_up = 0
		date_formats = ['%b. %d', '%B %d']
		for fmt in date_formats:
			try:
				time_tuple = strptime(date, fmt)
			except ValueError:
				pass
			else:
				break
		else:
			return
		# year in yearless formats is arbitrary but hopefully consistent, so normalize
		days = timegm(time_tuple) - timegm(strptime('1 1', '%m %d')) + fix_up

		# time format has been observed like the following:
		#	%H%M GMT
		#	%H%M:%S GMT
		#	%H%M-%H%M GMT, expressing a range. We only want the first part.
		# We can safely assume it's two words, with the former the time.
		# We can then easily split if it's a range and keep start.
		time = time.split(' ', 1)[0]
		time = time.split('-', 1)[0]
		time_formats = ['%H%M', '%H%M:%S']
		for fmt in time_formats:
			try:
				time_tuple = strptime(time, fmt)
			except ValueError:
				pass
			else:
				break
		else:
			return
		# date in dateless formats is arbitrary but hopefully consistent, so normalize
		time = timegm(time_tuple) - timegm(strptime('0000', '%H%M'))

		# put it all together. if it's already passed > 7 days ago, assume it means next year
		date = days + time
		now = gmtime()
		get_year_time = lambda year: timegm(strptime(str(year), '%Y'))
		timestamp = get_year_time(now.tm_year) + date
		if timegm(now) - timestamp > 60 * 60 * 24 * 7:
			timestamp = get_year_time(now.tm_year+1) + date

		return timestamp
