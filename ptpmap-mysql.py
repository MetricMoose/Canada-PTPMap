import mysql.connector
import simplekml
import progressbar
import dbconfig

cnx = mysql.connector.connect(user=dbconfig.user, password=dbconfig.password, host=dbconfig.host, database=dbconfig.database)

cursor = cnx.cursor(dictionary=True)


logFile = open("ptpmap-log.txt", "w")
print("Finding TX Licenses")
cursor.execute("""
	SELECT tafl_id, Frequency,OccupiedBandwidthKHz,AnalogCapacity,DigitalCapacity,HeightAboveGroundLevel,
	AzimuthOfMainLobe,Latitude,Longitude,AuthorizationNumber,LicenseeName,InserviceDate, Subservice
	FROM taflextract WHERE Service = 2 AND (Subservice = 200) AND TXRX='TX'
""")


txRecords = cursor.fetchall()


ptpLinks = []

print("Found " + str(len(txRecords)) + " licenses. Finding matching RX licenses")
for txRecord in progressbar.progressbar(txRecords):

	link = {}
	link['tx'] = txRecord


	findRxQuery = """
		SELECT tafl_id, Frequency,OccupiedBandwidthKHz,AnalogCapacity,DigitalCapacity,HeightAboveGroundLevel,
		AzimuthOfMainLobe,Latitude,Longitude,AuthorizationNumber,LicenseeName,InserviceDate,Subservice
		FROM taflextract WHERE AuthorizationNumber = '{}' AND TXRX="RX" AND Frequency = {} 
		AND Latitude != {} AND Longitude != {}

	""".format(txRecord['AuthorizationNumber'], txRecord['Frequency'], txRecord['Latitude'], txRecord['Longitude'])
	cursor.execute(findRxQuery)
	rxRecords = cursor.fetchall()

	link['rx'] = rxRecords;

	ptpLinks.append(link)

cnx.close()

print("Finding RX licenses done, starting KML generation")

kml = simplekml.Kml()

bellStyle = simplekml.Style()
bellStyle.linestyle.width = 2
bellStyle.linestyle.color = 'ffff0000'

rogersStyle = simplekml.Style()
rogersStyle.linestyle.width = 2
rogersStyle.linestyle.color = 'ff0000ff'

telusStyle = simplekml.Style()
telusStyle.linestyle.width = 2
telusStyle.linestyle.color = 'ff3CFF14'

otherStyle = simplekml.Style()
otherStyle.linestyle.width = 2
otherStyle.linestyle.color = 'ffFF78F0'

for ptp in progressbar.progressbar(ptpLinks):

	if len(ptp['rx']) == 1:


		linkDesc = """
		Bandwidth(MHz): {}
		Analog Capacity (Calls): {}
		Digital Capacity (Mbps): {}
		In Service Date: {}
		""".format(
		str(float(ptp['tx']['OccupiedBandwidthKHz'])/1000),
		str(ptp['tx']['AnalogCapacity']),
		str(ptp['tx']['DigitalCapacity']),
		str(ptp['tx']['InserviceDate'])
		)

		kmlLink = kml.newlinestring(
			name="{} | {}".format(ptp['tx']['LicenseeName'], str(ptp['tx']['Frequency'])),
			description=linkDesc,
			coords=[
			(ptp['tx']['Longitude'],ptp['tx']['Latitude'],ptp['tx']['HeightAboveGroundLevel']),
			(ptp['rx'][0]['Longitude'],ptp['rx'][0]['Latitude'],ptp['rx'][0]['HeightAboveGroundLevel']),
			]

		)
		kmlLink.altitudemode = simplekml.AltitudeMode.relativetoground
		#kmlLink.style.linestyle.width = 2
		if ptp['tx']['LicenseeName'].lower().find('bell') != -1:
			#kmlLink.style.linestyle.color = 'ffff0000'
			kmlLink.style = bellStyle
		elif ptp['tx']['LicenseeName'].lower().find('rogers') != -1:
			#kmlLink.style.linestyle.color = 'ff0000ff'
			kmlLink.style = rogersStyle
		elif ptp['tx']['LicenseeName'].lower().find('telus') != -1:
			#kmlLink.style.linestyle.color = 'ff3CFF14'
			kmlLink.style = telusStyle
		else:
			#kmlLink.style.linestyle.color = 'ffFF78F0'
			kmlLink.style = otherStyle
	

	elif len(ptp['rx']) > 1:

		# Subservice 201 is Point to Multipoint, one TX with multiple RX
		if ptp['tx']['Subservice'] == "201":
			for endpoint in ptp['rx']:
				kmlLink = kml.newlinestring(
					name="{} | {}".format(ptp['tx']['LicenseeName'], str(ptp['tx']['Frequency'])),
					description=linkDesc,
					coords=[
					(ptp['tx']['Longitude'],ptp['tx']['Latitude'],ptp['tx']['HeightAboveGroundLevel']),
					(endpoint['Longitude'],endpoint['Latitude'],endpoint['HeightAboveGroundLevel']),
					]

				)
				kmlLink.altitudemode = simplekml.AltitudeMode.relativetoground
				#kmlLink.style.linestyle.width = 2
				if ptp['tx']['LicenseeName'].lower().find('bell') != -1:
					#kmlLink.style.linestyle.color = 'ffff0000'
					kmlLink.style = bellStyle
				elif ptp['tx']['LicenseeName'].lower().find('rogers') != -1:
					#kmlLink.style.linestyle.color = 'ff0000ff'
					kmlLink.style = rogersStyle
				elif ptp['tx']['LicenseeName'].lower().find('telus') != -1:
					#kmlLink.style.linestyle.color = 'ff3CFF14'
					kmlLink.style = telusStyle
				else:
					#kmlLink.style.linestyle.color = 'ffFF78F0'
					kmlLink.style = otherStyle
		else:

			errorMsg = """
Multiple RX Frequencies Found!
DBID: {}
TXFrequency: {}
LicenseeName: {}
AuthorizationNumber: {}
--------------------------\n
			""".format(
				ptp['tx']['tafl_id'],
				ptp['tx']['Frequency'],
				ptp['tx']['LicenseeName'],
				ptp['tx']['AuthorizationNumber'],
			)
			print(errorMsg)
			logFile.write(errorMsg)

	elif len(ptp['rx']) == 0:

		errorMsg = """
No RX frequencies found!
DBID: {}
TXFrequency: {}
LicenseeName: {}
AuthorizationNumber: {}
--------------------------\n
		""".format(
			ptp['tx']['tafl_id'],
			ptp['tx']['Frequency'],
			ptp['tx']['LicenseeName'],
			ptp['tx']['AuthorizationNumber'],
		)
		print(errorMsg)
		logFile.write(errorMsg)


print("Saving KML and Log")
kml.save("ptpmap.kml")
logFile.close()