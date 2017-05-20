
import math
import random
import time

from ekimbot.botplugin import ClientPlugin
from ekimbot.commands import CommandHandler


class InvestGame(ClientPlugin):
	"""A very simple idle game based around 'investing money'"""

	name = 'invest'

	# (name, short name, return per day, risk per day)
	# eg. ("Example investment", "example", 0.1, 0.01) means 10% interest, but 1% chance per day to lose everything
	# keep in mind expected value = (1 + return) * (1 - risk)
	FUNDS = [
		("Savings account", "savings", .01, .0),
		("Index fund", "index", .025, .001),
		("Hedge fund", "hedge", .06, .027),
		("Play the stocks", "stocks", .17, .1),
		("Embezzle company money", "embezzle", 1.5, .5),
	]

	# As a failsafe for player losing all money, put BASE_INCOME/day into BASE_FUND
	BASE_FUND = "savings"
	BASE_INCOME = 100

	# Store schema: players: {player name: [last updated, {fund short name: [amount in fund, time of last bust or None]}]}
	# timestamps in epoch float.

	@CommandHandler("invest help", 0)
	def help(self, msg, *args):
		"""Explain how the investment game works"""
		self.reply(msg, (
			"The invest game lets you invest money in various funds. They give a fixed return "
			"over time, but you always run the risk of losing everything! You'll always get ${}/day "
			"coming into your savings account. Move funds with `invest move FROM TO AMOUNT`. "
			"See available funds with `invest funds`. Check your or others' net worth with "
			"`invest check` or `invest check NAME`."
		).format(self.BASE_INCOME))
		self.reply(msg,
			"Important: Right now some technical limitations mean each instance of "
			"ekimbot tracks your money seperately. So you kinda have two accounts. Sorry."
		)


	@CommandHandler("invest funds", 0)
	def funds(self, msg, *args):
		"""List available funds to invest in"""
		for name, short, rate, risk in self.FUNDS:
			self.reply(msg,
				"{name} ({short!r}): {rate}%/day{bust_str}".format(
					name=name, short=short, rate=100*rate,
					bust_str=(", but {}%/day to go bust!".format(100*risk) if risk else ""),
				)
			)

	@CommandHandler("invest check", 0)
	def check(self, msg, *args):
		"""Check your or someone else's investments

		You can either pass a target user, or no-one to check yourself.
		"""
		target = args[0] if args else msg.sender
		self.update(target)
		_, funds = self.store['players'][target]
		for name, short, rate, risk in self.FUNDS:
			if short not in funds:
				continue
			amount, last_bust = funds[short]
			bust_str = " (last went bust at {} UTC)".format(time.strftime('%F %T', time.gmtime(last_bust))) if last_bust is not None else ""
			self.reply(msg, "{target} has ${amount:.2f} in {name}{bust_str}".format(
				target=target, amount=amount, name=name, bust_str=bust_str,
			))
		# If we ever change funds list, this could happen. Leave it be until the user removes it.
		# It won't make any money.
		defunct = set(funds) - set(short for name, short, rate, risk in self.FUNDS)
		if defunct:
			self.reply(msg, "{} has money in the following defunct funds: {}".format(target,
				", ".join("{!r} (${})".format(short, funds[short][0]) for short in defunct),
			))
		total = sum(amount for amount, last_bust in funds.values())
		self.reply(msg, "{} has ${:.2f} in total (plus {} of a cent)".format(
			target, int(total * 100) / 100., (total * 100) % 1,
		))


	@CommandHandler("invest move", 3)
	def move(self, msg, src, dest, amount):
		"""Move money from one fund to another. Args are FROM, TO, AMOUNT. AMOUNT can be "all".

		Move an amount of money from one invest fund to another.
		You need to use the short names given under `invest funds`.
		AMOUNT can either be a positive number, or "all" for all available.
		"""

		src = src.lower()
		dest = dest.lower()
		for short in (src, dest):
			if short not in (short for name, short, rate, risk in self.FUNDS):
				self.reply(msg, "{!r} is not a fund name. You need to use the short name as it appears in `invest funds`.".format(short))
				return

		if src == dest:
			self.reply(msg, "Can't move from a fund to itself")
			return

		if amount.lower().strip() == 'all':
			amount = 'all'
		else:
			try:
				_amount = float(amount)
				if math.isnan(_amount) or math.isinf(_amount) or _amount <= 0:
					raise ValueError
			except ValueError:
				self.reply(msg, "Amount must be a positive number, not {!r}".format(amount))
				return
			else:
				amount = _amount

		target = msg.sender
		self.update(target)
		_, funds = self.store['players'][target]

		src_amount, _ = funds.get(src, (0, None))
		dest_amount, _ = funds.get(dest, (0, None))

		if amount == 'all':
			amount = src_amount
		elif amount > src_amount:
			self.reply(msg, "You don't have that much money in that fund. You have: ${:.2f}".format(src_amount))
			return

		src_amount -= amount
		dest_amount += amount

		if src_amount > 0:
			funds[src] = src_amount, None
		else:
			funds.pop(src, None)
		funds[dest] = dest_amount, None
		self.save_store()

		self.reply(msg, "{}: Moved ${} from {} to {}".format(target, amount, src, dest))


	def update(self, target):
		"""Update target's money in the store"""
		# Interest is compounded infinitely fast (comes out to exponential, (1+r/n)^tn -> e^tr as n -> inf)
		# Risk is also infinitely divided (similarly, (1-p/n)^tn -> e^-tp as n -> inf).
		# So for example, the actual risk and return after a day (t=1) for return 10%/day at 1% risk/day is:
		#   return: e^0.1 ~= 1.105, 1.105 - 1 = 10.5% increase
		#   risk: e^-0.01 ~= 0.99005, 1 - 0.99005 = 0.00995% risk

		# We choose a time of bust by "working backwards" from the random value we rolled.
		# Suppose we picked a uniform random value X, deciding that a bust occurred if X > e^(-tp)
		# (ie. that 1-X < 1 - e^(-tp), which is the risk as above)
		# Then let's ask, for what value of t would we have _just_ gotten a bust? Call it B. Then:
		#     X = e^(-Bp)
		#     -Bp = ln X
		#     B = -(ln X)/p
		# This gives us how long in the past the bust occurred. Note we can prove B < t.
		# For an extreme example, suppose risk was 60%/day (p=0.6) and we're looking at 1 day (t=1).
		# From above, success chance = e^-.6 ~= 0.54. We roll x in [0,1) and get 0.9 - this means we've gone bust.
		# Using the above formula, B = -(ln 0.9)/0.6 ~= 0.175, or 4.2 hours.
		# As a nice side effect, checking if B < period is exactly the same as the initial check
		# that X > success chance, so we can just calculate everything at once.

		# Final complication is base income. It arrives steadily and we need to account for it
		# in our compound interest.
		# By considering interest at infinitely thin time slices and with I = income rate,
		# total = integral 0 to t of I e^(t-x)r dx = I e^rt (integral 0 to t of e^-rx dx)
		# = I e^rt (1 - e^-rt) / r.
		# So for example $100/day for 1 day at 10%/day gives 100 * e^(1*0.1) * (1 - e^-(1*0.1)) / 0.1 ~= $105.17

		now = time.time()

		if target not in self.store.setdefault('players', {}):
			self.store['players'][target] = now, {self.BASE_FUND: (self.BASE_INCOME, None)}
			return

		oldtime, funds = self.store['players'][target]
		period = now - oldtime

		for name, short, rate, risk in self.FUNDS:
			this_period = period
			rate_sec = rate / 86400
			risk_sec = risk / 86400
			income_sec = self.BASE_INCOME / 86400

			if short in funds:
				amount, last_bust = funds[short]
			elif short == self.BASE_FUND:
				amount, last_bust = 0, None
			else:
				continue

			if risk_sec:
				since_bust = - math.log(random.random()) / risk_sec
				if since_bust < period:
					last_bust = now - since_bust
					this_period = since_bust # only calculate new amounts (eg. for income) since bust
					amount = 0

			amount *= math.exp(this_period * rate_sec) # add interest
			if short == self.BASE_FUND:
				# add income + income's interest
				amount += income_sec * math.exp(this_period*rate_sec) * (1 - math.exp(-this_period*rate_sec)) / rate_sec

			funds[short] = amount, last_bust

		self.store['players'][target] = now, funds
		self.save_store()
