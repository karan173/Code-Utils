from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError
import webapp2
import sys
import logging
import jinja2
import os
import re
sys.path.insert(0, 'libs') #to add external library beautiful soup
from bs4 import BeautifulSoup
from google.appengine.api import users
import json
from google.appengine.ext import ereporter
import time
""" 
Code Information :
Things stored in memcache:
	1) "all_keys"				: 	Returns the list of keys for Problem entities in database.
	2) str(id), namespace='p' : 	Returns the entity corresponding to the Problem key. Note id here varies from problem to problem. 
	
Hence any updates on entities must either update the corresponding value in memcache or flush the memcache for that key   
"""

### Global Variables Begin ###
master_url = "http://www.codechef.com/problems/";
sub_urls = ["easy", "medium", "hard", "challenge", "school"] #extcontest is not scraped bcoz it contains a LARGE amount of problems 1492
user_url = "http://www.codechef.com/users/"
username_pattern = re.compile('^[a-z]{1}[a-z0-9_]{3,13}$')	

JINJA_ENVIRONMENT = jinja2.Environment(
		loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
		extensions=['jinja2.ext.autoescape'],
		autoescape=True)

tag_set = set(['2-sat', 'bit', 'adhoc', 'aho-corasick', 'articulation-point', 'backtracking', 'bellman-ford', 'bfs', 'biconnected-comp', 'big-integer', 'binary-numbers', 'binary-search', 'binary-tree', 'binomial', 'bipartite', 'bitmasking', 'bitwise', 'bridges', 'brute-force', 'burnside', 'chinese-remainder', 'combinatorics', 'complete-search', 'convex-hull', 'data-structure', 'decomposition', 'deque', 'dfs', 'dijkstra', 'discretization', 'disjoint-set', 'divide-and-conquer', 'dp', 'enumeration', 'euler-tour', 'expectation', 'exponentiation', 'factorial', 'factorization', 'fft', 'fibonacci', 'floyd-warshall', 'game-theory', 'gauss-elim', 'gcd', 'geometry', 'grammar-parsing', 'graphs', 'greedy', 'hashing', 'heaps', 'heavy-light', 'heuristic', 'hungarian', 'impartial-game', 'implementation', 'inclusion-exclusion', 'inversions', 'kd-tree', 'kmp', 'kruskal', 'lca', 'lcp', 'line-sweep', 'linear-programming', 'link-cut-tree', 'matching', 'maths', 'matrix-expo', 'max-independent-set', 'maxflow', 'meet-in-middle', 'memoization', 'miller-rabin', 'min-cost-flow', 'mincut', 'modulo', 'mst', 'newton-raphson', 'number-theory', 'offline-query', 'order-statistic', 'palindrome', 'permutation', 'persistence', 'pigeonhole', 'polygons', 'precision', 'prefix-sum', 'preprocessing', 'prim', 'prime', 'probability', 'queue', 'rabin-karp', 'recurrence', 'recursion', 'regex', 'scc', 'segment-tree', 'shortest-path', 'sieve', 'sliding-window', 'sorting', 'sparse-tables', 'splay-tree', 'sprague-grundy', 'sqrt-decomposition', 'stable-marriage', 'stack', 'string', 'suffix-array', 'suffix-auto', 'suffix-trees', 'ternary-search', 'topological-sort', 'treap', 'tree-dp', 'trees', 'trie', 'two-pointers', 'union-find', 'vertex-cover', 'xor', 'zero-sum-game'])
### Global Variables End ###

urlfetch.set_default_fetch_deadline(60)
ereporter.register_logger()

### Models Begin ###
class Problem(ndb.Model):
	"""
	Model for Problem on Codechef. ID of this model is problem code.
	"""
	pname = ndb.StringProperty(required = True)
	submissions = ndb.IntegerProperty(required = True)
	accuracy = ndb.FloatProperty(required = True)
	author = ndb.StringProperty()
	num_fav = ndb.IntegerProperty(default = 0)
	sum_rating = ndb.IntegerProperty(indexed = False, default = 0)
	num_rating = ndb.IntegerProperty(indexed = False, default = 0)
	avg_rating = ndb.ComputedProperty(lambda self : (self.sum_rating*1.0)/(self.num_rating) if self.num_rating else None)
	tags = ndb.StringProperty(repeated=True)

	def get_url(self):
		"""
		Returns url for the given problem
		"""
		return master_url + self.key.id()

	def parse(self):
		"""
		Sets author and tags for a problem. Only invoked when a new problem entity is created.
		Returns True/False depending on whether parsing was successful or not.
		Eg. problem link for INS02 in Peer is dead.
		"""
		url = self.get_url()
		try:
			result = urlfetch.fetch(url, follow_redirects = False)
			if result.status_code == 200:
					uni = result.content.decode("utf8")
					soup = BeautifulSoup(uni)
					l = list(soup.findAll('a', 'problem-tag-small '))
					for tag in l:
						new_tag = tag.string.strip().encode('ascii','ignore')
						self.tags.append(str(new_tag))
					self.author = soup.find("td", width = '14%').next_sibling.next_sibling.string
					return True
			else:
				logging.error("Can't access the url " + url + "\n")
				return False
		except urlfetch.Error, e:
			logging.error("in parse " + self.key.id() + " recieved exception " + str(e))
			return False

	def to_html_string(self):
		"""
		Returns html for a particular problem. Useful for problem updates
		"""
		template = JINJA_ENVIRONMENT.get_template('/html/row.html')
		return template.render({"prob" : self})

class MyUser(ndb.Model):
	"""
	User model. ID of this model is the unique user_id returned by appengine user service
	"""
	codechef_id = ndb.StringProperty(required = True) 
	mail_id = ndb.StringProperty(required = True) 
	fav_problems = ndb.StringProperty(repeated = True) 
	todo_list = ndb.StringProperty(repeated = True)
	solved_id_list = ndb.StringProperty(repeated = True) 
	last_solved_count = ndb.IntegerProperty() #this is the solved count on the webpage, useful for detecting changes. 
	username = ndb.StringProperty(required = True, indexed = True) #username specific to this site

	@staticmethod
	def get_user():
		"""
		Returns MyUser currently logged in else None
		"""
		user = users.get_current_user()
		if user:
			database_user =  MyUser.get_by_id(user.user_id())
			if database_user:
				return database_user
			else:
				logging.error('User logged in but not in datastore, see MyUser model')
				return None
		return None

	def get_num_solved(self):
		return len(self.solved_id_list) if self.solved_id_list else 0

	@staticmethod
	def get_solved(user_html, codechef_id):
		"""
		Returns set of problems solved by the given user
		"""
		# if codechef_id is None:
		# 	logging.error('Codechef id is not registered')
		# 	return None
		regex = r'status\/(.+?),' + codechef_id
		##case must be ignored, since codechef user id is case insensitive
		return set(re.findall(regex, user_html, re.IGNORECASE))

	@staticmethod
	def get_user_page(codechef_id):
		"""
		Get codechef page of a given user
		"""
		try:
			url = user_url + codechef_id
			result = urlfetch.fetch(url, follow_redirects = False)
			if result.status_code == 200:
				return result.content
			else:
				return None
		except urlfetch.Error, e:
			logging.error("Error in get_user_page() " + codechef_id + " " + str(e))
			return None
		

	@staticmethod
	def get_solved_count(user_html):
		"""
		Returns solved count of a given user as reported on codechef, which may be inconsistent with the number of problems 
		shown for the user, see anudeep2011 profile
		"""
		soup = BeautifulSoup(user_html)
		return int(soup.find_all('table')[4].tr.find_next_sibling('tr').td.string) #see html structure of user page to see why this works
### Models End ###

### Utility classes Begin ###
class Mapper(object):
	"""
	Adapted from https://developers.google.com/appengine/articles/deferred. Modified to work with ndb. Should be subclassed for use
	"""
	# Subclasses should replace this with a model class (eg, model.Person).
	KIND = None
	# Subclasses can replace this with a list of (property, value) tuples to filter by.
	FILTERS = []
	def __init__(self):
		self.to_put = []
		self.to_delete = []
	def map(self, entity):
		"""
		Updates a single entity.
		Implementers should return a tuple containing two iterables (to_update, to_delete).
		"""
		return ([], [])

	def finish(self):
		"""Called when the mapper has finished, to allow for any final work to be done."""
		pass

	def get_query(self):
		"""Returns a query over the specified kind, with any appropriate filters applied."""
		q = self.KIND.query()
		for prop, value in self.FILTERS:
			q.filter("%s =" % prop, value)
		q.order(self.KIND.key)
		return q

	def run(self, batch_size=100):
		"""Starts the mapper running."""
		self._continue(None, batch_size)

	def _batch_write(self):
		"""Writes updates and deletes entities in a batch."""
		if self.to_put:
			ndb.put_multi(self.to_put)
			self.to_put = []
		if self.to_delete:
			ndb.delete_multi(self.to_delete)
			self.to_delete = []

	def _continue(self, start_key, batch_size):
		q = self.get_query()
		# If we're resuming, pick up where we left off last time.
		if start_key:
			q.filter(self.KIND.key > start_key)
			# Keep updating records until we run out of time.
			try:
			# Steps over the results, returning each entity and its index.
				for i, entity in enumerate(q):
					map_updates, map_deletes = self.map(entity)
					self.to_put.extend(map_updates)
					self.to_delete.extend(map_deletes)
					# Do updates and deletes in batches.
					if (i + 1) % batch_size == 0:
						self._batch_write()
						# Record the last entity we processed.
					start_key = entity.key
				self._batch_write()
			except DeadlineExceededError:
				# Write any unfinished updates to the datastore.
				self._batch_write()
				# Queue a new task to pick up where we left off.
				deferred.defer(self._continue, start_key, batch_size)
				return
				self.finish()

class MyUserUpdater(Mapper):
	"""
	Mapper to update stats for all users
	"""
	KIND = MyUser
	def map(self, my_user):
		new_page = MyUser.get_user_page(my_user.codechef_id)
		# logging.info(my_user.codechef_id)
		if not new_page:
			logging.error('Error updating user ' + my_user.key.id() + ' ' + my_user.codechef_id + ' in MyUserUpdater')
			return ([], [])
		new_solved_count = MyUser.get_solved_count(new_page)
		if new_solved_count != my_user.last_solved_count:
			my_user.solved_id_list = MyUser.get_solved(new_page, my_user.codechef_id)
			my_user.last_solved_count = new_solved_count
			logging.info(my_user.codechef_id + " updated")
			return ([my_user], [])
		#logging.info(my_user.codechef_id + " not updated")
		return ([], [])
### Utility classes End ###

### Global Functions Begin ###
def scrape(url):
	"""
	Function to scrape a url, add new problems and update stats for existing problems. Used via ProblemScraperHandler.
	"""
	try:
		result = urlfetch.fetch(url, follow_redirects = False)
	except urlfetch.Error, e:
		logging.error("Error fetching url in scrape for " + url)
		return
	to_put = []
	#these are for updating the memcache
	new_keys_added = []
	modified_entities = {}
	if result.status_code == 200:
		uni = result.content.decode("utf8")
		soup = BeautifulSoup(uni)
		try:
			for row in soup.findAll('tr', 'problemrow'):
				l = list(row)
				pcode = l[1].string
				problem = Problem.get_by_id(pcode)
				submissions = int(l[2].string) 
				accuracy = float(l[3].string)
				if problem:
					if problem.submissions == submissions and problem.accuracy == accuracy:
						#logging.info(pcode + " not updated")
						continue
					logging.info(pcode + " updated")
					problem.submissions = submissions
					problem.accuracy = accuracy
					to_put.append(problem)
					modified_entities[pcode] = problem
					continue
				#logging.info(pcode + " added")
				#else new problem found
				pname = row.b.string			
				problem = Problem(
						id = pcode,
						pname = pname,
						submissions = submissions,
						accuracy = accuracy
								)
				success = problem.parse()
				if not success:
					continue	
				to_put.append(problem)	
				modified_entities[pcode] = problem
				new_keys_added.append(problem.key)	
		except DeadlineExceededError:
			logging.error("DeadlineExceededError for scrape " + url + ".")
		finally:
			#update datastore
			ndb.put_multi(to_put)
			#update memcache
			if new_keys_added:
				update_key_list(new_keys_added)
			if modified_entities:
				update_problem_cache(modified_entities)
	else:
		logging.error("Can't access the url in scrape " + url + "\n")

### WARNING : SEE IF THERE'S A LIMIT ON MAX NO OF KEYS THAT CAN BE FETCHED
def get_key_list():
	"""
	Returns list of keys of all problems in database. It's retreived via memcache if possible, else from datastore.
	"""
	key_list = memcache.get('all_keys') #actual list of keys is stored, not the query object
	if key_list is None:
		key_list = Problem.query().fetch(keys_only = True) #retrieve from db
		#logging.info('key_list not in memcache')
		if not memcache.set(key = 'all_keys', value = key_list):
			logging.error('Error while setting memcache in get_key_list()')
	return key_list

def get_problem_list(key_list):
	"""
	Returns list of problems in datastore as per the key_list. Uses and updates memcache as necessary.
	"""
	id_list = [key.id() for key in key_list]
	retrieved_dict = memcache.get_multi(id_list, namespace='p') #these returns a dict of (id, entity) retreived from memcache
	retrieved_problems = retrieved_dict.values()
	retrieved_ids = retrieved_dict.keys()
	not_retrieved_ids = list(set(id_list) - set(retrieved_ids))
	if not not_retrieved_ids: #saves 1 memcache set rpc
		return retrieved_problems
	not_retrieved_keys = [ndb.Key(Problem, id) for id in not_retrieved_ids]
	not_retrieved_problems = ndb.get_multi(not_retrieved_keys)
	not_retrieved_dict = dict(zip(not_retrieved_ids, not_retrieved_problems))
	memcache.set_multi(not_retrieved_dict, namespace='p')
	return retrieved_problems + not_retrieved_problems

def get_entity(my_key, put_in_cache = True):
	"""
	Returns Problem entity corresponding to key. If put_in_cache is True, the entity is also entered into the memcache.
	"""
	my_entity = memcache.get(my_key.id(), namespace='p')
	if my_entity is None:
		my_entity = my_key.get()
		if put_in_cache and not memcache.set(my_key.id(), value = my_entity, namespace='p'):
			logging.error('Error while puting entity in memcache at get_entity() ' + my_key.id())
	return my_entity

def update_key_list(new_keys_added):
	"""
	Updates key list in memcache with new_keys_added passed as argument
	"""
	key_list = get_key_list()
	key_list.extend(new_keys_added)
	if not memcache.set(key = 'all_keys', value = key_list):
		memcache.delete(key = 'all_keys')
		logging.error('Error while setting memcache for new_keys_added in update_key_list')

def update_problem_cache(modified_entities):
	"""
	Updates dict(key, entity) of modified_entities in memcache
	"""
	not_set_key_list = memcache.set_multi(mapping = modified_entities, namespace='p')
	memcache.delete_multi(not_set_key_list, namespace = 'p')
	#logging.error('Error while deleting memcache for modified_entities in update_problem_cache')

### Global Functions End ###

### Handlers Begin ###
class BaseHandler(webapp2.RequestHandler):
    """
    BaseHandler class from which all RequestHandlers inherit. Defines base exception handling function for uncaught exceptions.
    """
    def handle_exception(self, exception, debug):
        # Log the error.
        logging.exception(exception)
        # Set a custom message.
        self.write_basic_page('An error occurred. Please retry your request again. Contact site admin if the error persists.')
        # If the exception is a HTTPException, use its error code.
        # Otherwise use a generic 500 error code.
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)

    def write_basic_page(self, content):
    	"""
    	Function to output a webpage with "content" and default site layout.
    	"""
        self.render("/html/template.html",  {"page_content" : content})

    def render(self, webpage, template_dict, base_set = False):
		"""
		Output a webpage as per template_dict. base_set tells whether variables for the base template have been set or not.
		"""
		template = JINJA_ENVIRONMENT.get_template(webpage)
		if not base_set:
			my_user = MyUser.get_user()
			template_dict['base_user'] = my_user
			template_dict['base_toggle_url'] = users.create_logout_url('/') if my_user else '/signin'
		self.response.out.write(template.render(template_dict))


class UserUpdateHandler(BaseHandler):
	"""
	Handler for cron job to update stats corresponding to all users in database.
	"""
	def get(self):
		mapper = MyUserUpdater()
		deferred.defer(mapper.run, _queue="user-cron-queue")

class ProblemScraperHandler(BaseHandler):
	"""
	Handler to parse all sub_urls, add new problems and update submissions and accuracy for existing problems
	"""
	def get(self):
		for sub_url in sub_urls:
			url = master_url + sub_url
			deferred.defer(scrape, url, _queue="problem-cron-queue")
		
# class QueryHandler(BaseHandler):
# 	def get(self):
# 		query = Problem.query()
# 		self.response.headers['Content-Type'] = 'text/plain'
# 		for prob in query:
# 			self.response.write(str(prob.key.id()) + " " + str(prob.key.kind()) + " \n")

# class DeleteAllHandler(BaseHandler):
# 	def get(self):
# 		for prob in Problem.query():
# 			prob.key.delete()

	
class ResponseHandler(BaseHandler):
	"""
	Handler for homepage.
	"""
	def get(self):

		my_user = MyUser.get_user()
		key_list = get_key_list()
		prob_list = get_problem_list(key_list)
		if my_user:
			toggle_url = users.create_logout_url(self.request.uri)
			solved = set(my_user.solved_id_list)
			todo = set(my_user.todo_list)
		else:
			toggle_url = '/signin'
			solved = set()
			todo = set()
		template_dict = {"problems" : prob_list, "base_user" : my_user, "base_toggle_url" : toggle_url, "solved" : solved, "todo" : todo}
		# render("compressed/response.min.html", self.response, template_dict, base_set = True)
		
		self.render("/html/response.html", template_dict, base_set = True)

class TodoHandler(BaseHandler):
	"""
	Handler for MarkTodo action on homepage. Updates single MyUser entity. Used via ajax.
	"""
	def post(self):
		self.response.headers['Content-Type'] = 'application/json'
		response_dict = {}
		my_user = MyUser.get_user()
		if not my_user:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Only logged in users can have todo lists.'
			self.response.write(json.dumps(response_dict))
			return	
		prob_id = self.request.get('id')
		if not prob_id: 
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Invalid Request. Request must send a Problem id.'
			self.response.write(json.dumps(response_dict))
			return
		my_key = ndb.Key(Problem, prob_id)
		if not my_key:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Invalid Problem Code.'
			self.response.write(json.dumps(response_dict))
			return
		if prob_id in my_user.solved_id_list:
			response_dict['fail'] = True
			response_dict['fail_msg'] = "You can't mark a solved problem as To-do."
			self.response.write(json.dumps(response_dict))
			return
		response_dict['fail'] = False
		if prob_id not in my_user.todo_list:
			response_dict['success_msg'] = prob_id + " was successfully added to your Todo List." 
			my_user.todo_list.append(prob_id)
			my_user.put()
		else:
			response_dict['success_msg'] = prob_id + " is already in your Todo List." 
		self.response.write(json.dumps(response_dict))
		return

class UnTodoHandler(BaseHandler):
	"""
	Handler for Un-Mark Todo action on homepage. Updates single MyUser entity. Used via ajax.
	"""
	def post(self):
		self.response.headers['Content-Type'] = 'application/json'
		response_dict = {}
		my_user = MyUser.get_user()
		if not my_user:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Only logged in users can have todo lists.'
			self.response.write(json.dumps(response_dict))
			return	
		prob_id = self.request.get('id')
		if not prob_id: 
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Invalid Request. Request must send a Problem id.'
			self.response.write(json.dumps(response_dict))
			return
		my_key = ndb.Key(Problem, prob_id)
		if not my_key:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Invalid Problem Code.'
			self.response.write(json.dumps(response_dict))
			return
		if prob_id not in my_user.todo_list:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Problem is not in your Todo list.'
			self.response.write(json.dumps(response_dict))
			return
		response_dict['fail'] = False
		response_dict['success_msg'] = prob_id + " was successfully removed from your Todo List." 
		my_user.todo_list.remove(prob_id)
		my_user.put()
		self.response.write(json.dumps(response_dict))
		return

class DataUpdateHandler(BaseHandler):
	"""
	Handler for '/dataupdate' corresponding to Update button on homepage. Used via ajax. Updates single MyUser and single Problem entity.
	Updates tags, num_fav, num_rating, sum_rating for a Problem and fav_problems for a MyUser.
	"""
	def post(self):
		self.response.headers['Content-Type'] = 'application/json'
		response_dict = {}
		my_user = MyUser.get_user()
		if not my_user:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Only logged in users can make updates.'
			self.response.write(json.dumps(response_dict))
			return
		prob_id = self.request.get('id')
		if not prob_id: 
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'Invalid Request.'
			self.response.write(json.dumps(response_dict))
			return
		my_key = ndb.Key(Problem, prob_id)
		if prob_id not in my_user.solved_id_list:
			response_dict['fail'] = True
			response_dict['fail_msg'] = 'You can only update problems you have solved.'
			self.response.write(json.dumps(response_dict))
			return
		prob = get_entity(my_key, put_in_cache = False)
		rating = self.request.get('rating')
		if rating:
			rating = int(rating)
			if rating < 0 or rating > 5:
				response_dict['fail'] = True
				response_dict['fail_msg'] = "Invalid rating request. Rating must be between 0 and 5 inclusive."
				self.response.write(json.dumps(response_dict))
				return
			prob.num_rating += 1
			prob.sum_rating += rating
		##WARNING: Should the app remember that a particular user updated a particular problem?

		response_dict['fail'] = False
		#to validate and check for empty string
		tags = set(json.loads(self.request.get('tags'))) #we get a string containing a json array from client
		tags = tags.intersection(tag_set) #only keep those which exist in tag_set
		tags = tags.union(prob.tags)
		prob.tags = list(tags) #merge lists removing duplicates
		if self.request.get('yes_radio') == 'true' and (prob_id not in my_user.fav_problems):
			prob.num_fav +=1
			my_user.fav_problems.append(prob_id) #add to list of fav problems of user
			my_user.put() 
		prob.put()
		#put in memcache
		if not memcache.set(key = my_key.id(), value = prob, namespace='p'):
			memcache.delete(key = my_key.id(), namespace = 'p')
			logging.error('Error putting entity in memcache at post DataUpdateHandler with ' + prob_id)
		response_dict['updated_row'] = prob.to_html_string() #serialize ndb model
		self.response.write(json.dumps(response_dict)) #convert to json
		return


class SignInHandler(BaseHandler):
	"""
	Handler for /signin , which is an intermediate url for signin/signup
	"""
	def get(self):
		user = users.get_current_user()
		if not user:
			self.redirect(users.create_login_url(dest_url = self.request.uri))
		elif MyUser.get_by_id(user.user_id()): #if signed in
			self.redirect('/')
		else: #create a new user in datastore
			self.render("/html/registration.html", {})

# class UserHandler(BaseHandler):
# 	def get(self):
# 		self.response.headers['Content-Type'] = 'text/plain'
# 		codechef_id = self.request.get('id')
# 		result = MyUser.get_user_page(codechef_id)
# 		if result:
# 			s = MyUser.get_solved(result, codechef_id)
# 			self.response.write(str(len(s)) + "\n")
# 			self.response.write(s)
# 		else:
# 			self.response.write('Error : Given user does not exist!')


	
class AccountFormHandler(BaseHandler):
	"""
	Handler for '/accountform'. Creates a new MyUser entity.
	"""
	def post(self):
		user = users.get_current_user()
		if not user: #first login in to google
			self.redirect('/signin')
			return
		username = self.request.get('username')
		codechef_id = self.request.get('codechef-id')
		if not username or not username_pattern.match(username):
			message = "Please enter a valid username. Redirecting you to the registration page."
			url = "/signin"
		elif not codechef_id or not username_pattern.match(codechef_id):
			message = "Please enter a valid codechef_id. Redirecting you to the registration page."
			url = "/signin"
		elif MyUser.query(MyUser.username == username).get():
			message = "The username you entered is already registered. Try another username. Redirecting you to the registration page."
			url = "/signin"
		else:
			result = MyUser.get_user_page(codechef_id)
			if result:
				new_user = MyUser(
							id = user.user_id(),
							codechef_id = codechef_id,
							mail_id = user.email(),
							solved_id_list = MyUser.get_solved(result, codechef_id),
							username = username,
							last_solved_count = MyUser.get_solved_count(result)
							)
				message = "Your registration was successful. Redirecting you to the homepage"
				url = '/'
				new_user.put()
			else:
				message = "Your Codechef ID can't be validated! Enter a correct Codechef ID and try again. Redirecting you to the registration page."
				url = "/signin"
		self.render("/html/reg_validate.html", {"message" : message, "url" : url})

class AccountHandler(BaseHandler):
	"""
	Handler for '/users/(\w+)'. Shows webpage corresponding to a MyUser entity.
	"""
	def get(self, username): #codechef_id is captured via regex
		self.response.headers['Content-Type'] = 'text/html'
		user = MyUser.query(MyUser.username == username).get()
		if not user:
			self.write_basic_page('Given user does not exist')
			return
		self.render("/html/account.html", {"user" : user})

class CompareHandler(BaseHandler):
	"""
	Handler for '/compare' or userVSuser request page.
	"""
	def get(self):
		self.render("/html/compare.html", {})

class UserVsUserHandler(BaseHandler):
	"""
	Handler for /result or userVSuser response page.
	"""
	def get(self):
		user1 = self.request.get('user1')
		user2 = self.request.get('user2')
		if not user1 or not username_pattern.match(user1):
			self.write_basic_page('Invalid Request. Please enter correct user 1 value.')
			return
		if not user2 or not username_pattern.match(user2):
			self.write_basic_page('Invalid Request. Please enter correct user 2 value.')
			return
		page1 = MyUser.get_user_page(user1)
		page2 = MyUser.get_user_page(user2)
		if page1 and page2:
			pset1 = MyUser.get_solved(page1, user1)
			pset2 = MyUser.get_solved(page2, user2)
			both = pset1.intersection(pset2)
			only1 = pset1.difference(both)
			only2 = pset2.difference(both)
			template_dict =  {"both" : both, "only1" : only1, "only2" : only2, "user1" : user1, "user2" : user2}
			template_dict['len1'] = len(only1)
			template_dict['len2'] = len(only2)
			template_dict['lenb'] = len(both)
			self.render("/html/result.html", template_dict)
		elif not page1:
			self.write_basic_page(user1 + " does not exist or problem in fetching user statistics. Try Later.")
		elif not page2:
			self.write_basic_page(user2 + " does not exist or problem in fetching user statistics. Try Later.")

class AboutHandler(BaseHandler):
	def get(self):
		self.render("/html/about.html",  {})

# class ExpHandler(BaseHandler):
# 	def get(self):
# 		render("exp.html", self.response.out, {})
### Handlers End ###

app = webapp2.WSGIApplication(
	[
		#('/deleteall', DeleteAllHandler),
		# ('/query', QueryHandler),
		# ('/tasks/tagupdate',TagUpdateHandler),
		('/', ResponseHandler),
		('/dataupdate', DataUpdateHandler),
		# ('/distag', DistinctTagHandler),
		('/signin', SignInHandler),
		# ('/getprobs', UserHandler),
		('/accountform', AccountFormHandler),
		('/todo', TodoHandler),
		('/users/(\w+)', AccountHandler),
		('/compare', CompareHandler),
		('/result', UserVsUserHandler),
		('/tasks/userupdate', UserUpdateHandler),
		('/tasks/problemupdate', ProblemScraperHandler),
		('/about', AboutHandler),
		('/untodo', UnTodoHandler)
		# ('/exp', ExpHandler)
	],
	debug = True
	)

