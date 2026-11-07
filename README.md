# Data Engineer 2K27 🚀

A structured learning and hands-on preparation repository focused on modern Data Engineering, Big Data technologies, cloud data platforms, and Data Engineering System Design.

---

## 🎯 Objective

The objective of this repository is to develop expertise in building scalable, reliable and cost-efficient data engineering platforms.

This repository covers:

- Data Lakes and Lakehouse Architecture
- Apache Spark and PySpark
- Data Warehousing
- Data Modeling
- Data Engineering System Design
- Python Programming
- Azure Data Engineering
- Databricks
- Azure Data Lake Storage (ADLS)
- Azure Data Factory (ADF)
- AWS Data Engineering
- Amazon S3
- Apache Airflow
- Apache Kafka

---

## 📚 Learning Roadmap

### 01. Data Lake and Lakehouse Architecture

- Data Lake fundamentals
- Data Lake vs Data Warehouse vs Lakehouse
- Data Lake architecture
- Data ingestion architecture
- Landing, Raw, Curated and Serving zones
- Medallion Architecture
- Bronze, Silver and Gold layers
- Data Lake storage strategies
- Partitioning and file organization
- File formats: CSV, JSON, Avro, Parquet and ORC
- Compression techniques
- Small file problem
- File compaction
- Schema-on-read vs Schema-on-write
- Schema evolution
- Metadata management
- Data retention and lifecycle management
- Apache Iceberg
- Delta Lake
- Apache Hudi
- ACID transactions in Data Lakes
- Time travel and versioning
- Data Lake security and governance

### 02. Apache Spark and PySpark

**Spark Fundamentals**
- Introduction to Apache Spark
- Spark architecture
- Driver and Executors
- Cluster Managers
- Spark execution model
- Jobs, Stages and Tasks
- DAG Scheduler
- Task Scheduler
- Lazy Evaluation
- Transformations and Actions
- Narrow and Wide Transformations
- RDD vs DataFrame vs Dataset

**PySpark**
- PySpark architecture
- SparkSession and SparkContext
- DataFrame creation
- Schema definition
- DataFrame operations
- Column expressions
- Built-in functions
- Aggregations and Grouping
- Joins and Window Functions
- UDFs and Pandas UDFs
- Nested and complex data types
- JSON and Parquet processing
- Reading and writing data
- Handling nulls and duplicates

**Advanced Spark**
- Partitioning and Repartitioning
- Coalesce
- Shuffle operations
- Broadcast joins
- Sort-Merge joins
- Hash joins
- Data Skew
- Salting techniques
- Caching and Persistence
- Checkpointing
- Catalyst Optimizer
- Tungsten Execution Engine
- Adaptive Query Execution (AQE)
- Predicate Pushdown
- Partition Pruning
- Memory Management
- Executor tuning
- Spark UI and execution plans
- Performance optimization
- Structured Streaming
- Spark on Databricks

### 03. Data Warehousing

- Data Warehouse fundamentals
- OLTP vs OLAP
- Data Warehouse architecture
- Enterprise Data Warehouse
- Data Marts
- Staging and Integration layers
- Presentation layer
- Star Schema
- Snowflake Schema
- Fact Tables
- Dimension Tables
- Fact table grain
- Transaction, Snapshot and Accumulating Snapshot facts
- Slowly Changing Dimensions (SCD)
- SCD Type 0, 1, 2 and 3
- Surrogate and Natural Keys
- Conformed Dimensions
- Role-playing Dimensions
- Junk and Degenerate Dimensions
- Bridge Tables
- Late-arriving Facts and Dimensions
- Incremental Data Loading
- Data Warehouse Loading Strategies
- Data Vault fundamentals
- Query optimization
- Aggregations and Materialized Views
- Data Warehouse performance tuning
- Cloud Data Warehousing

### 04. Data Modeling

- Data Modeling fundamentals
- Conceptual Data Model
- Logical Data Model
- Physical Data Model
- Entity Relationship Diagrams
- Entities, Attributes and Relationships
- Primary and Foreign Keys
- Natural and Surrogate Keys
- Normalization
- Denormalization
- 1NF, 2NF, 3NF and BCNF
- Relational Data Modeling
- Dimensional Data Modeling
- Star and Snowflake Schema
- Fact and Dimension Design
- Slowly Changing Dimensions
- Data Vault Modeling
- Wide Table Design
- Nested and Semi-structured Data Modeling
- Schema Design for Data Lakes
- Schema Evolution
- Data Contracts
- Schema Versioning
- Data Model Documentation

### 05. Data Engineering System Design

**System Design Fundamentals**
- Requirements Gathering
- Functional and Non-functional Requirements
- High-Level Design (HLD)
- Low-Level Design (LLD)
- Architecture Diagrams
- Data Flow Diagrams
- Capacity Planning
- Throughput and Latency Estimation
- Storage and Compute Estimation
- Cost Estimation

**Distributed Systems**
- Distributed System Fundamentals
- Horizontal and Vertical Scaling
- Partitioning and Sharding
- Replication
- Fault Tolerance
- High Availability
- CAP Theorem
- Consistency Models
- Eventual Consistency
- Distributed Transactions
- Leader Election
- Load Balancing
- Backpressure
- Retry and Recovery Strategies

**Data Pipeline Architecture**
- Batch Processing Architecture
- Streaming Architecture
- ETL and ELT Architecture
- Incremental Data Pipeline
- CDC Architecture
- Lambda Architecture
- Kappa Architecture
- Medallion Architecture
- Event-driven Architecture
- Data Lakehouse Architecture
- Data Platform Architecture

**Reliability and Operations**
- Idempotency
- Deduplication
- Checkpointing
- Replay and Reprocessing
- Data Quality
- Source-to-Target Reconciliation
- Schema Evolution
- Data Lineage
- Monitoring and Observability
- Logging and Alerting
- Disaster Recovery
- RPO and RTO
- Security and Governance
- Performance and Cost Optimization

**System Design Case Studies**
- Design a Batch ETL Platform
- Design a Real-Time Streaming Platform
- Design a CDC Pipeline
- Design a Cloud Data Lake
- Design a Lakehouse Platform
- Design a Data Warehouse
- Design a Customer 360 Platform
- Design a Clickstream Analytics Platform
- Design an E-commerce Data Platform
- Design a Financial Reconciliation Pipeline
- Design a Data Quality Monitoring Platform
- Design a Scalable Multi-Tenant Data Platform

### 06. Python Programming for Data Engineering

- Python Fundamentals
- Data Types and Variables
- Lists, Tuples, Sets and Dictionaries
- Conditional Statements and Loops
- Functions and Lambda Functions
- Modules and Packages
- Object-Oriented Programming
- Exception Handling
- File Handling
- Iterators and Generators
- Decorators
- List and Dictionary Comprehensions
- Regular Expressions
- JSON and CSV Processing
- Working with APIs
- REST API Integration
- Requests Library
- Pandas
- NumPy
- Logging
- Unit Testing
- Pytest
- Multithreading
- Multiprocessing
- Async Programming
- Database and Cloud Connectivity
- Python Automation
- Writing reusable ETL frameworks

### 07. Azure Data Engineering

**Azure Data Lake Storage (ADLS Gen2)**
- ADLS Architecture
- Storage Accounts
- Containers and File Systems
- Hierarchical Namespace
- Blob Storage
- Access Control Lists (ACLs)
- RBAC
- Lifecycle Management
- Storage Tiers
- Security and Encryption
- Data Lake Folder Structure
- Data Ingestion and Storage Strategies

**Azure Data Factory (ADF)**
- ADF Architecture
- Linked Services
- Datasets
- Pipelines
- Activities
- Integration Runtime
- Copy Activity
- Mapping Data Flows
- Parameters and Variables
- Triggers
- Scheduling
- Tumbling Window Triggers
- ForEach and If Condition
- Lookup and Get Metadata
- Stored Procedure Activity
- Pipeline Dependencies
- Incremental Data Loading
- Metadata-driven Pipelines
- Error Handling
- Monitoring and Debugging
- CI/CD and Deployment

**Azure Databricks**
- Databricks Architecture
- Workspace and Compute
- Clusters and Cluster Policies
- Notebooks
- Jobs and Workflows
- Spark on Databricks
- Delta Lake
- Delta Tables
- Delta Live Tables / Lakeflow concepts
- Unity Catalog
- Managed and External Tables
- Schema Enforcement
- Schema Evolution
- Time Travel
- MERGE Operations
- Change Data Feed
- Auto Loader
- Structured Streaming
- Photon Engine
- Cluster Optimization
- Databricks Workflows
- Security and Governance
- Performance Optimization

### 08. AWS Data Engineering

**Amazon S3**
- S3 Architecture
- Buckets and Objects
- Storage Classes
- Versioning
- Lifecycle Policies
- Replication
- Encryption
- Bucket Policies
- IAM Access
- Event Notifications
- Data Lake Architecture on S3
- Partitioning and File Formats
- Cost Optimization

**AWS Data Engineering Services**
- AWS Glue
- Glue Data Catalog
- Glue Crawlers
- Glue ETL Jobs
- AWS EMR
- Amazon Redshift
- AWS Database Migration Service (DMS)
- Amazon Kinesis
- AWS Lambda
- AWS Step Functions
- Amazon CloudWatch
- AWS IAM
- AWS Lake Formation
- EventBridge
- AWS Data Lake Architecture

### 09. Apache Airflow

- Workflow Orchestration Fundamentals
- Airflow Architecture
- DAGs
- Tasks and Dependencies
- Operators
- Sensors
- Hooks
- Connections
- Variables
- XCom
- Scheduling
- Timetables
- Task Groups
- Branching
- Dynamic Task Mapping
- Retries and Timeouts
- Catchup and Backfill
- Executors
- Pools and Concurrency
- Idempotent Tasks
- Error Handling
- Logging and Monitoring
- Secrets Management
- Airflow Deployment
- High Availability
- DAG Testing
- Production Best Practices

### 10. Apache Kafka

- Messaging Fundamentals
- Kafka Architecture
- Brokers
- Topics and Partitions
- Producers
- Consumers
- Consumer Groups
- Offsets
- Replication Factor
- Leader and Follower
- In-Sync Replicas (ISR)
- Partition Key Selection
- Producer Acknowledgements
- Idempotent Producers
- Kafka Transactions
- Consumer Rebalancing
- Consumer Lag
- Retention and Log Compaction
- Schema Registry
- Avro, JSON and Protobuf
- Kafka Connect
- Source and Sink Connectors
- Kafka Streams
- Dead Letter Topics
- Retry Strategies
- Kafka Security
- Monitoring and Performance Tuning

---

## 🗂️ Repository Structure

```text
Data_Engineer_2K27/
│
├── 01_Data_Lake_Lakehouse/
│
├── 02_Apache_Spark_PySpark/
│   ├── Spark_Fundamentals/
│   ├── PySpark/
│   ├── Spark_SQL/
│   ├── Structured_Streaming/
│   └── Performance_Tuning/
│
├── 03_Data_Warehousing/
│
├── 04_Data_Modeling/
│
├── 05_System_Design/
│   ├── Fundamentals/
│   ├── Distributed_Systems/
│   ├── Batch_Architecture/
│   ├── Streaming_Architecture/
│   ├── CDC_Architecture/
│   └── Case_Studies/
│
├── 06_Python/
│   ├── Fundamentals/
│   ├── Advanced_Python/
│   ├── Pandas/
│   ├── NumPy/
│   └── Automation/
│
├── 07_Azure_Data_Engineering/
│   ├── ADLS/
│   ├── ADF/
│   └── Databricks/
│
├── 08_AWS_Data_Engineering/
│   ├── S3/
│   ├── Glue/
│   ├── EMR/
│   ├── Redshift/
│   └── DMS/
│
├── 09_Apache_Airflow/
│
├── 10_Apache_Kafka/
│
├── 11_Projects/
│   ├── Batch_ETL/
│   ├── CDC_Pipeline/
│   ├── Streaming_Pipeline/
│   ├── Lakehouse/
│   └── End_To_End_Data_Platform/
│
└── 12_Interview_Preparation/
    ├── Spark_PySpark/
    ├── Data_Warehousing/
    ├── System_Design/
    ├── Azure/
    ├── AWS/
    ├── Airflow/
    └── Kafka/
```

---

## 📅 Preparation Strategy

| Phase | Focus Area |
|---|---|
| 01 | Data Lake and Data Engineering Fundamentals |
| 02 | Python Programming |
| 03 | Apache Spark and PySpark |
| 04 | Data Warehousing and Data Modeling |
| 05 | Azure: ADLS, ADF and Databricks |
| 06 | AWS: S3 and Data Engineering Services |
| 07 | Apache Airflow and Kafka |
| 08 | Data Engineering System Design |
| 09 | End-to-End Projects and Interview Preparation |

---

**Created and maintained by Shubham Panchal**

*Data Engineer 2K27*
