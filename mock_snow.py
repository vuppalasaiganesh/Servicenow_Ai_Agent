from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/incidents', methods=['GET'])
def get_incidents():
    incidents = {
        "result": [
            {
                "number": "INC1001",
                "short_description": "Data pipeline failure in production environment",
                "sys_id": "de-001"
            },
            {
                "number": "INC1002",
                "short_description": "ETL job timing out during nightly batch process",
                "sys_id": "de-002"
            },
            {
                "number": "INC1003",
                "short_description": "Data warehouse sync failed between Redshift and S3",
                "sys_id": "de-003"
            },
            {
                "number": "INC1004",
                "short_description": "Schema mismatch during BigQuery migration",
                "sys_id": "mig-001"
            },
            {
                "number": "INC1005",
                "short_description": "Null values detected post PostgreSQL to Snowflake migration",
                "sys_id": "mig-002"
            },
            {
                "number": "INC1006",
                "short_description": "Broken data lineage after Airflow DAG deployment",
                "sys_id": "de-004"
            },
            {
                "number": "INC1007",
                "short_description": "Kafka consumer lagging behind expected offsets",
                "sys_id": "de-005"
            },
            {
                "number": "INC1008",
                "short_description": "Data duplication issue after MongoDB to DynamoDB migration",
                "sys_id": "mig-003"
            }
        ]
    }
    return jsonify(incidents)

if __name__ == '__main__':
    app.run(debug=False)
