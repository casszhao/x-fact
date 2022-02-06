import pandas as pd
import csv
import json

# 5 yo change

tsv = pd.read_csv('test.all.tsv', sep='\t', index_col=False, on_bad_lines='skip')
print(tsv.shape)
df = tsv[['claimDate','claim','label']]
df['exp_split'] = 'test'
print(df.shape)

# take years
df['claimDate'] = df.claimDate.astype(str).str[:4]
# take only true and false
print(' -------- take only true and false')
print(df['label'].value_counts())
df = df.loc[(df['label'] == 'false') | (df['label'] == 'true')]
print('count label unique values')
print(df['label'].value_counts())



df['annotation_id'] = 'placeholder'
df['label_id'] = df['label']
df['label']=df['label'].replace({'false':0, 'true':1})
print(df['label'].value_counts())
print(df)

df = df.rename(columns={"claim": "text"})
Bi2020 = df.loc[(df['claimDate'] == '2020')]
Bi2020 = Bi2020[['annotation_id','exp_split','text','label','label_id']]
print('------Bi2020-------------')
print(Bi2020.shape)
print(Bi2020.head())

Bi2018 = df.loc[(df['claimDate'] == '2018')]
Bi2018 = Bi2018[['annotation_id','exp_split','text','label','label_id']]
print('------Bi2018-------------')
print(Bi2018.shape)
print(Bi2018.head())

Bi2016 = df.loc[(df['claimDate'] == '2016')]
Bi2016 = Bi2016[['annotation_id','exp_split','text','label','label_id']]
print('------Bi2016-------------')
print(Bi2016.shape)
print(Bi2016.head())



def csv_to_json(csvFilePath, jsonFilePath):
   jsonArray = []

   # read csv file
   with open(csvFilePath) as csvf:
      # load csv file data using csv library's dictionary reader
      csvReader = csv.DictReader(csvf)

      # convert each csv row into python dict
      for row in csvReader:
         # print(row['label'])
         row['label'] = int(row['label'])

         # add this python dict to json array
         jsonArray.append(row)

   # convert python jsonArray to JSON String and write to file
   with open(jsonFilePath, 'w') as jsonf:
      jsonString = json.dumps(jsonArray, indent=4)
      jsonf.write(jsonString)



Bi2020.to_csv('dev.csv', index = False)
csvFilePath = 'dev.csv'
csv_to_json(csvFilePath, 'Bi2020_test.json')

Bi2018.to_csv('dev.csv', index = False)
csvFilePath = 'dev.csv'
csv_to_json(csvFilePath, 'Bi2018_test.json')

Bi2016.to_csv('dev.csv', index = False)
csvFilePath = 'dev.csv'
csv_to_json(csvFilePath, 'Bi2016_test.json')

