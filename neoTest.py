from neo4j.v1 import GraphDatabase, basic_auth

# helper function to get the db session
def get_session():
    driver = GraphDatabase.driver("bolt://localhost", auth=basic_auth("neo4j", "neo4j"))
    session = driver.session()
    return session

# helper function to validate if the user is present in the db.
def validate_user(name):
	session = get_session()
	result = session.run("MATCH (u:User {name: {name}}) RETURN u.name AS name", {"name": name})
	results = list(result)
	session.close()
	if len(results) >0:
		return (results[0]['name'] == name)
	return False

# create request object either as owner or on behalf of some other user.
def create_request(user, title, desc, owner=None):
	if not validate_user(user):
		return {'result': False, 'error': 'User not present'}

	session = get_session()
	if owner is not None:
		if not validate_user(owner):
			return {'result': False, 'error': 'Owner not present'}

		result = session.run("MATCH (u:User {name: {name}})"
							 "CREATE (r:Request {title: {title}, desc: {desc}})"
							 "CREATE (u)-[:Owner]->(r)"
							 "RETURN r", {"name": owner, "title": title, "desc": desc})
	else:
		result = session.run("MATCH (u:User {name: {name}})"
							 "CREATE (r:Request {title: {title}, desc: {desc}})"
							 "CREATE (u)-[:Owner]->(r)"
							 "RETURN r", {"name": user, "title": title, "desc": desc})
	results = list(result)
	session.close()
	if len(results) >0:
		return {'result': True, 'error': None}
	return {'result': False, 'error': results}

# create a new user, everyone should be able to do it.
def create_user(name, born):
	session = get_session()
	try:
		session.run("CREATE (u:User {name: {name}, born: {born}, is_active: True})",
					{"name": name, "born": born})
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
		result = session.run("MATCH (u:User {name: {user}}), (g:Group {name: {group}}), \
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
	if not validate_user(name) or not validate_user(as_user):
		return {'result': False, 'error': 'User/AS User not present'}
	session = get_session()
	if name == as_user:
		result = session.run("MATCH (o:Object {name: 'User'}) RETURN o.self_update_exceptions AS exceptions")
		exceptions = (list(result)[0]['exceptions'])
		for key in data:
			if key in exceptions:
				session.close()
				return({'result': False, 'error': 'sorry you are not allowed to perform this operation'})
		session.run("MATCH (u:User {name: {name}}) SET u += {data}", {"name": name, "data": data})
		session.close()
		return({'result': True, 'error': None})
	result = session.run("MATCH (u1:User {name: {as_user}}), (u2:User {name: {name}}), \
						  p = shortestPath((u1)-[*]->(u2)) RETURN p", {"as_user": as_user, "name": name})
	path = False
	for record in result:
		if len(record['p'].relationships) > 0:
			path = True
	if path:
		session.run("MATCH (u:User {name: {name}}) SET u += {data}", {"name": name, "data": data})
	session.close()
	return({'result': True, 'error': None})

# promote a user iff there is a path from the acting user to the group they are trying to promote to.
def promote(user, groupName, as_user):
	if not validate_user(user) or not validate_user(as_user):
		return {'result': False, 'error': 'User/AS User not present'}
	session = get_session()
	result = session.run("MATCH (u:User {name: {user}}), (g:Group {name: {group}}), \
						  p = shortestPath((u)-[*]->(g)) RETURN p", {"user": as_user, "group": groupName})
	path = False
	for record in result:
		if len(record['p'].relationships) > 0:
			path = True

	if path:
		session.run("MATCH (u:User {name: {user}}), (g:Group {name: {group}}) \
				     CREATE (u)-[:In]->(g) Return u", {"user": user, "group": groupName})
		session.close()
		return{'result': True, 'error': None}
	session.close()
	return{'result': False, 'error': 'we were not able to assign the user to the group.'}

# take action on a request iff the action allows you to draw the Taken edge to it.
def take_action(action, request, as_user):
	if not validate_user(as_user):
		return {'result': False, 'error': 'AS User not present'}
	session = get_session()
	action_result = session.run("MATCH (a:Action {name: {action}}) RETURN a.Taken as reqs", {"action": action})
	action_paths = (list(action_result)[0]['reqs'])
	print(action_paths)
	paths = session.run("MATCH (u:User {name: {user}}), (r:Request {title: {request}}), \
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


if __name__ == '__main__':
	#print(create_request('Keanu Reeves','testing','just a test'))
	#print(create_user('Ahmad Chatha', '1/1/1999'))
	#print(promote('Carrie-Anne Moss', 'Sfari Admin', 'Carrie-Anne Moss'))
	#print(take_action('Create', 'Top Gun', 'Laurence Fishburne'))
	#print(take_action('Create', 'Top Gun', 'Keanu Reeves'))
	#print(take_action('Submit', 'Top Gun', 'Carrie-Anne Moss'))
	#print(take_action('Approve', 'Top Gun', 'Carrie-Anne Moss'))
	#print(take_action('Approve', 'Top Gun', 'Keanu Reeves'))
	#print(update_user(name='Keanu Reeves', as_user='Keanu Reeves', data={'born': 2016}))
	#print(update_user(name='Keanu Reeves', as_user='Keanu Reeves', data={'is_active': False}))
	#print(update_user( name='Carrie-Anne Moss', as_user='Keanu Reeves', data={'born': 2016}))
	# notice how we are using the same function to create different types of objects
	#print(create_object('Keanu Reeves', 'Action', 'generic action'))
	#print(create_object('Keanu Reeves', 'Group', 'generic group'))
