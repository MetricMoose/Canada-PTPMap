# Canada-PTPMap
This project was founded by MetricMoose as a way to visualize the Point-to-Point wireless connections in use within Canada, as shown within the Spectrum Management System made available by Innovation, Science and Economic Development Canada (ISED).

## Prerequisites
- python3
- python3-pip

## Steps to generate the map
1) Install required pip modules: `pip install progressbar2 simplekml`
2) Download the dataset from ISED's website: `wget http://www.ic.gc.ca/engineering/SMS_TAFL_Files/TAFL_LTAF.zip`
3) Extract the obtained dataset to reveal the Comma-Separated Values document containing the data.
4) Run the map generation script: `python3 ptpmap-local.py`

## Other notes
Other options for datasets (including Field Descriptions) can be obtained at the following link: https://sms-sgs.ic.gc.ca/eic/site/sms-sgs-prod.nsf/eng/h_00010.html