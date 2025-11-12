# **Real-Time Streaming ML Evaluation with CapyMOA & Kafka**

This project provides a complete, end-to-end framework for evaluating streaming machine learning models in real-time. It uses Apache Kafka to simulate high-throughput data streams (including concept drift) and CapyMOA to perform prequential (test-then-train) evaluation on multiple online classifiers and regressors.

The results are logged to CSV files and visualized live in an interactive Streamlit dashboard.

## **Features**

* **Real-Time Data Pipeline:** Uses Kafka producers to stream data to different topics.  
* **Parallel Evaluation:** Runs multiple evaluator consumers in parallel to process streams.  
* **Concept Drift Simulation:** Includes a dedicated producer to simulate both gradual and sudden concept drift.  
* **Prequential Evaluation:** Uses CapyMOA's `ClassificationEvaluator` and `ClassificationWindowedEvaluator` patterns (test-then-train).  
* **Multi-Model Comparison:** Evaluates and compares `HoeffdingTree`, `HoeffdingAdaptiveTree`, `NaiveBayes`, `AdaptiveRandomForestClassifier`, and more, simultaneously.  
* **Interactive Dashboard:** A Streamlit dashboard provides live plots for:  
  * Comparing all learners on a single metric (e.g., windowed accuracy).  
  * Deep-diving into all metrics for a single learner.  
  * A side-by-side comparison of model performance on the "Normal" vs. "Drift" stream.

## **Workflow**

The system runs two primary pipelines in parallel, and the dashboard reads the results from both.

1. **Preprocessing:** The `data_preprocessor.py` script cleans the raw `city_day.csv` and saves it as `data/cleaned_aqi_data.csv`.  
2. **Pipeline 1 (Normal Stream):**  
   * `producer.py` reads `cleaned_aqi_data.csv` and streams it to the `aqi-stream` Kafka topic.  
   * `evaluator_classification.py` consumes from `aqi-stream`, evaluates models, and logs results to `metrics/metrics_classification.csv`.  
3. **Pipeline 2 (Drift Stream):**  
   * `producer_drift.py` generates a synthetic stream with concept drift and sends it to the `aqi-drift-stream` topic.  
   * `evaluator_classification_drift.py` consumes from `aqi-drift-stream`, evaluates the *same* models, and logs results to `metrics/metrics_classification_drift.csv`.  
4. **Dashboard:**  
   * `dashboard.py` runs a web server, reads *both* CSV files in real-time, and provides interactive plots to compare all models and scenarios.

## **Project Structure**

bda\_project\_generic3/  
├── data/  
│   ├── city\_day.csv        \# \<-- You must place the raw dataset here  
│   └── .gitkeep  
├── kafka/  
│   ├── bin   
│   └── other files  
├── data\_logs/  
│   └── .gitkeep            \# \<-- Output CSVs will be saved here  
├── src/  
│   ├── data\_preprocessor.py  
│   ├── producer.py  
│   ├── producer\_drift.py  
│   ├── evaluator\_classification.py  
│   ├── evaluator\_classification\_drift.py  
│   ├── evaluator\_regression.py  
│   ├── dashboard.py  
│   └── plot\_metrics.py  
├── README.md  
└── requirements.txt

## **Setup and Installation (How to Begin)**

Follow these steps precisely to set up your environment.

### **1\. Prerequisites**

* **Python 3.9+**  
* **Git**  
* **Apache Kafka:** You must have a working Kafka installation.  
  * **Download:** [https://kafka.apache.org/downloads](https://kafka.apache.org/downloads)  
  * **Quickstart:** Follow the official Kafka quickstart to learn how to start Zookeeper and the Kafka Server.

### **2\. Clone the Repository**

git clone \<https://github.com/blackhat-coder21/bda_project_generic3.git>  
cd bda\_project\_generic3

### **3\. Set Up Kafka**

Before running any Python scripts, you **must** start Zookeeper and your Kafka Server.

* **Terminal A (Start Zookeeper):**  
  \# Navigate to your Kafka installation directory  
  *bin/zookeeper-server-start.sh config/zookeeper.properties*

* **Terminal B (Start Kafka Server):**  
  \# Navigate to your Kafka installation directory  
  *bin/kafka-server-start.sh config/server.properties*

### **4\. Create Kafka Topics**

Open a **new terminal** and create the two topics required for the pipelines.

* **Normal Stream Topic:**  
  *bin/kafka-topics.sh \--create \--topic aqi-stream \\*  
    *\--bootstrap-server localhost:9092 \--partitions 1 \--replication-factor 1*

* **Drift Stream Topic:**  
  *bin/kafka-topics.sh \--create \--topic aqi-drift-stream \\*  
    *\--bootstrap-server localhost:9092 \--partitions 1 \--replication-factor 1*

You can verify the topics were created with:  
*bin/kafka-topics.sh \--list \--bootstrap-server localhost:9092*

### 

### **5\. Create Virtual Environment (venv)**

It is crucial to use a virtual environment to manage dependencies.

\# From the project root (kafka\_capymoa\_project/)  
*python3 \-m venv venv*

**Activate the venv:**

* **On macOS / Linux:**  
  *source venv/bin/activate*

* **On Windows (Command Prompt):**  
  *.\\venv\\Scripts\\activate*

Your terminal prompt should now show (venv).

### **6\. Install Dependencies**

Install all required Python packages.

\# Make sure your venv is active  
*pip install \-r requirements.txt*

### **7\. Get the Dataset**

This project uses the **"Air Quality Data in India"** dataset.

1. Download the city\_day.csv file from [this Kaggle page](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).  
2. Place the city\_day.csv file inside the data/ directory.

## 

## **How to Run**

With Kafka and the venv running, you can now start the services. **Run each command in a new terminal window** from the **project root directory** (bda\_project\_generic3/).

1. **Terminal 1 (Run Once): Preprocess Data**  
   This script reads data/city\_day.csv and creates data/cleaned\_aqi\_data.csv.  
   *(venv) $ python3 src/data\_preprocessor.py*

2. **Terminal 2 (Producer): Normal Stream**  
   Starts streaming data/cleaned\_aqi\_data.csv to the aqi-stream topic.  
   *(venv) $ python3 src/producer.py*

3. **Terminal 3 (Producer): Drift Stream**  
   Starts streaming a synthetic, drifting stream to the aqi-drift-stream topic.  
   *(venv) $ python3 src/producer\_drift.py*

4. **Terminal 4 (Evaluator): Normal Classifier**  
   Consumes from aqi-stream and writes results to metrics/metrics\_classification.csv.  
   *(venv) $ python3 src/evaluator\_classification.py*

5. **Terminal 5 (Evaluator): Drift Classifier**  
   Consumes from aqi-drift-stream and writes results to metrics/metrics\_classification\_drift.csv.  
   *(venv) $ python3 src/evaluator\_classification\_drift.py*

6. **Terminal 6 (Evaluator): Regression**  
   Consumes from aqi-stream and writes results to metrics/metrics\_regression.csv.  
   *(venv) $ python3 src/evaluator\_regression.py*

7. **Terminal 7 (Dashboard): START HERE**  
   This is the main web interface. It will open a new tab in your browser.  
   *(venv) $ streamlit run src/dashboard.py*

We can now view the dashboard in your browser. Use the sidebar to switch between "Live Monitoring" (for the regression and normal classification tasks) and "Drift Comparison" (to see the powerful side-by-side plot).