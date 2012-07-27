from rainwave.user import User
from api import fieldtypes
from libs import config
import api.returns

import tornado.web
import tornado.escape
import time
import re

# This is the Rainwave API main handling request class.  You'll inherit it in order to handle requests.
# Does a lot of form checking and validation of user/etc.  There's a request class that requires no authentication at the bottom of this module.

# VERY IMPORTANT: YOU MUST DECORATE YOUR CLASSES.

# from api.server import handle_url
# @handle_url(...)

# Pass a string there for the URL to handle at /api/[url] and the server will do the rest of the work.

class RequestHandler(tornado.web.RequestHandler):
	# The following variables can be overridden by you.
	# Fields is a hash with { "form_name" => fieldtypes.[something] } format, so that automatic form validation can be done for you.
	fields = {}
	# This URL variable is setup by the server decorator - DON'T TOUCH IT.
	url = False
	# Do we need a Rainwave auth key for this request?
	auth_required = True
	# return_name is used for documentation, can be an array.
	# If not inherited, return_key automatically turns into url + "_result".  Useful for simple requests like rate, vote, etc.
	return_name = False
	# Validate user's tuned in status first.
	tunein_required = False
	# Validate user's logged in status first.
	login_required = False
	# Validate user is a station administrator.
	admin_required = False
	# Validate user is currently DJing.
	dj_required = False
	# Do we need a valid SID as part of the submitted form?
	sid_required = True
	# Description string for documentation.
	description = "Undocumented."

	# Called by Tornado, allows us to setup our request as we wish. User handling, form validation, etc. take place here.
	def prepare(self):
		self._startclock = time.clock()

		if self.return_name == False:
			self.return_name = self.__class__.url + "_result"
		else:
			self.return_name = self.__class__.return_name
			
		if self.admin_required or self.dj_required:
			self.login_required = True
	
		if 'in_order' in self.request.arguments:
			self._output = []
			self._output_array = True
		else:
			self._output = {}
			self._output_array = False
			
		request_ok = True
	
		self.args = {}
		for field, type in self.__class__.fields.iteritems():
			if not field in self.request.arguments:
				self.append("error", api.returns.ErrorReturn(-1000, "Missing %s argument." % field))
				request_ok = False
			else:
				parsed = getattr(fieldtypes, type)(self.get_argument(field))
				if parsed == None:	
					self.append("error", api.returns.ErrorReturn(-1000, "Invalid argument %s: %s" % (field, getattr(fieldtypes, "%s_error" % type))))
					request_ok = False
				else:
					self.args[field] = parsed
		
		self.user = None
		if request_ok:
			if self.auth_required and not self.rainwave_auth():
				self.finish()
		
		if self.sid_required and not "id" in self.request.arguments:
			self.append("error", api.returns.ErrorReturn(-1000, "Missing station ID argument."))
			request_ok = False
		elif "id" in self.request.arguments:
			self.sid = int(self.request.arguments("sid"))
		elif self.user:
			self.sid = self.user.sid
		else:
			self.append("error", api.returns.ErrorReturn(-1000, "Missing station ID argument."))

		# Now we strictly enforce valid station IDs.
		if not self.sid in config.station_ids or self.sid == 0:
			self.append("error", api.returns.ErrorReturn(-1000, "Invalid station ID."))
			request_ok = False
				
		if not request_ok:
			self.finish()
	
	def rainwave_auth(self):
		request_ok = True
		
		if not "user_id" in self.request.arguments:
			self.append("error", api.returns.ErrorReturn(-1000, "Missing user_id argument."))
			request_ok = False
		elif not fieldtypes.numeric(self.get_argument("user_id")):
			self.append("error", api.returns.ErrorReturn(-1000, "Invalid user ID %s."))
			request_ok = False
		if not "key" in self.request.arguments:
			self.append("error", api.returns.ErrorReturn(-1000, "Missing 'key' argument."))
			request_ok = False
		
		self.user = None
		if request_ok:
			self.user = User(long(self.get_argument("user_id")))
			self.user.authorize(self.sid, self.request.remote_ip, self.get_argument("key"))
			if not self.user.authorized:
				self.append("error", api.returns.ErrorReturn(403, "Authorization failed."))
				request_ok = False
			else:
				self.sid = self.user.request_sid
		
		if self.user and request_ok:
			if self.login_required and not user.is_anonymous():
				self.append("error", api.returns.ErrorReturn(-1001, "Login required for %s." % url))
				request_ok = False
			if self.tunein_required and not user.is_tunedin():
				self.append("error", api.returns.ErrorReturn(-1001, "You must be tuned in to use %s." % url))
				request_ok = False
			if self.admin_required and not user.is_admin():
				self.append("error", api.returns.ErrorReturn(-1001, "You must be an admin to use %s." % url))
				request_ok = False
			if self.dj_required and not user.is_dj():
				self.append("error", api.returns.ErrorReturn(-1001, "You must be DJing to use %s." % url))
				request_ok = False
		
		return request_ok

	# Handles adding dictionaries for JSON output
	# Will return a "code" if it exists in the hash passed in, if not, returns True
	def append(self, key, hash):
		if hash == None:
			return
		if self._output_array:
			self._output.append({ key: hash })
		else:
			self._output[key] = hash
		if "code" in hash:
			return hash["code"]
		return True

	# Sends off the data to the user.
	def finish(self, chunk=None):
		self.set_header("Content-Type", "application/javascript")
		if hasattr(self, "_output"):
			if hasattr(self, "_startclock"):
				exectime = time.clock() - self._startclock
			else:
				exectime = -1
			self.append("api_info", { "exectime": exectime, "time": round(time.time()) })
			self.write(tornado.escape.json_encode(self._output))
		super(RequestHandler, self).finish(chunk)
