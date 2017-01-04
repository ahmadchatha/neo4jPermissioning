# neo4jPermissioning
CRUD permissions in Neo4j

#### A prototype for implementing permissions in a graph db such as Neo4j
https://docs.google.com/presentation/d/1jGh-QAI1EZVVPothAw8CjpWOfDcUVmYaA7OMdBdXaTs/edit?usp=sharing

Setup
-------

First install community version of Neo4j for your os at https://neo4j.com/ 

Create virtualenv, activate it and do

	pip install -r requirements.txt
	
Run the CREATE queries from cql.txt in the neo4j UI to insert the data into the db.
	
Run
-------

Make sure neo4j server is running. Uncomment function calls in neoTest.py and run

	python neoTest.py
	
Make sure to update the db username/password in neoTest.py if you updated it when setting up neo4j.
