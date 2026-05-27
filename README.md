# Real-time Smart City Analytics System

## Project Description

This project is a Real-Time Smart City Analytics System developed using Apache Kafka, Apache Spark Streaming, Machine Learning, and Streamlit.

The system simulates real-time smart city data streams related to:

* Traffic Monitoring
* Energy Consumption
* Pollution Monitoring

The project performs:

* Real-time data streaming
* Distributed data processing
* Machine learning-based prediction
* Anomaly detection
* Live dashboard visualization

Technologies such as Kafka and Spark Streaming are integrated to create a scalable end-to-end streaming analytics pipeline.

## Technologies Used

- Python 3.9.13
- Apache Kafka 2.13-3.7.0
- Apache Spark 3.5.0
- Hadoop 3.3.6
- PySpark 3.5.0
- Streamlit
- Pandas
- NumPy
- Scikit-learn
- Matplotlib
- Seaborn

- ## Features

- Real-time Kafka streaming
- Spark Streaming analytics
- Machine learning prediction
- Traffic prediction
- Energy consumption prediction
- AQI prediction
- Anomaly detection
- Interactive Streamlit dashboard
- ETL pipeline implementation

- ## Architecture

- Data Generator
      ↓
Kafka Producer
      ↓
Kafka Topics
      ↓
Spark Streaming
      ↓
Machine Learning Prediction
      ↓
Anomaly Detection
      ↓
Streamlit Dashboard

## Machine Learning Models

- Linear Regression
- Decision Tree Regressor
- Random Forest Regressor
- Gradient Boosted Tree Regressor

- ## Project Execution Steps

1. Run generate_data.py
2. Execute data.ipynb
3. Execute model.ipynb
4. Start ZooKeeper
5. Start Kafka Broker
6. Create Kafka Topics
7. Run producer.py
8. Run spark_streaming.py
9. Run Streamlit dashboard

## Note:
The historical datasets used in this project were generated synthetically using the generate_data.py script. Due to file size limitations, full datasets are not included in this repository. Users can regenerate the datasets by running the data generation script.
