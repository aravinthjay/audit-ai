import pandas as pd
import sqlite3

# -------------------------------
# STEP 0: Create initial dataset (0NF)
# -------------------------------

conn_challenge = sqlite3.connect(':memory:')

challenge_data = {
    "Visit_ID": [5001, 5001, 5002, 5003],
    "Student_ID": [101, 101, 102, 104],
    "Student_Name": ["Alice", "Alice", "Bob", "David"],
    "Doctor_ID": ["DOC_XYZ", "DOC_XYZ", "DOC_ABC", "DOC_XYZ"],
    "Doctor_Name": ["Dr. Evans", "Dr. Evans", "Dr. Green", "Dr. Evans"],
    "Doctor_Clinic": ["General Medicine", "General Medicine", "Sports Med", "General Medicine"],
    "Prescriptions": ["Amoxicillin, Ibuprofen", "Amoxicillin, Ibuprofen", "Bandages", "Vitamin D"]
}

df_0nf = pd.DataFrame(challenge_data)
df_0nf.to_sql('Patient_Visits_0NF', conn_challenge, index=False, if_exists='replace')

print("---- 0NF TABLE ----")
print(df_0nf)


# -------------------------------
# STEP 1: Convert to 1NF
# -------------------------------

df_1nf = df_0nf.copy()

# Split prescriptions into lists
df_1nf['Prescriptions'] = df_1nf['Prescriptions'].str.split(', ')

# Convert list values into separate rows
df_1nf = df_1nf.explode('Prescriptions')

df_1nf.reset_index(drop=True, inplace=True)

df_1nf.to_sql('Patient_Visits_1NF', conn_challenge, index=False, if_exists='replace')

print("\n---- 1NF TABLE ----")
print(df_1nf)


# -------------------------------
# STEP 2: Convert to 2NF
# Remove partial dependency (Student_Name depends only on Student_ID)
# -------------------------------

# Student Table
student_df = df_1nf[['Student_ID', 'Student_Name']].drop_duplicates()

# Main visit table without student name
visit_df = df_1nf.drop(columns=['Student_Name'])

student_df.to_sql('Students', conn_challenge, index=False, if_exists='replace')
visit_df.to_sql('Visits_2NF', conn_challenge, index=False, if_exists='replace')

print("\n---- STUDENT TABLE (2NF) ----")
print(student_df)

print("\n---- VISIT TABLE (2NF) ----")
print(visit_df)


# -------------------------------
# STEP 3: Convert to 3NF
# Remove transitive dependency (Doctor_Clinic depends on Doctor_ID)
# -------------------------------

# Doctor Table
doctor_df = df_1nf[['Doctor_ID', 'Doctor_Name', 'Doctor_Clinic']].drop_duplicates()

# Final visit table without doctor details
final_visit_df = visit_df.drop(columns=['Doctor_Name', 'Doctor_Clinic'])

doctor_df.to_sql('Doctors', conn_challenge, index=False, if_exists='replace')
final_visit_df.to_sql('Visits_3NF', conn_challenge, index=False, if_exists='replace')

print("\n---- DOCTOR TABLE (3NF) ----")
print(doctor_df)

print("\n---- FINAL VISIT TABLE (3NF) ----")
print(final_visit_df)


# -------------------------------
# FINAL STRUCTURE (3NF)
# -------------------------------

print("\n✅ FINAL NORMALIZED TABLES:")
print("\n1. Students")
print(student_df)

print("\n2. Doctors")
print(doctor_df)

print("\n3. Visits")
print(final_visit_df)