from neo4j.v1 import GraphDatabase, basic_auth
import collections

# helper function to get the db session
def get_session():
    driver = GraphDatabase.driver("bolt://localhost", auth=basic_auth("neo4j", "simonsnyc"))
    session = driver.session()
    return session

# helper function to validate if the user is present in the db.
def validate_user(name):
	session = get_session()
	result = session.run("MATCH (u:User {username: {username}}) RETURN u.username AS username, u.password AS password", {"username": self.username})
	results = list(result)
	session.close()
	if len(results) >0:
		return (results[0]['name'] == name)
	return False

# create request object either as owner or on behalf of some other user.
def create_request(user, data, type):
	#really should get them from somewhere
	if type == 'sfari':
		request_group = 'Sfari Requests'
	else:
		request_group = 'Life Sciences Requests'
	session = get_session()
	# assumes only applicant can create requests for now
	result = session.run("MATCH (o:Object {name: 'Request'}) RETURN o."+type+"_applicant_owner_write AS fields")
	fields = []
	given_fields = []
	for key in data:
		given_fields.append(key)
	for record in result:
		fields = record['fields']
	compare = lambda x, y: collections.Counter(x) == collections.Counter(y)
	if compare(fields,given_fields) == True:
		session.run("MATCH (u:User {username: {name}}), (g:Group {name: {group_name}})"
					 "CREATE (r:Request)"
					 "CREATE (u)-[:"+type+"_applicant_owner {read_allowed:[], read_denied:[], write_allowed:[], write_denied:[]}]->(r)"
					 "CREATE (g)-[:admin_owner {read_allowed:[], read_denied:[], write_allowed:[], write_denied:[]}]->(r)"
					 "SET r+={data}"
					 "RETURN r", {"name": user, "data": data, "group_name": request_group})
		session.close()
		return True
	session.close()
	return False
# SHOULD FIX THE FOLLOWING 2 funcs
def get_request(title, as_user):
	session = get_session()
	result = session.run("MATCH (u:User {username: {user}}), (r:Request {title: {title}}), (o:Object {name: 'Request'}), \
						  p = shortestPath((u)-[*]->(r)) RETURN p,r,o", {"user": as_user, "title": title})
	session.close()
	request = None
	for record in result:
		request = {}
		positive_exceps = record['p'].relationships[len(record['p'].relationships)-1].properties['read_allowed']
		negative_exceps = record['p'].relationships[len(record['p'].relationships)-1].properties['read_denied']
		relationship = record['p'].relationships[len(record['p'].relationships)-1].type
		workflow_fields = record['o'].properties[relationship+'_read']
		for i in positive_exceps:
			if i not in workflow_fields:
				workflow_fields.append(i)
		for j in negative_exceps:
			if j in workflow_fields:
				workflow_fields.remove(j)
		for k in workflow_fields:
			request[k] = record['r'].properties[k]
	return(request)

def update_request(data, as_user):
	session = get_session()
	result = session.run("MATCH (u:User {username: {user}}), (r:Request {title: {title}}), (o:Object {name: 'Request'}), \
						  p = shortestPath((u)-[*]->(r)) RETURN p,r,o", {"user": as_user, "title": data['title']})
	status = False
	for record in result:
		positive_exceps = record['p'].relationships[len(record['p'].relationships)-1].properties['write_allowed']
		negative_exceps = record['p'].relationships[len(record['p'].relationships)-1].properties['write_denied']
		relationship = record['p'].relationships[len(record['p'].relationships)-1].type
		workflow_fields = record['o'].properties[relationship+'_write']
		for i in positive_exceps:
			if i not in workflow_fields:
				workflow_fields.append(i)
		for j in negative_exceps:
			if j in workflow_fields:
				workflow_fields.remove(j)
		valid = True
		for key in data:
			if key not in workflow_fields:
				valid = False
				break
		if valid:
			result = session.run("MATCH (r:Request {title: {title}}) SET r += {data}", {"title": title, "data": data})
			status = True
	session.close()
	return(status)

# only update an object if you are in permission admin group
def update_object(user, data):
	session = get_session()
	result = session.run("MATCH (u:User {username:{username}}), (g:Group {name: 'Permission Admin'}) \
						OPTIONAL MATCH (u)-[p]->(g) RETURN p",{"username": user})
	permitted = False
	for record in result:
		if record['p'].type == 'in':
			permitted = True
	if permitted:
		result = session.run("MATCH (o:Object {name: {name}}) SET o += {data}", {"name": data['name'], "data": data})
		session.close()
		return True
	session.close()
	return False

# only get the object if you are in permission admin group
def get_object(user, object_name):
	session = get_session()
	result = session.run("MATCH (u:User {username:{username}}), (g:Group {name: 'Permission Admin'}) \
						OPTIONAL MATCH (u)-[p]->(g) RETURN p",{"username": user})
	permitted = False
	answer = None
	for record in result:
		if record['p'].type == 'in':
			permitted = True
	if permitted:
		result = session.run("MATCH (o:Object {name: {name}}) RETURN o", {"name": object_name})
		for record in result:
			answer = record['o'].properties
	session.close()	
	return answer

# only apply exceptions if you are in permission admin group
def apply_exceptions(as_user, user, object_name, object_pk):
	session = get_session()
	result = session.run("MATCH (u:User {username:{username}}), (g:Group {name: 'Permission Admin'}) \
						OPTIONAL MATCH (u)-[p]->(g) RETURN p",{"username": as_user})
	permitted = False
	for record in result:
		if record['p'].type == 'in':
			permitted = True
	if permitted:
		result = session.run("MATCH (u:User {username: {user}}), (o:"+object_name+" {"+object_pk['key']+": {value}}),  \
						  p = shortestPath((u)-[*]->(o)) RETURN p", {"user": user, "value": object_pk['value']})
		for record in result:
			print(record['p'].relationships)



# create a new user, everyone should be able to do it.
def create_user(username, password):
	session = get_session()
	try:
		session.run("CREATE (u:User {username: {username}, password: {password}, is_active: True})",
					{"username": username, "password": password})
	except CypherError:
		raise RuntimeError("Something really bad has happened!")
	finally:
		session.close()
	return {'result': True, 'error': None}

# create objects by looking at the meta nodes.
def create_object(user_name, object_name, data_name):
	if not validate_user(user_name):
		return {'result': False, 'error': 'User/AS User not present'}
	session = get_session()
	query = "MATCH (o:Object {name: "+object_name+"}) RETURN o.create AS allowed"
	result = session.run("MATCH (o:Object {name: 'Action'}) RETURN o.create AS allowed")
	allowed_groups = (list(result)[0]['allowed'])
	present = False
	for group in allowed_groups:
		result = session.run("MATCH (u:User {username: {user}}), (g:Group {name: {group}}), \
						  p = shortestPath((u)-[*]->(g)) RETURN p", {"user": user_name, "group": group})
		path = False
		for record in result:
			if len(record['p'].relationships) > 0:
				path = True
				break
		if path:
			present = True
			break

	if present:
		query = "CREATE (o:"+object_name+" {name: {name}}) RETURN o"
		session.run(query, {"name": data_name})
		session.close()
		return({'result': True, 'error': None})
	session.close()
	return({'result': False, 'error': "you don't have the necessary perssion to create this action"})

# update user by looking at the User meta node
def update_user(name, as_user, data):
	if not validate_user(name):
		return {'result': False, 'error': 'User/AS User not present'}
	session = get_session()
	if name == as_user:
		result = session.run("MATCH (o:Object {name: 'User'}) RETURN o.self_update_exceptions AS exceptions")
		exceptions = (list(result)[0]['exceptions'])
		for key in data:
			if key in exceptions:
				session.close()
				return({'result': False, 'error': 'sorry you are not allowed to perform this operation'})
		session.run("MATCH (u:User {username: {name}}) SET u += {data}", {"name": name, "data": data})
		session.close()
		return({'result': True, 'error': None})
	result = session.run("MATCH (u1:User {username: {as_user}}), (u2:User {username: {name}}), \
						  p = shortestPath((u1)-[*]->(u2)) RETURN p", {"as_user": as_user, "name": name})
	path = False
	for record in result:
		if len(record['p'].relationships) > 0:
			path = True
	if path:
		session.run("MATCH (u:User {username: {name}}) SET u += {data}", {"name": name, "data": data})
	session.close()
	return({'result': True, 'error': None})

# promote a user iff there is a path from the acting user to the group they are trying to promote to.
def promote(user, groupName, as_user):
	if not validate_user(user):
		return {'result': False, 'error': 'User not present'}
	session = get_session()
	result = session.run("MATCH (u:User {username: {user}}), (g:Group {name: {group}}), \
						  p = shortestPath((u)-[*]->(g)) RETURN p", {"user": as_user, "group": groupName})
	path = False
	for record in result:
		if len(record['p'].relationships) > 0:
			path = True

	if path:
		session.run("MATCH (u:User {username: {user}}), (g:Group {name: {group}}) \
				     CREATE (u)-[:In]->(g) Return u", {"user": user, "group": groupName})
		session.close()
		return{'result': True, 'error': None}
	session.close()
	return{'result': False, 'error': 'we were not able to assign the user to the group.'}

# take action on a request iff the action allows you to draw the Taken edge to it.
def take_action(action, request, as_user):
	session = get_session()
	action_result = session.run("MATCH (a:Action {name: {action}}) RETURN a.Taken as reqs", {"action": action})
	action_paths = (list(action_result)[0]['reqs'])
	print(action_paths)
	paths = session.run("MATCH (u:User {username: {user}}), (r:Request {title: {request}}), \
						 p = allShortestPaths((u)-[*]->(r)) RETURN p", {"user": as_user, "request": request})
	path_exist = False
	for record in paths:
		path = ''
		relationships = list(record['p'].relationships)
		for i in range(0,len(relationships)):
			path = path + relationships[i].type
			if i != (len(relationships)-1):
				path = path + '_'
		if(path in action_paths):
			path_exist = True
			break
	if path_exist:
		session.run("MATCH (a:Action {name: {action}}), (r:Request {title: {request}}) \
				     CREATE (r)-[:Taken {By: {user}}]->(a) RETURN a", 
				     {"action": action, "request": request, "user": as_user})
		session.close()
		return{'result': True, 'error': None}
	session.close()
	return{'result': False, 'error': 'we were not able to take that action on the request.'}
