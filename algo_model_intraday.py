import numpy as np
import pandas as pd

import yfinance as yf
import numpy

import keras
from keras.models import Sequential
from keras.layers import Dense,Dropout,LSTM
#from keras.callbacks import EarlyStopping,ModelCheckpoint,TensorBoard
#from keras.wrappers.scikit_learn import KerasRegressor
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

import math
from sklearn.metrics import mean_squared_error
from numpy import array

from smartapi import SmartConnect
import requests
import datetime
import time
import pyotp


#Download Tata motors data from yahoo finance
df = yf.download('HINDUNILVR.NS')

# check open price for first day and close price for last day
print("Starting price: ",df.iloc[0][0])
print("Ending price: ", df.iloc[-1][3])

# check start date and end date in our dataset
print("Starting date: ",df.index[0])
print("Ending date: ", df.index[-1])

# drop all columns except 'close ' columns as we are going to do prediction only on closing price
df.drop(columns=['Open','High','Low','Adj Close','Volume'],inplace=True)

# Resample the data to weekly frequency.we can use mean or last
df = df.resample('W').mean()

# LSTM are sensitive to the scale of the data. so we apply MinMax scaler 
# Preprocess the data
scaler=MinMaxScaler(feature_range=(0,1))
df1=scaler.fit_transform(np.array(df).reshape(-1,1))

# Split data into training and testing sets
train_size=int(len(df1)*0.7)
test_size=len(df1)-train_size
train_data,test_data=df1[0:train_size,:],df1[train_size:len(df1),:1]

# convert an array of values into a dataset matrix
#function to create new dataset which is required by LSTM.giving sequence of data to our LSTM model
def create_dataset(dataset, time_step=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-time_step-1):
        a = dataset[i:(i+time_step), 0]   ###i=0, 0,1,2,3-----99   100 
        dataX.append(a)
        dataY.append(dataset[i + time_step, 0])
    return np.array(dataX), numpy.array(dataY)

# reshape into X=t,t+1,t+2,t+3 and Y=t+4
time_step = 20
X_train, y_train = create_dataset(train_data, time_step)
X_test, ytest = create_dataset(test_data, time_step)

model=Sequential()
model.add(LSTM(50,input_shape=(time_step,1)))
model.add(Dropout(0.2))
#model.add(LSTM(50,return_sequences=True))
#model.add(LSTM(50))
model.add(Dense(1))
model.compile(loss='mean_squared_error',optimizer='adam')

print(model.summary())
history = model.fit(X_train,y_train,validation_data=(X_test,ytest),epochs=100,batch_size=64,verbose=1)

### Lets Do the prediction and check performance metrics
train_predict=model.predict(X_train)
test_predict=model.predict(X_test)

##Transformback to original form
train_predict=scaler.inverse_transform(train_predict)
test_predict=scaler.inverse_transform(test_predict)

### Calculate RMSE performance metrics
print(math.sqrt(mean_squared_error(y_train,train_predict)))

### Test Data RMSE
print(math.sqrt(mean_squared_error(ytest,test_predict)))



# Generate buy and sell signals
buy_signals = []
sell_signals = []
for i in range(len(test_predict)):
    if i == 0:
        continue
    if test_predict[i] > test_predict[i - 1]:
        buy_signals.append(df.index[train_size + time_step + i])
    else:
        sell_signals.append(df.index[train_size + time_step + i])

# Print buy and sell signals
print("Buy signals:")
for signal in buy_signals:
    print(signal.date())
print("Sell signals:")
for signal in sell_signals:
    print(signal.date())
    
user_name = ""  # your user id
password = ""   #your password
api_key= ""     #your api key
token1=""       #your token
feed_token = None
token_map = None

obj=SmartConnect(api_key=api_key)
data = obj.generateSession(user_name,password,pyotp.TOTP(token1).now())

def place_order(symbol,token,qty,exch_seg,buy_sell,ordertype,price):
    try:
        orderparams = {
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": buy_sell,
            "exchange": exch_seg,
            "ordertype": ordertype,
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": price,
            "quantity": qty
            }
        orderId=obj.placeOrder(orderparams)
        print("The order id is: {}".format(orderId))
    except Exception as e:
        print("Order placement failed: {}".format(e))
        
def enter_in_trade():
    try:
        if test_predict[-1] > df['Close'][-1]:
            a=1
            print('Placing BUY order')
            place_order("HINDUNILVR-EQ","1394",100,'NSE','BUY','MARKET',0)
        else:
            a=2
            print('Placing SELL order')
            place_order("HINDUNILVR-EQ","1394",100,'NSE','SELL','MARKET',0)
    
        exitPosition(a)

    except:
            print("ERROR OCCURED at level1")
            time.sleep(1)

    

def exitPosition(a):
    traded = "No"

    while traded == "No":
        dt = datetime.datetime.now()
        try:        
            if ((a==1) and (dt.hour >= 15 and dt.minute >= 15)) :
                print('Closing BUY order')
                place_order("HINDUNILVR-EQ","1394",100,'NSE','SELL','MARKET',0)
                traded = "BUY"
            elif ((a==2) and (dt.hour >= 15 and dt.minute >= 15)) :
                print('Closing SELL order')
                place_order("HINDUNILVR-EQ","1394",100,'NSE','BUY','MARKET',0)
                traded = "SELL"
            else:
                print("WAITING FOR EXIT TIME")
                time.sleep(1)

        except:
            print("ERROR OCCURED at level2")
            time.sleep(1)

        

def checkTime():
    x = 1
    while x == 1:
        dt = datetime.datetime.now()
        if( dt.hour >= 9 and dt.minute >= 15 and dt.second >= 0 ):
            print("time reached")
            x = 2
            enter_in_trade()
    
        else:
            time.sleep(3)
            print(dt , " Waiting for Time to check price ")
            
checkTime()