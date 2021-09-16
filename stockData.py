# pip install streamlit fbprophet yfinance plotly
import streamlit as st
from datetime import date
import yfinance as yf
import numpy as np
import pandas as pd
from fbprophet import Prophet
from fbprophet.plot import plot_plotly
from fbprophet.diagnostics import cross_validation
from plotly import graph_objs as go
import pycountry
import re
from sklearn.metrics import mean_squared_error
from math import sqrt

@st.cache
def load_data(ticker, period, interval, date_index):
    comp = yf.Ticker(ticker)
    data = comp.history(period=period, interval=interval)
    data.reset_index(inplace=True)
    data[date_index] = data[date_index].astype(str)
    if(date_index == 'Datetime'):
        data[date_index] = data[date_index].str[:-6]
    return data

# Plot raw data
def plot_raw_data(data, date_index):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data[date_index], y=data['Open'], name="stock_open"))
    fig.add_trace(go.Scatter(x=data[date_index], y=data['Close'], name="stock_close"))
    fig.layout.update(title_text='Time Series data in Line-chart', xaxis_rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

    csfig = go.Figure(data=[go.Candlestick(
        x=data[date_index],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'])]
    )
    csfig.layout.update(title_text='Time Series data in Candle-chart', xaxis_rangeslider_visible=True)
    st.plotly_chart(csfig, use_container_width=True)

def build_model(comp_country_code):
    # Define forecasting model.
    m = Prophet(
            interval_width=0.95, 
            daily_seasonality=True,
            # weekly_seasonality=True, 
            changepoint_prior_scale=1 
            )
    if(comp_country_code):
        m.add_country_holidays(country_name=comp_country_code)
    return m

def show_forecast(m, forecast, data, p):
    # Show and plot forecast
    st.subheader('Forecast data')

    original = data['Close']
    prediction = forecast['yhat'][:-p]

    only_forecast = forecast # [len(data)-1:len(forecast)]
    only_forecast['Confidence (%)'] = (prediction / original) *100
    only_forecast['y'] = original
    st.write(only_forecast[["ds","y","yhat","yhat_lower","yhat_upper","Confidence (%)"]].iloc[::-1])

    mse = mean_squared_error(original, prediction)/len(data)
    st.write('Mean Confidence Percentage ', round(only_forecast['Confidence (%)'].mean() - mse, 2), '%')
    st.write('Mean Squared Error ',mse)
    st.write('Root Mean Squared Error ',sqrt(mse))

    st.subheader(f'Forecast plot ')
    fig1 = plot_plotly(m, forecast)
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("Forecast components")
    fig2 = m.plot_components(forecast)
    st.write(fig2)


def main():
    st.set_page_config(
            page_title="FINAnce preDICT",
            page_icon="•",
            layout="centered",
            initial_sidebar_state="expanded",
            )

    menu = ['Stocks', 'Forex', 'Crypto']
    choice = st.sidebar.selectbox('Select your market choice', menu)

    if(choice==menu[0]):
        st.title('Stock Prediction')

        selected_stock = st.text_input("Type in a ticker symbol:", value='TCS.NS', help="'[TICKER]' for Nasdaq and '[TICKER].NS' for NSE registered stocks")
        st.write('*Forgotten the ticker symbol?* Find it [here](https://finance.yahoo.com/lookup)')
        if not selected_stock:
            selected_stock = 'TCS.NS'
        comp = yf.Ticker(selected_stock)
        comp_info = comp.info
        comp_country_code = pycountry.countries.search_fuzzy(comp_info.get('country'))[0].alpha_2

        st.write('\nShowing results for**', comp_info.get('longName'),'**\n')
        # st.write(comp_info)
        st.write('\nRecommendation :**', comp_info.get('recommendationKey'),'**\n')
        
    elif(choice==menu[1]):
        st.title('Forex Prediction')

        x = st.text_input("From", value='USD')
        y = st.text_input("To", value='INR')
        selected_stock = x+y+'=X'
        st.write('*Forgotten the currency symbols?* Find them [here](https://finance.yahoo.com/currencies)')
        if not selected_stock:
            selected_stock = 'USDINR=X'
        comp = yf.Ticker(selected_stock)
        comp_country_code = False

        st.write('\nShowing results for**', x.upper(), '**to**', y.upper(), '** coversion rate.\n')

    elif(choice==menu[2]):
        st.title('Crypto Prediction')

        selected_stock = st.text_input("Type in a conversion string (For eg. 'BTC-INR' to get Bitcoin to Indian Rupee conversion rate.)", value='BTC-INR')
        st.write('*Forgotten the currency symbols?* Find them [here](https://finance.yahoo.com/cryptocurrencies)')
        if not selected_stock:
            selected_stock = 'BTC-INR'
        comp = yf.Ticker(selected_stock)
        comp_country_code = False
        x = re.search("^[a-zA-Z]*", selected_stock)
        y = re.search("[a-zA-Z]*$", selected_stock)

        st.write('\nShowing results for**', x.group().upper(), '**to**', y.group().upper(), '** coversion rate.\n')


    interval_aliases = ('5 mins', '15 mins', '30 mins', '1 hour', '1 day', '1 week', '1 month')
    interval_choices = ('5m', '15m', '30m', '60m', '1d', '1wk', '1mo')
    interval_alias = st.sidebar.radio('Select interval:', interval_aliases, index=4, help="Prediction only supported for '1 day' interval.") 
    interval = interval_choices[interval_aliases.index(interval_alias)]

    if(interval=='5m'):
        l = 60
        t = 'd'
        date_index = 'Datetime'
        # p = 10
        # f = '5min'
    elif(interval=='15m'):
        l = 60
        t = 'd'
        date_index = 'Datetime'
        # p = 10
        # f = 'h'
    elif(interval=='30m'):
        l = 60 
        t = 'd'
        date_index = 'Datetime'
        # p = 10
        # f = '30min'
    elif(interval=='60m'):
        l = 60 
        t = 'd'
        date_index = 'Datetime'
        # p = st.sidebar.slider('No. of hour\'s prediction:', 1, 60)
        # f = 'h'
    elif(interval=='1d'):
        y = st.sidebar.slider('No. of months\' data to fetch:', 1, 12, value=4)
        y *= 30
        t = 'd'
        period = str(y)+t
        date_index = 'Date'
        p = 1  # st.sidebar.slider('No. of day\'s prediction:', 1, 10)
        f = 'd'
    elif(interval=='1wk'):
        l = 10 
        t = 'y'
        date_index = 'Date'
        # f = 'W'
    elif(interval=='1mo'):
        l = 10 
        t = 'y'
        date_index = 'Date'
        # f = 'm'

    if(interval!='1d'):
        y = st.sidebar.slider('No. of days\' data to fetch:', 1, l)
        period = str(y)+t

    data = load_data(selected_stock, period, interval, date_index)

    st.subheader('Raw data')
    st.dataframe(data)
    plot_raw_data(data, date_index)

    df_train = data[[date_index,'Close']]
    df_train = df_train.rename(columns={date_index: "ds", "Close": "y"})
    # df_train['y'] = np.log(df_train['y'])
    # st.write(df_train)

    if (interval in interval_choices[4:5]):
        data_load_state = st.text('Predicting prices...')
        m = build_model(comp_country_code)
        m.fit(df_train)
        # Predict forecast.
        future = m.make_future_dataframe(periods=p)
        forecast = m.predict(future)
        # forecast["Prediction"] = np.exp(forecast.yhat)

        show_forecast(m, forecast, data, p)
        
        data_load_state.text('Prediction done.')

        # df_cv = cross_validation(m, initial='30 days', period='1 day', horizon = '10 days')
        # st.write(df_cv)

if __name__ == '__main__':
    try:
        main()
    except AttributeError:
        st.error("Found nothing with the inputs :'(")
    except KeyError:
        st.error("Input is not valid :-!")
    except ValueError:
        st.error("Didn't get enough value :(")


