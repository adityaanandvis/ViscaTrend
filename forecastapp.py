import streamlit as st
import pandas as pd
import numpy as np

import pystan
from prophet import Prophet
from prophet.plot import add_changepoints_to_plot
from prophet.diagnostics import cross_validation
from prophet.diagnostics import performance_metrics
from prophet.plot import plot_cross_validation_metric
import json
from prophet.serialize import model_to_json, model_from_json
import holidays

import altair as alt
import plotly as plt
import plotly.offline as pyoff
import plotly.graph_objs as go
import plotly.figure_factory as ff
import base64
import itertools
from datetime import datetime
import json

st.set_page_config(page_title ="Viscadia Trend Forecasting Tool",
                    initial_sidebar_state="collapsed",
                    page_icon="")

tabs = ["Application"]
page = st.sidebar.radio("Tabs",tabs)

@st.cache(persist=False,
          allow_output_mutation=True,
          suppress_st_warning=True,
          show_spinner= True)
def load_csv():
    
    df_input = pd.DataFrame()  
    df_input=pd.read_csv(input,sep=None ,engine='python', encoding='utf-8',
                            parse_dates=True,
                            infer_datetime_format=True)
    return df_input

def prep_data(df):

    df_input = df.rename({date_col:"ds",metric_col:"y"},errors='raise',axis=1)
    st.markdown("The selected date column is now labeled as **ds** and the values columns as **y**")
    df_input = df_input[['ds','y']]
    df_input =  df_input.sort_values(by='ds',ascending=True)
    return df_input


code_options = ["Dataframe information","Model fitting","Cross validation","Hyperparam tuning"]

if page == "Application":
    
    with st.sidebar:
        if st.button(label='Clear cache'):
            caching.clear_cache()
    
    from PIL import Image
    # Load an image file 
    image = Image.open("Viscadia_logo_BLUE_with-tagline_LARGE-copy.jpg") 
    st.image(image, width=300, height=300, use_column_width=False)
    st.markdown(
    """
    <style>
        h1 {
            color: #143e66;
        }
    </style>
    """,
    unsafe_allow_html=True, 
    )


    st.title('ViscaTrend: Viscadia Trend Forecasting Tool')
    caching.clear_cache()
    df =  pd.DataFrame()   

    st.subheader('1. Data loading ')
    st.write("Import a time series csv file.")
    with st.beta_expander("Data format"): 
        st.write("The dataset can contain multiple columns but you will need to select a column to be used as dates and a second column containing the metric you wish to forecast. The columns will be renamed as **ds** and **y** to be compliant with Prophet.The ideal format for the ds (datestamp) column should be YYYY-MM-DD for a date or YYYY-MM-DD HH:MM:SS for a timestamp. The y column must be numeric.")

    input = st.file_uploader('',key='in')

    if input:
        with st.spinner('Loading data..'):
            df = load_csv()
    
            st.write("Columns:")
            st.write(list(df.columns))
            columns = list(df.columns)
    
            col1,col2 = st.beta_columns(2)
            with col1:
                date_col = st.selectbox("Select date column",index= 0,options=columns,key="date")
            with col2:
                metric_col = st.selectbox("Select values column",index=1,options=columns,key="values")

            df = prep_data(df)
            output = 0


    if st.checkbox('Chart data',key='show'):
        with st.spinner('Plotting data..'):
            col1,col2 = st.beta_columns(2)
            with col1:
                st.dataframe(df)
                
            with col2:    
                st.write("Dataframe description:")
                st.write(df.describe())

        try:
            line_chart = alt.Chart(df).mark_line().encode(
                x = 'ds:T',
                y = "y:Q",tooltip=['ds:T', 'y']).properties(title="Time series preview").interactive()
            st.altair_chart(line_chart,use_container_width=True)
            
        except:
            st.line_chart(df['y'],use_container_width =True,height = 300)
            
        

    st.subheader("2. Parameters configuration")

    with st.beta_container():
        st.write('In this section you can modify the algorithm settings.')
            
        with st.beta_expander("Horizon"):
            periods_input = st.number_input('Select how many future periods (months) to forecast.',
            min_value = 1, max_value = 3660,value=24)

        with st.beta_expander("Seasonality"):
            st.markdown("""The default seasonality used is additive, but the best choice depends on the specific case, therefore specific domain knowledge is required.""")
            seasonality = st.radio(label='Seasonality',options=['additive','multiplicative'])

        with st.beta_expander("Seasonality components"):
            monthly = st.checkbox("Monthly")
            yearly = st.checkbox("Yearly")

        with st.beta_expander("Growth model"):
            st.write('Prophet uses by default a linear growth model.')
            st.write('Disclaimer: For using the logistic function please first select the cap value higher than the floor value.')
            growth = st.radio(label='Growth model',options=['linear',"logistic"]) 

            if growth == 'linear':
                growth_settings= {
                            'cap':1,
                            'floor':0
                        }
                cap=1
                floor=1
                df['cap']=1
                df['floor']=0

            if growth == 'logistic':
                st.info('Configure saturation')

                cap = st.slider('Cap',min_value=0.0,max_value=1.0,step=0.05)
                floor = st.slider('Floor',min_value=0.0,max_value=1.0,step=0.05)
                if floor > cap:
                    st.error('Invalid settings. Cap must be higher then floor.')
                    growth_settings={}

                if floor == cap:
                    st.warning('Cap must be higher than floor')
                else:
                    growth_settings = {
                        'cap':cap,
                        'floor':floor
                        }
                    df['cap']=cap
                    df['floor']=floor
            
            
        with st.beta_expander('Holidays'):
            
            countries = ['Country name','Italy','Spain','United States','France','Germany','UK']
            
            with st.beta_container():
                years=[2021]
                selected_country = st.selectbox(label="Select country",options=countries)

                if selected_country == 'Italy':
                    for date, name in sorted(holidays.IT(years=years).items()):
                        st.write(date,name) 
                            
                if selected_country == 'Spain':
                    
                    for date, name in sorted(holidays.ES(years=years).items()):
                            st.write(date,name)                      

                if selected_country == 'United States':
                    
                    for date, name in sorted(holidays.US(years=years).items()):
                            st.write(date,name)
                            
                if selected_country == 'France':
                    
                    for date, name in sorted(holidays.FR(years=years).items()):
                            st.write(date,name)
                            
                if selected_country == 'Germany':
                    
                    for date, name in sorted(holidays.DE(years=years).items()):
                            st.write(date,name)
                            
                if selected_country == 'UK':
                    
                    for date, name in sorted(holidays.UK(years=years).items()):
                            st.write(date,name)

                else:
                    holidays = False
                            
                holidays = st.checkbox('Add country holidays to the model')

        with st.beta_expander('Hyperparameters'):
            st.write('In this section it is possible to tune the scaling coefficients.')
            
            seasonality_scale_values= [0.1, 1.0,5.0,10.0]    
            changepoint_scale_values= [0.01, 0.1, 0.5,1.0]

            st.write("The changepoint prior scale determines the flexibility of the trend, and in particular how much the trend changes at the trend changepoints.")
            changepoint_scale= st.select_slider(label= 'Changepoint prior scale',options=changepoint_scale_values)
            
            st.write("The seasonality change point controls the flexibility of the seasonality.")
            seasonality_scale= st.select_slider(label= 'Seasonality prior scale',options=seasonality_scale_values)    


    with st.beta_container():
        st.subheader("3. Forecast")
        st.write("Fit the model on the data and generate future prediction.")
        st.write("Load a time series to activate.")
        
        if input:
            
            if st.checkbox("Initialize model (Fit)",key="fit"):
                if len(growth_settings)==2:
                    m = Prophet(seasonality_mode=seasonality,
                                growth=growth,
                                changepoint_prior_scale=changepoint_scale,
                                seasonality_prior_scale= seasonality_scale)
                    if holidays:
                        m.add_country_holidays(country_name=selected_country)
                        
                    if monthly:
                        m.add_seasonality(name='monthly', period=30.4375, fourier_order=5)

                    with st.spinner('Fitting the model..'):

                        m = m.fit(df)

                        future = m.make_future_dataframe(periods=periods_input,freq='M')
                        future['cap']=cap
                        future['floor']=floor
                        st.write("The model will produce forecast up to ", future['ds'].max())
                        st.success('Model fitted successfully')

                else:
                    st.warning('Invalid configuration')

            if st.checkbox("Generate forecast (Predict)",key="predict"):
                # try:
                    with st.spinner("Forecasting.."):

                        forecast = m.predict(future)
                        st.success('Prediction generated successfully')
                        # st.success("Dataframe error")
                        fig1 = m.plot(forecast)
                        st.write(fig1)
                        output = 1

                        if growth == 'linear':
                            fig2 = m.plot(forecast)
                            a = add_changepoints_to_plot(fig2.gca(), m, forecast)
                            st.write(fig2)
                            output = 1
                        
            
            if st.checkbox('Show components'):
                try:
                    with st.spinner("Loading.."):
                        fig3 = m.plot_components(forecast)
                        st.write(fig3)
                        # plot
                except: 
                    st.warning("Requires forecast generation..") 

        st.subheader('4. Model validation ')
        st.write("In this section it is possible to do cross-validation of the model.")
        with st.beta_expander("Explanation"):
            st.markdown("""The Prophet library makes it possible to divide our historical data into training data and testing data for cross validation. The main concepts for cross validation with Prophet are:""")
            st.write("Training data (initial): The amount of data set aside for training. The parameter is in the API called initial.")
            st.write("Horizon: The data set aside for validation.")
            st.write("Cutoff (period): a forecast is made for every observed point between cutoff and cutoff + horizon.""")

            
        with st.beta_expander("Cross validation"):    
            initial = st.number_input(value= 6,label="initial",min_value=1,max_value=108)
            initial = str(initial) + " Months"

            period = st.number_input(value= 6,label="period",min_value=1,max_value=108)
            period = str(period) + " Months"

            horizon = st.number_input(value= 24, label="horizon",min_value=1,max_value=500)
            horizon = str(horizon) + " Months"

            st.write(f"Here we do cross-validation to assess prediction performance on a horizon of **{horizon}**, starting with **{initial}** of training data in the first cutoff and then making predictions every **{period}**.")
        
            
        with st.beta_expander("Metrics"):
            
            if input:
                if output == 1:
                    metrics = 0
                    if st.checkbox('Calculate metrics'):
                        with st.spinner("Cross validating.."):
                            try:
                                df_cv = cross_validation(m, initial=initial,
                                                        period=period, 
                                                        horizon = horizon,
                                                        parallel="processes")                                        
                            
                            
                            
                                df_p= performance_metrics(df_cv)
                                # st.write(df_p)
                                metrics = 1
                            except:
                                st.write("Invalid configuration. Try other parameters.")
                                metrics = 0


                            st.markdown('**Metrics definition**')
                            st.write("Mse: mean absolute error")
                            st.write("Mae: Mean average error")
                            st.write("Mape: Mean average percentage error")
                            
                            if metrics == 1:

                                metrics = ['Choose a metric','mse','mae','mape']
                                selected_metric = st.selectbox("Select metric to plot",options=metrics)
                                if selected_metric != metrics[0]:
                                    fig4 = plot_cross_validation_metric(df_cv, metric=selected_metric)
                                    st.write(fig4)
                        
            else:
                st.write("Create a forecast to see metrics")

        
        st.subheader('5. Export results ')
        
        st.write("Finally you can export your forecast result into an excel file.")
        
        if input:
            if output == 1:
                col1, col2, col3, col4 = st.beta_columns(4)

                with col1:
                    
                    if st.button('Export forecast (.csv)'):
                        with st.spinner("Exporting.."):

                            export_forecast = pd.DataFrame(forecast[['ds','yhat_lower','yhat','yhat_upper']])
                            export_forecast= export_forecast.to_csv(decimal='.')
                            b64 = base64.b64encode(export_forecast.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}">Download CSV File</a> (click to download csv file **forecast.csv**)'
                            st.markdown(href, unsafe_allow_html=True)
            
                with col2:
                    
                    if st.button("Export model metrics (.csv)"):
                        try:
                            df_p = df_p.to_csv(decimal=',')
                            b64 = base64.b64encode(df_p.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}">Download CSV File</a> (click derecho > guardar como **metrics.csv**)'
                            st.markdown(href, unsafe_allow_html=True)
                        except:
                            st.write("No metrics to export")

               
            else:
                st.write("Generate a forecast to download.")

