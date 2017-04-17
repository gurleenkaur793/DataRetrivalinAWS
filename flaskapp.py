from flask import Flask, request, make_response, render_template, redirect, url_for,session
import time, MySQLdb, os, math, random
import boto3, botocore
import memcache
#from passlib.hash import sha256_crypt
from decimal import *
import csv

app = Flask(__name__)

#global IFlag = 'FALSE'

#Connecting to RDS
db = MySQLdb.connect("gurleen.crads19wqzue.us-west-2.rds.amazonaws.com","root","Gurleen123","asg3and4",local_infile=1)
print "Connection to RDS Established!!"
cursor = db.cursor()

#Connecting to S3 through Boto3
s3 = boto3.resource('s3')
print "Connection to S3 Established!!"

#Connecting to Memcache
mc = memcache.Client(['gurleen.m0jlhf.cfg.usw2.cache.amazonaws.com:11211'], debug=0)
print "Connection to MEMECACHE Established!!"

@app.route('/')
def Welcome():
    return render_template('register.html')

@app.route('/upload', methods=['POST','GET'])
def upload():
	file = request.files['file']
	file_name = file.filename
	csvfile= csv.reader(file_name)

	# Assigning bucket name - user session name 
	bucket_name = "aws-gurleen-test1-"+session.get('username')
	
	#import botocore for bucket access
	bucket = s3.Bucket(bucket_name)
	exists = True
	try:
		s3.meta.client.head_bucket(Bucket=bucket_name)
	except botocore.exceptions.ClientError as e:
		# If a client error is thrown, then check that it was a 404 error.
		# If it was a 404 error, then the bucket does not exist.
		error_code = int(e.response['Error']['Code'])
		if error_code == 404:
			exists = False
			#Creating Bucket in S3
			#s3.create_bucket(Bucket=bucket_name
			s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
			 'LocationConstraint': 'us-west-2'})
			print "Bucket "+bucket_name+" Created Successfully" 
			
	if exists == True:
	   print "\nBucket "+bucket_name+" Already Exists" 

	print "\n\tExecuting Queries for File Upload:"	
	
	#Start Timer
	start_time = time.clock()
	print "Start Time to Load Data into S3: "+ str(round(Decimal(start_time),5))+" seconds"
	
	#Storing Data
	s3.Object(bucket_name, file_name).put(Body=file.read())

	#End Timer
	total_time = Decimal(time.clock() - start_time)
	print "Total Time to Load Data into S3: "+ str(round(Decimal(total_time),5))+" seconds"
	
	
	row1 = next(csvfile)
	print row1
	# file_name = "UNPrecip.csv"
	table_name = file_name[:-4]

	sql = "CREATE TABLE IF NOT EXISTS " + table_name + "("
	for i in range (0,len(row1)):
	    sql+= row1[i] + " varchar(100)"
	    if(i<len(row1)-1):
	        sql+=","
	sql+=")"

	#print "query fired"
	print "===========\n"+sql+"\n==========="

	startTime = time.clock()
	print 'start time is :' + str(round(Decimal(startTime),3)) + "seconds"
	cursor.execute(sql)
	endTime = time.clock()
	print 'end time is :' + str(round(Decimal(endTime),3)) + "seconds"
	totalTime = endTime - startTime
	print totalTime

	return "File "+file_name+" Uploaded Successfully on S3.Table created successfully in "+totalTime+" seconds."
	
	
@app.route('/execute', methods=['POST','GET'])
def execute():
	sql=str(request.form['my_query'])
	ukey = str(request.form['key'])
	
	print "\n\n\tUser Key:" +ukey
	print "\n\tQuery:\n" +sql
	
	sql_time = nosql_time = Decimal(0.0)
	
	if "SELECT " or "Select " or "select " in sql: 	
	
		start_time = time.clock()
		mcobj = mc.get(ukey)
		nosql_time = Decimal(time.clock() - start_time)
			
		if not mcobj:
			print "\n\tLoaded Data for \n"+str(sql)+" from RDS MySQLdb"
			
			# Make nosql_time:
			nosql_time = Decimal(0.0)
			
			#Execute MySQLdb Queries:
			start_time = time.clock()
			cursor.execute(sql)
			result = cursor.fetchall()
			sql_time = Decimal(time.clock() - start_time)
			#num_rows = int(cursor.rowcount)
					
			#How toreturn a string with this render template incase you wanna return time along with page for 0 results???
			if cursor.rowcount==0:
				#return render_template("index_login.html")
				return "Query Executed Successfully and Returned 0 Results.\n Total SQL Execution Time:\t"+str(round(Decimal(sql_time),5))
			else:
				list = '\n\t Row Count: '+str(cursor.rowcount)
				for row in result:
					list = list + str(row)+'\n'
				mc.set(ukey,list)
				list = list + '\n\t Total SQL Time To Execute Query In SECONDS: '+str(round(Decimal(sql_time),5))
				return list
		else:
			print "\n\tLoaded Data for \n"+str(sql)+"\nfrom MEMCACHE"
			list = ''
			for row in mcobj:
				list = list + str(row)+'\n'
			list = list + '\n\t Total NoSQL Time To Execute Query In SECONDS: '+str(round(Decimal(nosql_time),5))
			return list
	
	elif "INSERT " or "Insert " or "insert " in sql:
		start_time = time.clock()
		cursor.execute(sql)
		result = cursor.fetchall()
		sql_time = Decimal(time.clock() - start_time)
		db.commit()
		print "\n\tInserted Data Successfully\n"
		list = '\n\t Row Count: '+str(cursor.rowcount)
		for row in result:
			list = list + str(row)+'\n'
		mc.clear()
		return list+"\nQuery Executed Successfully and Returned 0 Results.\n Total SQL Insert Execution Time:\t"+str(round(Decimal(sql_time),5))
	
	else:
		return "Check Your Query Cause It is not Supported By Our Application"


app.secret_key = "1|D0N'T|W4NT|TH15|T0|3E|R4ND0M"

@app.route('/', methods=['POST','GET'])
def register():
	if 'username' in session:
		return render_template('index_login.html', username = session.get('username'))
	
	if request.method == 'POST':
		
		username = request.form['username']
		password = request.form['password']
		if(username == '' or password == ''):
			return render_template('register.html')
			
		sql = "select username from register where username='"+username+"'"
		cursor.execute(sql)
		if cursor.rowcount == 1:
			return render_template('register.html')
		
		sql = "insert into register (username, password) values ('"+username+"','"+password+"')"
		cursor.execute(sql)
		db.commit()
		return render_template('login.html')
	else:
		return render_template('register.html')
		

@app.route('/login', methods=['POST','GET'])
def login():
	if 'username' in session:
		return render_template('index_login.html', username = session.get('username'))
	
	if request.method == 'POST':
		
		username = request.form['username']
		password = request.form['password']
		
		sql = "select password from register where username = '"+username+"'"
		cursor.execute(sql)
		if cursor.rowcount == 1:
			results = cursor.fetchall()
			for row in results:
				print row[0]
				if password == row[0]:
					session['username'] = username
					return render_template('index_login.html', username = username)
		return render_template('login.html')
	else:
		return render_template('login.html')


@app.route('/logout', methods=['POST','GET'])
def logout():
	if 'username' in session:
		session.pop('username', None)
	return redirect(url_for('register'))


if __name__ == '__main__':
	app.run(debug=True)