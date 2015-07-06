import gevent

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class Arcophobia(ClientPlugin):
	name = 'arcophobia'

	def init(self):
		self.games = {} # maps {channel: greenlet playing}

	@CommandHandler('arcophobia start', 0)
	def start(self, msg):
		"""Begin a game of arcophobia in the channel"""
		channel = msg.target
		if self.client.matches_nick(channel):
			self.reply(msg, "You can't start arcophobia via PM, I need a channel.")
			return
		if channel in self.games and not self.games[channel].ready():
			self.reply(msg, "A game of arcophobia is already running in this channel.")
			return
		self.games[channel] = self.client._group.spawn(ArcophobiaGame(self, channel).play)
		self.games[channel].link(lambda g: self.games[channel] is g and self.games.pop(channel))

	@CommandHandler('arcophobia cancel', 0)
	def cancel(self, msg):
		"""Abort an in-progress arcophobia game"""
		channel = msg.target
		if channel not in self.games or self.games[channel].ready():
			self.reply(msg, "There is no arcophobia game currently running in this channel.")
			return
		self.games[channel].kill(block=True)
		self.reply(msg, "The arcophobia game has been cancelled.")


class ArcophobiaGame(object):
	def __init__(self, plugin, channel):
		self.client = plugin.client
		self.logger = plugin.logger.getChild("game").getChild(channel)
		self.channel = channel
		self.scores = {}

	def say(self, msg, *args, **kwargs):
		self.client.msg(self.channel, msg.format(*args, **kwargs))

	def play(self):
		try:
			self.print_rules()
			gevent.sleep(5)
			self.do_round(6)
			self.do_round(7)
			self.do_round(8)
			self.pick_finalists()
			self.do_final_round(3)
			self.do_final_round(4)
			self.do_final_round(5)
		except Exception as ex:
			self.logger.exception("Error while playing")
			self.say("Uh, something went wrong. Sorry! I'll try to get you the final scores.")
			self.print_scores()

	def print_rules(self):
		self.say("Welcome to arcophobia! There will be several rounds.")
		self.say("Each round, you will be given an acronym.")
		self.say("Submit what you think it stands for using {}submit. Be fast - you only get 60 seconds.",
		         self.client.config['command_prefix'])
		self.say("You then get to vote on whose submission was best - you can't vote for yourself!")
		self.say("Anyone can vote, but only once. After 30 seconds voting closes.")
		self.say("You get 1 point per vote for your submission.")

	def do_final_round(self, num_letters):
		self.do_round(num_letters, timer=20, finals=True)

	def do_round(self, num_letters, timer=60, finals=False):
		acronym = self.gen_acronym(num_letters)

		submissions = OrderedDict() # {submission: user}

		target = self.client.nick if finals else self.channel
		@CommandHandler('submit', 1, target=target)
		def submit(msg, *args):
			submission = ' '.join(args)
			if msg.sender in submissions.values():
				utils.reply(self.client, msg, "Sorry {}, you've already submitted".format(msg.sender))
				return
			if submission in submissions:
				utils.reply(self.client, msg, "Sorry {}, someone already submitted that.".format(msg.sender))
				return
			submissions[submission] = msg.sender

		self.say("Your acronym for this round is: {}", acronym)
		self.say("You have {} seconds.", timer)
		if finals:
			self.say("Remember, in the finals rounds you have to submit via PM")

		if timer > 10:
			gevent.sleep(timer - 10)
			self.say("Hurry up! Only 10 seconds left!")
			gevent.sleep(10)
		else:
			gevent.sleep(timer)

		if not submissions:
			self.say("Nothing? Wow, you guys all suck. I'm taking my ball and going home.")
			raise gevent.GreenletExit
		sub_list = submissions.keys()
		first = sub_list[0]
		random.shuffle(sub_list)

		# TODO voting

		self.say("Submissions:")
		for n, submission in enumerate(sub_list):
			self.say("{}: {}".format(n+1, submission))
		self.say("You have 20s to vote.")

		# TODO UPTO
