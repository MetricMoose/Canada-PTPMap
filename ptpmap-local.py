import csv
import progressbar
import simplekml

csvData = open('TAFL_LTAF.csv', 'r', encoding='utf-8')

taflCsv = csv.DictReader(csvData, fieldnames=[
    'TXRX', 'Frequency', 'FrequencyRecordIdentifier', 'RegulatoryService', 'CommunicationType',
    'ConformityToFrequencyPlan',
    'FrequencyAllocationName', 'Channel', 'LegacySystemInternationalCoordinationNumber', 'AnalogDigital',
    'OccupiedBandwidthKHz',
    'DesignationOfEmission', 'ModulationType', 'FiltrationInstalled', 'TxERPdBW', 'TxTransmitterPowerW',
    'TotalLossesDB', 'AnalogCapacity',
    'DigitalCapacity', 'RxUnfadedSignalLevel', 'RxThresholdSignalLevelBer10e', 'AntManufacturer', 'AntModel', 'AntGain',
    'AntPattern', 'HalfpowerBeamwidth',
    'FrontToBackRatio', 'Polarization', 'HeightAboveGroundLevel', 'AzimuthOfMainLobe', 'VerticalElelevationAngle',
    'StationLocation', 'LicenseeStationReference',
    'Callsign', 'StationType', 'ITUClassOfStation', 'StationCostCategory', 'NumberOfIdenticalStations',
    'ReferenceIdentifier', 'Provinces', 'Latitude',
    'Longitude', 'GroundElevationAboveSealevel', 'AntennaStructureHeightAboveGroundLevel', 'CongestionZone',
    'RadiusOfOperation', 'SatelliteName',
    'AuthorizationNumber', 'Service', 'Subservice', 'LicenceType', 'AuthorizationStatus', 'InserviceDate',
    'AccountNumber', 'LicenseeName', 'LicenseeAddress',
    'OperationalStatus', 'StationClassification', 'HorizontalPower', 'VerticalPower', 'StandbyTransmitterInformation'
])

logFile = open("ptpmap-log.txt", "w")

print("Finding TX Licenses")

allRxRecs = []
txRecords = []
txLicAuthNumSet = set()
txFreqSet = set()
#txLatSet = set()
#txLongSet = set()
ptpLinks = []

for row in taflCsv:
    if row['Service'] == '2' and row['Subservice'] in ['200','201'] and row['TXRX'] == 'TX':
        txRecords.append(row)
        txLicAuthNumSet.add(row['AuthorizationNumber'])
        txFreqSet.add(row['Frequency'])
        #txLatSet.add(row['Latitude'])
        #txLongSet.add(row['Longitude'])
    if row['TXRX'] == 'RX':
        allRxRecs.append(row)
print("Found " + str(len(txRecords)) + " licenses. Finding matching RX licenses")
cleanrx = []
for rec in allRxRecs:
    if rec['AuthorizationNumber'] in txLicAuthNumSet and rec['Frequency'] in txFreqSet:
#            and rec['Latitude'] not in txLatSet and rec['Longitude'] not in txLongSet:
        cleanrx.append(rec)

for txRecord in progressbar.progressbar(txRecords):
    link = {'tx': txRecord}
    rxRecords = []
    for txlicense in cleanrx:
        if txlicense['AuthorizationNumber'] == txRecord['AuthorizationNumber'] and \
                txlicense['Frequency'] == txRecord['Frequency'] and \
                txlicense['Latitude'] != txRecord['Latitude'] and \
                txlicense['Longitude'] != txRecord['Longitude']:
            rxRecords.append(txlicense)
    link['rx'] = rxRecords
    ptpLinks.append(link)

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
freedomStyle.linestyle.color = 'ff14B4FF' # Orange

otherStyle = simplekml.Style()
otherStyle.linestyle.width = 2
otherStyle.linestyle.color = 'ffFF78F0' # Magenta


def styleLink(licName, kmlLink):
    kmlLink.altitudemode = simplekml.AltitudeMode.relativetoground
    licNameLow = licName.lower()

    if licNameLow.find('bell') != -1:
        kmlLink.style = bellStyle
    elif licNameLow.find('rogers') != -1:
        kmlLink.style = rogersStyle
    elif licNameLow.find('telus') != -1:
        kmlLink.style = telusStyle
    elif licNameLow.find('xplornet') != -1:
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

        kmlLink = kml.newlinestring(
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
                kmlLink = kml.newlinestring(
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