
import os
from dotenv import load_dotenv
import asyncio
import requests
import csv
import pandas as pd
from bamboohrclient import BambooHRClient,get_timesheets
from datetime import datetime,timedelta



load_dotenv()
def normalize_hours(x):
    return round(float(x), 2)

def count_holiday_days(client : BambooHRClient, week1_start, week1_end, week2_start, week2_end):
    days_off = client.get("time_off/whos_out",params={
        "start" : week1_start,
        "end": week2_end
    })
    week1_total = 0
    week2_total = 0
    holidays = [
    item for item in days_off
    if item.get("type") == "holiday"
    ]
    
    for h in holidays:
        h_start = datetime.strptime(h["start"], "%Y-%m-%d")
        h_end = datetime.strptime(h["end"], "%Y-%m-%d")

        # holidays in week 1
        overlap_start = max(week1_start, h_start)
        overlap_end = min(week1_end, h_end)

        if overlap_start <= overlap_end:
            week1_total += (overlap_end - overlap_start).days + 1

       # holidays in week 2
        overlap_start = max(week2_start, h_start)
        overlap_end = min(week2_end, h_end)

        if overlap_start <= overlap_end:
            week2_total += (overlap_end - overlap_start).days + 1


    return week1_total,week2_total
def count_pto_hours(client: BambooHRClient, employee_id, week1_start, week1_end, week2_start, week2_end):

    pto_requests = client.get("time_off/requests",params={
        "employeeId" : employee_id,
        "start" : week1_start.strftime("%Y-%m-%d"),
        "end": week2_end.strftime("%Y-%m-%d")
    })
    week1_pto = 0
    week2_pto = 0
    for pto_request in pto_requests:
        if(pto_request["status"]["status"] == "approved"):
            for date,value in pto_request["dates"].items():
                if week1_start <= datetime.strptime(date, "%Y-%m-%d") <= week1_end:
                    week1_pto += float(value)
                elif week2_start <= datetime.strptime(date, "%Y-%m-%d") <= week2_end:
                    week2_pto+= float(value)
    return week1_pto,week2_pto
    

def main():
    bamboo_client = BambooHRClient("BEAM",os.environ.get("API_KEY"))
   

    name_file = input("Enter the Payroll Hours Detail file name WITH .csv: ") 
    name_file2 =  input("Enter the Approved Hours report file name WITH .csv: ") 
    while True:
        try:
            start =  input("Enter a start date (YYYY-MM-DD): ") 
            end =  input("Enter an end date (YYYY-MM-DD): ") 
            
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            if (end_dt - start_dt == timedelta(days=13)):
                break
            else:
                print("Invalid date range, please ensure the date range is 14 days")

        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD.")
    week1_start = start_dt
    week1_end = start_dt +timedelta(days=6)
    week2_start = end_dt- timedelta(days=6)
    week2_end = end_dt
    week1_pto,week2_pto = 0,0
    df = pd.read_csv(name_file)
    df = df[df['Total Hours']!=0]
    if "OT" not in df.columns:
        df["OT"] = 0
    df["Employee Number"] = pd.to_numeric(df["Employee Number"], errors="coerce") + 108
    df["REG"] = pd.to_numeric(df.get("REG", 0), errors="coerce").fillna(0)
    df["OT"] = pd.to_numeric(df.get("OT", 0), errors="coerce").fillna(0)
    df["Time Off"] = pd.to_numeric(df.get("Time Off", 0), errors="coerce").fillna(0)
    rows = []
    if 'Holiday' in df.columns:
        week1_holiday_count,week2_holiday_count = count_holiday_days(client=bamboo_client,week1_start=week1_start,week1_end=week1_end,week2_start=week2_start,week2_end=week2_end)

    for _, row in df.iterrows():
        emp_id = row["Employee Number"] 
        
        # split name safely
        name_parts = str(row["Name"]).split(",", 1)
        first_name = name_parts[1]
        last_name = name_parts[0] if len(name_parts) > 1 else ""
        print("Processing ",first_name,last_name)
        if row["Time Off"] != 0:

            week1_pto,week2_pto = count_pto_hours(client=bamboo_client,employee_id=emp_id,week1_start=week1_start,week1_end=week1_end,week2_start=week2_start,week2_end=week2_end)
            if(row["Time Off"]!=week1_pto+week2_pto):
                print("Error Time off incorrect")
        
        # BambooHR enrichment
        emp = bamboo_client.get(
            f"employees/{emp_id}",
            params={
                "fields": "firstName,lastName,homeEmail",
                "onlyCurrent": "true"
            }
        )
        week1_reg_hours = 0
        week2_reg_hours = 0
        week1_ot_hours = 0
        week2_ot_hours = 0
        # load second file 
        df_two = pd.read_csv(name_file2)
        df_two = df_two[df_two['Date'].notna()]
        df_two['Date'] = pd.to_datetime(df_two['Date'])
        df_two["Reg Hours"] = pd.to_numeric(df_two["Reg Hours"], errors="coerce").fillna(0)
        if "OT Hours" in df_two.columns:
            df_two["OT Hours"] = pd.to_numeric(df_two["OT Hours"], errors="coerce").fillna(0)
        
        df_employee_timesheets = df_two[df_two['Employee Number']== row["Employee Number"]-108]


        for _,row2 in df_employee_timesheets.iterrows():
            row_hours = row2["Reg Hours"]
            ot_hours = row2["OT Hours"]
            if  week1_start<= row2["Date"] <= week1_end:
                week1_ot_hours+=ot_hours
                week1_reg_hours+=row_hours
            elif week2_start<= row2["Date"] <= week2_end:
                 week2_reg_hours+=row_hours
                 week2_ot_hours+=ot_hours
        
        if 'Holiday' in df and row['Holiday']!=0:
            week1_reg_hours-=(7.5 *week1_holiday_count)
            week2_reg_hours-=(7.5 *week2_holiday_count)
            week1_pto+=(7.5 *week1_holiday_count)
            week2_pto+=(7.5 *week2_holiday_count)
        if 'Holiday' in df.columns and normalize_hours(week1_reg_hours+week2_reg_hours)!=normalize_hours(row["REG"]) and normalize_hours(week1_pto+week2_pto)==normalize_hours(row["Time Off"]+row["Holiday"]):
            print("You did something wrong hours aren't the same for",first_name,last_name)
            print("Week1's Hours:",normalize_hours(week1_reg_hours),"Week2's Hours:",normalize_hours(week2_reg_hours))
            print("Total Hours: ",normalize_hours(week1_reg_hours+week2_reg_hours),row["REG"],"OT Hours:", row["OT"] )
            print("Holiday Hours:",row["Holiday"],"PTO Hours:",row["Time Off"])
            print("PTO Column New: ",normalize_hours(week1_pto+week2_pto) )
        elif 'Holiday' not in  df.columns and normalize_hours(week1_reg_hours+week2_reg_hours)!=normalize_hours(row["REG"]):
            print("You did something wrong hours aren't the same for",first_name,last_name)
            print("Week1's Hours:",normalize_hours(week2_reg_hours),"Week2's Hours:",normalize_hours(week2_reg_hours))
            print("Total Hours: ",normalize_hours(week1_reg_hours+week2_reg_hours),row["REG"],"OT Hours:", row["OT"] )
            
        
        rows.append({
            "First Name": first_name,
            "Last Name": last_name,
            "Work Email": emp.get("homeEmail"),
            "Start Date": week1_start,
            "End Date": week1_end,
            "Regular Hours": normalize_hours(week1_reg_hours),
            "Overtime Hours": normalize_hours(week1_ot_hours),
            "Paid Time Off Hours": normalize_hours(week1_pto)
        })
        rows.append({
            "First Name": first_name,
            "Last Name": last_name,
            "Work Email": emp.get("homeEmail"),
            "Start Date": week2_start,
            "End Date": week2_end,
            "Regular Hours": normalize_hours(week2_reg_hours),
            "Overtime Hours": normalize_hours(week2_ot_hours),
            "Paid Time Off Hours": normalize_hours(week2_pto)
        })
    
    transformed_df = pd.DataFrame(rows)
    print(transformed_df)

    transformed_df.to_csv("example_output.csv", index=False)

if __name__ == "__main__":
    main()