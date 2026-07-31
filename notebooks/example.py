# Databricks notebook source
# COMMAND ----------

print("Hello from db_works, running on Databricks Free Edition serverless compute!")

# COMMAND ----------

df = spark.range(10)
df.show()
