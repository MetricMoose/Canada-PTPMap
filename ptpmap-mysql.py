import mysql.connector
import simplekml
import progressbar
import dbconfig

cnx = mysql.connector.connect(user=dbconfig.user, password=dbconfig.password, host=dbconfig.host, database=dbconfig.database)

cursor = cnx.cursor(dictionary=True)


logFile = open("ptpmap-log.txt", "w")
print("Finding TX Licenses")
cursor.execute("""
	SELECT tafl_id, Frequency,OccupiedBandwidthKHz,AnalogCapacity,DigitalCapacity,HeightAboveGroundLevel, Provinces,
	AzimuthOfMainLobe,Latitude,Longitude,AuthorizationNumber,LicenseeName,InserviceDate, Subservice, FrequencyRecordIdentifier
	FROM taflextract WHERE Service = 2 AND (Subservice = 200 OR Subservice = 201) AND TXRX='TX'
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
bellStyle.linestyle.color = 'ffff0000' # Blue

rogersStyle = simplekml.Style()
rogersStyle.linestyle.width = 2
rogersStyle.linestyle.color = 'ff0000ff' # Red

telusStyle = simplekml.Style()
telusStyle.linestyle.width = 2
telusStyle.linestyle.color = 'ff3CFF14' # Green

xplornetStyle = simplekml.Style()
xplornetStyle.linestyle.width = 2
xplornetStyle.linestyle.color = 'FF1478A0' # Brown

freedomStyle = simplekml.Style()
freedomStyle.linestyle.width = 2
freedomStyle.linestyle.color = '6414B4FF' # Orange

otherStyle = simplekml.Style()
otherStyle.linestyle.width = 2
otherStyle.linestyle.color = 'ffFF78F0' # Magenta

kmlFolders = {}

kmlFolders['AB'] = kml.newfolder(name='Alberta')
kmlFolders['BC'] = kml.newfolder(name='British Columbia')
kmlFolders['CW'] = kml.newfolder(name='All Canada')
kmlFolders['NL'] = kml.newfolder(name='Newfoundland and Labrador')
kmlFolders['NB'] = kml.newfolder(name='New Brunswick')
kmlFolders['MB'] = kml.newfolder(name='Manitoba')
kmlFolders['NU'] = kml.newfolder(name='Nunavut')
kmlFolders['ON'] = kml.newfolder(name='Ontario')
kmlFolders['PE'] = kml.newfolder(name='Prince Edward Island')
kmlFolders['QC'] = kml.newfolder(name='Quebec')
kmlFolders['SK'] = kml.newfolder(name='Saskatchewan')
kmlFolders['NT'] = kml.newfolder(name='North West Territories')
kmlFolders['US'] = kml.newfolder(name='United States')
kmlFolders['NS'] = kml.newfolder(name='Nova Scotia')
kmlFolders['YT'] = kml.newfolder(name='Yukon')
kmlFolders['IP'] = kml.newfolder(name='Interprovincial')
kmlFolders[''] = kml.newfolder(name='Other')



def styleLink(licName, kmlLink):
    kmlLink.altitudemode = simplekml.AltitudeMode.relativetoground
    licNameLow = licName.lower()

    if licNameLow.find('bell') != -1:
        kmlLink.style = bellStyle
    elif licNameLow.find('rogers') != -1:
        kmlLink.style = rogersStyle
    elif licNameLow.find('telus') != -1:
        kmlLink.style = telusStyle
    elif licNameLow.find('xplore inc') != -1:
        kmlLink.style = xplornetStyle
    elif licNameLow.find('freedom mobile') != -1:
        kmlLink.style = freedomStyle
    else:
        kmlLink.style = otherStyle

for ptp in progressbar.progressbar(ptpLinks):
    if len(ptp['rx']) == 1:

        linkDesc = f"""
        Bandwidth(MHz): {str(float(ptp['tx']['OccupiedBandwidthKHz']) / 1000)}
        Analog Capacity (Calls): {str(ptp['tx']['AnalogCapacity'])}
        Digital Capacity (Mbps): {str(ptp['tx']['DigitalCapacity'])}
        In Service Date: {str(ptp['tx']['InserviceDate'])}
        """

        #kmlLink = kml.newlinestring(
        kmlLink = kmlFolders[ptp['tx']['Provinces']].newlinestring(
            name="{} | {}".format(ptp['tx']['LicenseeName'], str(ptp['tx']['Frequency'])),
            description=linkDesc,
            coords=[
                (ptp['tx']['Longitude'], ptp['tx']['Latitude'], ptp['tx']['HeightAboveGroundLevel']),
                (ptp['rx'][0]['Longitude'], ptp['rx'][0]['Latitude'], ptp['rx'][0]['HeightAboveGroundLevel']),
            ]

        )
        styleLink(ptp['tx']['LicenseeName'], kmlLink)

    elif len(ptp['rx']) > 1:
        # Subservice 201 is Point to Multipoint, one TX with multiple RX
        # There's not really a good way to display this for large systems like BC Hydro or Milton Hydro
        # It just looks like a mess and makes Google Earth chug, so I'm whitelisting a few interesting systems
        if ptp['tx']['Subservice'] == "201" and ptp['tx']['LicenseeName'] in [
            'Bell Canada','Northwestel Inc.', 'Telus Communications Inc.', 'Sasktel', 'Hydro-Québec'
        ]:
            for endpoint in ptp['rx']:
                #kmlLink = kml.newlinestring(
                kmlLink = kmlFolders[ptp['tx']['Provinces']].newlinestring(
                    name="{} | {}".format(ptp['tx']['LicenseeName'], str(ptp['tx']['Frequency'])),
                    description=linkDesc,
                    coords=[
                        (ptp['tx']['Longitude'], ptp['tx']['Latitude'], ptp['tx']['HeightAboveGroundLevel']),
                        (endpoint['Longitude'], endpoint['Latitude'], endpoint['HeightAboveGroundLevel']),
                    ]

                )
                styleLink(ptp['tx']['LicenseeName'], kmlLink)
        else:

            errorMsg = f"""
Multiple RX Frequencies Found!
DBID: {ptp['tx']['FrequencyRecordIdentifier']}
TXFrequency: {ptp['tx']['Frequency']}
LicenseeName: {ptp['tx']['LicenseeName']}
AuthorizationNumber: {ptp['tx']['AuthorizationNumber']}
--------------------------\n
            """
            #print(errorMsg)
            logFile.write(errorMsg)

    elif len(ptp['rx']) == 0:

        errorMsg = f"""
No RX frequencies found!
DBID: {ptp['tx']['FrequencyRecordIdentifier']}
TXFrequency: {ptp['tx']['Frequency']}
LicenseeName: {ptp['tx']['LicenseeName']}
AuthorizationNumber: {ptp['tx']['AuthorizationNumber']}
--------------------------\n
        """
        #print(errorMsg)
        logFile.write(errorMsg)

print("Saving KML and Log")
kml.save("ptpmap.kml")
logFile.close()