import tornado.web

from api.web import RequestHandler
from api.server import test_get
from api.server import test_post
from api.server import handle_url

from libs import cache
from rainwave import playlist

sessions = {}

@handle_url("sync_update_all")
class SyncUpdateAll(tornado.web.RequestHandler):
	sid_required = True

	def prepare(self):
		self._rw_update_clients = True
		if not self.request.remote_ip == "127.0.0.1":
			self._rw_update_clients = False
			self.set_status(403)
			self.finish()
			
	def get(self):
		if self._rw_update_clients:
			self.write("Processing.")
	
	def on_finish(self):
		if not self._rw_update_clients:
			return
		cache.update_local_cache_for_sid(self.sid)
		
		for session in sessions[self.sid]:
			session.update(True)
		sessions[self.sid] = []
		
@handle_url("sync_update_user")
class SyncUpdateUser(tornado.web.RequestHandler):
	sid_required = False

	def prepare(self):
		self._rw_update_clients = True
		if not self.request.remote_ip == "127.0.0.1":
			self._rw_update_clients = False
			self.set_status(403)
			self.finish()
			
	def get(self):
		if self._rw_update_clients:
			self.write("Processing.")
			
	def on_finish(self):
		if not self._rw_update_clients:
			return

		user_id = long(self.request.arguments['user_id'])
		for sid in sessions:
			for session in sessions[sid]:
				if session.user.id == user_id:
					session.update_user()
					sessions[sid].remove(session)
					return
			
@handle_url("sync_update_ip")
class SyncUpdateIP(tornado.web.RequestHandler):
	sid_required = False

	def prepare(self):
		self._rw_update_clients = True
		if not self.request.remote_ip == "127.0.0.1":
			self._rw_update_clients = False
			self.set_status(403)
			self.finish()
			
	def get(self):
		if self._rw_update_clients:
			self.write("Processing.")
			
	def on_finish(self):
		if not self._rw_update_clients:
			return
		
		ip_address = long(self.request.arguments['ip_address'])
		for sid in sessions:
			for session in sessions[sid]:
				if session.request.remote_ip == ip_address:
					session.update_user()
					sessions[sid].remove(session)
					return

@handle_url("sync")
class Sync(RequestHandler):
	auth_required = True
	
	@tornado.web.asynchronous
	def post(self):
		self.set_header("Content-Type", "application/json")
		if "init" in self.request.arguments:
			self.update()
		else:
			if not self.sid in sessions:
				sessions[sid] = []
			sessions[self.user.sid].append(self)
		
	def update(self, use_local_cache = False):
		# Front-load all non-animated content ahead of the schedule content
		# Since the schedule content is the most animated on R3, setting this content to load
		# first has a good impact on the perceived animation smoothness since table redrawing
		# doesn't have to take place during the first few frames.
		
		self.user.refresh(use_local_cache)
		self.append("user", self.user.get_public_dict())
		
		if 'playlist' in self.request.arguments:
			self.append("all_albums", playlist.fetch_all_albums(self.user))
		elif 'artist_list' in self.request.arguments:
			self.append("artist_list", playlist.fetch_all_artists(self.sid))
		elif 'init' not in self.request.arguments:
			self.append("album_diff", cache.get_local_station(self.sid, 'album_diff'))
		
		if use_local_cache:
			self.append("requests_all", cache.get_local_station(self.sid, "request_all"))
		else:
			self.append("requests_all", cache.get_station(self.sid, "request_all"))
		self.append("requests_user", self.user.get_requests())
		self.append("calendar", cache.local["calendar"])
		self.append("listeners_current", cache.get_local_station(self.sid, "listeners_current"))
		
		self.append("sched_current", self.user.make_event_jsonable(cache.get_local_station(self.sid, "sched_current"), use_local_cache))
		self.append("sched_next", self.user.make_events_jsonable(cache.get_local_station(self.sid, "sched_next"), use_local_cache))
		self.append("sched_history", self.user.make_event_jsonable(cache.get_local_station(self.sid, "sched_history"), use_local_cache))
		self.finish()
	
	def update_user(self):
		self.user.refresh()
		self.append("user", self.user.get_public_dict())
		self.finish()
