import csv
import progressbar
import simplekml
import pandas as pd


taflCsv = pd.read_csv('TAFL_LTAF.csv', header=None, low_memory=False)

taflCsv.columns = [
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
]

# Drop unused columns
taflCsv = taflCsv.drop(columns=[
    'RegulatoryService',
    'CommunicationType',
    'ConformityToFrequencyPlan',
    'FrequencyAllocationName',
    'Channel',
    'LegacySystemInternationalCoordinationNumber',
    'AnalogDigital',
    'DesignationOfEmission',
    'ModulationType',
    'FiltrationInstalled',
    'TxERPdBW',
    'TxTransmitterPowerW',
    'TotalLossesDB',
    'TotalLossesDB',
    'RxUnfadedSignalLevel',
    'RxThresholdSignalLevelBer10e',
    'AntManufacturer',
    'AntModel',
    'AntGain',
    'AntPattern',
    'HalfpowerBeamwidth',
    'FrontToBackRatio',
    'Polarization',
    'AzimuthOfMainLobe',
    'VerticalElelevationAngle',
    'StationLocation',
    'LicenseeStationReference',
    'Callsign',
    'StationType',
    'ITUClassOfStation',
    'StationCostCategory',
    'NumberOfIdenticalStations',
    'ReferenceIdentifier',
    'GroundElevationAboveSealevel',
    'AntennaStructureHeightAboveGroundLevel',
    'CongestionZone',
    'LicenceType',
    'AuthorizationStatus',
    'OperationalStatus',
    'StationClassification',
    'HorizontalPower',
    'VerticalPower',
    'StandbyTransmitterInformation',
])

logFile = open("ptpmap-log.txt", "w")

print("Finding TX Licenses")


ptpLinks = []

# Get a list of all Point-to-Point and Point-to-Multipoint Licenses
txRecords = taflCsv.query('TXRX == "TX" and Service == 2 and Subservice in ("200","201")')
# Get a list of all receive licenses
allRxRecords = taflCsv.query('TXRX == "RX"')
# Get a list of RX records that have a matching TX record
cleanrx = allRxRecords[allRxRecords['AuthorizationNumber'].isin(txRecords['AuthorizationNumber']) & allRxRecords['Frequency'].isin(txRecords['Frequency'])]

# Loop through all the TX records to find the corresponding RX record
for txRecord in progressbar.progressbar(txRecords.itertuples(), max_value=len(txRecords.index)):
    # Store the TX record
    link = {'tx': txRecord}
    rxRecordsDf = cleanrx[
        # Needs to have a matching authorization number
        (cleanrx['AuthorizationNumber'] == txRecord.AuthorizationNumber) &
        # The RX frequency has to match the TX frequency
        (cleanrx['Frequency'] == txRecord.Frequency) &
        # The RX GPS coordinates cannot match the TX coordinates
        (cleanrx['Latitude'] != txRecord.Latitude) &
        (cleanrx['Longitude'] != txRecord.Longitude)
    ]
    # Store a dictionary of the RX record/records
    link['rx'] = rxRecordsDf.to_dict(orient='records')
    # Add the TX and RX records together into the ptpLinks list
    ptpLinks.append(link)

print("Finding RX licenses done, starting KML generation")

#Create a new KML file
kml = simplekml.Kml()

# Create the line widths and styles
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

# Applies a style to the link based on the provided organization name
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

# Generate folders for the different province codes
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

# Loop through the list of PTP links and generate the lines and description boxes
for ptp in progressbar.progressbar(ptpLinks):
    # Handle the empty province names by setting them to an empty string
    if type(ptp['tx'].Provinces) is str:
       kmlFolderName = ptp['tx'].Provinces
    else:
       kmlFolderName = '';

    # Generate the lines/descriptions for links with only one RX location (PTP)
    if len(ptp['rx']) == 1:
        # Generate description box
        linkDesc = f"""
        Bandwidth(MHz): {str(float(ptp['tx'].OccupiedBandwidthKHz) / 1000)}
        Analog Capacity (Calls): {str(ptp['tx'].AnalogCapacity)}
        Digital Capacity (Mbps): {str(ptp['tx'].DigitalCapacity)}
        In Service Date: {str(ptp['tx'].InserviceDate)}
        """

        # Generate the line/link between the two points
        kmlLink = kmlFolders[kmlFolderName].newlinestring(
            name="{} | {}".format(ptp['tx'].LicenseeName, str(ptp['tx'].Frequency)),
            description=linkDesc,
            coords=[
                (ptp['tx'].Longitude, ptp['tx'].Latitude, ptp['tx'].HeightAboveGroundLevel),
                (ptp['rx'][0]['Longitude'], ptp['rx'][0]['Latitude'], ptp['rx'][0]['HeightAboveGroundLevel']),
            ]
        )
        styleLink(ptp['tx'].LicenseeName, kmlLink)
    # Generate the lines/descriptions for links with multiple RX locations (PTMP)
    elif len(ptp['rx']) > 1:
        # Subservice 201 is Point to Multipoint, one TX with multiple RX
        # There's not really a good way to display this for large systems like BC Hydro or Milton Hydro
        # It just looks like a mess and makes Google Earth chug, so I'm whitelisting a few interesting systems
        if ptp['tx'].Subservice == "201" and ptp['tx'].LicenseeName in [
            'Bell Canada','Northwestel Inc.', 'Telus Communications Inc.', 'Sasktel', 'Hydro-Québec'
        ]:
            # Generate description box
            linkDesc = f"""
            Bandwidth(MHz): {str(float(ptp['tx'].OccupiedBandwidthKHz) / 1000)}
            Analog Capacity (Calls): {str(ptp['tx'].AnalogCapacity)}
            Digital Capacity (Mbps): {str(ptp['tx'].DigitalCapacity)}
            In Service Date: {str(ptp['tx'].InserviceDate)}
            """
            # Generate the lines/links between the TX location and the RX locations
            for endpoint in ptp['rx']:
                kmlLink = kmlFolders[kmlFolderName].newlinestring(
                    name="{} | {}".format(ptp['tx'].LicenseeName, str(ptp['tx'].Frequency)),
                    description=linkDesc,
                    coords=[
                        (ptp['tx'].Longitude, ptp['tx'].Latitude, ptp['tx'].HeightAboveGroundLevel),
                        (endpoint['Longitude'], endpoint['Latitude'], endpoint['HeightAboveGroundLevel']),
                    ]
                )
                styleLink(ptp['tx'].LicenseeName, kmlLink)
        else:

            errorMsg = f"""
Multiple RX Frequencies Found!
DBID: {ptp['tx'].FrequencyRecordIdentifier}
TXFrequency: {ptp['tx'].Frequency}
LicenseeName: {ptp['tx'].LicenseeName}
AuthorizationNumber: {ptp['tx'].AuthorizationNumber}
--------------------------\n
            """
            #print(errorMsg)
            logFile.write(errorMsg)

    elif len(ptp['rx']) == 0:

        errorMsg = f"""
No RX frequencies found!
DBID: {ptp['tx'].FrequencyRecordIdentifier}
TXFrequency: {ptp['tx'].Frequency}
LicenseeName: {ptp['tx'].LicenseeName}
AuthorizationNumber: {ptp['tx'].AuthorizationNumber}
--------------------------\n
        """
        #print(errorMsg)
        logFile.write(errorMsg)

print("Saving KML and Log")
kml.save("ptpmap.kml")
logFile.close()

