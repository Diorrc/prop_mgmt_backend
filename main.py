from fastapi import FastAPI, Depends, HTTPException, status
from google.cloud import bigquery
from typing import Literal
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from pydantic import BaseModel
app = FastAPI()

PROJECT_ID = "project-fdc64e01-d38d-4013-b83"
DATASET = "property_mgmt"


# ---------------------------------------------------------------------------
# Dependency: BigQuery client
# ---------------------------------------------------------------------------

def get_bq_client():
    client = bigquery.Client()
    try:
        yield client
    finally:
        client.close()


# ── Configuration ──────────────────────────────────────────────────────────────
# Replace these two values with your actual GCP project ID and dataset name
# before running the app.{project-fdc64e01-d38d-4013-b83} = "project-fdc64e01-d38d-4013-b83"


TABLE = f"{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.properties"

# ── BigQuery client ────────────────────────────────────────────────────────────
client = bigquery.Client(project="project-fdc64e01-d38d-4013-b83")


# CORS middleware tells the browser which cross-origin requests are allowed.
# Allowing all origins ("*") is fine for a classroom demo but should be
# restricted to specific domains in a real production application.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # accept requests from any origin
    allow_methods=["GET", "POST"],
    allow_headers=["*"],       # accept any request headers
)

#Error Message 

app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail
        }
    )


# ── Pydantic model ─────────────────────────────────────────────────────────────
# Pydantic validates incoming JSON automatically. If a request body is missing
# a required field or has the wrong type, FastAPI returns a 422 error before
# our code ever runs.
#
# Literal restricts `category` to exactly three allowed string values; any
# other value is rejected at validation time.
class PropertyCreate(BaseModel):
    name: str
    address: str
    units: int


class IncomeCreate(BaseModel):
    amount: float
    description: str
class ExpenseCreate(BaseModel):
    amount: float
    description: str



# ── Endpoints ──────────────────────────────────────────────────────────────────
properties = []

@app.post("/properties")
def add_property(property: PropertyCreate, bq: bigquery.Client = Depends(get_bq_client)):
    properties.append(property.dict())  # just save to list for now
    return {"message": "Property added!", "property": property}

@app.get("/properties")
def get_properties(bq: bigquery.Client = Depends(get_bq_client)):
    """
    Returns all properties in the database.
    """
    query = f"""
        SELECT
            property_id,
            name,
            address,
            city,
            state,
            postal_code,
            property_type,
            tenant_name,
            monthly_rent
        FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.properties`
        ORDER BY property_id
    """

    try:
        results = bq.query(query).result()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

    properties = [dict(row) for row in results]
    return properties

@app.get("/properties/{property_id}")
def get_propety(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """Return a single property, or 404 if not found."""
    query = f"""
        SELECT *
        FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.properties`
        WHERE property_id = {property_id}
        LIMIT 1
    """
    rows = list(bq.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail="Property not found")
    return dict(rows[0])
@app.get("/income/{property_id}", status_code=200)
def return_income(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """Return an existing Income record."""
    query = f"""
        SELECT *
        FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.income`
        WHERE property_id = {property_id}
    """
    results = bq.query(query).result()
    return [dict(row) for row in results]


@app.post("/income/{property_id}")
def add_income(property_id: int, body: IncomeCreate, bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        INSERT INTO `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.income`
        (property_id, amount, description, created_at)
        VALUES (
            {property_id},
            {body.amount},
            '{body.description}',
            CURRENT_TIMESTAMP()
        )
    """
    bq.query(query).result()

    return {"message": "Income added successfully"}

@app.get("/expenses/{property_id}", status_code=201)
def get_expenses(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    """Return an existing Expense record."""
    query = f"""
        SELECT *
        FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.expenses`
        WHERE property_id = {property_id}   
        """
    results = bq.query(query).result()
    return [dict(row) for row in results]   

@app.post("/expenses/{property_id}")
def add_expense(property_id: int, body: ExpenseCreate, bq: bigquery.Client = Depends(get_bq_client)):   
    query= f"""
        INSERT INTO `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.expenses`
        (property_id, amount, description, created_at)
        VALUES (
            {property_id}, {body.amount}, '{body.description}', CURRENT_TIMESTAMP()
        )
    """
    bq.query(query).result()
    return {"message": "Expense added successfully"}

@app.delete("/expenses/{property_id}")
def delete_expense(property_id: int, expense_id: int, bq: bigquery.Client = Depends(get_bq_client)):   
    query = f"""
        DELETE FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.expenses`
        WHERE property_id = {property_id} AND expense_id = {expense_id}
    """
    bq.query(query).result()
    return {"message": "Expense deleted successfully"}

@app.delete("/income/{property_id}")
def delete_income(property_id: int, income_id: int, bq: bigquery.Client = Depends(get_bq_client)):  
    query = f"""
        DELETE FROM `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.income`
        WHERE property_id = {property_id} AND income_id = {income_id}
    """
    bq.query(query).result()
    return {"message": "Income deleted successfully"}  


@app.get("/profit/{property_id}")
def get_profit(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    query = f"""
        SELECT
            SUM(income.amount) - SUM(expenses.amount) AS profit
        FROM
            `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.income` AS income
        JOIN
            `{"project-fdc64e01-d38d-4013-b83"}.{"property_mgmt"}.expenses` AS expenses
        ON
            income.property_id = expenses.property_id
        WHERE
            income.property_id = {property_id}
    """
    rows= list(bq.query(query).result())
    return dict(rows[0]) if rows else {"profit": 0}

@app.get("/summary/{property_id}")
def property_summary(property_id: int, bq: bigquery.Client = Depends(get_bq_client)):
    query = """
    SELECT 
        p.property_id,
        p.name,
        p.address,
        i.total_income,
        e.total_expenses,
        COALESCE(i.total_income, 0) - COALESCE(e.total_expenses, 0) AS profit
    FROM 
        `project-fdc64e01-d38d-4013-b83.property_mgmt.properties` AS p
    LEFT JOIN `project-fdc64e01-d38d-4013-b83.property_mgmt.income` i USING(property_id)
    LEFT JOIN `project-fdc64e01-d38d-4013-b83.property_mgmt.expenses` e USING(property_id)
    WHERE 
        p.property_id = @property_id
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("property_id", "INT64", property_id)
        ]
    )

    rows = list(bq.query(query, job_config=job_config).result())

    if not rows:
        raise HTTPException(status_code=404, detail="Property not found")

    return dict(rows[0])


