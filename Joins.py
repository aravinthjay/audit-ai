import pandas as pd
import sqlite3

#Explanation why SRV-03 Excluded

# due to inner join SRV-03 is missing

# Create in-memory SQLite database
conn = sqlite3.connect(':memory:')

# Data setup
servers_inventory = {
    "Host_ID": ["SRV-01", "SRV-02", "SRV-03"],
    "Role": ["Web Front", "API Gateway", "Database Replica"]
}

live_interfaces = {
    "Interface_ID": ["eth0", "eth1"],
    "Mapped_Host": ["SRV-01", "SRV-02"],
    "IP_Address": ["10.0.0.4", "10.0.0.9"]
}

# Convert to DataFrames
df_srv = pd.DataFrame(servers_inventory)
df_inf = pd.DataFrame(live_interfaces)

# Load into SQL tables
df_srv.to_sql('Servers', conn, index=False, if_exists='replace')
df_inf.to_sql('Interfaces', conn, index=False, if_exists='replace')


#Faulty INNER JOIN Query
faulty_query = """
SELECT s.Host_ID, s.Role, i.Interface_ID, i.IP_Address
FROM Servers s
INNER JOIN Interfaces i
ON s.Host_ID = i.Mapped_Host;
"""

print("\n--- INNER JOIN Result (SRV-03 Missing) ---")
df_faulty = pd.read_sql_query(faulty_query, conn)
print(df_faulty)


# Correct LEFT JOIN 
correct_query = """
SELECT s.Host_ID, s.Role, i.Interface_ID, i.IP_Address
FROM Servers s
LEFT JOIN Interfaces i
ON s.Host_ID = i.Mapped_Host;
"""

print("\n--- LEFT JOIN Result (All Servers Included) ---")
df_correct = pd.read_sql_query(correct_query, conn)
print(df_correct)

# Close connection
conn.close()
